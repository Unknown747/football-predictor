import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "experiments"
sys.path.insert(0, str(SCRIPT_DIR))

from benchmark_model_families import (  # noqa: E402
    LAB,
    calculate_metrics,
    closing_odds_probabilities,
    paired_week_bootstrap,
    safe_feature_columns,
    validate_output_path,
)


class BenchmarkModelFamiliesTests(unittest.TestCase):
    def test_feature_whitelist_excludes_odds_targets_and_post_match_fields(self):
        frame = pd.DataFrame({
            "home_form5_gf": [1.2],
            "h2h_n": [3],
            "sum_expected_goals": [2.7],
            "odds_pH": [0.5],
            "target_1x2": [0],
            "FTHG": [2],
        })
        self.assertEqual(
            safe_feature_columns(frame),
            ["home_form5_gf", "h2h_n", "sum_expected_goals"],
        )

    def test_multiclass_probability_metrics_are_perfect_for_certain_predictions(self):
        y = np.array([0, 1, 2])
        probabilities = np.eye(3, dtype=float) * 0.98 + 0.02 / 3
        metrics = calculate_metrics(y, probabilities, "multiclass")
        self.assertEqual(metrics["n"], 3)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertLess(metrics["logloss"], 0.03)
        self.assertLess(metrics["brier"], 0.001)

    def test_binary_probability_metrics(self):
        y = np.array([0, 0, 1, 1])
        probabilities = np.array([
            [0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9],
        ])
        metrics = calculate_metrics(y, probabilities, "binary")
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["auc"], 1.0)
        self.assertLess(metrics["logloss"], 0.2)

    def test_closing_odds_are_available_only_as_reference(self):
        rows = pd.DataFrame({
            "odds_pH": [0.5, np.nan],
            "odds_pD": [0.25, 0.3],
            "odds_pA": [0.25, 0.7],
            "odds_pOver25": [0.6, 0.4],
        })
        valid, probabilities = closing_odds_probabilities(rows, "1x2")
        self.assertEqual(valid.tolist(), [True, False])
        self.assertAlmostEqual(float(probabilities.sum()), 1.0)
        self.assertIsNone(closing_odds_probabilities(rows, "home_ou05"))

    def test_experiment_output_is_confined_to_model_lab(self):
        valid = LAB / "results" / "test-run"
        self.assertEqual(validate_output_path(valid), valid.resolve())
        with self.assertRaises(ValueError):
            validate_output_path(LAB.parent.parent / "models")

    def test_week_bootstrap_is_paired_and_reports_familywise_correction(self):
        base = pd.DataFrame({
            "_row_id": [1, 2, 3, 4],
            "Date": pd.to_datetime([
                "2025-08-01", "2025-08-02", "2025-08-08", "2025-08-09",
            ]),
            "y_true": [1, 1, 0, 0],
            "p0": [0.5] * 4,
            "p1": [0.5] * 4,
        })
        candidate = base.copy()
        candidate["p0"] = [0.1, 0.1, 0.9, 0.9]
        candidate["p1"] = [0.9, 0.9, 0.1, 0.1]
        result = paired_week_bootstrap(candidate, base, class_count=2, reps=128)
        self.assertLess(result["delta_logloss"], 0)
        self.assertEqual(result["unit"], "calendar_week")
        self.assertEqual(result["bonferroni_comparisons"], 32)


if __name__ == "__main__":
    unittest.main()
