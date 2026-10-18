import unittest
from evaluate import evaluate


class EvaluationTests(unittest.TestCase):
    def test_seeded_cold_warm_and_counterexample_matrix(self):
        result = evaluate()
        self.assertEqual(result["cases"], 60)
        self.assertEqual(result["diagnosis_matches"], 60)
        self.assertEqual(result["healthy_counterexamples_correct"], 60)
        self.assertEqual(result["warm_planner_calls"], 0)
        self.assertLess(result["warm_actions"], result["cold_actions"])
