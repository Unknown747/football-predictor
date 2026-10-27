import pandas as pd
import sys
sys.path.insert(0, '.')
from features import build_team_rows

print("=" * 70)
print("VERIFIKASI TIPE DATA 'season'")
print("=" * 70)

print("\n[1] master_canon.csv")
master = pd.read_csv('data/master_canon.csv', low_memory=False, nrows=1000)
print(f"  dtype: {master['season'].dtype}")
print(f"  sample values: {master['season'].head(5).tolist()}")
print(f"  unique (first 10): {sorted(master['season'].unique())[:10]}")

print("\n[2] features_train.csv")
feat = pd.read_csv('data/features_train.csv', low_memory=False, nrows=1000)
print(f"  dtype: {feat['season'].dtype}")
print(f"  sample values: {feat['season'].head(5).tolist()}")
print(f"  unique (first 10): {sorted(feat['season'].unique())[:10]}")

print("\n[3] build_team_rows() output 'season'")
master_full = pd.read_csv('data/master_canon.csv', low_memory=False, nrows=500)
master_full['Date'] = pd.to_datetime(master_full['Date'])
tr = build_team_rows(master_full)
print(f"  dtype: {tr['season'].dtype}")
print(f"  sample values: {tr['season'].head(5).tolist()}")

print("\n[4] Target row inference")
md = pd.Timestamp('2023-01-02')
y, m = md.year, md.month
season_str = f"{str(y-1)[2:]}{str(y)[2:]}" if m < 7 else f"{str(y)[2:]}{str(y+1)[2:]}"
season_int = int(season_str)
print(f"  season_str = {season_str!r}  type={type(season_str).__name__}")
print(f"  season_int = {season_int}  type={type(season_int).__name__}")
print(f"  master_canon 2223 sample: {master[master['season'].astype(str)=='2223']['season'].iloc[0] if len(master[master['season'].astype(str)=='2223'])>0 else 'NOT FOUND'}")

print("\n[5] Groupby test: campuran int vs str")
test_df = pd.DataFrame({
    'team': ['Rangers']*3,
    'season': [2223, 2223, '2223'],
})
g = test_df.groupby(['team', 'season']).size()
print(f"  groupby result: {dict(g)}")
print(f"  Jumlah group: {len(g)}  (1 = tipe disatukan, 2 = terpisah)")

print("\n[6] KESIMPULAN")
if master['season'].dtype.kind in 'iu':
    print("  → season = INTEGER → infer_season() HARUS return int")
    print("  → Patch: infer_season return int")
elif master['season'].dtype.kind == 'O':
    print("  → season = OBJECT/STRING → infer_season() return str")
    print("  → TIDAK perlu patch type")
else:
    print(f"  → season dtype tidak terduga: {master['season'].dtype}")
