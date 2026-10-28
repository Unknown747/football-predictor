#!/usr/bin/env python3
"""Focused contract checks for the primary EXP-06 inference mode."""

import unittest
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import predict


class FixedProbabilityModel:
    def __init__(self, classes, probabilities):
        self.classes_ = np.asarray(classes)
        self.probabilities = np.asarray(probabilities, dtype=float)

    def predict_proba(self, X):
        return self.probabilities.reshape(1, -1)


class Exp06PredictionTests(unittest.TestCase):
    def test_blend_aligns_model_class_order(self):
        models = {
            "1x2": [
                (FixedProbabilityModel([0, 1, 2], [0.2, 0.5, 0.3]), 0.25),
                (FixedProbabilityModel([2, 1, 0], [0.6, 0.2, 0.2]), 0.75),
            ]
        }
        result = predict.predict_exp06_market(
            models, "1x2", np.zeros((1, 74), dtype=float)
        )
        np.testing.assert_allclose(result, [0.2, 0.275, 0.525], atol=1e-12)
        self.assertAlmostEqual(float(result.sum()), 1.0)

    def test_binary_blend_returns_positive_class_probability(self):
        models = {
            "ou25": [
                (FixedProbabilityModel([0, 1], [0.6, 0.4]), 0.5),
                (FixedProbabilityModel([1, 0], [0.8, 0.2]), 0.5),
            ]
        }
        result = predict.predict_exp06_market(
            models, "ou25", np.zeros((1, 74), dtype=float)
        )
        np.testing.assert_allclose(result, [0.4, 0.6], atol=1e-12)

    def test_incomplete_classes_fail_closed(self):
        models = {
            "1x2": [
                (FixedProbabilityModel([0, 2], [0.4, 0.6]), 1.0),
            ]
        }
        with self.assertRaisesRegex(ValueError, "Kelas model tidak lengkap"):
            predict.predict_exp06_market(
                models, "1x2", np.zeros((1, 74), dtype=float)
            )

    def test_primary_bundle_loads_with_frozen_odds_free_features(self):
        models, features = predict.load_exp06_bundle()
        self.assertEqual(len(features), 74)
        self.assertFalse(any(column.startswith("odds_") for column in features))
        self.assertEqual(set(models), set(predict.MARKET_CLASS_COUNTS))
        self.assertEqual(
            predict.EXP06_PREDICTION_TAG,
            "EXP06_BLEND_V1_PRIMARY_REFERENCE_ONLY",
        )

        X = np.zeros((1, len(features)), dtype=float)
        for market, class_count in predict.MARKET_CLASS_COUNTS.items():
            result = predict.predict_exp06_market(models, market, X)
            self.assertEqual(result.shape, (class_count,))
            self.assertTrue(np.isfinite(result).all())
            self.assertTrue((result >= 0).all())
            self.assertAlmostEqual(float(result.sum()), 1.0, places=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
