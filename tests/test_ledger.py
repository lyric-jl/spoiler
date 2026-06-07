import unittest

from sandbox3.ledger import entry, visible, ledger_text


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.led = [
            entry("入职第1周·周三", "第1幕[接活]：摘要A", ["周默", "沈雯"]),
            entry("入职第1周·周五", "第1幕后果结算：私聊 → 结果", ["沈雯", "陈磊"]),
        ]

    def test_visible_filters_by_witness(self):
        self.assertEqual(len(visible(self.led, "周默")), 1)
        self.assertEqual(len(visible(self.led, "沈雯")), 2)
        self.assertEqual(len(visible(self.led, "路人")), 0)

    def test_text_with_time_prefix(self):
        t = ledger_text(self.led)
        self.assertIn("[入职第1周·周三]", t)
        self.assertNotIn("在场", t)

    def test_text_with_witnesses(self):
        t = ledger_text(self.led, show_witnesses=True)
        self.assertIn("（在场：沈雯、陈磊）", t)

    def test_empty_message(self):
        self.assertEqual(ledger_text([]), "（尚无可引用的既往事件）")


if __name__ == "__main__":
    unittest.main()
