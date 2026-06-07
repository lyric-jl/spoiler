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


if __name__ == "__main__":
    unittest.main()
