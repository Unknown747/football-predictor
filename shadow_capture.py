#!/usr/bin/env python3
"""
shadow_capture.py - Helper untuk shadow test validation.
READ-ONLY terhadap production. TIDAK fetch fixture. TIDAK ubah model/dataset.

Cara pakai:
  python shadow_capture.py --input fixture.csv --output-dir reports/shadow_test_<ts>/ --label SYNTHETIC_TEST_ONLY

Label wajib:
  - SYNTHETIC_TEST_ONLY: fixture buatan untuk test helper
  - HISTORICAL_FIXTURE: fixture historis (untuk test, bukan prospektif)

Output:
  - shadow_predictions.csv (append-safe, unik per run)
  - input_manifest.csv (hash input)
  - run.log
  - limitations.md
  - config.json
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Import predict.py (aman, main guarded)
sys.path.insert(0, str(Path(__file__).parent))
import predict as P

PROJECT_ROOT = Path(__file__).parent.resolve()
PRODUCTION_HASHES = {
    "predict.py": "3942d9babe6df0db8d4f88ed71ebe2d3845d60991583c8e556996154f4f5142b",
    "features.py": "ba8f4c7313ec734a19aaad593a4135186884433d24992c77beee0150d52dbfbc",
    "train.py": "5df530499a9694721d8f259470d7b51fc7e35a6a66a9b5a9378c274bd19fd7fc",
    "data/features_train.csv": "37b54914bd714fdb752e8f794e00d92a0d192d24d57aa452d496f20b34ff2f09",
}

REQUIRED_COLS = ["date", "home_team", "away_team", "league_name"]
ODDS_COLS = ["odds_home", "odds_draw", "odds_away", "odds_over25", "odds_under25"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_input(df):
    """Return (errors_list, validated_df). Tidak mengubah nilai, hanya flag."""
    errors = []
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        errors.append(f"missing_required_columns: {missing_cols}")
        return errors, None

    # Validate date
    parsed_dates = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df[parsed_dates.isna()]
    if len(bad_dates) > 0:
        errors.append(f"invalid_date_rows: {len(bad_dates)}")

    # home != away
    same = df["home_team"].str.strip().str.lower() == df["away_team"].str.strip().str.lower()
    if same.any():
        errors.append(f"home_eq_away_rows: {int(same.sum())}")

    # Validate odds if provided (numeric, > 1, or empty/NaN)
    for col in ODDS_COLS:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            valid_mask = df[col].notna() & (df[col] != "")
            bad = valid_mask & ((vals <= 1) | vals.isna())
            if bad.any():
                errors.append(f"invalid_odds_{col}_rows: {int(bad.sum())}")

    return errors, df


def check_production_integrity():
    """Return (ok, report_dict)."""
    report = {}
    ok = True
    for f, expected in PRODUCTION_HASHES.items():
        p = PROJECT_ROOT / f
        if not p.exists():
            report[f] = f"MISSING"
            ok = False
            continue
        actual = sha256_file(p)
        match = (actual == expected)
        report[f] = {"expected": expected, "actual": actual, "match": match}
        if not match:
            ok = False
    return ok, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path fixture CSV")
    parser.add_argument("--output-dir", required=True, help="Output directory (new or empty)")
    parser.add_argument("--label", required=True,
                        choices=["SYNTHETIC_TEST_ONLY", "HISTORICAL_FIXTURE"])
    parser.add_argument("--source", default="manual",
                        help="Sumber fixture (manual/copy_paste)")
    parser.add_argument("--odds-source", default="unknown",
                        help="Sumber odds (bet365/pinnacle/avg/unknown)")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = out_dir / "run.log"
    log_fh = open(log_path, "a")  # append, jangan timpa

    def L(msg):
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        log_fh.write(line + "\n")
        log_fh.flush()

    ts_utc = datetime.now(timezone.utc).isoformat()
    L(f"=== START shadow_capture ===")
    L(f"Input: {input_path}")
    L(f"Output dir: {out_dir}")
    L(f"Label: {args.label}")
    L(f"Source: {args.source}")
    L(f"Odds source: {args.odds_source}")

    # ==== Pre-flight: production integrity ====
    L("Checking production integrity...")
    ok, integrity_report = check_production_integrity()
    if not ok:
        L(f"FATAL: production integrity mismatch")
        for f, r in integrity_report.items():
            if isinstance(r, dict) and not r.get("match", False):
                L(f"  {f}: expected {r['expected'][:16]}... got {r['actual'][:16]}...")
        log_fh.close()
        sys.exit(1)
    L("Production integrity OK")

    # ==== Read input ====
    if not input_path.exists():
        L(f"FATAL: input tidak ada: {input_path}")
        log_fh.close()
        sys.exit(1)

    df_in = pd.read_csv(input_path)
    L(f"Input rows: {len(df_in)}")

    # ==== Validate input ====
    L("Validating input...")
    errors, df_valid = validate_input(df_in)
    if errors:
        L(f"FATAL: input validation failed: {errors}")
        log_fh.close()
        sys.exit(1)
    L("Input validation OK")

    # ==== Save input manifest ====
    input_hash = sha256_file(input_path)
    input_manifest = pd.DataFrame([{
        "input_path": str(input_path),
        "input_sha256": input_hash,
        "input_rows": len(df_in),
        "capture_ts_utc": ts_utc,
        "label": args.label,
        "source": args.source,
        "odds_source": args.odds_source,
    }])
    input_manifest.to_csv(out_dir / "input_manifest.csv", index=False)
    L(f"Input manifest saved (input_sha256: {input_hash[:16]}...)")

    # ==== Load predict.py resources ====
    L("Loading models & resources...")
    try:
        models = P.load_models()
        raw_to_canon, canon_set = P.load_team_map()
        league_set = P.load_league_set()
        feat_cols = P.load_feat_cols()
    except Exception as e:
        L(f"FATAL: load failed: {e}")
        log_fh.close()
        sys.exit(1)
    L(f"Loaded: {len(models)} models, {len(canon_set)} teams, {len(league_set)} leagues, {len(feat_cols)} feat cols")

    # ==== Predict each row ====
    L(f"Predicting {len(df_valid)} matches...")
    results = []
    for i, row in df_valid.iterrows():
        row_dict = row.to_dict()
        try:
            r = P.predict_one(row_dict, models, feat_cols,
                              raw_to_canon, canon_set, league_set)
        except Exception as e:
            # Fail-closed: NaN semua probability, status explicit
            r = {c: None for c in P.SCHEMA}
            r["match_id"] = row_dict.get("date", "unknown")
            r["data_status"] = "HELPER_PREDICT_FAILED"
            r["notes"] = f"predict_one exception: {type(e).__name__}: {e}"
        # Tambah kolom capture metadata
        r["capture_label"] = args.label
        r["capture_ts_utc"] = ts_utc
        r["source_fixture"] = str(input_path)
        r["odds_source"] = args.odds_source
        results.append(r)

    # ==== Save predictions ====
    df_out = pd.DataFrame(results)
    pred_path = out_dir / "shadow_predictions.csv"
    df_out.to_csv(pred_path, index=False)
    L(f"Predictions saved: {pred_path} ({len(df_out)} rows)")

    # ==== Save config ====
    config = {
        "capture_ts_utc": ts_utc,
        "input_path": str(input_path),
        "input_sha256": input_hash,
        "input_rows": len(df_in),
        "label": args.label,
        "source": args.source,
        "odds_source": args.odds_source,
        "n_predictions": len(df_out),
        "n_ok": int((df_out["data_status"] == "OK").sum()) if "data_status" in df_out.columns else 0,
        "n_warning": int((df_out["data_status"] == "OK_WITH_WARNING").sum()) if "data_status" in df_out.columns else 0,
        "n_error": int((df_out["data_status"].isin(["UNKNOWN_TEAM", "UNKNOWN_LEAGUE",
                       "INVALID_DATE", "INVALID_MATCH", "DATE_NOT_IN_FUTURE",
                       "HELPER_PREDICT_FAILED"])).sum()) if "data_status" in df_out.columns else 0,
        "production_integrity": integrity_report,
        "model_hashes": {
            "lgb_1x2_modeB.txt": sha256_file(PROJECT_ROOT / "models/lgb_1x2_modeB.txt"),
            "lgb_ou25_modeB.txt": sha256_file(PROJECT_ROOT / "models/lgb_ou25_modeB.txt"),
            "lgb_home_ou05_modeB.txt": sha256_file(PROJECT_ROOT / "models/lgb_home_ou05_modeB.txt"),
            "lgb_home_ou15_modeB.txt": sha256_file(PROJECT_ROOT / "models/lgb_home_ou15_modeB.txt"),
            "lgb_away_ou05_modeB.txt": sha256_file(PROJECT_ROOT / "models/lgb_away_ou05_modeB.txt"),
            "lgb_away_ou15_modeB.txt": sha256_file(PROJECT_ROOT / "models/lgb_away_ou15_modeB.txt"),
        },
    }
    with open(out_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2, default=str)
    L("config.json saved")

    # ==== Save limitations ====
    lim = """# Limitations - shadow_capture.py

1. Helper ini hanya VALIDASI TEKNIS. Label SYNTHETIC_TEST_ONLY atau HISTORICAL_FIXTURE
   berarti TIDAK untuk prediksi live.
2. Tidak ada fetch fixture otomatis. User harus supply CSV manual.
3. Tidak ada download odds otomatis. User supply odds manual (jika ada).
4. Predictions dari helper ini TIDAK untuk taruhan. Tidak ada klaim profitabilitas.
5. Timestamp capture di UTC. Tanggal kickoff mengikuti konvensi CSV input (YYYY-MM-DD).
6. Model hash diverifikasi sebelum predict. Jika mismatch, helper exit.
7. Probabilities NaN (fail-closed) jika input invalid. Tidak menebak.
8. Output immutable setelah capture: JANGAN edit shadow_predictions.csv manual.
"""
    (out_dir / "limitations.md").write_text(lim)
    L("limitations.md saved")

    L("=== DONE ===")
    L(f"Output dir: {out_dir}")
    log_fh.close()


if __name__ == "__main__":
    main()
