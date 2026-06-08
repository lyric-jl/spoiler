# tests/test_distill.py
import pathlib
import unittest

from sandbox3.cast import Cast
from sandbox3.distill import distill
from sandbox3.prompts import distill as DP
from tests.fakes import FakeLLM

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
MATERIALS = DATA / "materials_zhou"

# stage2 应答：合法角色卡（满足 from_cards：name/role/persona 非空 + playbook 3-9 条 + kind 合法）
GOOD_CARD = {
    "name": "周默", "kind": "candidate", "role": "新人·后端开发工程师",
    "persona": "你是周默，刚入职一周的后端开发工程师。",
    "playbook": ["如果没听懂→先应下来回头查", "如果必须问→优先 IM 发文字",
                 "如果被点名→给保守回答", "如果被忽视→加班证明自己"],
}


def _stage1_reply(n):
    """构造第 n 份材料的 stage1 应答，evidence 句里带可识别标志串。"""
    return {"source": f"材料{n}", "evidence": [f"行为证据-标志{n}"], "perspective": "self"}


def _router(stage1_replies, stage2_reply):
    """按 system 区分 stage1/stage2；stage1 按调用顺序逐个出。"""
    state = {"i": 0}

    def router(system, user):
        if system == DP.STAGE1_SYSTEM:
            r = stage1_replies[state["i"]]
            state["i"] += 1
            return r
        if system == DP.STAGE2_SYSTEM:
            return stage2_reply
        raise AssertionError(f"未知 system：{system[:40]}")
    return router


class TestDistill(unittest.TestCase):
    def test_n_materials_n_stage1_plus_1_stage2(self):
        n = len(sorted(MATERIALS.glob("*.md")))
        self.assertEqual(n, 4)     # 材料包是 4 份 .md
        replies = [_stage1_reply(i) for i in range(n)]
        fake = FakeLLM(router=_router(replies, GOOD_CARD))
        distill(fake, MATERIALS)
        self.assertEqual(len(fake.calls), n + 1)     # 4 次 stage1 + 1 次 stage2 = 5
        stage1_calls = [c for c in fake.calls if c[0] == DP.STAGE1_SYSTEM]
        stage2_calls = [c for c in fake.calls if c[0] == DP.STAGE2_SYSTEM]
        self.assertEqual(len(stage1_calls), n)
        self.assertEqual(len(stage2_calls), 1)

    def test_card_passes_cast_validation(self):
        replies = [_stage1_reply(i) for i in range(4)]
        fake = FakeLLM(router=_router(replies, GOOD_CARD))
        card = distill(fake, MATERIALS)
        # distill 内部已借 Cast.from_cards 验过；这里再独立验一次返回卡能入名单
        cast = Cast.from_cards([card, {"name": "_上级", "kind": "counterpart", "role": "占位",
                                       "persona": "占位", "playbook": ["a", "b", "c"]}])
        self.assertEqual(cast.candidate().name, "周默")

    def test_jd_in_both_stages(self):
        jd = "JD标志串-后端岗位特殊要求XYZ"
        replies = [_stage1_reply(i) for i in range(4)]
        fake = FakeLLM(router=_router(replies, GOOD_CARD))
        distill(fake, MATERIALS, jd=jd)
        stage1_users = [u for s, u in fake.calls if s == DP.STAGE1_SYSTEM]
        stage2_users = [u for s, u in fake.calls if s == DP.STAGE2_SYSTEM]
        for u in stage1_users:                       # 每次 stage1 user 都含 JD
            self.assertIn(jd, u)
        self.assertIn(jd, stage2_users[0])           # stage2 user 也含 JD

    def test_stage2_user_contains_all_stage1_outputs(self):
        n = 4
        replies = [_stage1_reply(i) for i in range(n)]
        fake = FakeLLM(router=_router(replies, GOOD_CARD))
        distill(fake, MATERIALS)
        stage2_user = [u for s, u in fake.calls if s == DP.STAGE2_SYSTEM][0]
        for i in range(n):                           # 各 stage1 产物的标志串都被序列化进 stage2 user
            self.assertIn(f"行为证据-标志{i}", stage2_user)
            self.assertIn(f"材料{i}", stage2_user)

    def test_empty_dir_raises(self):
        empty = DATA / "_distill_empty_test_dir"
        empty.mkdir(parents=True, exist_ok=True)
        try:
            with self.assertRaises(ValueError):
                distill(FakeLLM(), empty)
        finally:
            empty.rmdir()

    def test_bad_stage2_card_raises_casterror(self):
        """live 最易踩：LLM 产不合格卡（playbook 不足 3 条）→ 借校验器抛 CastError，
        错误亮到调用方，不静默放行坏卡。"""
        from sandbox3.cast import CastError
        bad_card = dict(GOOD_CARD, playbook=["只有一条"])
        replies = [_stage1_reply(i) for i in range(4)]
        fake = FakeLLM(router=_router(replies, bad_card))
        with self.assertRaises(CastError):
            distill(fake, MATERIALS)


if __name__ == "__main__":
    unittest.main()
