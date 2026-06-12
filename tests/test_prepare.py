# tests/test_prepare.py
"""备料编排器 prepare_case 的离线集成测试：FakeLLM 按 prompt 关键词路由，
覆盖前段五个模块（quiz_gen/quiz_answer/distill/cast_gen/scene_gen）的真实校验闸，
证明编排把它们按正确顺序串起来、产物落盘、名单可入沙盘——全程无网络、<1s。
依赖注入边界（非 mock）：以 FakeLLM 注入 client；产品代码无 mock 分支。"""
from __future__ import annotations
import http.client
import json
import pathlib
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

import sandbox3.server as server
from sandbox3 import config, prepare
from sandbox3.cast import Cast
from tests.fakes import FakeLLM

CAND_NAME = "林女士"


def _good_q(risk: str) -> dict:
    return {"情景": "跨部门评审上你的方案被当众质疑。", "价值": "全好", "问法": "最像你", "风险": risk,
            "选项": [
                {"id": "A", "文本": "摆出数据据理力争，对事不对人。", "dim_tendency": "建设性对峙", "risk_dir": "低"},
                {"id": "B", "文本": "先记下来，会后私下找对方沟通。", "dim_tendency": "回避私下", "risk_dir": "中"},
                {"id": "C", "文本": "含糊带过，回头慢慢拖着。", "dim_tendency": "拖延迂回", "risk_dir": "中"},
                {"id": "D", "文本": "当场顺从对方意见不争。", "dim_tendency": "顺从退让", "risk_dir": "高"}]}


def _bad_q(risk: str) -> dict:
    # 全坏题：四个选项都不健康（无 risk_dir='低'），过 _bad_leak 闸
    return {"情景": "项目出纰漏要有人担，最不像你的做法是？", "价值": "全坏", "问法": "最不像你", "风险": risk,
            "选项": [
                {"id": "A", "文本": "把锅甩给新来的同事。", "dim_tendency": "甩锅", "risk_dir": "高"},
                {"id": "B", "文本": "装作不知道闷头不吭声。", "dim_tendency": "回避", "risk_dir": "中"},
                {"id": "C", "文本": "阴阳怪气抱怨流程烂。", "dim_tendency": "消极对抗", "risk_dir": "中高"},
                {"id": "D", "文本": "撂挑子直接不管了。", "dim_tendency": "撂挑子", "risk_dir": "高"}]}


_LONG = "你是这个角色，做事有自己的一套风格，在乎交付也在乎关系，遇到冲突会按本能反应，藏着一点不轻易外露的小心思，跟新人磨合时会有张力。"


def _team(n_others: int) -> dict:
    team = [{"name": "上级老王", "kind": "counterpart", "role": "直属上级·团队负责人",
             "persona": _LONG, "playbook": ["如果新人主动汇报→给更重的活", "如果闷头不说→点名要进度", "如果交付出问题→当众指出不翻旧账"]}]
    for i in range(n_others - 1):
        team.append({"name": f"同事{i}", "kind": "colleague", "role": "同组资深同事",
                     "persona": _LONG, "playbook": ["如果被认真请教→倾囊相授", "如果敷衍→丢一句文档里有", "如果模块被乱改→当场叫停"]})
    return {"team": team}


def _scenes_for(user: str) -> dict:
    ids = re.findall(r"id=([A-Za-z0-9\-]+)", user)
    return {"scenes": [{"id": sid, "category": "x", "title": "x",
                        "sketch": f"贴本岗位的情节梗概第{i}幕，具体可演。", "owner_hints": "新人"}
                       for i, sid in enumerate(ids, 1)]}


