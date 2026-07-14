import unittest
from unittest.mock import patch

from app.agents.tools import compliance_flags, edit_interaction


class EditInteractionTests(unittest.TestCase):
    def edit(self, request: str, llm_result: dict | None = None) -> dict:
        with patch("app.agents.tools.ask_json", return_value=llm_result or {}):
            return edit_interaction.invoke({"request": request})

    def test_name_correction(self):
        self.assertEqual(self.edit("The name should be Dr. Priya Nair")["hcp_name"], "Dr. Priya Nair")

    def test_sentiment_correction(self):
        self.assertEqual(self.edit("Change the sentiment to negative")["sentiment"], "negative")

    def test_channel_correction(self):
        self.assertEqual(self.edit("Change the last interaction's channel to in-person visit")["interaction_type"], "visit")

    def test_date_correction(self):
        self.assertEqual(self.edit("Change the visit date to 2026-08-15")["occurred_at"], "2026-08-15T09:00:00")

    def test_product_correction(self):
        self.assertEqual(self.edit("Set product to CardioMax")["products"], ["CardioMax"])

    def test_follow_up_correction(self):
        self.assertEqual(self.edit("Set follow-up action to email the study summary")["follow_up_action"], "email the study summary")

    def test_hallucinated_llm_fields_are_dropped(self):
        result = self.edit("Update the record", {"doctor_age": 55, "interaction_type": "meeting"})
        self.assertNotIn("doctor_age", result)
        self.assertNotIn("interaction_type", result)


class ComplianceTests(unittest.TestCase):
    def test_word_variants_are_flagged(self):
        flags = compliance_flags("The drug guarantees cures after an off label use with side effects and adverse events.")
        self.assertEqual(len(flags), 5)


if __name__ == "__main__":
    unittest.main()