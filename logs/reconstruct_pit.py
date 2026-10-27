#!/usr/bin/env python3
"""
Rekonstruksi point-in-time. Hanya baca master_canon, bukan features_train.
Menggunakan fungsi features.py untuk konsistensi formula.
"""
import json
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '.')
from features import (
    build_team_rows, rolling_features, rest_days, cumulative_season,
    h2h_features,
)

MASTER = pd.read_csv('data/master_canon.csv', low_memory=False)
MASTER['Date'] = pd.to_datetime(MASTER['Date'])

def infer_season(d):
    """Return season code sebagai int (konsisten dengan dtype season di
    master_canon/features_train/build_team_rows = int64).

    Konvensi: season Jul-Jun. Jul-Des tahun Y -> Y Y+1.
              Jan-Jun tahun Y -> (Y-1) Y.
    """
    y, m = d.year, d.month
    if m >= 7:
        return int(f"{str(y)[2:]}{str(y+1)[2:]}")
    else:
        return int(f"{str(y-1)[2:]}{str(y)[2:]}")

def venue_form_from_history(history_team, venue_filter, cutoff_date, window=5):
    """Mean form 5 match terakhir SEBELUM cutoff_date di venue tertentu.

    Semantik HARUS identik dengan venue_rolling() di features.py:
    shift(1) + rolling(window=5, min_periods=1) per (team, venue).
    Filter strict date < cutoff_date mencegah target row masuk.

    Jika tidak ada match di venue tsb sebelum cutoff -> NaN (min_periods=1
    berlaku jika ada >=1 match; jika 0 match -> NaN).
    """
    sub = history_team[
        (history_team['venue'] == venue_filter) &
        (history_team['date'] < cutoff_date)
    ].tail(window)
    if len(sub) == 0:
        return {"ppg": np.nan, "gf": np.nan, "ga": np.nan, "win_rate": np.nan}
    return {
        "ppg": sub['points'].mean(),
        "gf": sub['gf'].mean(),
        "ga": sub['ga'].mean(),
        "win_rate": sub['won'].mean(),
    }

def reconstruct(match_date, home, away, league):
    md = pd.Timestamp(match_date)
    # Strict cutoff
    h = MASTER[MASTER['Date'] < md].copy().reset_index(drop=True)

    # --- target row untuk rolling (tidak masuk H2H) ---
    target = {c: np.nan for c in MASTER.columns}
    target.update({
        'Date': md,
        'HomeTeam_canon': home,
        'AwayTeam_canon': away,
        'FTHG': 0.0, 'FTAG': 0.0, 'FTR': 'D',
        'HTHG': 0.0, 'HTAG': 0.0, 'HTR': 'D',
        'league_name': league,
        'season': infer_season(md),
    })
    m = pd.concat([h, pd.DataFrame([target])], ignore_index=True)
    tr = build_team_rows(m)

    HOME_ID, AWAY_ID = -1, -2
    tr.loc[(tr['date'] == md) & (tr['team'] == home), 'match_id'] = HOME_ID
    tr.loc[(tr['date'] == md) & (tr['team'] == away), 'match_id'] = AWAY_ID

    # --- rolling (form5, form10) ---
    r5 = rolling_features(tr, "form5_", 5)
    r10 = rolling_features(tr, "form10_", 10)
    # --- rest days ---
    rd = rest_days(tr)
    # --- cumulative season (menggunakan infer_season via target['season']) ---
    cs = cumulative_season(tr)

    # --- merge for target rows ---
    fdf = r5.merge(r10, on=["team","date","match_id"], how="left")
    fdf = fdf.merge(rd, on=["team","date","match_id"], how="left")
    fdf = fdf.merge(cs, on=["team","date","match_id"], how="left")

    home_row = fdf[(fdf['team']==home) & (fdf['match_id']==HOME_ID)].iloc[0]
    away_row = fdf[(fdf['team']==away) & (fdf['match_id']==AWAY_ID)].iloc[0]

    out = {}
    # form & rest & season
    for c in fdf.columns:
        if c in ('team','date','match_id'): continue
        out[f'home_{c}'] = home_row[c]
        out[f'away_{c}'] = away_row[c]

    # --- venue rolling: hitung manual per team, per venue ---
    tr_h = tr[tr['team'] == home]
    tr_a = tr[tr['team'] == away]
    vh = venue_form_from_history(tr_h, 'H', md, 5)
    va = venue_form_from_history(tr_a, 'A', md, 5)
    for k, v in vh.items():
        out[f'home_venue_form5_{k}'] = v
    for k, v in va.items():
        out[f'away_venue_form5_{k}'] = v

    # --- H2H: pakai fungsi features.py, DENGAN cutoff strict (tanpa target) ---
    h2h_df = h.copy()
    if 'match_id' not in h2h_df.columns:
        h2h_df['match_id'] = h2h_df.index.astype('int64')
    # Filter hanya pair ini, lalu jalankan h2h_features
    pair_mask = (
        ((h2h_df['HomeTeam_canon']==home) & (h2h_df['AwayTeam_canon']==away)) |
        ((h2h_df['HomeTeam_canon']==away) & (h2h_df['AwayTeam_canon']==home))
    )
    h2h_sub = h2h_df[pair_mask].copy()
    # Tambah target row (untuk dihitung fitur H2H target)
    target_h2h = target.copy()
    target_h2h['match_id'] = -1
    # FTR dummy agar h2h_features tidak crash; tidak akan dipakai untuk update H2H-nya sendiri
    # (karena cutoff: target row tidak masuk history)
    h2h_input = pd.concat([h2h_sub, pd.DataFrame([target_h2h])], ignore_index=True)
    h2h_out = h2h_features(h2h_input)
    target_h2h_row = h2h_out[h2h_out['match_id'] == -1]
    if len(target_h2h_row) == 0:
        raise RuntimeError(f"H2H target row missing for {home} vs {away} {md}")
    target_h2h_row = target_h2h_row.iloc[0]
    out['h2h_n'] = target_h2h_row['h2h_n']
    out['h2h_home_wins'] = target_h2h_row['h2h_home_wins']
    out['h2h_away_wins'] = target_h2h_row['h2h_away_wins']
    out['h2h_draws'] = target_h2h_row['h2h_draws']
    out['h2h_total_goals_avg'] = target_h2h_row['h2h_total_goals_avg']

    # --- derived ---
    out['diff_ppg5'] = out.get('home_form5_ppg', np.nan) - out.get('away_form5_ppg', np.nan)
    out['diff_gf5'] = out.get('home_form5_gf', np.nan) - out.get('away_form5_gf', np.nan)
    out['diff_ga5'] = out.get('home_form5_ga', np.nan) - out.get('away_form5_ga', np.nan)
    out['diff_ppg10'] = out.get('home_form10_ppg', np.nan) - out.get('away_form10_ppg', np.nan)
    out['diff_season_ppg'] = out.get('home_season_ppg', np.nan) - out.get('away_season_ppg', np.nan)
    out['sum_expected_goals'] = out.get('home_form5_gf', np.nan) + out.get('away_form5_gf', np.nan)
    out['diff_venue_ppg'] = (out.get('home_venue_form5_ppg', np.nan)
                              - out.get('away_venue_form5_ppg', np.nan))

    # --- odds: NaN (tidak ada odds untuk match target historis tanpa input manual) ---
    out['odds_pH'] = np.nan
    out['odds_pD'] = np.nan
    out['odds_pA'] = np.nan
    out['odds_pOver25'] = np.nan

    return out
