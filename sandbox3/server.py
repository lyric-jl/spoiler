# sandbox3/server.py
"""操作台本地服务（stdlib，零第三方依赖；名单制多人原生底座）。
路由：GET / 页面；GET /api/state 状态；GET /api/events?since=N 事件流（轮询）；
GET /api/batch_latest 最新批聚合；GET /api/cases 样本+预备案例；GET /api/prep_state 备料进度；
POST /api/run 开拍；/api/chat 场景共创；/api/crystallize 共创结晶入库（走 BANK.add_custom）；
/api/import_cast 导入整套名单；/api/jd 暂存自由文本 JD；
/api/prepare JD 驱动（mode=live 现做整条前段→换名单+场景+画像；mode=load 秒加载磁盘案例）。
注：JD 驱动已落地（作者 2026-06-09 拍翻"JD 只入档不驱动"旧口径）；/api/jd 自由文本框为遗留入口。
用法：python -m sandbox3.server [--port 8781]

依赖注入边界（非 mock）：模块级 LLM / CAST / BANK 是可替换的全局对象——
测试以 `sandbox3.server.LLM = FakeLLM(...)` 注入；产品路径唯一=DeepSeek live。
并发纪律：单进程一个 BANK 实例；/api/crystallize 走 BANK.add_custom 必须在 LOCK 内
（add_custom 的 id 生成依赖内存计数，双实例/并发必撞号）。"""
from __future__ import annotations
import argparse, json, pathlib, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import config
from . import prepare
from .cast import Cast, CastError
from .engine import run_simulation
from .llm import DeepSeekClient, LLMError
from .prompts import sm as PS
from .scenes import SceneBank
from .trace import save_run
from .pages.theater import PAGE

# ---- 可替换的模块级全局（依赖注入口；推演中 CAST 不可换） ----
LLM = DeepSeekClient()
CAST = Cast.load_default()
BANK = SceneBank()

# jd_text=驱动场景导演二次贴岗 + 落盘记 JD（JD 驱动后启用）；
# prep=备料进度/产物（JD→画像+名单+场景的前段管线状态）。
STATE = {"running": False, "events": [], "jd": "", "jd_text": "",
         "prep": {"running": False, "log": [], "ready": False, "error": None,
                  "portrait": None, "meta": None}}
LOCK = threading.Lock()


def _fresh_prep() -> dict:
    return {"running": False, "log": [], "ready": False, "error": None,
            "portrait": None, "meta": None}


def _emit(event: dict) -> None:
    with LOCK:
        STATE["events"].append(event)


def _run_thread(cfg: dict) -> None:
    try:
        # JD 驱动（作者 2026-06-09 拍翻"只入档不驱动"旧口径）：备料时存的 jd_text
        # 喂场景导演二次贴岗，也随轨迹落盘。未走 JD 驱动时 jd_text="" 退回旧行为。
        with LOCK:
            jd = STATE["jd_text"] or STATE["jd"]
        trace = run_simulation(cast=CAST, llm=LLM, bank=BANK,
                               n_scenes=cfg["scenes"], start_tp=cfg["start"],
                               seed=cfg.get("seed"), jd=jd, emit=_emit)
        out_dir = save_run(trace, jd=jd)
        _emit({"type": "saved", "path": str(out_dir)})
    except Exception as e:                                   # noqa: BLE001 直播必须把错误亮给页面
        _emit({"type": "error", "text": f"{type(e).__name__}: {e}"})
    finally:
        with LOCK:
            STATE["running"] = False


def _prep_log(msg: str) -> None:
    with LOCK:
        STATE["prep"]["log"].append(msg)


def _apply_prepared(result: dict) -> None:
    """把备料/秒加载的产物装进运行态：换名单 CAST、换场景库 BANK、记 jd_text + 画像。"""
    global CAST, BANK
    new_cast = Cast.from_cards(result["cast"])
    new_bank = SceneBank(preset_path=pathlib.Path(result["scene_bank_path"]),
                         custom_path=pathlib.Path("__no_custom_for_case__"))
    with LOCK:
        CAST = new_cast
        BANK = new_bank
        STATE["jd_text"] = result["jd_text"]
        STATE["jd"] = result["jd_text"]
        STATE["prep"]["portrait"] = result["portrait"]
        STATE["prep"]["meta"] = result["meta"]
        STATE["prep"]["ready"] = True
        STATE["prep"]["error"] = None        # 装配成功＝清掉上一轮可能残留的旧红旗


