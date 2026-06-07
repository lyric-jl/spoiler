# tests/test_cast.py
import unittest

from sandbox3.cast import Cast, CastError
from tests.fixtures import card_zhou, card_shen, card_colleague


class TestCastValidation(unittest.TestCase):
    def test_two_person_cast_ok(self):
        c = Cast.from_cards([card_zhou(), card_shen()])
        self.assertEqual(c.candidate().name, "周默")
        self.assertEqual([m.name for m in c.members()], ["周默", "沈雯"])

    def test_three_person_cast_ok(self):
        c = Cast.from_cards([card_zhou(), card_shen(), card_colleague()])
        self.assertEqual(len(c.members()), 3)
        self.assertEqual([m.name for m in c.others()], ["沈雯", "陈磊"])

    def test_no_candidate_rejected(self):
        with self.assertRaises(CastError):
            Cast.from_cards([card_shen()])

    def test_two_candidates_rejected(self):
        z2 = card_zhou(); z2["name"] = "李四"
        with self.assertRaises(CastError):
            Cast.from_cards([card_zhou(), z2, card_shen()])

    def test_bad_playbook_rejected(self):
        z = card_zhou(); z["playbook"] = ["只有一条"]
        with self.assertRaises(CastError):
            Cast.from_cards([z, card_shen()])

    def test_duplicate_name_rejected(self):
        with self.assertRaises(CastError):
            Cast.from_cards([card_zhou(), card_zhou()])

    def test_persona_block_contains_playbook(self):
        c = Cast.from_cards([card_zhou(), card_shen()])
        block = c.persona_block("周默")
        self.assertIn("行为手册", block)
        self.assertIn("周默", block)


if __name__ == "__main__":
    unittest.main()
