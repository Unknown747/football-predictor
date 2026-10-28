#!/usr/bin/env python3
"""
predict.py — Prediction pipeline with EXP-06 as primary and Mode B as legacy.

Prinsip:
- Cutoff ketat: hanya pakai data master_canon dengan Date < target_date.
- Default model: primary EXP06_BLEND_V1 blend bundle.
- Mode B remains available explicitly as a legacy comparison.
- Missing odds remain missing Mode B features; never switch to another model mode.
- Fail closed: UNKNOWN_TEAM / UNKNOWN_LEAGUE / DATE_NOT_IN_FUTURE → NaN, tidak predict.
- Deterministik: match_id dari sha256 jika tidak disupply user.

Tidak mengubah file produksi apapun. Hanya membaca + menulis ke output CSV.
"""
import argparse
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb

# Path setup
BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
MODELS = BASE / "models"
LOGS = BASE / "logs"
PREDICTIONS = BASE / "predictions"
PREDICTIONS.mkdir(exist_ok=True)

# Import reconstruct_pit (read-only, no side effects)
sys.path.insert(0, str(LOGS))
try:
    from reconstruct_pit import reconstruct, MASTER
except Exception as e:
    print(f"FATAL: gagal import reconstruct_pit: {e}", file=sys.stderr)
    sys.exit(1)

# Konstanta
CUTOFF_DATE = pd.Timestamp("2026-10-21")
FUZZY_THRESHOLD = 95.0
EXP06_MODE = "EXP06_BLEND_V1"
EXP06_PREDICTION_TAG = "EXP06_BLEND_V1_PRIMARY_REFERENCE_ONLY"
DEFAULT_PREDICTION_MODE = EXP06_MODE
EXP06_BUNDLE_DIR = MODELS / "exp06_blend_v1"

MARKET_CLASS_COUNTS = {
    "1x2": 3,
    "ou25": 2,
    "home_ou05": 2,
    "home_ou15": 2,
    "away_ou05": 2,
    "away_ou15": 2,
}

MODEL_MAP = {
    "1x2": "lgb_1x2_modeB.txt",
    "ou25": "lgb_ou25_modeB.txt",
    "home_ou05": "lgb_home_ou05_modeB.txt",
    "home_ou15": "lgb_home_ou15_modeB.txt",
    "away_ou05": "lgb_away_ou05_modeB.txt",
    "away_ou15": "lgb_away_ou15_modeB.txt",
}

# Final schema (50 columns)
SCHEMA = [
    "match_id", "date", "home_team", "away_team", "league_name",
    "data_status", "notes", "warning_insufficient_history",
    "p_H", "p_D", "p_A", "pred_1x2",
    "p_over25", "p_under25", "pred_ou25",
    "p_home_over05", "pred_home_ou05",
    "p_home_over15", "pred_home_ou15",
    "p_away_over05", "pred_away_ou05",
    "p_away_over15", "pred_away_ou15",
    "odds_home", "odds_draw", "odds_away",
    "implied_H", "implied_D", "implied_A",
    "value_1x2_H", "value_1x2_D", "value_1x2_A",
    "odds_over25", "odds_under25",
    "implied_over25", "implied_under25",
    "value_ou25_over", "value_ou25_under",
    "used_odds_input",
    # --- Kolom H2H & Statistik ---
    "h2h_n", "h2h_home_wins", "h2h_draws", "h2h_away_wins",
    "home_venue_form5_win_rate", "away_venue_form5_win_rate",
    "home_form5_gf", "home_form5_ga", "away_form5_gf", "away_form5_ga",
    "prediction_mode",
]


# ============================================================
# Loaders
# ============================================================

def load_models():
    """Load only the six production Mode B models."""
    models = {}
    for name, fname in MODEL_MAP.items():
        path = MODELS / fname
        if not path.exists():
            raise FileNotFoundError(f"Model Mode B tidak ditemukan: {path}")
        models[name] = lgb.Booster(model_file=str(path))
    return models


def load_team_map():
    """Return dict raw_name -> canonical + set of canonical names."""
    path = BASE / "team_map.csv"
    if not path.exists():
        raise FileNotFoundError(f"team_map.csv tidak ada: {path}")
    tm = pd.read_csv(path)
    raw_to_canon = dict(zip(tm["raw_name"], tm["canonical_name"]))
    canon_set = set(tm["canonical_name"])
    return raw_to_canon, canon_set


