import unittest
from unittest.mock import patch

from app.agents.graph import classify


class TalkingPointClassificationTests(unittest.TestCase):
    def test_talking_point_phrasings_do_not_fall_through_to_log(self):
        messages = [
            "Help me prepare for Dr. Rao",
            "What should I bring up with Dr. Singh?",
            "Prep notes for tomorrow's call with Dr. Mehta",
            "Give me talking points for my next visit",
            "What should I discuss with Dr. Sharma next visit?",
        ]
        with patch("app.agents.graph.ask_json", return_value={"intent": "log_interaction"}):
            for message in messages:
                self.assertEqual(classify({"message": message})["intent"], "suggest_talking_points")


if __name__ == "__main__":
    unittest.main()