def prepare_router():
    def router(system: str, user: str):
        if "测评出题专家" in system:
            risk = "团队不合" if "团队不合" in user else "主动离职"
            return {"questions": [_good_q(risk), _good_q(risk), _bad_q(risk)]}
        if "扮演一位真实求职者" in system:
            return {"choice": "A", "why": "我会这么做。"}
        if "证据提取员" in system:
            return {"source": "测评作答记录", "evidence": ["她倾向据理力争", "答题稳定"], "perspective": "self"}
        if "人设合成器" in system:
            return {"name": "占位会被覆盖", "kind": "candidate", "role": "新人·试用期",
                    "persona": _LONG, "playbook": ["如果被否→据理力争", "如果卡住→先自查再问", "如果被忽视→闷声加班"]}
        if "组织行为顾问" in system:          # cast_gen
            return _team(3)
        if "情景编剧" in system:               # scene_gen
            return _scenes_for(user)
        raise AssertionError(f"prepare_router 未覆盖的调用：{system[:40]}")
    return router


def probe_router(answer_seq: list[str]):
    """同 prepare_router，但答题按给定序列出、出题按轮次回数（首轮 2好+1坏，追题轮只回 2 好），
    测自适应追题：飘→追→稳/封顶。"""
    base = prepare_router()
    it = iter(answer_seq)
    quiz_calls = {"n": 0}

    def router(system: str, user: str):
        if "测评出题专家" in system:
            quiz_calls["n"] += 1
            risk = "团队不合" if "团队不合" in user else "主动离职"
            if quiz_calls["n"] == 1:
                return {"questions": [_good_q(risk), _good_q(risk), _bad_q(risk)]}
            return {"questions": [_good_q(risk), _good_q(risk)]}    # 追题轮：2 道全好变体
        if "扮演一位真实求职者" in system:
            return {"choice": next(it, "A"), "why": "我会这么做。"}
        return base(system, user)
    return router


class AdaptiveProbeTest(unittest.TestCase):
    """自适应追题（作者 2026-06-12 拍）：低置信→+2 全好变体→仍低→最后+2→封顶诚实判低。
    选项风险值：A=低(1) D=高(3)，全好题答 A/D 交替=飘（极差 2>1.0 → 低置信）。"""

    def setUp(self):
        self._orig_out = config.OUTPUT_DIR
        self._tmp = tempfile.mkdtemp()
        config.OUTPUT_DIR = pathlib.Path(self._tmp)
        self.dims = [prepare.quiz_gen.DIMENSIONS[0]]   # 单维即可证明机制

    def tearDown(self):
        config.OUTPUT_DIR = self._orig_out

    def _run(self, answer_seq):
        llm = FakeLLM(router=probe_router(answer_seq))
        result = prepare.prepare_case(llm, "JD158_新媒体运营经理", "CV1_林女士",
                                      n_good=2, n_bad=1, dims=self.dims)
        return result["portrait"]["scores"][0]

    def test_wobble_to_cap_stays_low_honestly(self):
        # 初测 A,D（飘）+坏题A；追1轮答 D,A 仍飘；追2轮答 A,D 仍飘 → 封顶 7 题、诚实低置信
        s = self._run(["A", "D", "A", "D", "A", "A", "D"])
        self.assertEqual(s["probe_rounds"], 2)
        self.assertEqual(s["n_questions"], 7)
        self.assertEqual(s["probe_trail"], ["低", "低", "低"])
        self.assertEqual(s["confidence"], "低")       # 追满仍飘＝低，不准为好看硬编

    def test_majority_stabilizes_rescues_to_mid_not_high(self):
        # 初测 A,D（飘）+坏题A；追1轮答 A,A → 全好 [1,3,1,1] 多数稳 → 升"中"（封顶中，不给高）且停止追题
        s = self._run(["A", "D", "A", "A", "A"])
        self.assertEqual(s["probe_rounds"], 1)
        self.assertEqual(s["n_questions"], 5)
        self.assertEqual(s["probe_trail"], ["低", "中"])
        self.assertEqual(s["confidence"], "中")

    def test_stable_answers_no_probe(self):
        # 答得稳：不触发追题，题量=初始 3
        s = self._run(["A", "A", "A"])
        self.assertEqual(s["probe_rounds"], 0)
        self.assertEqual(s["n_questions"], 3)
        self.assertEqual(s["confidence"], "高")