def load_league_set():
    """Daftar league_name yang valid dari master_canon."""
    return set(MASTER["league_name"].dropna().unique())


def load_feat_cols():
    path = LOGS / "feat_cols_modeB_ordered.json"
    if not path.exists():
        raise FileNotFoundError(f"feat_cols tidak ada: {path}")
    with open(path) as f:
        return json.load(f)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _feature_hash(columns):
    return hashlib.sha256("\n".join(columns).encode("utf-8")).hexdigest()


def load_exp06_bundle():
    """Load and integrity-check the primary EXP-06 reference-only bundle."""
    import joblib

    manifest_path = EXP06_BUNDLE_DIR / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Bundle {EXP06_MODE} tidak ditemukan: {manifest_path}. "
            "Bangun bundle dengan new/model_lab/experiments/"
            "build_exp06_inference_bundle.py."
        )
    with manifest_path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if (
        manifest.get("mode") != EXP06_MODE
        or manifest.get("prediction_mode") != EXP06_PREDICTION_TAG
        or manifest.get("status") != "REFERENCE_ONLY"
        or manifest.get("betting_ready") is not False
        or manifest.get("deployment_role") != "PRIMARY_REFERENCE_ONLY"
    ):
        raise ValueError(
            "Bundle utama EXP-06 tidak memiliki metadata PRIMARY_REFERENCE_ONLY "
            "yang valid."
        )
    if manifest.get("training_cutoff_inclusive") != "2026-06-30":
        raise ValueError("Cutoff bundle EXP-06 tidak cocok dengan cutoff yang dibekukan.")

    feat_cols = manifest.get("features")
    if (
        not isinstance(feat_cols, list)
        or not feat_cols
        or len(feat_cols) != manifest.get("feature_count")
        or _feature_hash(feat_cols) != manifest.get("features_sha256")
        or any(str(column).startswith("odds_") for column in feat_cols)
    ):
        raise ValueError("Daftar fitur bundle EXP-06 tidak valid atau memuat odds.")

    market_specs = manifest.get("markets")
    if not isinstance(market_specs, dict) or set(market_specs) != set(MARKET_CLASS_COUNTS):
        raise ValueError("Bundle EXP-06 harus berisi tepat enam pasar yang diharapkan.")

    models = {}
    for market, class_count in MARKET_CLASS_COUNTS.items():
        spec = market_specs[market]
        weights = spec.get("weights", {})
        model_specs = spec.get("models", {})
        if set(weights) != {"lgbm", "xgboost", "histgb", "logreg"}:
            raise ValueError(f"Daftar bobot model tidak lengkap untuk {market}.")
        if any(not np.isfinite(float(weight)) or float(weight) < 0
               for weight in weights.values()):
            raise ValueError(f"Bobot tidak valid untuk {market}.")
        if not np.isclose(sum(float(weight) for weight in weights.values()), 1.0):
            raise ValueError(f"Jumlah bobot bukan 1 untuk {market}.")
        expected_families = {name for name, weight in weights.items()
                             if float(weight) > 0}
        if set(model_specs) != expected_families:
            raise ValueError(f"Model bundle tidak sesuai dengan bobot untuk {market}.")

        market_models = []
        for family in sorted(expected_families):
            model_spec = model_specs[family]
            artifact = (EXP06_BUNDLE_DIR / model_spec["file"]).resolve()
            if artifact.parent != EXP06_BUNDLE_DIR.resolve() or not artifact.is_file():
                raise FileNotFoundError(f"Artefak model tidak valid: {artifact}")
            if _sha256_file(artifact) != model_spec.get("sha256"):
                raise ValueError(f"Hash model tidak cocok: {artifact.name}")
            estimator = joblib.load(artifact)
            feature_count = getattr(estimator, "n_features_in_", None)
            if feature_count is not None and int(feature_count) != len(feat_cols):
                raise ValueError(
                    f"Jumlah fitur {artifact.name} ({feature_count}) "
                    f"tidak sama dengan manifest ({len(feat_cols)})."
                )
            classes = set(int(value) for value in estimator.classes_)
            if classes != set(range(class_count)):
                raise ValueError(
                    f"Label kelas {artifact.name} tidak sesuai untuk {market}."
                )
            market_models.append((estimator, float(weights[family])))
        models[market] = market_models

    return models, feat_cols


