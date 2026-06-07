# tests/test_server.py
"""操作台 server 集成测试：http.client 实连一个本地起的服务线程。
依赖注入边界（非 mock）：以 sandbox3.server.LLM = FakeLLM(...) 注入测试替身；
产品代码无任何 mock 分支。覆盖 plan 四场景：
  1) GET /api/state → cast 含两人、candidate=周默；
  2) POST /api/import_cast 非法卡（无 candidate）→ 400；
  3) FakeLLM 注入后 POST /api/run {scenes:1}，轮询 /api/events 至 done →
     事件类型集合含 run_started/scene_open/beat_open/decision/audit/settle/done/saved；
  4) 跑中（running=True）再 POST /api/run → 409。"""
from __future__ import annotations
import http.client
import json
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer

import sandbox3.server as server
from sandbox3 import config
from tests.fakes import FakeLLM
from tests.fixtures import card_zhou, card_shen, router_factory


class ServerTestCase(unittest.TestCase):
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
        # 每个用例重置共享全局到干净基线（server 模块级全局可替换=依赖注入口）
        from sandbox3.cast import Cast
        server.CAST = Cast.load_default()
        server.STATE["running"] = False
        server.STATE["events"] = []
        server.STATE["jd"] = ""

    # ---- HTTP helpers ----
    def _conn(self):
        return http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)

    def _get(self, path):
        c = self._conn()
        c.request("GET", path)
        r = c.getresponse()
        body = json.loads(r.read().decode("utf-8"))
        c.close()
        return r.status, body

    def _post(self, path, obj):
        c = self._conn()
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        c.request("POST", path, body=data, headers={"Content-Type": "application/json"})
        r = c.getresponse()
        body = json.loads(r.read().decode("utf-8"))
        c.close()
        return r.status, body

    # ---- 场景 1：state ----
    def test_state_returns_cast_and_candidate(self):
        status, body = self._get("/api/state")
        self.assertEqual(status, 200)
        self.assertFalse(body["running"])
        names = [c["name"] for c in body["cast"]]
        self.assertEqual(names, ["周默", "沈雯"])
        self.assertEqual(body["candidate"], "周默")
        self.assertIn("kind", body["cast"][0])
        self.assertIn("role", body["cast"][0])
        self.assertGreater(len(body["scenes"]), 0)
        self.assertEqual(body["jd_len"], 0)

    # ---- 场景 2：非法名单 → 400 ----
    def test_import_cast_invalid_returns_400(self):
        # 两张 counterpart 卡：无 candidate → CastError → 400
        bad = dict(card_shen())
        bad2 = dict(card_shen())
        bad2["name"] = "另一个上级"
        status, body = self._post("/api/import_cast", {"cast": [bad, bad2]})
        self.assertEqual(status, 400)
        self.assertIn("candidate", body["error"])
        # 校验失败不得污染现有名单
        self.assertEqual([c.name for c in server.CAST.members()], ["周默", "沈雯"])

    def test_import_cast_valid_replaces(self):
        status, body = self._post("/api/import_cast", {"cast": [card_zhou(), card_shen()]})
        self.assertEqual(status, 200)
        self.assertEqual(body["candidate"], "周默")
        self.assertEqual([c["name"] for c in body["cast"]], ["周默", "沈雯"])

    # ---- 场景 3：FakeLLM 注入跑一局到 done ----
    def test_run_to_done_with_fake_llm(self):
        orig_llm = server.LLM
        orig_out = config.OUTPUT_DIR
        tmp = tempfile.mkdtemp()
        try:
            server.LLM = FakeLLM(router=router_factory())
            config.OUTPUT_DIR = __import__("pathlib").Path(tmp)
            status, body = self._post("/api/run", {"scenes": 1, "start": "C1-01", "seed": 1})
            self.assertEqual(status, 200)
            self.assertTrue(body["ok"])
            # 轮询 events 至 done/error
            types = self._poll_to_terminal()
            self.assertIn("done", types, f"事件未收口到 done；得到 {types}")
            self.assertNotIn("error", types, f"半局出错：{types}")
            for t in ("run_started", "scene_open", "beat_open", "decision", "audit", "settle"):
                self.assertIn(t, types, f"缺事件类型 {t}；得到 {types}")
            # saved 在 done 之后落盘（run 线程的 finally 前最后一步）
            self.assertIn("saved", types, f"未落盘 saved；得到 {types}")
        finally:
            server.LLM = orig_llm
            config.OUTPUT_DIR = orig_out

    def _poll_to_terminal(self, timeout=20.0):
        deadline = time.time() + timeout
        seen = []
        while time.time() < deadline:
            _, body = self._get(f"/api/events?since={len(seen)}")
            seen.extend(body["events"])
            types = {e["type"] for e in seen}
            if "done" in types or "error" in types:
                # done 之后还有 saved 事件，再拉一轮收尾
                time.sleep(0.2)
                _, body = self._get(f"/api/events?since={len(seen)}")
                seen.extend(body["events"])
                return {e["type"] for e in seen}
            time.sleep(0.1)
        return {e["type"] for e in seen}

    # ---- 场景 4：跑中再开 → 409 ----
    def test_run_while_running_returns_409(self):
        server.STATE["running"] = True
        try:
            status, body = self._post("/api/run", {"scenes": 1})
            self.assertEqual(status, 409)
            self.assertIn("error", body)
        finally:
            server.STATE["running"] = False

    def test_import_cast_while_running_returns_409(self):
        server.STATE["running"] = True
        try:
            status, body = self._post("/api/import_cast", {"cast": [card_zhou(), card_shen()]})
            self.assertEqual(status, 409)
        finally:
            server.STATE["running"] = False


if __name__ == "__main__":
    unittest.main()
