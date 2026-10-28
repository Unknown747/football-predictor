import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "experiments"
sys.path.insert(0, str(SCRIPT_DIR))

from simulate_odds_scenarios import (  # noqa: E402
    ODDS_MARGIN,
    SCENARIOS,
    _scenario_probabilities,
    generate_synthetic_odds,
    poisson_over_probability,
)


class SyntheticOddsScenarioTests(unittest.TestCase):
    def setUp(self):
        self.fixture = pd.Series({
            "_row_id": 42,
            "Date": pd.Timestamp("2026-08-01"),
            "Div": "L1",
            "HomeTeam": "Home",
            "AwayTeam": "Away",
            "diff_season_ppg": 0.8,
            "sum_expected_goals": 2.8,
            "home_form5_gf": 1.7,
            "home_form5_ga": 1.1,
            "away_form5_gf": 1.2,
            "away_form5_ga": 1.5,
            "home_venue_form5_gf": 1.8,
            "away_venue_form5_gf": 1.0,
        })
        self.priors = {
            "1x2": np.array([0.45, 0.27, 0.28]),
            "ou25": np.array([0.48, 0.52]),
            "home_ou05": np.array([0.25, 0.75]),
            "home_ou15": np.array([0.55, 0.45]),
            "away_ou05": np.array([0.4, 0.6]),
            "away_ou15": np.array([0.7, 0.3]),
        }

    def test_scenario_probabilities_are_valid_and_heavy_favourite_is_explicit(self):
        for market, prior in self.priors.items():
            for scenario in SCENARIOS:
                probs = _scenario_probabilities(self.fixture, market, scenario, prior)
                self.assertEqual(len(probs), 3 if market == "1x2" else 2)
                self.assertTrue(np.all(probs > 0))
                self.assertAlmostEqual(float(probs.sum()), 1.0)

        heavy = _scenario_probabilities(
            self.fixture, "1x2", "HEAVY_FAVOURITE", self.priors["1x2"]
        )
        mismatch = _scenario_probabilities(
            self.fixture, "1x2", "MISMATCHED_ODDS", self.priors["1x2"]
        )
        self.assertGreater(heavy[0], heavy[2])
        self.assertGreater(mismatch[2], mismatch[0])

    def test_overround_is_fixed_and_odds_are_decimal_prices(self):
        quotes = generate_synthetic_odds(pd.DataFrame([self.fixture]), self.priors)
        self.assertEqual(len(quotes), len(SCENARIOS) * 6)
        self.assertTrue(np.allclose(quotes["overround"], ODDS_MARGIN))
        valid_odds = quotes.filter(regex=r"^odds[0-2]$").stack()
        self.assertTrue((valid_odds > 1.0).all())
        self.assertEqual(set(quotes["quote_source"]), {"SYNTHETIC_NOT_BOOKMAKER"})

    def test_poisson_proxy_increases_over_probability_with_expected_goals(self):
        low = poisson_over_probability(0.8, 2.5)
        high = poisson_over_probability(3.8, 2.5)
        self.assertLess(low, high)


if __name__ == "__main__":
    unittest.main()
