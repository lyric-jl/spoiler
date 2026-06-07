# sandbox3/server.py
"""操作台本地服务（stdlib，零第三方依赖；名单制多人原生底座）。
路由：GET / 页面；GET /api/state 状态；GET /api/events?since=N 事件流（轮询）；
GET /api/batch_latest 最新批聚合；POST /api/run 开拍；/api/chat 场景共创；
/api/crystallize 共创结晶入库（走 BANK.add_custom 自动持久化）；
/api/import_cast 导入整套名单；/api/jd 暂存 JD（用途待定，只入档不驱动——作者拍）。
用法：python -m sandbox3.server [--port 8781]

依赖注入边界（非 mock）：模块级 LLM / CAST / BANK 是可替换的全局对象——
测试以 `sandbox3.server.LLM = FakeLLM(...)` 注入；产品路径唯一=DeepSeek live。
并发纪律：单进程一个 BANK 实例；/api/crystallize 走 BANK.add_custom 必须在 LOCK 内
（add_custom 的 id 生成依赖内存计数，双实例/并发必撞号）。"""
from __future__ import annotations
import argparse, json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import config
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

STATE = {"running": False, "events": [], "jd": ""}
LOCK = threading.Lock()


def _emit(event: dict) -> None:
    with LOCK:
        STATE["events"].append(event)


def _run_thread(cfg: dict) -> None:
    try:
        # JD 用途待定（作者 2026-06-07 拍：只做输入框）——只入档 jd.txt，不喂引擎
        trace = run_simulation(cast=CAST, llm=LLM, bank=BANK,
                               n_scenes=cfg["scenes"], start_tp=cfg["start"],
                               seed=cfg.get("seed"), emit=_emit)
        out_dir = save_run(trace, jd=STATE["jd"])
        _emit({"type": "saved", "path": str(out_dir)})
    except Exception as e:                                   # noqa: BLE001 直播必须把错误亮给页面
        _emit({"type": "error", "text": f"{type(e).__name__}: {e}"})
    finally:
        with LOCK:
            STATE["running"] = False


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
                            "jd_len": len(STATE["jd"])})
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
                STATE["jd"] = str(body.get("text") or "")
                self._json({"ok": True})
            else:
                self._json({"error": "not found"}, 404)
        except CastError as e:
            self._json({"error": str(e)}, 400)
        except (KeyError, ValueError, LLMError) as e:
            self._json({"error": str(e)}, 400)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=config.SERVER_PORT)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"操作台已起：http://127.0.0.1:{args.port}/  （Ctrl+C 停）", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
