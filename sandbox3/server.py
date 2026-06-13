# sandbox3/server.py
"""操作台本地服务（stdlib，零第三方依赖；名单制多人原生底座）。
路由：GET / 页面；GET /landing 新前端（粒子首页+界面2，静态资产同源伺服）；
GET /api/state 状态；GET /api/events?since=N 事件流（轮询）；GET /api/scenes 场景库全量；
GET /api/batch_latest 最新批聚合；GET /api/cases 样本+预备案例；GET /api/prep_state 备料进度；
POST /api/run 开拍；/api/chat 场景共创；/api/crystallize 共创结晶入库（走 BANK.add_custom）；
/api/import_cast 导入整套名单；/api/jd 暂存自由文本 JD；
/api/prepare JD 驱动（mode=live 现做整条前段→换名单+场景+画像；mode=load 秒加载磁盘案例）。
注：JD 驱动已落地（作者 2026-06-09 拍翻"JD 只入档不驱动"旧口径）；/api/jd 自由文本框为遗留入口。
用法：python -m sandbox3.server [--port 8781]

依赖注入边界（非 mock）：模块级 LLM / CAST / BANK 是可替换的全局对象——
测试以 `sandbox3.server.LLM = FakeLLM(...)` 注入；产品路径唯一=live（多模型分工见 config.ROLES）。
ACTOR_LLM/AUDIT_LLM/WRITER_LLM 缺省 None＝回落 LLM（测试只注入 LLM 即可），main() 启动时按工种实配。
并发纪律：单进程一个 BANK 实例；/api/crystallize 走 BANK.add_custom 必须在 LOCK 内
（add_custom 的 id 生成依赖内存计数，双实例/并发必撞号）。"""
from __future__ import annotations
import argparse, json, pathlib, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import config
from . import prepare
from . import quiz_answer
from . import quiz_gen
from . import answersheet
from . import jd_parse
from .cast import Cast, CastError
from .engine import run_simulation
from .llm import LLMClient, LLMError
from .prompts import sm as PS
from .scenes import SceneBank
from .trace import save_run
from .pages.theater import PAGE

# ---- 可替换的模块级全局（依赖注入口；推演中 CAST 不可换） ----
LLM = LLMClient("director")
ACTOR_LLM = None        # main() 实配 LLMClient("actor")；None=回落 LLM（测试态）
AUDIT_LLM = None        # main() 实配 LLMClient("auditor")
WRITER_LLM = None       # main() 实配 LLMClient("writer")，备料管线用
CAST = Cast.load_default()
BANK = SceneBank()

# 新前端（landing.html + head.glb 等）所在目录；_serve_static 只许伺服此目录内的真实文件
_STATIC_DIR = pathlib.Path(__file__).parent / "pages" / "static"
_MIME = {".html": "text/html; charset=utf-8", ".glb": "model/gltf-binary",
         ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".png": "image/png", ".jpg": "image/jpeg", ".md": "text/plain; charset=utf-8"}

# jd_text=驱动场景导演二次贴岗 + 落盘记 JD（JD 驱动后启用）；
# prep=备料进度/产物（JD→画像+名单+场景的前段管线状态）。
STATE = {"running": False, "events": [], "jd": "", "jd_text": "",
         "prep": {"running": False, "log": [], "ready": False, "error": None,
                  "portrait": None, "meta": None},
         "quiz": {"running": False, "log": [], "ready": False, "error": None, "result": None}}
LOCK = threading.Lock()


def _fresh_prep() -> dict:
    return {"running": False, "log": [], "ready": False, "error": None,
            "portrait": None, "meta": None}


def _fresh_quiz() -> dict:
    # 测评页出题状态（与首页"运行项目"分干净：出题只在这条线）
    return {"running": False, "log": [], "ready": False, "error": None, "result": None}


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
                               actor_llm=ACTOR_LLM or LLM, audit_llm=AUDIT_LLM or LLM,
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
        result = prepare.prepare_case(WRITER_LLM or LLM, jd_name, cv_name, progress=_prep_log)
        _apply_prepared(result)
        _prep_log("✓ 名单与场景已就位，可开始推演")
    except Exception as e:                                   # noqa: BLE001 备料失败必须亮到页面
        with LOCK:
            STATE["prep"]["error"] = f"{type(e).__name__}: {e}"
            STATE["prep"]["log"].append(f"✗ 备料失败：{type(e).__name__}: {e}")
    finally:
        with LOCK:
            STATE["prep"]["running"] = False


def _quiz_log(msg: str) -> None:
    with LOCK:
        STATE["quiz"]["log"].append(msg)


