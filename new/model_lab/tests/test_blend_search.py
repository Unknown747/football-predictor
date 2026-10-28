import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parents[1] / "experiments"
sys.path.insert(0, str(EXPERIMENT_DIR))

from benchmark_model_families import FOLDS, MARKETS, MODEL_NAMES  # noqa: E402
from search_blend_weights import (  # noqa: E402
    BLEND_NAME,
    _walk_forward_blends,
    blend_probabilities,
    choose_blend_weights,
    weight_grid,
)


class BlendSearchTests(unittest.TestCase):
    def test_simplex_grid_is_complete_and_nonnegative(self):
        candidates = weight_grid()
        self.assertEqual(len(candidates), 286)
        for weights in candidates:
            self.assertTrue(np.all(weights >= 0))
            self.assertAlmostEqual(float(weights.sum()), 1.0)

    def test_weight_search_prefers_the_perfect_model(self):
        y = np.array([0, 1, 0, 1])
        probabilities = np.array([
            [[0.99, 0.01], [0.1, 0.9], [0.4, 0.6], [0.6, 0.4]],
            [[0.01, 0.99], [0.9, 0.1], [0.4, 0.6], [0.6, 0.4]],
            [[0.99, 0.01], [0.1, 0.9], [0.4, 0.6], [0.6, 0.4]],
            [[0.01, 0.99], [0.9, 0.1], [0.4, 0.6], [0.6, 0.4]],
        ])
        weights = choose_blend_weights(y, probabilities, "binary")
        self.assertEqual(weights.tolist(), [1.0, 0.0, 0.0, 0.0])
        self.assertTrue(np.allclose(
            blend_probabilities(probabilities, weights).sum(axis=1), 1.0
        ))

    def _synthetic_oof_predictions(self):
        rows = []
        for fold_index, fold in enumerate(FOLDS):
            for market, (_, _, class_count) in MARKETS.items():
                for row_index in range(12):
                    row_id = fold_index * 1000 + row_index
                    label = row_index % class_count
                    for model_index, model in enumerate(MODEL_NAMES):
                        correct = np.full(class_count, 0.1 / max(class_count - 1, 1))
                        correct[label] = 0.9
                        probabilities = np.roll(
                            correct, model_index % class_count
                        )
                        probabilities = probabilities / probabilities.sum()
                        rows.append({
                            "_row_id": row_id,
                            "Date": pd.Timestamp("2022-07-01")
                            + pd.Timedelta(days=fold_index * 400 + row_index),
                            "Div": "TST",
                            "HomeTeam": "Home",
                            "AwayTeam": "Away",
                            "fold": fold["name"],
                            "market": market,
                            "model": model,
                            "y_true": label,
                            **{
                                f"p{class_id}": (
                                    float(probabilities[class_id])
                                    if class_id < class_count else np.nan
                                )
                                for class_id in range(3)
                            },
                        })
        return pd.DataFrame(rows)

    def test_latest_fold_weights_do_not_use_latest_fold_labels(self):
        predictions = self._synthetic_oof_predictions()
        _, original_weights = _walk_forward_blends(predictions)
        changed = predictions.copy()
        latest_mask = changed["fold"] == FOLDS[-1]["name"]
        for market, (_, _, class_count) in MARKETS.items():
            market_mask = latest_mask & (changed["market"] == market)
            changed.loc[market_mask, "y_true"] = (
                changed.loc[market_mask, "y_true"] + 1
            ) % class_count
        _, changed_weights = _walk_forward_blends(changed)

        original_latest = original_weights.loc[
            original_weights["fold"] == FOLDS[-1]["name"]
        ].reset_index(drop=True)
        changed_latest = changed_weights.loc[
            changed_weights["fold"] == FOLDS[-1]["name"]
        ].reset_index(drop=True)
        pd.testing.assert_frame_equal(original_latest, changed_latest)
        self.assertNotIn(
            FOLDS[-1]["name"],
            original_latest["training_folds"].iloc[0],
        )
        self.assertTrue(
            (original_weights["market"].map(lambda _: True)).all()
        )
        self.assertTrue((original_weights["weight_lgbm"].between(0, 1)).all())
        self.assertEqual(
            int((original_weights["weight_lgbm"] +
                 original_weights["weight_xgboost"] +
                 original_weights["weight_histgb"] +
                 original_weights["weight_logreg"] - 1.0).abs().max() < 1e-10),
            1,
        )
        self.assertEqual(BLEND_NAME, "OOF_BLEND_PREVIOUS_FOLDS")


if __name__ == "__main__":
    unittest.main()
