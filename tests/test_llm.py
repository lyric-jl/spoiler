# tests/test_llm.py
import unittest

from sandbox3.llm import DeepSeekClient, LLMError, _strip_fences


class TestStripFences(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_strip_fences('{"a": 1}'), '{"a": 1}')

    def test_fenced(self):
        self.assertEqual(_strip_fences('```json\n{"a": 1}\n```'), '{"a": 1}')


class TestClientGuards(unittest.TestCase):
    def test_no_key_raises_loudly(self):
        c = DeepSeekClient(api_key="")
        with self.assertRaises(LLMError):
            c.complete("s", "u")


class TestCompleteJsonRetry(unittest.TestCase):
    """DeepSeek 偶发吐坏 JSON——complete_json 重新取响应重试，仍失败才抛。"""

    def test_retries_bad_json_then_succeeds(self):
        c = DeepSeekClient(api_key="x")
        calls = {"n": 0}

        def fake_complete(system, user, **kw):
            calls["n"] += 1
            return '{"bad": ,}' if calls["n"] == 1 else '{"ok": 1}'

        c.complete = fake_complete                       # 替身：不走真网络
        self.assertEqual(c.complete_json("s", "u"), {"ok": 1})
        self.assertEqual(calls["n"], 2)                  # 第1次坏 JSON、重试第2次成功

    def test_raises_after_all_bad_json(self):
        c = DeepSeekClient(api_key="x")
        c.complete = lambda system, user, **kw: '{still bad,'
        with self.assertRaises(LLMError):
            c.complete_json("s", "u", json_retries=1)    # 2 次都坏 → 大声抛


if __name__ == "__main__":
    unittest.main()
