import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '.')
from features import build_team_rows, venue_rolling

print("=" * 70)
print("VERIFIKASI SEMANTIK venue_rolling() TRAINING")
print("=" * 70)

master = pd.DataFrame({
    'Date': pd.to_datetime([
        '2024-01-01', '2024-01-08', '2024-01-15',
        '2024-01-22', '2024-01-29', '2024-02-05',
    ]),
    'HomeTeam_canon': ['A']*6,
    'AwayTeam_canon': ['B','C','D','E','F','G'],
    'FTHG': [2, 3, 1, 0, 2, 1],
    'FTAG': [0, 1, 1, 2, 0, 1],
    'FTR': ['H','H','D','A','H','D'],
    'league_name': ['Test']*6,
    'season': [2324]*6,
})
master['match_id'] = master.index.astype('int64')

tr = build_team_rows(master)
print("\nTeam A rows (venue='H'):")
print(tr[tr['team']=='A'][['date','venue','points','gf','ga']].to_string(index=False))

vh = venue_rolling(tr, 'form5_', 5)
a_venue = vh[vh['team']=='A'].sort_values('date').reset_index(drop=True)
print("\nvenue_rolling output untuk team A:")
print(a_venue[['date','venue_home_form5_ppg','venue_home_form5_gf',
               'venue_home_form5_ga','venue_home_form5_win_rate']].to_string(index=False))

print("\n=== TEST ASSERTIONS ===")
# Match ke-1: NaN (row pertama)
row1_ok = pd.isna(a_venue.iloc[0]['venue_home_form5_ppg'])
print(f"[1] Match ke-1 → NaN (row pertama): {row1_ok}")

# Match ke-3: 2 match sebelumnya
row3 = a_venue.iloc[2]
exp3 = {'ppg':3.0, 'gf':2.5, 'ga':0.5, 'wr':1.0}
row3_ok = (abs(row3['venue_home_form5_ppg'] - exp3['ppg']) < 1e-9
           and abs(row3['venue_home_form5_gf'] - exp3['gf']) < 1e-9
           and abs(row3['venue_home_form5_ga'] - exp3['ga']) < 1e-9
           and abs(row3['venue_home_form5_win_rate'] - exp3['wr']) < 1e-9)
print(f"[2] Match ke-3 → {exp3}: {row3_ok}")
print(f"    actual: ppg={row3['venue_home_form5_ppg']}, gf={row3['venue_home_form5_gf']}, "
      f"ga={row3['venue_home_form5_ga']}, wr={row3['venue_home_form5_win_rate']}")

# Match ke-6: 5 match sebelumnya
row6 = a_venue.iloc[5]
exp6 = {'ppg':2.0, 'gf':1.6, 'ga':0.8, 'wr':0.6}
row6_ok = (abs(row6['venue_home_form5_ppg'] - exp6['ppg']) < 1e-9
           and abs(row6['venue_home_form5_gf'] - exp6['gf']) < 1e-9
           and abs(row6['venue_home_form5_ga'] - exp6['ga']) < 1e-9
           and abs(row6['venue_home_form5_win_rate'] - exp6['wr']) < 1e-9)
print(f"[3] Match ke-6 → {exp6}: {row6_ok}")
print(f"    actual: ppg={row6['venue_home_form5_ppg']}, gf={row6['venue_home_form5_gf']}, "
      f"ga={row6['venue_home_form5_ga']}, wr={row6['venue_home_form5_win_rate']}")

print("\n=== KESIMPULAN SEMANTIK ===")
all_ok = row1_ok and row3_ok and row6_ok
if all_ok:
    print("✓ venue_rolling() = '5 match terakhir di venue yang sama, sebelum match saat ini'")
    print("  Implementasi rekonstruksi HARUS identik dengan semantik ini")
    print("  Artinya: filter history [date < md] & [venue == X], ambil tail(5), mean")
else:
    print("✗ venue_rolling() TIDAK sesuai ekspektasi — perlu investigasi lanjutan")
    print("  JANGAN patch rekonstruksi berdasarkan asumsi ini")

sys.exit(0 if all_ok else 1)
