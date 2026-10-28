#!/usr/bin/env python3
"""
Rekonstruksi point-in-time. Hanya baca master_canon, bukan features_train.
Menggunakan fungsi features.py untuk konsistensi formula.
"""
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '.')
from features import build_team_rows

MASTER = pd.read_csv('data/master_canon.csv', low_memory=False)
MASTER['Date'] = pd.to_datetime(MASTER['Date'])
MASTER_TEAM_ROWS = build_team_rows(MASTER)

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
    # Strict cutoff. Build team histories once at module load instead of
    # rebuilding all rolling features from every historical match per fixture.
    history = MASTER[MASTER['Date'] < md]
    team_history = MASTER_TEAM_ROWS[MASTER_TEAM_ROWS['date'] < md]
    home_history = team_history[team_history['team'] == home].sort_values(
        ['date', 'match_id']
    )
    away_history = team_history[team_history['team'] == away].sort_values(
        ['date', 'match_id']
    )

    def rolling_stats(rows, prefix, window):
        recent = rows.tail(window)
        if recent.empty:
            return {
                f'{prefix}{name}': np.nan
                for name in (
                    'ppg', 'pts', 'gf', 'ga', 'gf_sum', 'ga_sum',
                    'win_rate', 'draw_rate', 'loss_rate', 'cs_rate',
                    'fts_rate',
                )
            } | {f'{prefix}n_played': 0}
        return {
            f'{prefix}ppg': recent['points'].mean(),
            f'{prefix}pts': recent['points'].sum(),
            f'{prefix}gf': recent['gf'].mean(),
            f'{prefix}ga': recent['ga'].mean(),
            f'{prefix}gf_sum': recent['gf'].sum(),
            f'{prefix}ga_sum': recent['ga'].sum(),
            f'{prefix}win_rate': recent['won'].mean(),
            f'{prefix}draw_rate': recent['drawn'].mean(),
            f'{prefix}loss_rate': recent['lost'].mean(),
            f'{prefix}cs_rate': recent['cs'].mean(),
            f'{prefix}fts_rate': recent['failed_to_score'].mean(),
            f'{prefix}n_played': len(rows),
        }

    def team_features(rows):
        result = {}
        result.update(rolling_stats(rows, 'form5_', 5))
        result.update(rolling_stats(rows, 'form10_', 10))

        result['rest_days'] = (
            (md - rows['date'].max()).days if not rows.empty else np.nan
        )
        season_rows = rows[rows['season'] == infer_season(md)]
        season_count = len(season_rows)
        result['season_n_played'] = season_count
        result['season_ppg'] = (
            season_rows['points'].sum() / season_count if season_count else np.nan
        )
        return result

    home_features = team_features(home_history)
    away_features = team_features(away_history)
    out = {
        **{f'home_{key}': value for key, value in home_features.items()},
        **{f'away_{key}': value for key, value in away_features.items()},
    }

    # --- venue form uses only matches strictly before the target date ---
    vh = venue_form_from_history(home_history, 'H', md, 5)
    va = venue_form_from_history(away_history, 'A', md, 5)
    for k, v in vh.items():
        out[f'home_venue_form5_{k}'] = v
    for k, v in va.items():
        out[f'away_venue_form5_{k}'] = v

    # --- H2H dihitung dari pasangan historis dengan cutoff strict ---
    pair_mask = (
        ((history['HomeTeam_canon'] == home) & (history['AwayTeam_canon'] == away)) |
        ((history['HomeTeam_canon'] == away) & (history['AwayTeam_canon'] == home))
    )
    h2h = history[pair_mask].sort_values(['Date', 'match_id'])
    home_wins = (
        ((h2h['HomeTeam_canon'] == home) & (h2h['FTR'] == 'H')) |
        ((h2h['AwayTeam_canon'] == home) & (h2h['FTR'] == 'A'))
    )
    away_wins = (
        ((h2h['HomeTeam_canon'] == away) & (h2h['FTR'] == 'H')) |
        ((h2h['AwayTeam_canon'] == away) & (h2h['FTR'] == 'A'))
    )
    out['h2h_n'] = len(h2h)
    out['h2h_home_wins'] = int(home_wins.sum())
    out['h2h_away_wins'] = int(away_wins.sum())
    out['h2h_draws'] = int((h2h['FTR'] == 'D').sum())
    out['h2h_total_goals_avg'] = (
        (h2h['FTHG'] + h2h['FTAG']).mean() if not h2h.empty else np.nan
    )

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
