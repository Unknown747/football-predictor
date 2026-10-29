#!/usr/bin/env python3
"""Append-only, no-stakes prospective tracker for the frozen EXP-06 bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAPER = Path(__file__).resolve().parent
FORECAST_LEDGER = PAPER / "exp07_forecasts.jsonl"
RESULT_LEDGER = PAPER / "exp07_results.jsonl"
PROTOCOL_PATH = PAPER / "exp07_protocol.json"
MODEL_TAG = "EXP06_BLEND_V1_PRIMARY_REFERENCE_ONLY"
MODEL_DIR = ROOT / "models" / "exp06_blend_v1"
EPSILON = 1e-15
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 20261028

MARKETS = {
    "1x2": ("p_H", "p_D", "p_A"),
    "ou25": ("p_over25",),
    "home_ou05": ("p_home_over05",),
    "home_ou15": ("p_home_over15",),
    "away_ou05": ("p_away_over05",),
    "away_ou15": ("p_away_over15",),
}
PREDICTION_KEY = ("date", "home_team", "away_team", "league_name")
VALID_DATA_STATUSES = {"OK", "OK_WITH_WARNING"}


class TrackerError(ValueError):
    """Raised for invalid or unsafe prospective-tracking input."""


def canonical_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_bundle(bundle_dir):
    """Hash names and contents in stable order, not filesystem timestamps."""
    bundle_dir = Path(bundle_dir).resolve()
    digest = hashlib.sha256()
    for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(bundle_dir).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def load_and_verify_model(bundle_dir=MODEL_DIR):
    bundle_dir = Path(bundle_dir).resolve()
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        raise TrackerError(f"Model manifest tidak ditemukan: {manifest_path}")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrackerError(f"Manifest model tidak valid: {exc}") from exc

    if (
        manifest.get("mode") != "EXP06_BLEND_V1"
        or manifest.get("prediction_mode") != MODEL_TAG
        or manifest.get("status") != "REFERENCE_ONLY"
        or manifest.get("betting_ready") is not False
        or set(manifest.get("markets", {})) != set(MARKETS)
    ):
        raise TrackerError(
            "Bundle bukan EXP-06 REFERENCE_ONLY yang dibekukan; "
            "tracker menolak mengubah klaim status model."
        )

    for market, market_info in manifest.get("markets", {}).items():
        for model_name, model_info in market_info.get("models", {}).items():
            filename = model_info.get("file")
            expected = model_info.get("sha256")
            if not filename or not expected:
                raise TrackerError(
                    f"Metadata hash model tidak lengkap: {market}/{model_name}"
                )
            artifact = (bundle_dir / filename).resolve()
            if artifact.parent != bundle_dir or not artifact.is_file():
                raise TrackerError(
                    f"Artefak model hilang atau path tidak aman: {filename}"
                )
            actual = sha256_file(artifact)
            if actual != expected:
                raise TrackerError(
                    f"Hash artefak model tidak cocok: {market}/{model_name}"
                )

    return {
        "model_tag": MODEL_TAG,
        "bundle_sha256": hash_bundle(bundle_dir),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "training_cutoff_inclusive": manifest.get("training_cutoff_inclusive"),
        "manifest": manifest,
    }


def parse_utc(value, field_name):
    if not value:
        raise TrackerError(f"{field_name} wajib berisi timestamp dengan zona waktu.")
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TrackerError(f"{field_name} bukan timestamp ISO yang valid: {text}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrackerError(f"{field_name} harus menyertakan zona waktu UTC.")
    return parsed.astimezone(timezone.utc)


def format_utc(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def verify_prediction_filename_timestamp(path, captured_at):
    match = re.fullmatch(
        r"predictions_(\d{8})_(\d{6})(?:_[A-Za-z0-9-]+)*\.csv",
        Path(path).name,
    )
    if not match:
        return
    filename_time = datetime.strptime(
        "".join(match.groups()), "%Y%m%d%H%M%S"
    ).replace(tzinfo=timezone.utc)
    if filename_time != captured_at:
        raise TrackerError(
            "Timestamp UTC tidak cocok dengan waktu pada nama snapshot prediksi."
        )


def event_id(match_id, kickoff_utc):
    return hashlib.sha256(
        f"fotmob:{match_id}:{kickoff_utc}".encode("utf-8")
    ).hexdigest()


def read_csv(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise TrackerError(f"CSV kosong atau tanpa header: {path}")
        return reader.fieldnames, list(reader)


def probability(row, column):
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError):
        raise TrackerError(f"Probabilitas {column} hilang atau bukan angka.")
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise TrackerError(f"Probabilitas {column} di luar rentang [0, 1].")
    return value


def probabilities_from_prediction(row):
    result = {
        "1x2": [
            probability(row, "p_H"),
            probability(row, "p_D"),
            probability(row, "p_A"),
        ],
        "ou25": [probability(row, "p_over25")],
        "home_ou05": [probability(row, "p_home_over05")],
        "home_ou15": [probability(row, "p_home_over15")],
        "away_ou05": [probability(row, "p_away_over05")],
        "away_ou15": [probability(row, "p_away_over15")],
    }
    if abs(sum(result["1x2"]) - 1.0) > 1e-5:
        raise TrackerError("Probabilitas 1X2 tidak berjumlah 1.")
    complements = {
        "ou25": ("p_under25",),
        "home_ou05": ("p_home_under05",),
        "home_ou15": ("p_home_under15",),
        "away_ou05": ("p_away_under05",),
        "away_ou15": ("p_away_under15",),
    }
    for market, fields in complements.items():
        if fields[0] in row and str(row[fields[0]]).strip():
            if abs(result[market][0] + probability(row, fields[0]) - 1.0) > 1e-5:
                raise TrackerError(f"Probabilitas {market} tidak saling melengkapi.")
    return result


def get_git_commit(root=ROOT):
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def build_forecast_records(
    prediction_rows,
    fixture_rows,
    captured_at_utc,
    registered_at_utc,
    prediction_sha256,
    fixture_sha256,
    model_info,
    git_commit,
):
    captured_at = parse_utc(captured_at_utc, "captured_at_utc")
    registered_at = parse_utc(registered_at_utc, "registered_at_utc")
    fixture_by_key = {}
    seen_ids = set()
    for fixture in fixture_rows:
        key = tuple(str(fixture.get(field, "")).strip() for field in PREDICTION_KEY)
        if not all(key):
            raise TrackerError("Fixture kehilangan identitas pertandingan.")
        if key in fixture_by_key:
            raise TrackerError(f"Fixture duplikat: {key}")
        fixture_by_key[key] = fixture

    records = []
    excluded_statuses = Counter()
    unmatched = 0
    for prediction in prediction_rows:
        status = str(prediction.get("data_status", "")).strip()
        if status not in VALID_DATA_STATUSES:
            excluded_statuses[status or "MISSING"] += 1
            continue
        if prediction.get("prediction_mode") != MODEL_TAG:
            raise TrackerError(
                "Snapshot memuat tag model selain EXP-06 REFERENCE_ONLY."
            )
        key = tuple(str(prediction.get(field, "")).strip() for field in PREDICTION_KEY)
        fixture = fixture_by_key.get(key)
        if fixture is None:
            unmatched += 1
            continue
        kickoff = parse_utc(fixture.get("utc"), "fixture.utc")
        if kickoff <= captured_at:
            raise TrackerError(
                f"Fixture tidak lagi prospektif saat diprediksi: {key} "
                f"(kickoff {format_utc(kickoff)})."
            )
        match_id = str(fixture.get("match_id_fotmob", "")).strip()
        if not match_id:
            raise TrackerError(f"Fixture tanpa match_id_fotmob: {key}")
        key_id = event_id(match_id, format_utc(kickoff))
        if key_id in seen_ids:
            raise TrackerError(f"Event duplikat di input: {key_id}")
        seen_ids.add(key_id)
        probabilities = probabilities_from_prediction(prediction)
        records.append({
            "event_id": key_id,
            "match_id_fotmob": match_id,
            "kickoff_utc": format_utc(kickoff),
            "captured_at_utc": format_utc(captured_at),
            "registered_at_utc": format_utc(registered_at),
            "home_team": key[1],
            "away_team": key[2],
            "league_name": key[3],
            "prediction_data_status": status,
            "prediction_sha256": prediction_sha256,
            "fixture_sha256": fixture_sha256,
            "model_tag": MODEL_TAG,
            "model_manifest_sha256": model_info["manifest_sha256"],
            "model_bundle_sha256": model_info["bundle_sha256"],
            "git_commit_at_registration": git_commit,
            "probabilities": probabilities,
        })
    return records, {
        "excluded_statuses": dict(excluded_statuses),
        "unmatched_predictions": unmatched,
        "matched_prospective": len(records),
    }


def seal_record(record, previous_hash):
    payload = dict(record)
    payload["previous_record_sha256"] = previous_hash
    payload["record_sha256"] = hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return payload


def read_chained_ledger(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    previous_hash = ""
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TrackerError(f"Ledger rusak pada baris {line_number}.") from exc
            recorded_hash = row.get("record_sha256")
            if row.get("previous_record_sha256") != previous_hash:
                raise TrackerError(f"Rantai hash ledger putus pada baris {line_number}.")
            payload = {key: value for key, value in row.items() if key != "record_sha256"}
            expected_hash = hashlib.sha256(
                canonical_json(payload).encode("utf-8")
            ).hexdigest()
            if recorded_hash != expected_hash:
                raise TrackerError(f"Hash ledger tidak cocok pada baris {line_number}.")
            rows.append(row)
            previous_hash = recorded_hash
    return rows


def append_chained_ledger(path, records, unique_key):
    path = Path(path)
    existing = read_chained_ledger(path)
    existing_by_key = {row[unique_key]: row for row in existing}
    additions = []
    for record in records:
        key = record[unique_key]
        prior = existing_by_key.get(key)
        if prior:
            comparable = {
                k: v for k, v in prior.items()
                if k not in {
                    "previous_record_sha256", "record_sha256", "registered_at_utc"
                }
            }
            candidate = {k: v for k, v in record.items() if k != "registered_at_utc"}
            if comparable != candidate:
                raise TrackerError(
                    f"Rekaman {key} sudah ada dan tidak boleh ditimpa."
                )
            continue
        additions.append(record)
        existing_by_key[key] = record

    previous_hash = existing[-1]["record_sha256"] if existing else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in additions:
            sealed = seal_record(record, previous_hash)
            handle.write(canonical_json(sealed) + "\n")
            previous_hash = sealed["record_sha256"]
        handle.flush()
        os.fsync(handle.fileno())
    return len(additions)


def ensure_protocol(protocol_path, model_info, first_capture, git_commit):
    protocol_path = Path(protocol_path)
    if protocol_path.exists():
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        if (
            protocol.get("model_manifest_sha256") != model_info["manifest_sha256"]
            or protocol.get("model_bundle_sha256") != model_info["bundle_sha256"]
            or protocol.get("model_tag") != MODEL_TAG
        ):
            raise TrackerError(
                "Model bundle berubah sejak EXP-07 dimulai; "
                "buat eksperimen terpisah, jangan gabungkan hasil."
            )
        return protocol

    protocol = {
        "experiment": "EXP-07",
        "status": "PROSPECTIVE_PAPER_ONLY",
        "created_at_utc": first_capture["registered_at_utc"],
        "first_forecast_at_utc": first_capture["captured_at_utc"],
        "model_tag": MODEL_TAG,
        "model_manifest_sha256": model_info["manifest_sha256"],
        "model_bundle_sha256": model_info["bundle_sha256"],
        "training_cutoff_inclusive": model_info["training_cutoff_inclusive"],
        "git_commit_at_registration": git_commit,
        "markets": list(MARKETS),
        "primary_metrics": [
            "logloss",
            "brier",
            "ece_10bin",
            "accuracy",
            "completed_match_coverage",
        ],
        "uncertainty": (
            "95% percentile intervals from 1,000 deterministic week-cluster "
            "bootstrap replicates; omitted when fewer than two completed weeks exist."
        ),
        "inclusion": (
            "One immutable EXP-06 forecast per FotMob match ID and scheduled "
            "kickoff; prediction must precede scheduled kickoff; only actual "
            "finished scores are scored."
        ),
        "exclusions": (
            "No historical replay, no post-kickoff replacement, no stakes, "
            "no ROI/profit claim, and no readiness certification."
        ),
        "readiness_assessment": "NOT_ASSESSED",
        "odds_comparison": (
            "Not available for this cohort: no bookmaker source and quote "
            "timestamp were captured."
        ),
    }
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    with protocol_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(protocol, indent=2, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return protocol


def capture(args):
    captured_at = parse_utc(args.captured_at_utc, "--captured-at-utc")
    verify_prediction_filename_timestamp(args.predictions, captured_at)
    model_info = load_and_verify_model(args.bundle_dir)
    if args.protocol.exists() != args.ledger.exists():
        raise TrackerError(
            "Protocol dan ledger tidak konsisten; periksa keduanya sebelum melanjutkan."
        )
    prediction_fields, prediction_rows = read_csv(args.predictions)
    fixture_fields, fixture_rows = read_csv(args.fixtures)
    if not set(PREDICTION_KEY).issubset(prediction_fields):
        raise TrackerError("CSV prediksi tidak memiliki kolom identitas wajib.")
    if not set(PREDICTION_KEY + ("utc", "match_id_fotmob")).issubset(fixture_fields):
        raise TrackerError("CSV fixture tidak memiliki UTC kick-off dan match ID.")

    prediction_sha = sha256_file(args.predictions)
    fixture_sha = sha256_file(args.fixtures)
    registered_at = datetime.now(timezone.utc)
    records, summary = build_forecast_records(
        prediction_rows,
        fixture_rows,
        format_utc(captured_at),
        format_utc(registered_at),
        prediction_sha,
        fixture_sha,
        model_info,
        get_git_commit(),
    )
    if not records and not args.protocol.exists():
        raise TrackerError("Tidak ada prediksi prospektif valid untuk membuka EXP-07.")
    old_records = read_chained_ledger(args.ledger)
    new_records = (
        append_chained_ledger(args.ledger, records, "event_id")
        if records else 0
    )
    if not args.protocol.exists():
        ensure_protocol(args.protocol, model_info, records[0], get_git_commit())
    else:
        ensure_protocol(args.protocol, model_info, records[0] if records else {
            "registered_at_utc": format_utc(registered_at),
            "captured_at_utc": format_utc(captured_at),
        }, get_git_commit())

    print(f"Snapshot prediksi: {args.predictions}")
    print(f"Timestamp prediksi UTC: {format_utc(captured_at)}")
    print(f"Fixture prospektif valid: {summary['matched_prospective']}")
    print(f"Prediksi baru direkam: {new_records}")
    print(f"Total cohort: {len(old_records) + new_records}")
    print(f"Prediksi tanpa fixture cocok: {summary['unmatched_predictions']}")
    print(f"Status yang dikecualikan: {summary['excluded_statuses']}")
    print(f"Manifest model SHA-256: {model_info['manifest_sha256']}")
    print("Status: menunggu hasil pertandingan; kesiapan tidak dinilai.")


def result_targets(record, home_goals, away_goals):
    return {
        "1x2": 0 if home_goals > away_goals else 1 if home_goals == away_goals else 2,
        "ou25": int(home_goals + away_goals > 2.5),
        "home_ou05": int(home_goals > 0.5),
        "home_ou15": int(home_goals > 1.5),
        "away_ou05": int(away_goals > 0.5),
        "away_ou15": int(away_goals > 1.5),
    }


def import_results(args):
    forecasts = read_chained_ledger(args.ledger)
    if not forecasts:
        raise TrackerError("Belum ada cohort prospektif yang tercatat.")
    forecast_by_event = {row["event_id"]: row for row in forecasts}
    _, rows = read_csv(args.input)
    required = {
        "event_id", "status", "home_goals", "away_goals",
        "actual_kickoff_utc", "result_source", "retrieved_at_utc",
    }
    if rows and not required.issubset(rows[0]):
        raise TrackerError(f"CSV hasil perlu kolom: {sorted(required)}")
    candidates = []
    seen = set()
    existing = {
        row["event_id"]: row for row in read_chained_ledger(args.result_ledger)
    }
    for row in rows:
        event = str(row.get("event_id", "")).strip()
        if not event or event in seen:
            raise TrackerError(f"Event ID kosong atau duplikat di hasil: {event!r}")
        seen.add(event)
        forecast = forecast_by_event.get(event)
        if forecast is None:
            raise TrackerError(f"Event tidak ada di cohort: {event}")
        if str(row.get("status", "")).strip().upper() != "FINISHED":
            raise TrackerError(f"Hasil untuk {event} belum berstatus FINISHED.")
        try:
            home_goals = int(row["home_goals"])
            away_goals = int(row["away_goals"])
        except (TypeError, ValueError) as exc:
            raise TrackerError(f"Skor bukan bilangan bulat untuk {event}.") from exc
        if home_goals < 0 or away_goals < 0:
            raise TrackerError(f"Skor negatif tidak valid untuk {event}.")
        actual_kickoff = parse_utc(
            row["actual_kickoff_utc"], f"{event}.actual_kickoff_utc"
        )
        captured_at = parse_utc(forecast["captured_at_utc"], f"{event}.captured_at")
        if captured_at >= actual_kickoff:
            raise TrackerError(
                f"Prediksi {event} tidak mendahului kick-off aktual; hasil ditolak."
            )
        retrieved_at = parse_utc(row["retrieved_at_utc"], f"{event}.retrieved_at_utc")
        if retrieved_at < actual_kickoff:
            raise TrackerError(f"Hasil {event} diambil sebelum kick-off.")
        registered_at = datetime.now(timezone.utc)
        if retrieved_at > registered_at:
            raise TrackerError(f"Waktu pengambilan hasil {event} masih di masa depan.")
        source = str(row.get("result_source", "")).strip()
        if not source:
            raise TrackerError(f"Sumber hasil wajib dicatat untuk {event}.")
        item = {
            "event_id": event,
            "match_id_fotmob": forecast["match_id_fotmob"],
            "actual_kickoff_utc": format_utc(actual_kickoff),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "status": "FINISHED",
            "result_source": source,
            "retrieved_at_utc": format_utc(retrieved_at),
            "registered_at_utc": format_utc(registered_at),
        }
        prior = existing.get(event)
        if prior:
            comparable = {
                key: value for key, value in prior.items()
                if key not in {"previous_record_sha256", "record_sha256", "registered_at_utc"}
            }
            candidate = {key: value for key, value in item.items() if key != "registered_at_utc"}
            if comparable != candidate:
                raise TrackerError(
                    f"Hasil {event} sudah tercatat dan tidak boleh ditimpa."
                )
        candidates.append(item)
    added = append_chained_ledger(args.result_ledger, candidates, "event_id")
    print(f"Hasil baru dicatat: {added}; hasil identik yang sudah ada tidak ditimpa.")


def score_for(market, prediction, target):
    if market == "1x2":
        probs = [min(max(float(p), EPSILON), 1.0) for p in prediction]
        total = sum(probs)
        probs = [p / total for p in probs]
        label = int(target)
        return {
            "logloss": -math.log(probs[label]),
            "brier": sum(
                (prob - int(index == label)) ** 2
                for index, prob in enumerate(probs)
            ),
            "confidence": max(probs),
            "correct": int(probs.index(max(probs)) == label),
            "observed": int(probs.index(max(probs)) == label),
        }
    p = min(max(float(prediction[0]), EPSILON), 1.0 - EPSILON)
    y = int(target)
    predicted = int(p > 0.5)
    return {
        "logloss": -(y * math.log(p) + (1 - y) * math.log1p(-p)),
        "brier": (p - y) ** 2,
        "confidence": p,
        "correct": int(predicted == y),
        "observed": y,
    }


def ece(records):
    if not records:
        return None
    result = 0.0
    for bin_index in range(10):
        lower = bin_index / 10
        upper = (bin_index + 1) / 10
        group = [
            row for row in records
            if row["confidence"] >= lower
            and (row["confidence"] < upper if bin_index < 9
                 else row["confidence"] <= upper)
        ]
        if group:
            avg_conf = sum(row["confidence"] for row in group) / len(group)
            avg_observed = sum(row["observed"] for row in group) / len(group)
            result += len(group) / len(records) * abs(avg_observed - avg_conf)
    return result


def metric_values(rows):
    return {
        "logloss": sum(row["logloss"] for row in rows) / len(rows),
        "brier": sum(row["brier"] for row in rows) / len(rows),
        "ece_10bin": ece(rows),
        "accuracy": sum(row["correct"] for row in rows) / len(rows),
    }


def bootstrap_intervals(rows, market, replicates=BOOTSTRAP_REPLICATES):
    clusters = defaultdict(list)
    for row in rows:
        kickoff = parse_utc(row["actual_kickoff_utc"], "actual_kickoff_utc")
        iso = kickoff.date().isocalendar()
        clusters[f"{iso.year}-W{iso.week:02d}"].append(row)
    if len(clusters) < 2:
        return {key: None for key in ("logloss", "brier", "ece_10bin", "accuracy")}
    cluster_keys = sorted(clusters)
    rng = random.Random(BOOTSTRAP_SEED + list(MARKETS).index(market))
    values = defaultdict(list)
    for _ in range(replicates):
        selected = [rng.choice(cluster_keys) for _ in cluster_keys]
        sample = [row for key in selected for row in clusters[key]]
        for metric, value in metric_values(sample).items():
            values[metric].append(value)
    intervals = {}
    for metric in ("logloss", "brier", "ece_10bin", "accuracy"):
        ordered = sorted(values[metric])
        low_index = max(0, math.floor(0.025 * (replicates - 1)))
        high_index = min(replicates - 1, math.ceil(0.975 * (replicates - 1)))
        intervals[metric] = [ordered[low_index], ordered[high_index]]
    return intervals


def make_scorecard(forecasts, results):
    result_by_event = {row["event_id"]: row for row in results}
    rows_by_market = defaultdict(list)
    scored_results = 0
    for forecast in forecasts:
        result = result_by_event.get(forecast["event_id"])
        if result is None:
            continue
        scored_results += 1
        targets = result_targets(
            forecast, int(result["home_goals"]), int(result["away_goals"])
        )
        for market in MARKETS:
            row = score_for(
                market, forecast["probabilities"][market], targets[market]
            )
            row["actual_kickoff_utc"] = result["actual_kickoff_utc"]
            rows_by_market[market].append(row)

    scorecard = []
    total = len(forecasts)
    kickoff_weeks = set()
    for row in rows_by_market.get("1x2", []):
        kickoff = parse_utc(row["actual_kickoff_utc"], "actual_kickoff_utc")
        iso = kickoff.date().isocalendar()
        kickoff_weeks.add(f"{iso.year}-W{iso.week:02d}")
    for market in MARKETS:
        rows = rows_by_market[market]
        scored = len(rows)
        values = metric_values(rows) if rows else {
            "logloss": None,
            "brier": None,
            "ece_10bin": None,
            "accuracy": None,
        }
        scorecard.append({
            "market": market,
            "captured_fixtures": total,
            "completed_matches": scored,
            "completed_match_coverage": scored / total if total else 0.0,
            "distinct_kickoff_weeks": len(kickoff_weeks) if rows else 0,
            **values,
            "95pct_week_cluster_bootstrap": (
                bootstrap_intervals(rows, market) if rows else None
            ),
            "evidence_status": (
                "PENDING_RESULTS" if not scored else "PROSPECTIVE_DESCRIPTIVE_ONLY"
            ),
            "readiness_assessment": "NOT_ASSESSED",
        })
    return scorecard, scored_results


def write_scorecard(args):
    forecasts = read_chained_ledger(args.ledger)
    results = read_chained_ledger(args.result_ledger)
    if not forecasts:
        raise TrackerError("Belum ada cohort prospektif untuk dinilai.")
    scorecard, scored_results = make_scorecard(forecasts, results)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "scorecard.json"
    csv_path = args.output_dir / "scorecard.csv"
    report_path = args.output_dir / "REPORT.md"
    json_path.write_text(
        json.dumps({
            "experiment": "EXP-07",
            "model_tag": MODEL_TAG,
            "forecast_count": len(forecasts),
            "finished_result_count": scored_results,
            "status": (
                "AWAITING_RESULTS" if scored_results == 0
                else "PROSPECTIVE_DESCRIPTIVE_ONLY"
            ),
            "readiness_assessment": "NOT_ASSESSED",
            "markets": scorecard,
            "limitations": [
                "Paper evaluation only; no stakes, execution data, or ROI claim.",
                "No bookmaker odds with a verifiable pre-match quote timestamp were captured.",
                "Descriptive scores do not certify readiness for live use.",
            ],
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    columns = [
        "market", "captured_fixtures", "completed_matches",
        "completed_match_coverage", "distinct_kickoff_weeks",
        "logloss", "logloss_ci_low", "logloss_ci_high",
        "brier", "brier_ci_low", "brier_ci_high",
        "ece_10bin", "ece_ci_low", "ece_ci_high",
        "accuracy", "accuracy_ci_low", "accuracy_ci_high",
        "evidence_status", "readiness_assessment",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in scorecard:
            output_row = {key: row.get(key) for key in columns}
            intervals = row.get("95pct_week_cluster_bootstrap") or {}
            for metric, prefix in (
                ("logloss", "logloss"),
                ("brier", "brier"),
                ("ece_10bin", "ece"),
                ("accuracy", "accuracy"),
            ):
                interval = intervals.get(metric)
                output_row[f"{prefix}_ci_low"] = interval[0] if interval else None
                output_row[f"{prefix}_ci_high"] = interval[1] if interval else None
            writer.writerow(output_row)

    def fmt_interval(row, metric):
        point = row.get(metric)
        if point is None:
            return "pending"
        interval = (row.get("95pct_week_cluster_bootstrap") or {}).get(metric)
        return (
            f"{point:.4f} [{interval[0]:.4f}, {interval[1]:.4f}]"
            if interval else f"{point:.4f}"
        )

    report_lines = [
        "# EXP-07 — Prospective paper evaluation",
        "",
        f"- Model: `{MODEL_TAG}`",
        f"- Cohort forecasts: {len(forecasts)}",
        f"- Finished matches scored: {scored_results}",
        f"- Status: **{'AWAITING_RESULTS' if scored_results == 0 else 'PROSPECTIVE_DESCRIPTIVE_ONLY'}**",
        "- Readiness assessment: **NOT ASSESSED**",
        "- No stakes, ROI, or profit claim.",
        "- No timestamped bookmaker odds were captured for this cohort.",
        "",
        "| Market | Captured | Finished | Coverage | LogLoss (95% CI) | Brier (95% CI) | ECE (95% CI) | Evidence |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in scorecard:
        report_lines.append(
            f"| {row['market']} | {row['captured_fixtures']} | "
            f"{row['completed_matches']} | {row['completed_match_coverage']:.1%} | "
            f"{fmt_interval(row, 'logloss')} | {fmt_interval(row, 'brier')} | "
            f"{fmt_interval(row, 'ece_10bin')} | {row['evidence_status']} |"
        )
    report_lines.extend([
        "",
        "Scores are descriptive prospective results only. EXP-07 does not make "
        "a readiness determination; a larger, stable sample and separately "
        "reviewed evidence are required before any readiness claim.",
        "",
        "Uncertainty intervals, when available, are 95% week-cluster bootstrap "
        "percentile intervals with 1,000 deterministic resamples. They are "
        "omitted when fewer than two completed kickoff weeks are represented.",
    ])
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Forecasts in cohort: {len(forecasts)}")
    print(f"Finished results scored: {scored_results}")
    print(f"Scorecard: {report_path}")
    print("Readiness assessment: NOT ASSESSED")


def write_results_template(args):
    forecasts = read_chained_ledger(args.ledger)
    results = read_chained_ledger(args.result_ledger)
    already_scored = {row["event_id"] for row in results}
    columns = [
        "event_id", "match_id_fotmob", "home_team", "away_team",
        "scheduled_kickoff_utc", "status", "home_goals", "away_goals",
        "actual_kickoff_utc", "result_source", "retrieved_at_utc",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and not args.force:
        raise TrackerError(f"File sudah ada; gunakan --force: {args.output}")
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in forecasts:
            if row["event_id"] not in already_scored:
                writer.writerow({
                    "event_id": row["event_id"],
                    "match_id_fotmob": row["match_id_fotmob"],
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                    "scheduled_kickoff_utc": row["kickoff_utc"],
                    "status": "",
                    "home_goals": "",
                    "away_goals": "",
                    "actual_kickoff_utc": "",
                    "result_source": "",
                    "retrieved_at_utc": "",
                })
    print(f"Template hasil: {args.output}")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser(
        "capture", help="Rekam snapshot EXP-06 sebelum kick-off."
    )
    capture_parser.add_argument("--predictions", type=Path, required=True)
    capture_parser.add_argument("--fixtures", type=Path, required=True)
    capture_parser.add_argument(
        "--captured-at-utc",
        required=True,
        help="Timestamp forecast dari nama snapshot, format ISO 8601 UTC.",
    )
    capture_parser.add_argument("--bundle-dir", type=Path, default=MODEL_DIR)
    capture_parser.add_argument("--ledger", type=Path, default=FORECAST_LEDGER)
    capture_parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    capture_parser.set_defaults(func=capture)

    results_parser = subparsers.add_parser(
        "import-results", help="Catat skor aktual pertandingan yang sudah selesai."
    )
    results_parser.add_argument("--input", type=Path, required=True)
    results_parser.add_argument("--ledger", type=Path, default=FORECAST_LEDGER)
    results_parser.add_argument("--result-ledger", type=Path, default=RESULT_LEDGER)
    results_parser.set_defaults(func=import_results)

    template_parser = subparsers.add_parser(
        "results-template", help="Buat CSV kosong untuk hasil pertandingan."
    )
    template_parser.add_argument(
        "--output",
        type=Path,
        default=PAPER / "exp07_results_input_template.csv",
    )
    template_parser.add_argument("--ledger", type=Path, default=FORECAST_LEDGER)
    template_parser.add_argument("--result-ledger", type=Path, default=RESULT_LEDGER)
    template_parser.add_argument("--force", action="store_true")
    template_parser.set_defaults(func=write_results_template)

    score_parser = subparsers.add_parser(
        "score", help="Hitung metrik prospective-only dari hasil yang tercatat."
    )
    score_parser.add_argument("--ledger", type=Path, default=FORECAST_LEDGER)
    score_parser.add_argument("--result-ledger", type=Path, default=RESULT_LEDGER)
    score_parser.add_argument(
        "--output-dir", type=Path, default=PAPER / "scorecard"
    )
    score_parser.set_defaults(func=write_scorecard)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (TrackerError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