def _prep_thread(jd_name: str, cv_name: str) -> None:
    try:
        result = prepare.prepare_case(LLM, jd_name, cv_name, progress=_prep_log)
        _apply_prepared(result)
        _prep_log("✓ 名单与场景已就位，可开始推演")
    except Exception as e:                                   # noqa: BLE001 备料失败必须亮到页面
        with LOCK:
            STATE["prep"]["error"] = f"{type(e).__name__}: {e}"
            STATE["prep"]["log"].append(f"✗ 备料失败：{type(e).__name__}: {e}")
    finally:
        with LOCK:
            STATE["prep"]["running"] = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):                       # 安静点，错误仍走 stderr
        pass

    # ---- helpers ----
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    # ---- GET ----
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/api/state":
            with LOCK:
                self._json({"running": STATE["running"], "n_events": len(STATE["events"]),
                            "cast": [{"name": c.name, "kind": c.kind, "role": c.role}
                                     for c in CAST.members()],
                            "candidate": CAST.candidate().name,
                            "scenes": [{"id": t["id"], "title": t["title"],
                                        "category": t["category"]} for t in BANK.all()],
                            "jd_len": len(STATE["jd"]),
                            "prep_running": STATE["prep"]["running"],
                            "prep_ready": STATE["prep"]["ready"],
                            "case": STATE["prep"]["meta"]})
        elif u.path == "/api/cases":
            try:
                self._json({"samples": prepare.available_samples(),
                            "prepared": prepare.list_prepared()})
            except OSError as e:
                self._json({"error": f"读样本/案例失败：{e}"}, 500)
        elif u.path == "/api/prep_state":
            with LOCK:
                p = STATE["prep"]
                self._json({"running": p["running"], "log": list(p["log"]),
                            "ready": p["ready"], "error": p["error"],
                            "portrait": p["portrait"], "meta": p["meta"]})
        elif u.path == "/api/events":
            since = int((parse_qs(u.query).get("since") or ["0"])[0])
            with LOCK:
                self._json({"events": STATE["events"][since:]})
        elif u.path == "/api/batch_latest":
            batches = sorted(config.OUTPUT_DIR.glob("batch_*/aggregate.json"))
            if not batches:
                self._json({"empty": True})
            else:
                try:
                    self._json(json.loads(batches[-1].read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError) as e:
                    self._json({"error": f"聚合文件读取失败：{e}"}, 500)
        else:
            self._json({"error": "not found"}, 404)

    # ---- POST ----
    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = self._body()
        except (ValueError, json.JSONDecodeError) as e:
            self._json({"error": f"请求体不是合法 JSON：{e}"}, 400)
            return
        try:
            if u.path == "/api/run":
                with LOCK:
                    if STATE["running"]:
                        self._json({"error": "已有推演在跑，等它收官"}, 409)
                        return
                    STATE["running"] = True
                    STATE["events"] = []
                cfg = {"scenes": max(1, min(6, int(body.get("scenes") or 2))),
                       "start": str(body.get("start") or "C1-01"),
                       "seed": body.get("seed")}
                BANK.by_id(cfg["start"])                      # 不存在则抛 KeyError
                threading.Thread(target=_run_thread, args=(cfg,), daemon=True).start()
                self._json({"ok": True})
            elif u.path == "/api/chat":
                msgs = body.get("messages") or []
                dialog = "\n".join(f"{'作者' if m.get('role') == 'user' else '助手'}：{m.get('content', '')}"
                                   for m in msgs[-12:])
                reply = LLM.complete(PS.COCREATE_SYSTEM, dialog,
                                     json_mode=False, temperature=0.8, max_tokens=400)
                self._json({"reply": reply})
            elif u.path == "/api/crystallize":
                msgs = body.get("messages") or []
                dialog = "\n".join(f"{'作者' if m.get('role') == 'user' else '助手'}：{m.get('content', '')}"
                                   for m in msgs)
                out = LLM.complete_json(PS.CRYSTALLIZE_SYSTEM, dialog, max_tokens=500)
                with LOCK:
                    scene = BANK.add_custom(out)
                self._json({"scene": scene})
            elif u.path == "/api/import_cast":
                with LOCK:
                    if STATE["running"]:
                        self._json({"error": "推演进行中不能换名单"}, 409)
                        return
                    global CAST
                    new_cast = Cast.from_cards(body.get("cast") or [])
                    CAST = new_cast
                self._json({"cast": [{"name": c.name, "kind": c.kind, "role": c.role}
                                     for c in CAST.members()],
                            "candidate": CAST.candidate().name})
            elif u.path == "/api/jd":
                with LOCK:
                    STATE["jd"] = str(body.get("text") or "")
                self._json({"ok": True})
            elif u.path == "/api/prepare":
                self._handle_prepare(body)
            else:
                self._json({"error": "not found"}, 404)
        except CastError as e:
            self._json({"error": str(e)}, 400)
        except FileNotFoundError as e:
            self._json({"error": str(e)}, 404)
        except (KeyError, ValueError, LLMError) as e:
            self._json({"error": str(e)}, 400)

    def _handle_prepare(self, body: dict) -> None:
        """JD 驱动：mode=load 秒加载磁盘案例（同步、不调 LLM）；mode=live 后台现做整条前段。"""
        with LOCK:
            if STATE["running"]:
                self._json({"error": "推演进行中，先等它收官再备料"}, 409)
                return
            if STATE["prep"]["running"]:
                self._json({"error": "备料已在进行，别重复点"}, 409)
                return
        mode = str(body.get("mode") or "live")
        jd_name = str(body.get("jd") or "").strip()
        cv_name = str(body.get("cv") or "").strip()
        if not jd_name or not cv_name:
            self._json({"error": "请选好 JD 和候选人"}, 400)
            return
        if mode == "load":
            jd_id, cv_id = prepare.resolve_ids(jd_name, cv_name)
            result = prepare.load_prepared(jd_id, cv_id)      # 缺档抛 FileNotFoundError→404
            with LOCK:
                STATE["prep"] = _fresh_prep()                 # 先清掉上一轮残留（旧红旗/旧日志）
            _apply_prepared(result)
            with LOCK:
                STATE["prep"]["log"] = [f"秒加载预备案例：{result['meta'].get('job', '')}"]
            self._json({"ok": True, "ready": True, "meta": result["meta"]})
        else:
            with LOCK:
                STATE["prep"] = _fresh_prep()
                STATE["prep"]["running"] = True
                STATE["prep"]["log"] = ["开始备料（现做）：出题→答题→蒸馏→搭班→生成场景…"]
            threading.Thread(target=_prep_thread, args=(jd_name, cv_name), daemon=True).start()
            self._json({"ok": True})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=config.SERVER_PORT)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"操作台已起：http://127.0.0.1:{args.port}/  （Ctrl+C 停）", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
