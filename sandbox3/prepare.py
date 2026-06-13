# sandbox3/prepare.py
"""案例备料编排器：JD + 候选人(CV) → (九维画像, 名单 cast, JD 专属场景库)，整条前段一次跑通。

把原来 7 步手动命令里的前 5 步（出题→答题→蒸馏→搭团队→生成场景）IN-PROCESS 串成一条：
被 server.py 的 /api/prepare 在后台线程调用；也可独立复用（"一键启动"的前半）。
产物落 output/cases/<jdid>__<cvid>/（git 已忽略 output/），供"秒加载预备案例"复现。

诚实口径（随产物走）：全程 live、每步真调大模型（备料五步全走编剧模型），失败大声抛/标，绝不空卡空题冒充；
答卷是模型**扮演**候选人的猜答、非真人作答，不构成对真实结局的预测。
"""
from __future__ import annotations
import json
import pathlib

from . import config
from .config import DATA_DIR
from .cast import Cast
from . import quiz_gen, quiz_answer, cast_gen, scene_gen
from .distill import distill as distill_card

CV_DIR = DATA_DIR / "cv_samples"


def _cases_root() -> pathlib.Path:
    # 运行时取 config.OUTPUT_DIR（不在导入期钉死，测试可覆盖到临时目录）
    return config.OUTPUT_DIR / "cases"


def load_jd(name: str) -> dict:
    """包一层 quiz_gen.load_jd：把它 CLI 式的 SystemExit 转成 FileNotFoundError——
    服务端/库上下文要的是普通异常（能干净 404），SystemExit 会打死请求线程。CLI 的 load_jd 不动。"""
    try:
        return quiz_gen.load_jd(name)
    except SystemExit as e:
        raise FileNotFoundError(str(e)) from None


def load_cv(name: str) -> dict:
    """name 可带或不带 .json；也可给完整路径。镜像 quiz_gen.load_jd。"""
    p = pathlib.Path(name)
    if not p.exists():
        p = CV_DIR / (name if name.endswith(".json") else name + ".json")
    if not p.exists():
        avail = sorted(x.stem for x in CV_DIR.glob("*.json")) if CV_DIR.exists() else []
        raise FileNotFoundError(f"找不到候选人 CV：{name}。可用：{avail}")
    return json.loads(p.read_text(encoding="utf-8"))


def available_samples() -> dict:
    """下拉框用：库里有哪些 JD / CV 样本。"""
    jd = sorted(x.stem for x in quiz_gen.JD_DIR.glob("*.json")) if quiz_gen.JD_DIR.exists() else []
    cv = sorted(x.stem for x in CV_DIR.glob("*.json")) if CV_DIR.exists() else []
    return {"jd": jd, "cv": cv}


def case_dir(jd_id: str, cv_id: str) -> pathlib.Path:
    return _cases_root() / f"{jd_id}__{cv_id}"


def resolve_ids(jd_name: str, cv_name: str) -> tuple[str, str]:
    """样本名（JD158_新媒体运营经理 / CV1_林女士）→ 案例 id（JD158 / CV1）。"""
    jd = load_jd(jd_name)
    cv = load_cv(cv_name)
    return jd.get("_jd_id", "JD"), cv.get("_cv_id", "CV")


def _meta_of(d: pathlib.Path) -> dict | None:
    f = d / "meta.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def list_prepared() -> list[dict]:
    """磁盘上已备好、可秒加载的案例（cast/portrait/scene_bank/meta 四件齐全才算数）。"""
    out: list[dict] = []
    root = _cases_root()
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        need = ("cast.json", "portrait.json", "scene_bank.json", "meta.json")
        if all((d / f).exists() for f in need):
            m = _meta_of(d)
            if m:
                out.append(m)
    return out