def _quiz_thread(jd_name: str, jd_text: str = "") -> None:
    """测评页：按 JD 并行出全维题。出题=测评卷网页独有功能，与星空首页"运行项目"分干净（边界红线）。
    jd_text 非空＝用户粘贴的自由文本 JD，先 LLM 解析成结构化；否则按 jd_name 加载样本。"""
    try:
        if jd_text.strip():
            _quiz_log("解析岗位 JD（自由文本 → 结构化）…")
            jd = jd_parse.parse_jd(WRITER_LLM or LLM, jd_text)
            _quiz_log(f"✓ JD 已结构化：{jd.get('职位名称', '')}")
        else:
            jd = prepare.load_jd(jd_name)                # 包过的 load_jd：找不到抛 FileNotFoundError
        by_dim, failed = quiz_gen.gen_all_dims(WRITER_LLM or LLM, jd, progress=_quiz_log)
        if not by_dim:
            raise quiz_gen.LLMError(f"全部维度出题都失败：{failed}——查编剧模型 Key 或稍后重试")
        with LOCK:
            STATE["quiz"]["result"] = {"job": jd.get("职位名称", ""), "jd_id": jd.get("_jd_id", ""),
                                       "jd": jd, "jd_name": jd_name, "by_dim": by_dim, "failed": failed}
            STATE["quiz"]["ready"] = True
        _quiz_log(f"✓ 出题完成（{len(by_dim)} 维"
                  f"{('，跳过 ' + '、'.join(failed)) if failed else ''}），可开始作答")
    except Exception as e:                               # noqa: BLE001 出题失败必须亮到页面
        with LOCK:
            STATE["quiz"]["error"] = f"{type(e).__name__}: {e}"
            STATE["quiz"]["log"].append(f"✗ 出题失败：{type(e).__name__}: {e}")
    finally:
        with LOCK:
            STATE["quiz"]["running"] = False


