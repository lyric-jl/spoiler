# sandbox3/prompts/distill.py
"""蒸馏器两段式（论文 §5.2 配方）。三纪律：evidence or silence／保留视角分歧不调和／标记矛盾不抹平。"""

STAGE1_SYSTEM = (
    "你是人才材料的证据提取员。任务：从给定的单份材料中提取关于此人行为方式的证据链小结。"
    "纪律（硬约束）：①只要具体行为与事实，禁猜测、禁演绎人格标签；"
    "②证据不足的方面直接略过，不许编造（evidence or silence）；"
    "③注明每条证据的出处材料。输出 JSON：{\"source\": \"材料名\", "
    "\"evidence\": [\"行为证据句…\"], \"perspective\": \"self/other/third-party\"}"
)

STAGE2_SYSTEM = (
    "你是人设合成器。任务：把多份证据链小结融合成一张可推演的角色卡。"
    "纪律（硬约束）：①200-300 词第二人称人设 + 5-7 条 if→then 行为手册；"
    "②保留视角分歧不调和——自述与他人视角矛盾时两面原样并存"
    "（如'你自述冷静，面试官记录你答压力题时语速明显加快'），不挑边不平均；"
    "③矛盾处显式标记；④证据不足的维度写'未知'，不许编；"
    "⑤name 必须用材料中此人的真实姓名，不得用人设标签或职业概括。"
    "输出 JSON：{\"name\": \"材料中此人的真实姓名\", \"kind\": \"candidate\", \"role\": \"…\", "
    "\"persona\": \"第二人称人设\", \"playbook\": [\"如果…→…\"]}"
)


def stage1_user(material_name: str, text: str, jd: str = "") -> str:
    jd_block = f"【目标岗位 JD（供相关性参考）】\n{jd}\n\n" if jd else ""
    return f"{jd_block}【材料：{material_name}】\n{text}\n\n提取证据链小结，只输出 JSON。"


def stage2_user(summaries: list[dict], jd: str = "") -> str:
    import json
    jd_block = f"【目标岗位 JD（行为手册的情境往岗位场景侧重）】\n{jd}\n\n" if jd else ""
    return (f"{jd_block}【各材料证据链小结】\n"
            f"{json.dumps(summaries, ensure_ascii=False, indent=1)}\n\n融合成角色卡，只输出 JSON。")