def predict_exp06_market(models, market, X):
    """Return a class-aligned weighted probability vector for one market."""
    class_count = MARKET_CLASS_COUNTS[market]
    blended = np.zeros(class_count, dtype=float)
    total_weight = 0.0
    for estimator, weight in models[market]:
        probabilities = np.asarray(estimator.predict_proba(X), dtype=float)
        classes = np.asarray(estimator.classes_)
        if probabilities.shape != (1, len(classes)):
            raise ValueError(
                f"predict_proba shape tidak valid untuk {market}: {probabilities.shape}"
            )
        if not np.isfinite(probabilities).all() or (probabilities < 0).any():
            raise ValueError(f"Probabilitas tidak valid dari model {market}.")
        aligned = np.zeros(class_count, dtype=float)
        seen = set()
        for position, label in enumerate(classes):
            class_id = int(label)
            if class_id < 0 or class_id >= class_count or class_id in seen:
                raise ValueError(f"Urutan kelas tidak valid pada model {market}.")
            aligned[class_id] = probabilities[0, position]
            seen.add(class_id)
        if seen != set(range(class_count)):
            raise ValueError(f"Kelas model tidak lengkap pada pasar {market}.")
        probability_sum = aligned.sum()
        if probability_sum <= 0:
            raise ValueError(f"Jumlah probabilitas nol pada pasar {market}.")
        blended += weight * (aligned / probability_sum)
        total_weight += weight
    if not np.isclose(total_weight, 1.0) or blended.sum() <= 0:
        raise ValueError(f"Bobot inferensi tidak valid pada pasar {market}.")
    return blended / blended.sum()


# ============================================================
# Validation helpers
# ============================================================

def resolve_team(name, raw_to_canon, canon_set):
    """Return canonical name atau None.

    Order:
    1. Exact match (raw_to_canon)
    2. Exact match (canon_set)
    3. Case-insensitive exact match (raw + canon)  <-- tambahan
    4. Fuzzy WRatio, case-insensitive, threshold 95 + unik (delta >= 5)
    """
    if not isinstance(name, str):
        return None
    name = name.strip()
    if not name:
        return None
    # 1. Exact raw
    if name in raw_to_canon:
        return raw_to_canon[name]
    # 2. Exact canon
    if name in canon_set:
        return name
    # 3. Case-insensitive exact
    name_lower = name.lower()
    for raw, canon in raw_to_canon.items():
        if raw.lower() == name_lower:
            return canon
    for canon in canon_set:
        if canon.lower() == name_lower:
            return canon
    # 4. Fuzzy WRatio, case-insensitive compare
    try:
        from rapidfuzz import fuzz, process
        # Build lower-case canon list, but keep mapping to original
        canon_list = list(canon_set)
        canon_lower_map = {c.lower(): c for c in canon_list}
        matches = process.extract(name_lower, list(canon_lower_map.keys()),
                                  scorer=fuzz.WRatio,
                                  limit=2, score_cutoff=FUZZY_THRESHOLD)
        if len(matches) == 1:
            return canon_lower_map[matches[0][0]]
        if len(matches) >= 2:
            if matches[0][1] - matches[1][1] >= 5:
                return canon_lower_map[matches[0][0]]
            return None
        return None
    except Exception:
        return None


def parse_date(s):
    if pd.isna(s):
        return None
    try:
        return pd.Timestamp(s)
    except Exception:
        return None


def validate_odds_value(v):
    """Return float atau None. Nilai harus numerik, finite, > 1."""
    if v is None or pd.isna(v):
        return None
    try:
        f = float(v)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(f):
        return None
    if f <= 1.0:
        return None
    return f


def validate_odds_group_1x2(h, d, a):
    """Return (valid, h, d, a). Semua atau tidak sama sekali."""
    hh = validate_odds_value(h)
    dd = validate_odds_value(d)
    aa = validate_odds_value(a)
    if hh is None or dd is None or aa is None:
        return False, None, None, None
    return True, hh, dd, aa


def validate_odds_group_ou(over, under):
    o = validate_odds_value(over)
    u = validate_odds_value(under)
    if o is None or u is None:
        return False, None, None
    return True, o, u


def implied_1x2(h, d, a):
    """Normalized implied probabilities. Sum == 1."""
    ph = 1.0 / h; pd_ = 1.0 / d; pa = 1.0 / a
    s = ph + pd_ + pa
    return ph / s, pd_ / s, pa / s


