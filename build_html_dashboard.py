import pandas as pd
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
PRED_DIR = BASE / "predictions"
OUT_HTML = BASE / "index.html"

# BACA FILE MASTER (KITAB SUCI DATA KITA)
master = pd.read_csv(BASE / "data" / "features_train.csv", low_memory=False)
master['Date'] = pd.to_datetime(master['Date'], errors='coerce')

# Ambil file prediksi terbaru
files = sorted(PRED_DIR.glob("predictions_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
# Ambil file terbaru berdasarkan waktu modifikasi (tidak peduli ada _CLEAN atau tidak)
latest_pred = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[0]

df_pred = pd.read_csv(latest_pred)
df_pred['date'] = pd.to_datetime(df_pred['date'], errors='coerce')
df_pred = df_pred.sort_values(by=['date'])

# PETA NAMA FOLDER (Untuk Statistik Home/Away per tim)
FOLDER_MAP = {
    "Cambuur": "sc_cambuur", "Lens": "rc_lens", "Milan": "ac_milan", 
    "Roma": "as_roma", "Sociedad": "real_sociedad"
}

# PETA NAMA TIM DI MASTER DATA (Jika API kirim nama beda)
NAME_TO_MASTER = {
    "Milan": "AC Milan", "Roma": "AS Roma", "Inter": "Inter Milan",
    "PSG": "Paris Saint-Germain", "Sociedad": "Real Sociedad"
}

LEAGUE_MAP = {
    "England-PL": "Premier League", "England-Champ": "Championship",
    "Spain-LaLiga": "LaLiga", "Italy-SA": "Serie A", "Italy-SB": "Serie B",
    "Germany-BL1": "Bundesliga", "France-L1": "Ligue 1",
    "Netherlands-ED": "Eredivisie", "Portugal-Liga1": "Primeira Liga",
    "Belgium-JPL": "Jupiler Pro League", "Turkey-SL": "Süper Lig",
    "Greece-SL": "Super League"
}

def get_folder(team):
    if team in FOLDER_MAP: return FOLDER_MAP[team]
    return team.lower().replace(" ", "_").replace(".", "").replace("-", "_")

def get_master_name(team):
    return NAME_TO_MASTER.get(team, team)

def get_team_stats(team, is_home, match_date):
    folder = get_folder(team)
    file_path = BASE / "data" / folder / ("home.csv" if is_home else "away.csv")
    
    if not file_path.exists(): return {"found": False}
    
    df = pd.read_csv(file_path)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    hist = df[df['Date'] < match_date]
    
    if len(hist) == 0: return {"found": True, "win_rate": 0, "avg_gf": 0, "avg_ga": 0, "n": 0}
    
    if is_home:
        return {"found": True, "win_rate": (hist['FTR'] == 'H').mean(), 
                "avg_gf": hist['FTHG'].mean(), "avg_ga": hist['FTAG'].mean(), "n": len(hist)}
    else:
        return {"found": True, "win_rate": (hist['FTR'] == 'A').mean(), 
                "avg_gf": hist['FTAG'].mean(), "avg_ga": hist['FTHG'].mean(), "n": len(hist)}

def get_h2h_from_master(home, away, match_date):
    db_home = get_master_name(home)
    db_away = get_master_name(away)
    folder_home = get_folder(db_home)

    # Baca file h2h.csv milik tim home
    path_h2h = BASE / "data" / folder_home / "h2h.csv"
    if not path_h2h.exists(): return None
        
    try:
        df = pd.read_csv(path_h2h)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # --- KUNCI: Filter berdasarkan kolom 'opponent' ---
        if 'opponent' not in df.columns:
            return None
            
        target_away = str(db_away).lower()
        mask_match = df['opponent'].astype(str).str.lower() == target_away
                     
        hist = df[mask_match & (df['Date'] < match_date)].sort_values('Date', ascending=False)
        
        if len(hist) == 0: return None

        n = len(hist)
        home_w = 0; away_w = 0; draw = 0; total_goals = 0
        last_m = []

        for _, r in hist.iterrows():
            # Karena ini file h2h dari sisi home, kita cek venue (H/A)
            is_home = (r['venue'] == 'H') if 'venue' in r else True
            
            # Ambil skor (kolom team_goals/opp_goals)
            tg = r.get('team_goals', r.get('FTHG', 0))
            og = r.get('opp_goals', r.get('FTAG', 0))
            
            if is_home:
                hg, ag = tg, og
            else:
                hg, ag = og, tg
                
            ftr = 'D'
            if hg > ag: ftr = 'H'
            elif ag > hg: ftr = 'A'
            
            total_goals += (hg + ag)
            
            if ftr == 'D': draw += 1
            elif (ftr == 'H' and is_home) or (ftr == 'A' and not is_home): home_w += 1
            else: away_w += 1

        for _, r in hist.head(3).iterrows():
            is_home = (r['venue'] == 'H') if 'venue' in r else True
            tg = int(r.get('team_goals', r.get('FTHG', 0)))
            og = int(r.get('opp_goals', r.get('FTAG', 0)))
            
            if is_home:
                score = f"{tg}-{og}"
                if tg > og: res = "W"
                elif tg < og: res = "L"
                else: res = "D"
            else:
                score = f"{og}-{tg}"
                if og > tg: res = "W"
                elif og < tg: res = "L"
                else: res = "D"
            
            venue = "H" if is_home else "A"
            last_m.append(f"{r['Date'].strftime('%Y')} ({venue}): {score} ({res})")

        return {"n": n, "home_w": home_w, "draw": draw, "away_w": away_w,
                "avg_goals": total_goals / n if n > 0 else 0, "last_matches": " | ".join(last_m)}
    except Exception as e:
        return None

def get_expected_score(row):
    if pd.isna(row.get('p_home_over15')): return "-"
    h = 2 if row['p_home_over15'] > 0.60 else (1 if row['p_home_over05'] > 0.60 else 0)
    a = 2 if row['p_away_over15'] > 0.60 else (1 if row['p_away_over05'] > 0.60 else 0)
    if h == a and row['p_H'] > 0.50: h += 1
    if h == a and row['p_A'] > 0.50: a += 1
    return f"{h} - {a}"

html = """
<!DOCTYPE html>
<html>
<head>\n


    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Football Prediction Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #0E1117; color: #FAFAFA; padding: 15px; margin: 0; }
        h1 { color: #1E88E5; text-align: center; font-size: 1.5rem; margin-bottom: 5px;}
        .subtitle { text-align:center; color:#888; font-size: 0.8rem; margin-bottom: 20px;}
        h2 { color: #E0E0E0; margin-top: 30px; font-size: 1.1rem; border-bottom: 1px solid #333; padding-bottom: 5px;}
        
        .card { background-color: #1E1E1E; border-radius: 8px; padding: 12px; margin-bottom: 15px; border-left: 4px solid #1E88E5; }
        .match-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
        .team { font-weight: bold; font-size: 1rem; width: 35%; }
        .team.away { text-align: right; }
        .score-box { background-color: #262730; padding: 8px 15px; border-radius: 5px; font-weight: bold; color: #00FF00; font-size: 1.2rem; text-align: center; }
        .score-label { font-size: 0.7rem; color: #AAA; text-align: center; margin-top: -2px; margin-bottom: 10px; }
        .league-badge { text-align: center; margin-bottom: 10px; }
        .league-badge span { background-color: #333; color: #FFF; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: bold;}
        
        .section-title { font-size: 0.75rem; color: #888; text-transform: uppercase; margin-bottom: 5px; margin-top: 10px;}
        
        .markets { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 0.85rem; margin-bottom: 5px;}
        .market-item { background-color: #2b2b36; padding: 8px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;}
        .market-label { color: #AAA; }
        .market-value { font-weight: bold; color: #FFF; font-size: 0.95rem; }
        
        .stats-box { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; font-size: 0.85rem; margin-bottom: 10px;}
        .stat-home { background-color: #2b2b36; padding: 6px; border-radius: 4px; text-align: center; border-top: 2px solid #FF9800;}
        .stat-away { background-color: #2b2b36; padding: 6px; border-radius: 4px; text-align: center; border-top: 2px solid #2196F3;}
        .stat-title { color: #888; font-size: 0.7rem; text-transform: uppercase;}
        .stat-val { font-weight: bold; color: #FFF; font-size: 1rem; }
        .stat-missing { color: #FF5252; font-size: 0.8rem; font-style: italic; }
        
        .h2h-box { background-color: #2b2b36; padding: 10px; border-radius: 4px; font-size: 0.85rem; border-left: 2px solid #F44336;}
        .h2h-title { font-weight: bold; color: #FF5252; margin-bottom: 5px; }
        .h2h-last { font-size: 0.75rem; color: #AAA; margin-top: 5px; font-style: italic; }
        .no-h2h { color: #666; font-style: italic; font-size: 0.8rem; margin-top: 5px;}
    
    .filter-container {
        display: flex; flex-wrap: wrap; gap: 15px;
        background: #1e1e24; padding: 15px; border-radius: 8px;
        margin-bottom: 20px; border-left: 4px solid #3b82f6;
    }
    .filter-group { display: flex; flex-direction: column; }
    .filter-group label { font-size: 0.8rem; color: #aaa; margin-bottom: 5px; }
    .filter-group select {
        background: #2b2b36; color: white; border: 1px solid #444;
        padding: 8px 12px; border-radius: 6px; font-size: 0.9rem;
    }
\n
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
\n</style>
</head>
<body>\n
<div style="background:#1e1e24; padding:15px; border-radius:8px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; border-left: 4px solid #3b82f6;">
    <div style="display:flex; gap:15px;">
        <div>
            <label style="color:#aaa; font-size:12px; display:block; margin-bottom:5px;">Pilih Tanggal</label>
            <select id="dateFilter" style="background:#2b2b36; color:white; padding:8px; border-radius:4px; border:1px solid #444; outline:none;">
                <option value="all">Semua Tanggal</option>
            </select>
        </div>
        <div>
            <label style="color:#aaa; font-size:12px; display:block; margin-bottom:5px;">Urutkan</label>
            <select id="sortFilter" style="background:#2b2b36; color:white; padding:8px; border-radius:4px; border:1px solid #444; outline:none;">
                <option value="default">Default</option>
                <option value="date-asc">Tanggal (Awal)</option>
                <option value="date-desc">Tanggal (Akhir)</option>
            </select>
        </div>
    </div>
    <div style="text-align:right;">
        <button id="btnScan" onclick="startScan()" style="background:#10b981; color:white; border:none; padding:10px 20px; border-radius:6px; font-weight:bold; cursor:pointer; display:flex; align-items:center; gap:10px; transition:all 0.3s;">
            <span id="scanIcon">🔄</span> <span id="scanText">Scan Ulang Data</span>
        </button>
        <div id="scanStatus" style="color:#FFC107; font-size:12px; margin-top:5px; font-weight:bold; text-align:right; max-width:200px; word-wrap:break-word;"></div>
    </div>
</div>
\n


    <h1>⚽ Complete Stats & Prediction Dashboard</h1>
    <div class="subtitle">Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M") + """</div>
"""

dates = df_pred['date'].dt.date.unique()
for d in dates:
    if pd.isna(d): continue
    html += f"<h2>{d.strftime('%A, %d %B %Y')}</h2>"
    daily_matches = df_pred[df_pred['date'].dt.date == d]
    
    for _, row in daily_matches.iterrows():
        if row['data_status'] not in ['OK', 'OK_WITH_WARNING']: continue
        
        home = row['home_team']
        away = row['away_team']
        match_date = row['date']
        league = LEAGUE_MAP.get(row['league_name'], row['league_name'])
        
        h_stats = get_team_stats(home, True, match_date)
        a_stats = get_team_stats(away, False, match_date)
        h2h = get_h2h_from_master(home, away, match_date)
        
        # --- SKIP JIKA TIDAK ADA H2H ---
        if h2h is None or h2h.get('n', 0) == 0:
            continue
        
        score_ai = get_expected_score(row)
        
        # Logika untuk teks Prediksi 1X2
        p_h = row.get('p_H', 0)
        p_d = row.get('p_D', 0)
        p_a = row.get('p_A', 0)
        pred_raw = str(row.get('pred_1x2', '')).upper()
        
        if pred_raw == 'H':
            pred_text = f"Home Win<br><span style='font-size:0.8rem; color:#aaa;'>({p_h*100:.1f}%)</span>"
        elif pred_raw == 'A':
            pred_text = f"Away Win<br><span style='font-size:0.8rem; color:#aaa;'>({p_a*100:.1f}%)</span>"
        elif pred_raw == 'D':
            pred_text = f"Draw<br><span style='font-size:0.8rem; color:#aaa;'>({p_d*100:.1f}%)</span>"
        else:
            pred_text = "Unknown"

        h_display = f"""
            <div class="stat-title">{home} (Home)</div>
            <div class="stat-val">{h_stats['win_rate']*100:.0f}% Menang</div>
            <div style="font-size:0.75rem; color:#aaa;">Avg Gol: {h_stats['avg_gf']:.1f} | Kebobolan: {h_stats['avg_ga']:.1f}</div>
            <div style="font-size:0.7rem; color:#666;">({h_stats['n']} laga)</div>
        """ if h_stats['found'] else f"""
            <div class="stat-title">{home} (Home)</div>
            <div class="stat-missing">Data tim tidak ada di database</div>
        """
        
        a_display = f"""
            <div class="stat-title">{away} (Away)</div>
            <div class="stat-val">{a_stats['win_rate']*100:.0f}% Menang</div>
            <div style="font-size:0.75rem; color:#aaa;">Avg Gol: {a_stats['avg_gf']:.1f} | Kebobolan: {a_stats['avg_ga']:.1f}</div>
            <div style="font-size:0.7rem; color:#666;">({a_stats['n']} laga)</div>
        """ if a_stats['found'] else f"""
            <div class="stat-title">{away} (Away)</div>
            <div class="stat-missing">Data tim tidak ada di database</div>
        """

        # H2H Logic
        if h2h and h2h['n'] >= 1:  # Tampilkan jika minimal 1 pertemuan
            h2h_html = f"""
            <div class="section-title">Head-to-Head (H2H)</div>
            <div class="h2h-box">
                <div class="h2h-title">{h2h['n']} Pertemuan (Avg {h2h['avg_goals']:.1f} Gol)</div>
                <span style="color:#4CAF50;">{h2h['home_w']} Menang {home}</span> | 
                <span style="color:#FFC107;">{h2h['draw']} Seri</span> | 
                <span style="color:#2196F3;">{h2h['away_w']} Menang {away}</span>
                <div class="h2h-last">3 Laga Terakhir: {h2h['last_matches']}</div>
            </div>
            """
        else:
            h2h_html = f"""
            <div class="section-title">Head-to-Head (H2H)</div>
            <div class="h2h-box" style="border-left: 2px solid #555;">
                <div class="no-h2h">Belum ada riwayat pertemuan yang cukup di database.</div>
            </div>
            """

        html += f"""
        <div class="card">
            <div class="league-badge"><span>{league}</span></div>
            <div class="match-header">
                <div class="team">{home}</div>
                <div>
                    <div class="score-box" style="color: #10b981; font-weight: bold; font-size: 1.1rem; padding: 8px;">
                        {pred_text}
                    </div>
                    <div class="score-label">Prediksi 1X2</div>
                </div>
                <div class="team away">{away}</div>
            </div>
            
            <div class="section-title">Statistik Historis (Kandang vs Tandang)</div>
            <div class="stats-box">
                <div class="stat-home">{h_display}</div>
                <div class="stat-away">{a_display}</div>
            </div>

            {h2h_html}

            <div class="section-title">1X2 & Total Gol</div>
            <div class="markets">
                <div class="market-item"><span class="market-label">Home Win</span> <span class="market-value">{row['p_H']*100:.1f}%</span></div>
                <div class="market-item"><span class="market-label">Away Win</span> <span class="market-value">{row['p_A']*100:.1f}%</span></div>
                <div class="market-item"><span class="market-label">Over 2.5</span> <span class="market-value">{row['p_over25']*100:.1f}%</span></div>
                <div class="market-item"><span class="market-label">Under 2.5</span> <span class="market-value">{row['p_under25']*100:.1f}%</span></div>
            </div>

            <div class="section-title">Gol Individu (Over/Under)</div>
            <div class="markets">
                <div class="market-item"><span class="market-label">{home} Gol > 0.5</span> <span class="market-value">{row['p_home_over05']*100:.1f}%</span></div>
                <div class="market-item"><span class="market-label">{home} Gol > 1.5</span> <span class="market-value">{row['p_home_over15']*100:.1f}%</span></div>
                <div class="market-item"><span class="market-label">{away} Gol > 0.5</span> <span class="market-value">{row['p_away_over05']*100:.1f}%</span></div>
                <div class="market-item"><span class="market-label">{away} Gol > 1.5</span> <span class="market-value">{row['p_away_over15']*100:.1f}%</span></div>
            </div>
        </div>
        """

html += """


\n

\n

\n

\n

\n

\n
<script>
document.addEventListener('DOMContentLoaded', function() {
    // --- 1. FILTER TANGGAL ---
    var dateFilter = document.getElementById('dateFilter');
    var cards = Array.from(document.querySelectorAll('.card'));
    var dates = new Set();
    
    cards.forEach(function(c) {
        var match = c.innerText.match(/[0-9]{4}-[0-9]{2}-[0-9]{2}/);
        if (match) {
            c.setAttribute('data-date', match[0]);
            dates.add(match[0]);
        }
    });
    
    Array.from(dates).sort().forEach(function(d) {
        dateFilter.innerHTML += '<option value="' + d + '">' + d + '</option>';
    });

    dateFilter.addEventListener('change', function() {
        var val = this.value;
        cards.forEach(function(c) {
            if (val === 'all' || c.getAttribute('data-date') === val) {
                c.style.display = 'block';
            } else {
                c.style.display = 'none';
            }
        });
    });
});

// --- 2. TOMBOL SCAN ---
async function startScan() {
    var btn = document.getElementById('btnScan');
    var status = document.getElementById('scanStatus');
    btn.disabled = true;
    btn.innerText = '⏳...';
    status.innerText = 'Memulai...';
    
    try {
        var res = await fetch('/api/scan', { method: 'POST' });
        if (!res.ok) throw new Error('Server sibuk');
        
        var interval = setInterval(async function() {
            var sres = await fetch('/api/status');
            var sdata = await sres.json();
            var lines = sdata.last_output.trim().split('\n');
            status.innerText = lines[lines.length - 1].substring(0, 30);
            
            if (!sdata.running) {
                clearInterval(interval);
                status.innerText = '✅ Selesai!';
                setTimeout(function() { window.location.reload(); }, 1500);
            }
        }, 2000);
    } catch (e) {
        status.innerText = '❌ Gagal.';
        btn.disabled = false;
        btn.innerText = '🔄 Scan';
    }
}
</script>
\n</body>
</html>
"""

OUT_HTML.write_text(html)
print(f"✅ Dashboard FINAL. H2H ditarik langsung dari master data (features_train.csv).")
