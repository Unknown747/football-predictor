import sys
import unittest
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "experiments"
sys.path.insert(0, str(SCRIPT_DIR))

from feature_ablation import (  # noqa: E402
    GROUP_NAMES,
    MARKET_MODELS,
    build_feature_groups,
    coherence_diagnostics,
)


class FeatureAblationTests(unittest.TestCase):
    def test_groups_are_cumulative_and_cover_every_safe_feature(self):
        features = [
            "home_form5_ppg",
            "away_form5_ppg",
            "home_form10_ppg",
            "away_form10_ppg",
            "home_venue_form5_ppg",
            "away_venue_form5_ppg",
            "home_rest_days",
            "away_rest_days",
            "home_season_ppg",
            "away_season_ppg",
            "h2h_n",
            "diff_ppg5",
            "sum_expected_goals",
        ]
        groups = build_feature_groups(features)
        self.assertEqual(tuple(groups), GROUP_NAMES)
        self.assertEqual(groups["F0"], features[:2])
        self.assertEqual(groups["F1"], features[:4])
        self.assertEqual(groups["F2"], features[:6])
        self.assertEqual(groups["F3"], features[:10])
        self.assertEqual(groups["F4"], features[:11])
        self.assertEqual(groups["F5"], features)
        for previous, current in zip(GROUP_NAMES, GROUP_NAMES[1:]):
            self.assertTrue(set(groups[previous]).issubset(groups[current]))

    def test_unknown_safe_feature_fails_instead_of_being_silently_omitted(self):
        with self.assertRaisesRegex(ValueError, "not assigned"):
            build_feature_groups(["home_form5_ppg", "unclassified_feature"])

    def test_selected_model_exists_for_each_market(self):
        self.assertEqual(set(MARKET_MODELS), {
            "1x2", "ou25", "home_ou05", "home_ou15", "away_ou05", "away_ou15",
        })
        self.assertTrue(set(MARKET_MODELS.values()).issubset(
            {"lgbm", "xgboost", "histgb", "logreg"}
        ))

    def test_coherence_diagnostics_catches_team_goal_probability_violation(self):
        rows = []
        values = {
            "1x2": [0.5, 0.3, 0.2],
            "ou25": [0.6, 0.4],
            "home_ou05": [0.2, 0.8],
            "home_ou15": [0.15, 0.85],
            "away_ou05": [0.4, 0.6],
            "away_ou15": [0.5, 0.5],
        }
        for market, probabilities in values.items():
            rows.append({
                "fold": "test",
                "feature_group": "F0",
                "_row_id": 1,
                "market": market,
                "p0": probabilities[0],
                "p1": probabilities[1],
                "p2": probabilities[2] if len(probabilities) == 3 else None,
            })
        diagnostics = coherence_diagnostics(pd.DataFrame(rows)).set_index("check")
        self.assertEqual(
            diagnostics.loc["home_over15_le_over05", "violations"], 1
        )
        self.assertEqual(diagnostics.loc["away_over15_le_over05", "violations"], 0)


if __name__ == "__main__":
    unittest.main()