def implied_ou(over, under):
    po = 1.0 / over; pu = 1.0 / under
    s = po + pu
    return po / s, pu / s


def check_history_status(recon):
    """Return (insufficient: bool, notes_list)."""
    notes = []
    insuff = False
    h5 = recon.get("home_form5_n_played")
    a5 = recon.get("away_form5_n_played")
    h10 = recon.get("home_form10_n_played")
    a10 = recon.get("away_form10_n_played")
    try:
        if h5 is not None and not pd.isna(h5) and h5 < 5:
            insuff = True; notes.append(f"home_form5_n_played={int(h5)}<5")
        if a5 is not None and not pd.isna(a5) and a5 < 5:
            insuff = True; notes.append(f"away_form5_n_played={int(a5)}<5")
        if h10 is not None and not pd.isna(h10) and h10 < 10:
            insuff = True; notes.append(f"home_form10_n_played={int(h10)}<10")
        if a10 is not None and not pd.isna(a10) and a10 < 10:
            insuff = True; notes.append(f"away_form10_n_played={int(a10)}<10")
        # Semua form NaN
        if (pd.isna(h5) or h5 == 0) and (pd.isna(a5) or a5 == 0):
            insuff = True; notes.append("both_teams_no_history")
    except Exception as e:
        notes.append(f"history_check_error:{e}")
        insuff = True
    return insuff, notes


# ============================================================
# Predict one match
# ============================================================

def empty_output(row, status, notes):
    """Return full schema row dengan NaN / None."""
    out = {c: None for c in SCHEMA}
    out["match_id"] = row.get("match_id", "")
    out["date"] = row.get("date", "")
    out["home_team"] = row.get("home_team", "")
    out["away_team"] = row.get("away_team", "")
    out["league_name"] = row.get("league_name", "")
    out["data_status"] = status
    out["notes"] = "; ".join(notes) if notes else ""
    out["warning_insufficient_history"] = False
    out["used_odds_input"] = "none"
    return out


