# sandbox3/distill.py
"""蒸馏器：材料包目录 → 两段式 → cast 角色卡 JSON（直接可入名单）。
用法：python -m sandbox3.distill data/materials_zhou [--jd jd.txt] [--out card.json]"""
from __future__ import annotations
import argparse, json, pathlib

from .cast import Cast
from .llm import DeepSeekClient
from .prompts import distill as DP


def distill(llm, material_dir: pathlib.Path, jd: str = "") -> dict:
    files = sorted(material_dir.glob("*.md"))
    if not files:
        raise ValueError(f"{material_dir} 下没有材料（*.md）")
    summaries = [llm.complete_json(DP.STAGE1_SYSTEM,
                                   DP.stage1_user(f.stem, f.read_text(encoding="utf-8"), jd))
                 for f in files]
    card = llm.complete_json(DP.STAGE2_SYSTEM, DP.stage2_user(summaries, jd))
    card.setdefault("kind", "candidate")
    Cast.from_cards([card, {"name": "_占位上级", "kind": "counterpart", "role": "占位",
                            "persona": "占位", "playbook": ["a", "b", "c"]}])   # 借校验器验卡
    return card


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("material_dir")
    ap.add_argument("--jd", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    jd = pathlib.Path(args.jd).read_text(encoding="utf-8") if args.jd else ""
    card = distill(DeepSeekClient(), pathlib.Path(args.material_dir), jd)
    out = pathlib.Path(args.out or "card.json")
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"角色卡已写出：{out}（导入操作台或 --cast 即用，引擎一行不改）")


if __name__ == "__main__":
    main()