class PrepareCaseTest(unittest.TestCase):
    def setUp(self):
        self._orig_out = config.OUTPUT_DIR
        self._tmp = tempfile.mkdtemp()
        config.OUTPUT_DIR = pathlib.Path(self._tmp)

    def tearDown(self):
        config.OUTPUT_DIR = self._orig_out

    def test_prepare_case_end_to_end_offline(self):
        llm = FakeLLM(router=prepare_router())
        # 只跑 2 维（1 团队不合 + 1 主动离职）够证明编排；全 9 维同理、慢
        dims = [prepare.quiz_gen.DIMENSIONS[0], prepare.quiz_gen.DIMENSIONS[4]]
        result = prepare.prepare_case(llm, "JD158_新媒体运营经理", "CV1_林女士",
                                      n_good=2, n_bad=1, n_others=3, dims=dims)

        # 名单：候选人 + 3 团队，姓名是事实（蒸馏 name= 覆盖）
        cast = result["cast"]
        self.assertEqual(len(cast), 4)
        cand = [c for c in cast if c["kind"] == "candidate"]
        self.assertEqual(len(cand), 1)
        self.assertEqual(cand[0]["name"], CAND_NAME)
        Cast.from_cards(cast)                       # 可直接入沙盘

        # 画像：2 维都有分
        scores = result["portrait"]["scores"]
        self.assertEqual(len(scores), 2)
        self.assertTrue(all("lean_label" in s and "confidence" in s for s in scores))

        # 场景库：与骨架等长、id 对得上
        scenes = json.loads(pathlib.Path(result["scene_bank_path"]).read_text(encoding="utf-8"))
        skel = prepare.scene_gen.load_skeleton()
        self.assertEqual(len(scenes), len(skel))
        self.assertEqual({s["id"] for s in scenes}, {s["id"] for s in skel})

        # 产物四件落盘
        d = prepare.case_dir("JD158", "CV1")
        for f in ("cast.json", "portrait.json", "scene_bank.json", "meta.json"):
            self.assertTrue((d / f).exists(), f"缺产物 {f}")

    def test_load_prepared_roundtrips(self):
        llm = FakeLLM(router=prepare_router())
        dims = [prepare.quiz_gen.DIMENSIONS[0]]
        prepare.prepare_case(llm, "JD158_新媒体运营经理", "CV1_林女士", dims=dims)
        # 列得出 + 读得回（不调 LLM）
        self.assertTrue(any(m["jd_id"] == "JD158" and m["cv_id"] == "CV1"
                            for m in prepare.list_prepared()))
        loaded = prepare.load_prepared("JD158", "CV1")
        self.assertEqual([c["name"] for c in loaded["cast"]][0], CAND_NAME)
        self.assertIn("scores", loaded["portrait"])
        self.assertTrue(pathlib.Path(loaded["scene_bank_path"]).exists())

    def test_load_prepared_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            prepare.load_prepared("NOPE", "NADA")