def load_prepared(jd_id: str, cv_id: str) -> dict:
    """秒加载：从磁盘读回一份已备好的案例（不调 LLM）。"""
    d = case_dir(jd_id, cv_id)
    need = ("cast.json", "portrait.json", "scene_bank.json", "meta.json")
    missing = [f for f in need if not (d / f).exists()]
    if missing:
        raise FileNotFoundError(f"案例 {jd_id}__{cv_id} 不完整，缺 {missing}（先现做一次）")
    cast = json.loads((d / "cast.json").read_text(encoding="utf-8"))
    portrait = json.loads((d / "portrait.json").read_text(encoding="utf-8"))
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    Cast.from_cards(cast)                       # 读回也过一遍校验，坏档明着失败不静默
    return {"cast": cast, "portrait": portrait, "scene_bank_path": str(d / "scene_bank.json"),
            "jd_text": meta.get("jd_text", ""), "meta": meta}


def prepare_case(client, jd_name: str, cv_name: str, *, n_good: int = 2, n_bad: int = 1,
                 n_others: int = 3, dims: list[dict] | None = None, progress=None) -> dict:
    """跑通前段：JD + CV → 画像 + 名单 + 场景库，全部落 output/cases/。
    progress(msg:str) = 进度回调（None 则静默）。返回 dict 同 load_prepared。"""
    progress = progress or (lambda m: None)
    jd = load_jd(jd_name)
    cv = load_cv(cv_name)
    jd_id = jd.get("_jd_id", "JD")
    cv_id = cv.get("_cv_id", "CV")
    jd_text = f"{jd.get('职位名称', '')}\n{jd.get('职位描述', '')}"
    dims = dims if dims is not None else quiz_gen.DIMENSIONS
    total = len(dims) * 2 + 3                    # 每维出题+答题 各算一步，再加 蒸馏/搭班/场景
    step = 0

    def tick(msg: str) -> None:
        nonlocal step
        step += 1
        progress(f"[{step}/{total}] {msg}")

    cdir = case_dir(jd_id, cv_id)
    (cdir / "材料").mkdir(parents=True, exist_ok=True)

    # ---- 1) 出题 + 答题 + 计分 → 九维画像 ----
    # 单维度容错（照 aggregate.main 的"单局失败不连坐整批"路子）：某维 LLM 反复出坏题/答题失败，
    # 大声记一笔并跳过、用成功的维度继续，绝不静默——总比一个维度抽风就整条白跑强。
    persona = quiz_answer.persona_block(cv)
    answers_by_dim: dict[str, list] = {}
    scores: list[dict] = []
    quiz_by_dim: dict[str, list] = {}
    failed_dims: list[str] = []
    for dim in dims:
        try:
            tick(f"出题：{dim['id']}（{dim['risk']}）")
            qs = quiz_gen.gen_dimension(client, jd, dim, n_good, n_bad, tries=5)
            tick(f"答题：{dim['id']}（{len(qs)} 题）")
            al = [quiz_answer.answer_one(client, persona, q) for q in qs]
        except Exception as e:                       # noqa: BLE001 单维失败不连坐，明着记+跳过
            failed_dims.append(dim["id"])
            progress(f"⚠ 维度[{dim['id']}]反复出不合格题/答题失败，已跳过：{type(e).__name__}: {e}")
            continue
        sc = quiz_answer.score_dim(dim["id"], dim["risk"], al)
        # 自适应追题（作者 2026-06-12 拍）：只有"低置信"触发；追 2 道全好变体重算，仍低再追
        # 最后一轮 2 道；封顶（3+2+2=7 题）后还飘就诚实判低——别逼出假置信。
        # 全好变体：换情境不换考点；不追全坏（部分维度全坏天生难出，别把追题拖死）。
        trail = [sc["confidence"]]
        try:
            for probe in (1, 2):
                if sc["confidence"] != "低":
                    break
                progress(f"  ↳ 追题：{dim['id']} 第{probe}轮 +2（作答飘，自适应探测）")
                more = quiz_gen.gen_dimension(client, jd, dim, 2, 0, tries=3)
                qs.extend(more)
                al.extend(quiz_answer.answer_one(client, persona, q) for q in more)
                sc = quiz_answer.score_dim(dim["id"], dim["risk"], al)
                trail.append(sc["confidence"])
        except Exception as e:                       # noqa: BLE001 追题失败不连坐本维：按已答计分、明着标
            progress(f"⚠ 维度[{dim['id']}]追题中途失败，按已答 {len(al)} 题计分：{type(e).__name__}: {e}")
        sc["n_questions"] = len(al)
        sc["probe_rounds"] = len(trail) - 1
        sc["probe_trail"] = trail                    # 例 ["低","低","中"]：两次追题后多数稳定
        quiz_by_dim[dim["id"]] = qs
        answers_by_dim[dim["id"]] = al
        scores.append(sc)

    if not scores:
        raise quiz_gen.LLMError(f"全部 {len(dims)} 维出题/答题都失败，无可用画像——查编剧模型的 API Key 或稍后重试")
    if failed_dims:
        progress(f"⚠ 画像 {len(scores)}/{len(dims)} 维成功，跳过：{'、'.join(failed_dims)}（其余照常）")

    portrait = {"cv_id": cv_id, "name": cv.get("姓名"), "jd_id": jd_id,
                "scores": scores, "failed_dims": failed_dims}
    (cdir / "portrait.json").write_text(
        json.dumps(portrait, ensure_ascii=False, indent=2), encoding="utf-8")
    (cdir / "画像.md").write_text(
        quiz_answer.render_portrait_md(cv, jd, scores), encoding="utf-8")
    (cdir / "quiz.json").write_text(
        json.dumps({"jd_id": jd_id, "by_dim": quiz_by_dim}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    # 作答记录单独落 材料/ 供蒸馏 glob（只喂"她的选择=行为证据"，不喂我们的画像解读）
    (cdir / "材料" / "测评作答记录.md").write_text(
        quiz_answer.render_record_md(cv, jd, answers_by_dim), encoding="utf-8")

    # ---- 2) 蒸馏作答记录 → 候选人角色卡（姓名是事实，显式传，不靠 LLM 蒸） ----
    tick("蒸馏作答记录 → 候选人人设卡")
    cand = distill_card(client, cdir / "材料", jd=jd_text, name=cv.get("姓名"))

    # ---- 3) 按 JD 现搭团队，拼成完整名单（候选人 + 团队） ----
    tick(f"按 JD 现搭团队（{n_others} 人）")
    team = cast_gen.gen_team(client, jd, n_others, cand)
    combined = [cand] + team
    Cast.from_cards(combined)                    # 终极闸：过沙盘真正的名单校验
    (cdir / "cast.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 4) 按 JD 重着色 15 幕场景 → JD 专属场景库 ----
    tick("按 JD 重着色场景库（保 id/类别/标题，只换皮）")
    scenes = scene_gen.gen_scenes(client, jd, scene_gen.load_skeleton())
    sb_path = cdir / "scene_bank.json"
    sb_path.write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 5) 案例元信息（秒加载读它，也供 UI 显示标题） ----
    meta = {
        "jd_id": jd_id, "cv_id": cv_id, "jd_name": jd_name, "cv_name": cv_name,
        "job": jd.get("职位名称", ""), "candidate": cv.get("姓名", ""),
        "n_cast": len(combined), "n_scenes": len(scenes), "jd_text": jd_text,
        "n_dims_ok": len(scores), "n_dims_req": len(dims), "failed_dims": failed_dims,
    }
    (cdir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    progress(f"备料完成（画像 {len(scores)}/{len(dims)} 维）")
    return {"cast": combined, "portrait": portrait, "scene_bank_path": str(sb_path),
            "jd_text": jd_text, "meta": meta}


def run_from_answers(client, jd: dict, answers_by_dim: dict, *, name: str = "",
                     n_others: int = 3, progress=None) -> dict:
    """星空首页"运行项目"专用：吃【真人答卷 answers_by_dim + 结构化 JD】→ 画像 + 蒸馏 + 搭班 + 场景，
    **不出题、不答题**（出题是测评卷网页的活，首页绝不出题——边界红线）。返回结构同 load_prepared。

    answers_by_dim = answersheet.parse_md 的产物：{维度: [{价值,问法,情景,chosen[含 dim_tendency·risk_dir],why}]}。
    与 prepare_case 的区别：跳过 quiz_gen 出题 + quiz_answer.answer_one 答题，直接用真人选择计分/蒸馏。"""
    progress = progress or (lambda m: None)
    jd_id = jd.get("_jd_id", "JD")
    cv_id = "REAL"                                   # 真人答卷无 CV 样本 id；REAL 占位（单候选人 demo 够用）
    name = name or "候选人"
    jd_text = f"{jd.get('职位名称', '')}\n{jd.get('职位描述', '')}"
    risk_of = {d["id"]: d["risk"] for d in quiz_gen.DIMENSIONS}
    cvstub = {"姓名": name, "_cv_id": cv_id}
    cdir = case_dir(jd_id, cv_id)
    (cdir / "材料").mkdir(parents=True, exist_ok=True)

    # ---- 1) 真人作答 → 计分 → 九维画像（无 LLM：真人已经答完了） ----
    progress("计分：真人答卷 → 九维画像")
    scores: list[dict] = []
    for dim_id, al in answers_by_dim.items():
        sc = quiz_answer.score_dim(dim_id, risk_of.get(dim_id, ""), al)
        sc["n_questions"] = len(al)
        sc["probe_rounds"] = 0                       # 追题已在测评页完成、混在 al 里；首页不再单列轨迹
        sc["probe_trail"] = [sc["confidence"]]
        scores.append(sc)
    if not scores:
        raise quiz_gen.LLMError("答卷里没有可计分的作答")
    portrait = {"cv_id": cv_id, "name": name, "jd_id": jd_id, "scores": scores, "failed_dims": []}
    (cdir / "portrait.json").write_text(
        json.dumps(portrait, ensure_ascii=False, indent=2), encoding="utf-8")
    (cdir / "画像.md").write_text(
        quiz_answer.render_portrait_md(cvstub, jd, scores, real=True), encoding="utf-8")
    (cdir / "材料" / "测评作答记录.md").write_text(
        quiz_answer.render_record_md(cvstub, jd, answers_by_dim, real=True), encoding="utf-8")

    # ---- 2) 蒸馏作答记录 → 候选人角色卡（姓名显式传，不靠 LLM 蒸） ----
    progress("蒸馏作答记录 → 候选人人设卡")
    cand = distill_card(client, cdir / "材料", jd=jd_text, name=name)

    # ---- 3) 按 JD 现搭团队 ----
    progress(f"按 JD 现搭团队（{n_others} 人）")
    team = cast_gen.gen_team(client, jd, n_others, cand)
    combined = [cand] + team
    Cast.from_cards(combined)
    (cdir / "cast.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 4) 按 JD 重着色场景库 ----
    progress("按 JD 重着色场景库（保 id/类别/标题，只换皮）")
    scenes = scene_gen.gen_scenes(client, jd, scene_gen.load_skeleton())
    sb_path = cdir / "scene_bank.json"
    sb_path.write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 5) 元信息 ----
    meta = {
        "jd_id": jd_id, "cv_id": cv_id, "jd_name": jd.get("职位名称", ""), "cv_name": name,
        "job": jd.get("职位名称", ""), "candidate": name,
        "n_cast": len(combined), "n_scenes": len(scenes), "jd_text": jd_text,
        "n_dims_ok": len(scores), "n_dims_req": len(answers_by_dim), "failed_dims": [],
        "source": "real_answersheet",
    }
    (cdir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    progress(f"运行项目就绪（画像 {len(scores)} 维 · 真人答卷）")
    return {"cast": combined, "portrait": portrait, "scene_bank_path": str(sb_path),
            "jd_text": jd_text, "meta": meta}