def predict_one(row, models, feat_cols, raw_to_canon, canon_set, league_set,
                mode=DEFAULT_PREDICTION_MODE):
    """Predict satu match. Return dict matching SCHEMA."""
    # Extract input
    raw_home = row.get("home_team", "")
    raw_away = row.get("away_team", "")
    league = row.get("league_name", "")
    date_s = row.get("date", "")

    # 1) Date validation
    md = parse_date(date_s)
    if md is None:
        return empty_output(row, "INVALID_DATE", [f"date tidak valid: {date_s!r}"])
    if md <= CUTOFF_DATE:
        return empty_output(row, "DATE_NOT_IN_FUTURE",
                            [f"date {md.date()} <= cutoff {CUTOFF_DATE.date()}"])
    if md > CUTOFF_DATE + pd.Timedelta(days=365 * 2):
        # sanity: not more than 2 years ahead
        return empty_output(row, "DATE_TOO_FAR",
                            [f"date {md.date()} > cutoff + 2y"])

    # 2) League validation
    if not isinstance(league, str) or league not in league_set:
        return empty_output(row, "UNKNOWN_LEAGUE", [f"league {league!r} tidak dikenal"])

    # 3) Team resolution
    home_c = resolve_team(raw_home, raw_to_canon, canon_set)
    away_c = resolve_team(raw_away, raw_to_canon, canon_set)
    if home_c is None:
        return empty_output(row, "UNKNOWN_TEAM",
                            [f"home_team {raw_home!r} tidak resolve"])
    if away_c is None:
        return empty_output(row, "UNKNOWN_TEAM",
                            [f"away_team {raw_away!r} tidak resolve"])
    if home_c == away_c:
        return empty_output(row, "INVALID_MATCH",
                            [f"home==away: {home_c}"])

    # 4) Reconstruct features (point-in-time, cutoff ketat)
    try:
        recon = reconstruct(md, home_c, away_c, league)
    except Exception as e:
        return empty_output(row, "RECONSTRUCT_FAILED", [f"reconstruct: {e}"])

    # 5) History sufficiency (warning, tapi tetap predict)
    insuff, hist_notes = check_history_status(recon)

    # 6) Odds: hybrid
    odds_1x2_ok, oh, od, oa = validate_odds_group_1x2(
        row.get("odds_home"), row.get("odds_draw"), row.get("odds_away"))
    odds_ou_ok, oo, ou_ = validate_odds_group_ou(
        row.get("odds_over25"), row.get("odds_under25"))

    odds_notes = []
    if odds_1x2_ok:
        impl_h, impl_d, impl_a = implied_1x2(oh, od, oa)
        recon["odds_pH"] = impl_h
        recon["odds_pD"] = impl_d
        recon["odds_pA"] = impl_a
    else:
        recon["odds_pH"] = np.nan
        recon["odds_pD"] = np.nan
        recon["odds_pA"] = np.nan
        has_any = any(not pd.isna(row.get(k)) for k in ["odds_home", "odds_draw", "odds_away"])
        if has_any:
            odds_notes.append("1x2 odds incomplete/invalid → NaN")

    if odds_ou_ok:
        impl_over, impl_under = implied_ou(oo, ou_)
        recon["odds_pOver25"] = impl_over
    else:
        recon["odds_pOver25"] = np.nan
        has_any = any(not pd.isna(row.get(k)) for k in ["odds_over25", "odds_under25"])
        if has_any:
            odds_notes.append("ou25 odds incomplete/invalid → NaN")

    # Record available odds separately from which model can safely use them.
    if odds_1x2_ok and odds_ou_ok:
        used = "both"
    elif odds_1x2_ok:
        used = "1x2"
    elif odds_ou_ok:
        used = "ou25"
    else:
        used = "none"
    if mode == EXP06_MODE:
        # EXP-06 is odds-free. Odds may still support value calculations below,
        # but they are not model inputs.
        used = "none"

    selected_models = models
    selected_feat_cols = feat_cols

    # 7) Build X in correct order
    try:
        X = np.array([[recon[c] for c in selected_feat_cols]], dtype=float)
    except Exception as e:
        return empty_output(row, "FEATURE_BUILD_FAILED", [f"X build: {e}"])
    if X.shape != (1, len(selected_feat_cols)):
        return empty_output(row, "FEATURE_BUILD_FAILED",
                            [f"X shape {X.shape} != (1,{len(selected_feat_cols)})"])

    # 8) Predict. EXP06 uses its frozen 74-statistic whitelist; odds stay excluded.
    try:
        if mode == "B":
            p_1x2 = selected_models["1x2"].predict(X)[0]  # (3,)
            p_ou25_over = float(selected_models["ou25"].predict(X)[0])
            p_home_ou05 = float(selected_models["home_ou05"].predict(X)[0])
            p_home_ou15 = float(selected_models["home_ou15"].predict(X)[0])
            p_away_ou05 = float(selected_models["away_ou05"].predict(X)[0])
            p_away_ou15 = float(selected_models["away_ou15"].predict(X)[0])
        elif mode == EXP06_MODE:
            p_1x2 = predict_exp06_market(selected_models, "1x2", X)
            p_ou25_over = float(predict_exp06_market(selected_models, "ou25", X)[1])
            p_home_ou05 = float(
                predict_exp06_market(selected_models, "home_ou05", X)[1]
            )
            p_home_ou15 = float(
                predict_exp06_market(selected_models, "home_ou15", X)[1]
            )
            p_away_ou05 = float(
                predict_exp06_market(selected_models, "away_ou05", X)[1]
            )
            p_away_ou15 = float(
                predict_exp06_market(selected_models, "away_ou15", X)[1]
            )
        else:
            raise ValueError(f"Prediction mode tidak dikenal: {mode}")
    except Exception as e:
        return empty_output(row, "MODEL_PREDICT_FAILED", [f"predict: {e}"])

    # 9) Validate output
    p_1x2 = np.clip(p_1x2, 0.0, 1.0)
    p_1x2 = p_1x2 / p_1x2.sum() if p_1x2.sum() > 0 else np.array([1/3, 1/3, 1/3])
    probs_list = [p_ou25_over, p_home_ou05, p_home_ou15, p_away_ou05, p_away_ou15]
    probs_list = [min(max(p, 0.0), 1.0) for p in probs_list]
    p_ou25_over, p_home_ou05, p_home_ou15, p_away_ou05, p_away_ou15 = probs_list

    # Status final
    coherence_notes = []
    if mode == EXP06_MODE:
        if p_home_ou15 > p_home_ou05 + 1e-12:
            coherence_notes.append(
                "EXP06 coherence warning: home Over 1.5 > home Over 0.5"
            )
        if p_away_ou15 > p_away_ou05 + 1e-12:
            coherence_notes.append(
                "EXP06 coherence warning: away Over 1.5 > away Over 0.5"
            )
    mode_notes = (
        ["PRIMARY_MODEL; REFERENCE_ONLY; odds are not model features"]
        if mode == EXP06_MODE else []
    )
    all_notes = mode_notes + hist_notes + odds_notes + coherence_notes
    status = "OK_WITH_WARNING" if insuff or coherence_notes else "OK"

    # Predicted labels
    pred_1x2 = ["H", "D", "A"][int(np.argmax(p_1x2))]
    pred_ou25 = "Over" if p_ou25_over >= 0.5 else "Under"
    pred_home_ou05 = "Over" if p_home_ou05 >= 0.5 else "Under"
    pred_home_ou15 = "Over" if p_home_ou15 >= 0.5 else "Under"
    pred_away_ou05 = "Over" if p_away_ou05 >= 0.5 else "Under"
    pred_away_ou15 = "Over" if p_away_ou15 >= 0.5 else "Under"

    # Value metrics (null jika odds tidak lengkap untuk grupnya)
    value_1x2_H = value_1x2_D = value_1x2_A = None
    impl_h = impl_d = impl_a = None
    if odds_1x2_ok:
        impl_h, impl_d, impl_a = implied_1x2(oh, od, oa)
        value_1x2_H = float(p_1x2[0]) * oh
        value_1x2_D = float(p_1x2[1]) * od
        value_1x2_A = float(p_1x2[2]) * oa

    value_ou25_over = value_ou25_under = None
    impl_over = impl_under = None
    if odds_ou_ok:
        impl_over, impl_under = implied_ou(oo, ou_)
        value_ou25_over = p_ou25_over * oo
        value_ou25_under = (1 - p_ou25_over) * ou_

    # match_id
    mid = row.get("match_id")
    if mid is None or (isinstance(mid, float) and pd.isna(mid)) or str(mid).strip() == "":
        s = f"{md.date()}|{home_c}|{away_c}|{league}"
        mid = hashlib.sha256(s.encode()).hexdigest()[:12]

    return {
        "match_id": mid,
        "date": str(md.date()),
        "home_team": raw_home,
        "away_team": raw_away,
        "league_name": league,
        "data_status": status,
        "notes": "; ".join(all_notes),
        "warning_insufficient_history": bool(insuff),
        "p_H": float(p_1x2[0]),
        "p_D": float(p_1x2[1]),
        "p_A": float(p_1x2[2]),
        "pred_1x2": pred_1x2,
        "p_over25": p_ou25_over,
        "p_under25": 1.0 - p_ou25_over,
        "pred_ou25": pred_ou25,
        "p_home_over05": p_home_ou05,
        "pred_home_ou05": pred_home_ou05,
        "p_home_over15": p_home_ou15,
        "pred_home_ou15": pred_home_ou15,
        "p_away_over05": p_away_ou05,
        "pred_away_ou05": pred_away_ou05,
        "p_away_over15": p_away_ou15,
        "pred_away_ou15": pred_away_ou15,
        "odds_home": oh if odds_1x2_ok else None,
        "odds_draw": od if odds_1x2_ok else None,
        "odds_away": oa if odds_1x2_ok else None,
        "implied_H": impl_h,
        "implied_D": impl_d,
        "implied_A": impl_a,
        "value_1x2_H": value_1x2_H,
        "value_1x2_D": value_1x2_D,
        "value_1x2_A": value_1x2_A,
        "odds_over25": oo if odds_ou_ok else None,
        "odds_under25": ou_ if odds_ou_ok else None,
        "implied_over25": impl_over,
        "implied_under25": impl_under,
        "value_ou25_over": value_ou25_over,
        "value_ou25_under": value_ou25_under,
        "used_odds_input": used,
        # --- Data H2H & Statistik ---
        "h2h_n": recon.get("h2h_n", 0),
        "h2h_home_wins": recon.get("h2h_home_wins", 0),
        "h2h_draws": recon.get("h2h_draws", 0),
        "h2h_away_wins": recon.get("h2h_away_wins", 0),
        "home_venue_form5_win_rate": recon.get("home_venue_form5_win_rate", 0),
        "away_venue_form5_win_rate": recon.get("away_venue_form5_win_rate", 0),
        "home_form5_gf": recon.get("home_form5_gf", 0),
        "home_form5_ga": recon.get("home_form5_ga", 0),
        "away_form5_gf": recon.get("away_form5_gf", 0),
        "away_form5_ga": recon.get("away_form5_ga", 0),
        "prediction_mode": (
            EXP06_PREDICTION_TAG if mode == EXP06_MODE else "B"
        ),
    }


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Predict with the primary EXP-06 model by default; "
            "Mode B remains available as a legacy option."
        )
    )
    parser.add_argument("--input", required=True, help="Input CSV (date, home_team, away_team, league_name, [odds_*])")
    parser.add_argument(
        "--mode",
        choices=["B", EXP06_MODE],
        default=DEFAULT_PREDICTION_MODE,
        help="EXP06_BLEND_V1 is primary; choose B for the legacy model.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Output directory (default: {PREDICTIONS}).",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else PREDICTIONS
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== START predict ===")
    print(f"Input: {args.input}")
    print(f"Output dir: {out_dir}")
    print(f"Prediction mode: {args.mode}")

    # Load resources
    if args.mode == "B":
        print("Loading legacy Mode B models...")
        models = load_models()
        print(f"  {len(models)} legacy Mode B models loaded")
        feat_cols = load_feat_cols()
        for model_name, model in models.items():
            expected_features = len(feat_cols)
            actual_features = model.num_feature()
            if actual_features != expected_features:
                raise ValueError(
                    f"Feature count Mode B ({model_name}) tidak cocok: "
                    f"model={actual_features}, daftar={expected_features}"
                )
        print(f"  Mode B features: {len(feat_cols)}")
    else:
        print("Loading primary EXP-06 bundle (REFERENCE_ONLY)...")
        models, feat_cols = load_exp06_bundle()
        print(f"  Six primary market strategies loaded; features: {len(feat_cols)}")

    print("Loading team map & league set...")
    raw_to_canon, canon_set = load_team_map()
    league_set = load_league_set()
    print(f"  Teams: {len(canon_set)}, Leagues: {len(league_set)}")

    # Read input
    if not Path(args.input).exists():
        print(f"FATAL: input tidak ada: {args.input}")
        sys.exit(1)
    df_in = pd.read_csv(args.input)
    print(f"Input rows: {len(df_in)}")

    # Validate required columns
    required = {"date", "home_team", "away_team", "league_name"}
    if not required.issubset(df_in.columns):
        missing = required - set(df_in.columns)
        print(f"FATAL: kolom wajib missing: {missing}")
        sys.exit(1)

    # Dedupe by (date, home_team, away_team, league_name)
    keys = ["date", "home_team", "away_team", "league_name"]
    dup_mask = df_in.duplicated(subset=keys, keep="first")
    n_dup = int(dup_mask.sum())
    if n_dup > 0:
        print(f"WARNING: {n_dup} duplicate rows, keeping first")
    df_in = df_in[~dup_mask].reset_index(drop=True)
    print(f"After dedupe: {len(df_in)} rows")

    # Predict
    results = []
    for i, row in df_in.iterrows():
        try:
            r = predict_one(row.to_dict(), models, feat_cols,
                            raw_to_canon, canon_set, league_set,
                            mode=args.mode)
        except Exception as e:
            r = empty_output(row.to_dict(), "UNEXPECTED_ERROR", [str(e)])
        r["prediction_mode"] = (
            EXP06_PREDICTION_TAG if args.mode == EXP06_MODE else "B"
        )
        results.append(r)
        if (i + 1) % 5 == 0 or i + 1 == len(df_in):
            print(f"Progress: {i + 1}/{len(df_in)} matches", flush=True)

    # Write output
    df_out = pd.DataFrame(results, columns=SCHEMA)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"predictions_{ts}.csv"
    df_out.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")
    print(f"Rows: {len(df_out)}, Columns: {len(df_out.columns)}")

    # Summary
    print("\n=== STATUS SUMMARY ===")
    print(df_out["data_status"].value_counts().to_string())
    print("\n=== used_odds_input SUMMARY ===")
    print(df_out["used_odds_input"].value_counts().to_string())
    print("\n=== prediction_mode ===")
    print(df_out["prediction_mode"].value_counts(dropna=False).to_string())
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
