#!/usr/bin/env python3
"""
predict_dc.py — Append Dixon-Coles probabilities ke output predict.py.

Prinsip:
- TIDAK menyentuh predict.py sama sekali.
- Baca predictions_*.csv, untuk setiap row OK, reconstruct ulang,
  hitung lambda dari recon, lalu append 8 kolom DC.
- Output: predictions_dc_*.csv di direktori yang sama.

Cara pakai:
    python3 predict_dc.py --input predictions/predictions_20261027_*.csv
    python3 predict_dc.py --input ... --rho -0.05
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "logs"))

try:
    from reconstruct_pit import reconstruct
except Exception as e:
    print(f"FATAL: gagal import reconstruct_pit: {e}", file=sys.stderr)
    sys.exit(1)

try:
    import dixon_coles as dc
except Exception as e:
    print(f"FATAL: gagal import dixon_coles: {e}", file=sys.stderr)
    sys.exit(1)


DC_LEAGUE_AVG = 2.6
DC_COLS = ["p_H_dc", "p_D_dc", "p_A_dc", "p_over25_dc", "p_btts_dc",
           "lam_home", "lam_away", "rho_used"]


def compute_lambda_from_recon(recon, league_avg=DC_LEAGUE_AVG):
    """Hitung (lam_home, lam_away) dari recon (gol rolling)."""
    half = league_avg / 2.0

    def _safe(x, default=half):
        try:
            x = float(x)
        except (TypeError, ValueError):
            return default
        if not np.isfinite(x) or x < 0:
            return default
        return max(0.05, min(x, 5.0))

    h_att = _safe(recon.get("home_form5_gf", np.nan))
    h_def = _safe(recon.get("home_form5_ga", np.nan))
    a_att = _safe(recon.get("away_form5_gf", np.nan))
    a_def = _safe(recon.get("away_form5_ga", np.nan))

    if pd.isna(recon.get("home_form5_gf", np.nan)):
        h_att = _safe(recon.get("home_venue_form5_gf", half))
    if pd.isna(recon.get("away_form5_gf", np.nan)):
        a_att = _safe(recon.get("away_venue_form5_gf", half))
    if pd.isna(recon.get("home_form5_ga", np.nan)):
        h_def = _safe(recon.get("home_venue_form5_ga", half))
    if pd.isna(recon.get("away_form5_ga", np.nan)):
        a_def = _safe(recon.get("away_venue_form5_ga", half))

    lam = 0.5 * (h_att + a_def)
    mu = 0.5 * (a_att + h_def)

    hv = recon.get("home_venue_form5_gf", np.nan)
    hf = recon.get("home_form5_gf", np.nan)
    if not pd.isna(hv) and not pd.isna(hf) and hf > 0.1:
        boost = max(0.5, min(hv / hf, 2.0))
        lam *= boost

    return float(lam), float(mu)


def predict_dc_from_recon(recon, rho=-0.05):
    lam, mu = compute_lambda_from_recon(recon)
    if lam <= 0 or mu <= 0:
        return None
    m = dc.markets(lam, mu, rho=rho)
    return {
        "p_H_dc": m["home"], "p_D_dc": m["draw"], "p_A_dc": m["away"],
        "p_over25_dc": m["over25"], "p_btts_dc": m["btts"],
        "lam_home": lam, "lam_away": mu, "rho_used": rho,
    }


def process_row(row, rho=-0.05):
    """Return dict 8 kolom DC, atau dict NaN kalau tidak bisa."""
    out = {c: np.nan for c in DC_COLS}
    status = str(row.get("data_status", "")).upper()
    if not status.startswith("OK"):
        out["lam_home"] = np.nan
        return out

    home = row.get("home_team")
    away = row.get("away_team")
    league = row.get("league_name")
    date_s = row.get("date")
    if not all([home, away, league, date_s]):
        return out

    try:
        md = pd.Timestamp(date_s)
    except Exception:
        return out

    try:
        recon = reconstruct(md, home, away, league)
    except Exception as e:
        print(f"  RECONSTRUCT_FAIL {home} vs {away}: {e}", file=sys.stderr)
        return out

    dcp = predict_dc_from_recon(recon, rho=rho)
    if dcp is None:
        return out
    out.update(dcp)
    return out


def main():
    parser = argparse.ArgumentParser(description="Append Dixon-Coles to predictions CSV")
    parser.add_argument("--input", required=True, help="predictions_*.csv dari predict.py")
    parser.add_argument("--output-dir", default=None, help="Default: sama dengan input")
    parser.add_argument("--rho", type=float, default=-0.05)
    parser.add_argument("--only-ok", action="store_true",
                        help="Hanya proses row data_status mulai OK")
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"FATAL: input tidak ada: {inp}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else inp.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(inp)
    print(f"Loaded: {inp} ({len(df)} rows, {len(df.columns)} cols)")
    print(f"rho = {args.rho}")

    if args.only_ok:
        mask = df["data_status"].astype(str).str.upper().str.startswith("OK")
        print(f"Filtering to data_status OK: {mask.sum()} rows")
        df = df[mask].reset_index(drop=True)

    dc_rows = []
    n_ok = 0
    for i, row in df.iterrows():
        r = process_row(row.to_dict(), rho=args.rho)
        if not pd.isna(r.get("p_H_dc", np.nan)):
            n_ok += 1
        dc_rows.append(r)
        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{len(df)} processed ({n_ok} with DC)")

    dc_df = pd.DataFrame(dc_rows)
    merged = pd.concat([df.reset_index(drop=True), dc_df], axis=1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"predictions_dc_{ts}.csv"
    merged.to_csv(out_path, index=False)

    print(f"\nSaved: {out_path}")
    print(f"Rows: {len(merged)}, DC columns added: {len(DC_COLS)}")
    print(f"Rows with DC probabilities: {n_ok}/{len(merged)}")

    if n_ok > 0:
        print("\n=== Sample 3 rows dengan DC ===")
        cols = ["home_team", "away_team", "p_H", "p_D", "p_A",
                "p_H_dc", "p_D_dc", "p_A_dc", "lam_home", "lam_away"]
        cols = [c for c in cols if c in merged.columns]
        print(merged.dropna(subset=["p_H_dc"])[cols].head(3).to_string(index=False))


if __name__ == "__main__":
    main()