class PrepareServerRouteTest(unittest.TestCase):
    """服务端 /api/prepare mode=load 路由：装配进运行态全局（CAST/BANK/jd_text/画像）。"""
    def setUp(self):
        self._orig_out = config.OUTPUT_DIR
        self._tmp = tempfile.mkdtemp()
        config.OUTPUT_DIR = pathlib.Path(self._tmp)
        # 先现做一份案例进临时目录，供秒加载
        prepare.prepare_case(FakeLLM(router=prepare_router()),
                             "JD158_新媒体运营经理", "CV1_林女士",
                             dims=[prepare.quiz_gen.DIMENSIONS[0]])
        self._orig_cast = server.CAST
        self._orig_bank = server.BANK
        server.STATE["prep"] = server._fresh_prep()
        server.STATE["jd_text"] = ""

    def tearDown(self):
        config.OUTPUT_DIR = self._orig_out
        server.CAST = self._orig_cast
        server.BANK = self._orig_bank
        server.STATE["prep"] = server._fresh_prep()
        server.STATE["jd_text"] = ""

    def test_apply_prepared_swaps_globals(self):
        result = prepare.load_prepared("JD158", "CV1")
        server._apply_prepared(result)
        self.assertEqual(server.CAST.candidate().name, CAND_NAME)
        self.assertTrue(server.STATE["prep"]["ready"])
        self.assertIsNotNone(server.STATE["prep"]["portrait"])
        self.assertTrue(server.STATE["jd_text"])      # JD 驱动后 run 会二次贴岗
        # BANK 已换成案例专属场景库（id 与骨架一致）
        self.assertGreater(len(server.BANK.all()), 0)

    def test_apply_prepared_clears_stale_error(self):
        # 回归：上一轮"现做"失败留了红旗，这轮成功装配必须把它清掉，否则页面误报失败
        server.STATE["prep"]["error"] = "上一轮失败：LLMError: 维度X 出不合格题"
        result = prepare.load_prepared("JD158", "CV1")
        server._apply_prepared(result)
        self.assertIsNone(server.STATE["prep"]["error"])
        self.assertTrue(server.STATE["prep"]["ready"])


class PrepareLoadHTTPTest(unittest.TestCase):
    """实连 HTTP 走"秒加载"整条路径（自控 UTF-8 字节，绕开 shell/curl 编码坑）：
    复现作者场景——上一轮"现做"失败留了红旗，这轮 load 成功必须清掉、页面就绪。"""
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.thread.join(timeout=5)

    def setUp(self):
        self._orig_out = config.OUTPUT_DIR
        self._tmp = tempfile.mkdtemp()
        config.OUTPUT_DIR = pathlib.Path(self._tmp)
        prepare.prepare_case(FakeLLM(router=prepare_router()),
                             "JD158_新媒体运营经理", "CV1_林女士",
                             dims=[prepare.quiz_gen.DIMENSIONS[0]])
        self._orig_cast, self._orig_bank = server.CAST, server.BANK
        server.STATE["prep"] = server._fresh_prep()
        server.STATE["jd_text"] = ""

    def tearDown(self):
        config.OUTPUT_DIR = self._orig_out
        server.CAST, server.BANK = self._orig_cast, self._orig_bank
        server.STATE["prep"] = server._fresh_prep()
        server.STATE["jd_text"] = ""

    def _post(self, path, obj):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("POST", path, body=json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                  headers={"Content-Type": "application/json"})
        r = c.getresponse()
        body = json.loads(r.read().decode("utf-8"))
        c.close()
        return r.status, body

    def _get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path)
        r = c.getresponse()
        body = json.loads(r.read().decode("utf-8"))
        c.close()
        return r.status, body

    def test_load_over_http_clears_stale_error_and_readies(self):
        server.STATE["prep"]["error"] = "上一轮现做失败留下的红旗"     # 复现作者场景
        st, body = self._post("/api/prepare",
                              {"jd": "JD158_新媒体运营经理", "cv": "CV1_林女士", "mode": "load"})
        self.assertEqual(st, 200, body)
        self.assertTrue(body["ok"])
        self.assertTrue(body["ready"])
        st2, ps = self._get("/api/prep_state")
        self.assertTrue(ps["ready"])
        self.assertIsNone(ps["error"], "旧红旗没清掉——页面会误报失败")
        self.assertGreaterEqual(len((ps.get("portrait") or {}).get("scores") or []), 1)
        # 名单已换成案例的候选人
        _, state = self._get("/api/state")
        self.assertEqual(state["candidate"], CAND_NAME)

    def test_load_missing_case_returns_404(self):
        # data/ 里没有的 JD 名 → resolve_ids 抛 → 404（不静默吞）
        st, body = self._post("/api/prepare",
                              {"jd": "JD999_不存在", "cv": "CV1_林女士", "mode": "load"})
        self.assertEqual(st, 404)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
