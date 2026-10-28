import importlib.util
import csv
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import tempfile
import unittest
from pathlib import Path


TRACKER_PATH = Path(__file__).resolve().parents[1] / "paper" / "exp07_tracker.py"
SPEC = importlib.util.spec_from_file_location("exp07_tracker", TRACKER_PATH)
tracker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tracker)


class Exp07TrackerTests(unittest.TestCase):
    def setUp(self):
        self.model_info = {
            "model_tag": tracker.MODEL_TAG,
            "bundle_sha256": "bundle-hash",
            "manifest_sha256": "manifest-hash",
            "training_cutoff_inclusive": "2026-06-30",
        }
        self.prediction = {
            "date": "2026-10-29",
            "home_team": "Home",
            "away_team": "Away",
            "league_name": "Test League",
            "data_status": "OK",
            "prediction_mode": tracker.MODEL_TAG,
            "p_H": "0.6",
            "p_D": "0.2",
            "p_A": "0.2",
            "p_over25": "0.55",
            "p_home_over05": "0.8",
            "p_home_over15": "0.45",
            "p_away_over05": "0.7",
            "p_away_over15": "0.3",
        }
        self.fixture = {
            "date": "2026-10-29",
            "home_team": "Home",
            "away_team": "Away",
            "league_name": "Test League",
            "match_id_fotmob": "12345",
            "utc": "2026-10-29T12:00:00.000Z",
        }

    def test_capture_requires_future_kickoff_and_keeps_warning_rows(self):
        warning = dict(self.prediction, data_status="OK_WITH_WARNING")
        records, summary = tracker.build_forecast_records(
            [warning],
            [self.fixture],
            "2026-10-28T12:00:00Z",
            "2026-10-28T12:01:00Z",
            "prediction-hash",
            "fixture-hash",
            self.model_info,
            "commit",
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["prediction_data_status"], "OK_WITH_WARNING")
        self.assertEqual(summary["matched_prospective"], 1)

    def test_capture_rejects_match_that_has_started(self):
        with self.assertRaisesRegex(tracker.TrackerError, "tidak lagi prospektif"):
            tracker.build_forecast_records(
                [self.prediction],
                [self.fixture],
                "2026-10-29T12:00:00Z",
                "2026-10-29T12:01:00Z",
                "prediction-hash",
                "fixture-hash",
                self.model_info,
                "commit",
            )

    def test_capture_rejects_invalid_probability_sum(self):
        bad_prediction = dict(self.prediction, p_H="0.7")
        with self.assertRaisesRegex(tracker.TrackerError, "tidak berjumlah 1"):
            tracker.build_forecast_records(
                [bad_prediction],
                [self.fixture],
                "2026-10-28T12:00:00Z",
                "2026-10-28T12:01:00Z",
                "prediction-hash",
                "fixture-hash",
                self.model_info,
                "commit",
            )

    def test_capture_timestamp_must_match_snapshot_filename(self):
        tracker.verify_prediction_filename_timestamp(
            "predictions_20261028_082637.csv",
            tracker.parse_utc("2026-10-28T08:26:37Z", "timestamp"),
        )
        with self.assertRaisesRegex(tracker.TrackerError, "tidak cocok"):
            tracker.verify_prediction_filename_timestamp(
                "predictions_20261028_082637.csv",
                tracker.parse_utc("2026-10-28T08:30:00Z", "timestamp"),
            )

    def test_binary_scores_match_definitions(self):
        score = tracker.score_for("ou25", [0.8], 1)
        self.assertAlmostEqual(score["logloss"], -__import__("math").log(0.8))
        self.assertAlmostEqual(score["brier"], 0.04)
        self.assertEqual(score["correct"], 1)

    def test_scorecard_is_pending_without_results(self):
        record, _ = tracker.build_forecast_records(
            [self.prediction],
            [self.fixture],
            "2026-10-28T12:00:00Z",
            "2026-10-28T12:01:00Z",
            "prediction-hash",
            "fixture-hash",
            self.model_info,
            "commit",
        )
        scorecard, scored = tracker.make_scorecard(record, [])
        self.assertEqual(scored, 0)
        self.assertEqual(len(scorecard), 6)
        self.assertTrue(all(row["evidence_status"] == "PENDING_RESULTS"
                            for row in scorecard))
        self.assertTrue(all(row["readiness_assessment"] == "NOT_ASSESSED"
                            for row in scorecard))

    def test_scorecard_scores_finished_results_and_bootstraps_weeks(self):
        now = datetime.now(timezone.utc)
        captured = tracker.format_utc(now)
        predictions = []
        fixtures = []
        results = []
        for index, days_ahead in enumerate((1, 9)):
            kickoff = now + timedelta(days=days_ahead)
            prediction = dict(
                self.prediction,
                date=kickoff.date().isoformat(),
                home_team=f"Home {index}",
                away_team=f"Away {index}",
            )
            fixture = dict(
                self.fixture,
                date=kickoff.date().isoformat(),
                home_team=f"Home {index}",
                away_team=f"Away {index}",
                match_id_fotmob=str(20000 + index),
                utc=tracker.format_utc(kickoff),
            )
            predictions.append(prediction)
            fixtures.append(fixture)

        records, _ = tracker.build_forecast_records(
            predictions,
            fixtures,
            captured,
            captured,
            "prediction-hash",
            "fixture-hash",
            self.model_info,
            "commit",
        )
        for index, record in enumerate(records):
            kickoff = tracker.parse_utc(record["kickoff_utc"], "kickoff")
            results.append({
                "event_id": record["event_id"],
                "actual_kickoff_utc": tracker.format_utc(kickoff),
                "home_goals": index + 1,
                "away_goals": 0,
            })

        scorecard, scored = tracker.make_scorecard(records, results)
        self.assertEqual(scored, 2)
        self.assertEqual(scorecard[0]["completed_matches"], 2)
        self.assertEqual(scorecard[0]["distinct_kickoff_weeks"], 2)
        self.assertIsNotNone(
            scorecard[0]["95pct_week_cluster_bootstrap"]["logloss"]
        )
        self.assertEqual(
            scorecard[0]["evidence_status"], "PROSPECTIVE_DESCRIPTIVE_ONLY"
        )
        self.assertEqual(scorecard[0]["readiness_assessment"], "NOT_ASSESSED")

    def test_import_results_checks_capture_actual_kickoff_and_source(self):
        now = datetime.now(timezone.utc)
        actual_kickoff = now - timedelta(hours=2)
        captured = now - timedelta(hours=3)
        fixture = dict(
            self.fixture,
            date=actual_kickoff.date().isoformat(),
            utc=tracker.format_utc(actual_kickoff),
        )
        prediction = dict(self.prediction, date=fixture["date"])
        forecasts, _ = tracker.build_forecast_records(
            [prediction],
            [fixture],
            tracker.format_utc(captured),
            tracker.format_utc(captured),
            "prediction-hash",
            "fixture-hash",
            self.model_info,
            "commit",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            forecast_ledger = root / "forecasts.jsonl"
            result_ledger = root / "results.jsonl"
            tracker.append_chained_ledger(forecast_ledger, forecasts, "event_id")
            input_path = root / "results.csv"
            fields = [
                "event_id", "status", "home_goals", "away_goals",
                "actual_kickoff_utc", "result_source", "retrieved_at_utc",
            ]
            with input_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "event_id": forecasts[0]["event_id"],
                    "status": "FINISHED",
                    "home_goals": 2,
                    "away_goals": 1,
                    "actual_kickoff_utc": tracker.format_utc(actual_kickoff),
                    "result_source": "test feed",
                    "retrieved_at_utc": tracker.format_utc(now - timedelta(minutes=1)),
                })
            tracker.import_results(SimpleNamespace(
                ledger=forecast_ledger,
                result_ledger=result_ledger,
                input=input_path,
            ))
            stored = tracker.read_chained_ledger(result_ledger)
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["status"], "FINISHED")

    def test_ledger_is_append_only_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            item = {"event_id": "event-1", "probabilities": {"ou25": [0.5]}}
            self.assertEqual(
                tracker.append_chained_ledger(ledger, [item], "event_id"), 1
            )
            self.assertEqual(
                tracker.append_chained_ledger(ledger, [item], "event_id"), 0
            )
            self.assertEqual(len(tracker.read_chained_ledger(ledger)), 1)
            with self.assertRaisesRegex(tracker.TrackerError, "tidak boleh ditimpa"):
                tracker.append_chained_ledger(
                    ledger,
                    [{"event_id": "event-1", "probabilities": {"ou25": [0.6]}}],
                    "event_id",
                )
            text = ledger.read_text(encoding="utf-8").replace('"ou25":[0.5]', '"ou25":[0.4]')
            ledger.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(tracker.TrackerError, "Hash ledger tidak cocok"):
                tracker.read_chained_ledger(ledger)

    def test_result_targets_follow_six_market_definitions(self):
        targets = tracker.result_targets({}, 2, 1)
        self.assertEqual(targets, {
            "1x2": 0,
            "ou25": 1,
            "home_ou05": 1,
            "home_ou15": 1,
            "away_ou05": 1,
            "away_ou15": 0,
        })


if __name__ == "__main__":
    unittest.main()