def _run_project_thread(md_text: str) -> None:
    """星空首页"运行项目"：吃拖入的答卷.md（内嵌结构化JD）→ run_from_answers（计分→蒸馏→搭班→场景，
    **不出题不答题**，守边界红线）→装进运行态。复用 STATE["prep"] 状态机，首页轮询 /api/prep_state。"""
    try:
        data = answersheet.parse_md(md_text)             # 解析失败抛 ValueError→落到下面 except 亮页面
        result = prepare.run_from_answers(WRITER_LLM or LLM, data["jd"], data["answers_by_dim"],
                                          name=data.get("name", ""), progress=_prep_log)
        _apply_prepared(result)
        _prep_log("✓ 项目就绪，可开始推演")
    except Exception as e:                               # noqa: BLE001 失败必须亮到页面
        with LOCK:
            STATE["prep"]["error"] = f"{type(e).__name__}: {e}"
            STATE["prep"]["log"].append(f"✗ 运行项目失败：{type(e).__name__}: {e}")
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
        elif u.path == "/api/scenes":
            with LOCK:
                self._json({"scenes": [dict(t) for t in BANK.all()]})
        elif u.path == "/api/quiz_demo":
            # 动态测评演示页数据源：最新备料案例的真 AIG 卷（?dims=N 节选前 N 维，缺省 3）
            try:
                cases = sorted(config.OUTPUT_DIR.glob("cases/*/quiz.json"),
                               key=lambda p: p.stat().st_mtime)
                if not cases:
                    self._json({"error": "没有任何备料案例（先跑一次 /api/prepare）"}, 404)
                    return
                case = cases[-1].parent
                quiz = json.loads((case / "quiz.json").read_text(encoding="utf-8"))
                meta = json.loads((case / "meta.json").read_text(encoding="utf-8"))
                n = max(1, int((parse_qs(u.query).get("dims") or ["3"])[0]))
                dims = [{"id": k, "risk": (qs[0].get("风险") or ""), "questions": qs}
                        for k, qs in list(quiz["by_dim"].items())[:n]]
                self._json({"jd_id": meta.get("jd_id"), "jd_name": meta.get("jd_name"),
                            "job": meta.get("job", ""), "dims": dims})
            except (OSError, json.JSONDecodeError, ValueError) as e:
                self._json({"error": f"读测评卷失败：{e}"}, 500)
        elif u.path == "/api/cases":
            try:
                self._json({"samples": prepare.available_samples(),
                            "prepared": prepare.list_prepared()})
            except OSError as e:
                self._json({"error": f"读样本/案例失败：{e}"}, 500)
        elif u.path == "/api/prep_state":
            with LOCK:
                p = STATE["prep"]
                try:                                    # 候选人人设/行为手册（前端起手屏的人设独白+手册藏卡接它）
                    c = CAST.candidate()
                    cand = {"name": c.name, "role": c.role, "persona": c.persona,
                            "playbook": list(c.playbook)}
                except Exception:                       # noqa: BLE001 没候选人就不给，前端保留样张
                    cand = None
                self._json({"running": p["running"], "log": list(p["log"]),
                            "ready": p["ready"], "error": p["error"],
                            "portrait": p["portrait"], "meta": p["meta"],
                            "candidate": cand})
        elif u.path == "/api/quiz_state":
            with LOCK:
                q = STATE["quiz"]
                self._json({"running": q["running"], "log": list(q["log"]),
                            "ready": q["ready"], "error": q["error"], "result": q["result"]})
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
            self._serve_static(u.path)

    def _serve_static(self, path: str):
        """/landing 与首页静态资产（head.glb 等）同源伺服——landing 页要调 /api/*，
        file:// 打开调不到，必须从本服务出。防穿越：resolve 后必须仍在 static 目录内。"""
        name = "landing.html" if path == "/landing" else path.lstrip("/")
        fp = _STATIC_DIR / name
        try:
            ok = fp.is_file() and fp.resolve().is_relative_to(_STATIC_DIR.resolve())
        except OSError:
            ok = False
        if not ok:
            self._json({"error": "not found"}, 404)
            return
        body = fp.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", _MIME.get(fp.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
            elif u.path == "/api/quiz_score":
                # 演示页计分：与产品同一套 score_dim，零逻辑漂移
                ans = [{"价值": a.get("价值"), "chosen": a.get("chosen") or {}, "why": ""}
                       for a in (body.get("answers") or [])]
                self._json(quiz_answer.score_dim(str(body.get("dim") or ""),
                                                 str(body.get("risk") or ""), ans))
            elif u.path == "/api/quiz_probe":
                # 演示页追题：与备料管线同一台出题器，live 现编 2 道全好变体
                dim = next((d for d in quiz_gen.DIMENSIONS if d["id"] == body.get("dim")), None)
                if dim is None:
                    self._json({"error": f"未知维度：{body.get('dim')!r}"}, 400)
                    return
                jd = body.get("jd")
                if not isinstance(jd, dict) or not jd.get("职位描述"):   # 优先用页面回传的结构（支持粘贴的JD）
                    try:
                        jd = quiz_gen.load_jd(str(body.get("jd_name") or ""))
                    except SystemExit as e:      # load_jd 找不到 JD 时 SystemExit——别让它杀请求线程
                        self._json({"error": str(e)}, 400)
                        return
                try:
                    qs = quiz_gen.gen_dimension(WRITER_LLM or LLM, jd, dim, 2, 0)
                except RuntimeError as e:        # 质量闸三试不过：大声失败（live-only，不给假题）
                    self._json({"error": f"追题现编失败：{e}"}, 500)
                    return
                self._json({"questions": qs})
            elif u.path == "/api/quiz_build":
                # 测评页：按 JD 现编整卷（9 维并行出题，后台线程，页面轮询 /api/quiz_state）。
                # 出题只在这条线发生——首页绝不出题（边界红线）。第二批先吃现成结构化 JD158。
                with LOCK:
                    if STATE["quiz"]["running"]:
                        self._json({"error": "出题已在进行，别重复点"}, 409)
                        return
                    STATE["quiz"] = _fresh_quiz()
                    STATE["quiz"]["running"] = True
                    STATE["quiz"]["log"] = ["开始按 JD 现编测评卷（9 维并行出题，约 1-2 分钟）…"]
                jd_name = str(body.get("jd") or "JD158_新媒体运营经理")
                jd_text = str(body.get("jd_text") or "")     # 非空＝用户粘贴的自由文本 JD
                threading.Thread(target=_quiz_thread, args=(jd_name, jd_text), daemon=True).start()
                self._json({"ok": True})
            elif u.path == "/api/quiz_export":
                # 真人答完→导出答卷.md（页面回传 name/jd/by_dim[含隐藏键]/choices；渲染走 answersheet 单一格式源）
                md = answersheet.render_md(str(body.get("name") or ""), body.get("jd") or {},
                                           body.get("by_dim") or {}, body.get("choices") or {})
                self._json({"ok": True, "md": md,
                            "filename": f"测评答卷_{body.get('name') or '匿名'}.md"})
            elif u.path == "/api/run_project":
                # 星空首页：吃拖入的答卷.md → 运行项目（无出题）。复用 prep 状态机，页面轮询 /api/prep_state。
                md_text = str(body.get("md") or "")
                if not md_text.strip():
                    self._json({"error": "没收到答卷内容（请拖入测评页导出的 .md）"}, 400)
                    return
                with LOCK:
                    if STATE["running"]:
                        self._json({"error": "推演进行中，先等它收官"}, 409)
                        return
                    if STATE["prep"]["running"]:
                        self._json({"error": "正在运行项目，别重复点"}, 409)
                        return
                    STATE["prep"] = _fresh_prep()
                    STATE["prep"]["running"] = True
                    STATE["prep"]["log"] = ["读入答卷，运行项目（计分→蒸馏→搭班→场景，无出题）…"]
                threading.Thread(target=_run_project_thread, args=(md_text,), daemon=True).start()
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
    global ACTOR_LLM, AUDIT_LLM, WRITER_LLM
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=config.SERVER_PORT)
    args = ap.parse_args()
    # 正式启动＝四工种实配（测试不走 main，只注入 LLM、其余回落）
    ACTOR_LLM = LLMClient("actor")
    AUDIT_LLM = LLMClient("auditor")
    WRITER_LLM = LLMClient("writer")
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"操作台已起：http://127.0.0.1:{args.port}/  （Ctrl+C 停）", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
