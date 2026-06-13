# sandbox3/jd_parse.py
"""自由文本招聘 JD → 结构化 JD（出题器 quiz_gen 要的字段）。

测评卷网页支持"粘贴/拖入任意岗位 JD 现场出题"——但 quiz_gen 吃的是结构化格子
（职位名称/职位描述/薪资…），故先用 LLM 把一段招聘文案抽取成这些字段。
live-only：抽取失败大声抛；职位描述兜底=原文全文（绝不让出题失去 JD 依据）。
"""
from __future__ import annotations
import re

from .llm import LLMError

_SYS = """你是招聘信息抽取助手。把一段招聘 JD 原文抽成结构化字段，供后续按岗位出情境测评题用。
规矩：①只抽原文里有的，缺失留空字符串，别编造；②职位描述要完整保留"岗位职责+任职要求"的关键信息、
别概括丢细节（出题要靠它长出真实职场情景）；③只输出 JSON，不要任何解释。"""

_USER_TMPL = """【招聘 JD 原文】
{text}

【抽取成下面这些字段，只输出 JSON】
{{
  "职位名称": "（如'新媒体运营经理'，必填，原文找不到就用最贴近的岗位名）",
  "职类名称": "（如'运营'，没有留空）",
  "薪资": "（没有留空）",
  "年限要求": "（如'3年以上'，没有留空）",
  "学历要求": "（没有留空）",
  "城市要求": "（没有留空）",
  "职位关键词": "（几个关键词逗号分隔，没有留空）",
  "职位描述": "（完整保留岗位职责与任职要求的要点，别丢关键信息）"
}}"""

_FIELDS = ["职位名称", "职类名称", "薪资", "年限要求", "学历要求", "城市要求", "职位关键词", "职位描述"]


def parse_jd(client, text: str) -> dict:
    """text=招聘文案原文 → 结构化 JD dict（含 _jd_id/_源）。"""
    text = (text or "").strip()
    if len(text) < 8:
        raise LLMError("JD 文本太短，至少给一段像样的岗位描述")
    out = client.complete_json(_SYS, _USER_TMPL.format(text=text[:6000]),
                               temperature=0.2, max_tokens=1500)
    jd = {f: str(out.get(f, "") or "").strip() for f in _FIELDS}
    # 兜底：职位描述空→用原文全文（出题绝不能没 JD 依据）；职位名称空→给个占位
    if not jd["职位描述"]:
        jd["职位描述"] = text
    if not jd["职位名称"]:
        jd["职位名称"] = "（未命名岗位）"
    # _jd_id：用户贴的 JD 无样本编号——取职位名称里的字母数字做短稳定后缀，便于案例目录命名
    slug = re.sub(r"[^0-9A-Za-z一-鿿]", "", jd["职位名称"])[:6] or "USER"
    jd["_jd_id"] = "JDU_" + slug
    jd["_源"] = "用户粘贴 JD（自由文本，已结构化）"
    return jd
