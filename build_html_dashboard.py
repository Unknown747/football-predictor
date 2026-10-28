import pandas as pd
import re
import os
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
PREDICTIONS_SETTING = Path(os.environ.get("PREDICTIONS_DIR", "predictions"))
PRED_DIR = (
    PREDICTIONS_SETTING
    if PREDICTIONS_SETTING.is_absolute()
    else BASE / PREDICTIONS_SETTING
)
OUTPUT_SETTING = Path(os.environ.get("DASHBOARD_OUTPUT_FILE", "index.html"))
OUT_HTML = OUTPUT_SETTING if OUTPUT_SETTING.is_absolute() else BASE / OUTPUT_SETTING
TEST_OUTPUT = os.environ.get("DASHBOARD_TEST_MODE") == "1"

# BACA FILE MASTER (KITAB SUCI DATA KITA)
master = pd.read_csv(BASE / "data" / "features_train.csv", low_memory=False)
master['Date'] = pd.to_datetime(master['Date'], errors='coerce')

team_map = pd.read_csv(BASE / "team_map.csv", dtype=str).fillna("")
TEAM_NAME_TO_CANON = {}
TEAM_FOLDER_BY_CANON = {}
for _, entry in team_map.iterrows():
    raw_name = str(entry.get("raw_name", "")).strip()
    canonical_name = str(entry.get("canonical_name", "")).strip()
    folder_name = str(entry.get("folder_name", "")).strip()
    if raw_name and canonical_name:
        TEAM_NAME_TO_CANON.setdefault(raw_name.casefold(), canonical_name)
    if canonical_name:
        TEAM_NAME_TO_CANON.setdefault(canonical_name.casefold(), canonical_name)
        if folder_name:
            TEAM_FOLDER_BY_CANON.setdefault(canonical_name.casefold(), folder_name)

MODE_B_VALUES = {"B", "B_ONLY", "B_WITH_ODDS"}
PRIMARY_MODEL_TAG = "EXP06_BLEND_V1_PRIMARY_REFERENCE_ONLY"
PRIMARY_MODEL_VALUES = {PRIMARY_MODEL_TAG}
SUPPORTED_MODEL_VALUES = MODE_B_VALUES | PRIMARY_MODEL_VALUES


def prediction_snapshot_modes(path):
    columns = pd.read_csv(path, nrows=0).columns
    if "prediction_mode" not in columns:
        return set()
    modes = pd.read_csv(path, usecols=["prediction_mode"])["prediction_mode"]
    return set(modes.dropna().astype(str).str.strip().str.upper())


def is_supported_prediction_snapshot(path):
    """Reject untagged, mixed, or unknown prediction snapshots."""
    modes = prediction_snapshot_modes(path)
    return bool(modes) and modes.issubset(SUPPORTED_MODEL_VALUES)


def is_primary_prediction_snapshot(path):
    """The main dashboard must never silently fall back to legacy Mode B."""
    return prediction_snapshot_modes(path) == PRIMARY_MODEL_VALUES


def prediction_file_key(path):
    """Prefer timestamp in the filename; use mtime and name for deterministic ties."""
    match = re.search(r"predictions_(\d{8}_\d{6})", path.name)
    timestamp = match.group(1) if match else ""
    return timestamp, path.stat().st_mtime_ns, path.name


files = [
    path for path in PRED_DIR.glob("predictions_*.csv")
    if is_supported_prediction_snapshot(path)
    and is_primary_prediction_snapshot(path)
]
if not files:
    raise FileNotFoundError(
        f"Tidak ada snapshot prediksi EXP-06 primary yang valid di {PRED_DIR}; "
        "dashboard tidak akan memakai snapshot legacy Mode B sebagai fallback."
    )
latest_pred = max(files, key=prediction_file_key)

df_pred = pd.read_csv(latest_pred)
df_pred['date'] = pd.to_datetime(df_pred['date'], errors='coerce')
df_pred = df_pred.sort_values(by=['date'])
snapshot_modes = (
    set(df_pred["prediction_mode"].dropna().astype(str).str.strip().str.upper())
    if "prediction_mode" in df_pred.columns else set()
)
uses_primary_model = bool(snapshot_modes & PRIMARY_MODEL_VALUES)


def paper_tracking_summary():
    """Show the no-stakes cohort status without presenting it as readiness."""
    paper_dir = BASE / "new" / "model_lab" / "paper"
    protocol_path = paper_dir / "exp07_protocol.json"
    forecasts_path = paper_dir / "exp07_forecasts.jsonl"
    results_path = paper_dir / "exp07_results.jsonl"
    scorecard_path = paper_dir / "scorecard" / "scorecard.json"
    if not protocol_path.is_file():
        return "EXP-07 paper tracking belum dimulai."

    try:
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        if protocol.get("model_tag") != PRIMARY_MODEL_TAG:
            return "EXP-07 tidak cocok dengan model utama; status perlu diaudit."

        def read_records(path):
            if not path.is_file():
                return []
            records = []
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        records.append(json.loads(line))
            return records

        forecasts = read_records(forecasts_path)
        results = read_records(results_path)
        if any(row.get("model_tag") != PRIMARY_MODEL_TAG
               for row in forecasts):
            return "EXP-07 memuat tag model berbeda; status perlu diaudit."
        finished_count = sum(
            str(row.get("status", "")).upper() == "FINISHED" for row in results
        )
        if finished_count == 0:
            result_state = "hasil pertandingan masih menunggu"
        elif scorecard_path.is_file():
            scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
            if (
                scorecard.get("model_tag") == PRIMARY_MODEL_TAG
                and scorecard.get("finished_result_count") == finished_count
            ):
                result_state = "scorecard deskriptif sudah diperbarui"
            else:
                result_state = "hasil tercatat; scorecard perlu diperbarui"
        else:
            result_state = "hasil tercatat; scorecard perlu dibuat"
        return (
            f"Paper test tanpa stake: {len(forecasts)} prediksi tersimpan, "
            f"{finished_count} hasil selesai; {result_state}. "
            "Status kesiapan tidak dinilai."
        )
    except (OSError, json.JSONDecodeError, TypeError):
        return "EXP-07 tidak dapat dibaca; periksa ledger sebelum menilai hasil."


paper_status_text = paper_tracking_summary()

LEAGUE_MAP = {
    "England-PL": "Premier League", "England-Champ": "Championship",
    "Spain-LaLiga": "LaLiga", "Italy-SA": "Serie A", "Italy-SB": "Serie B",
    "Germany-BL1": "Bundesliga", "France-L1": "Ligue 1",
    "Netherlands-ED": "Eredivisie", "Portugal-Liga1": "Primeira Liga",
    "Belgium-JPL": "Jupiler Pro League", "Turkey-SL": "Süper Lig",
    "Greece-SL": "Super League"
}

def get_folder(team):
    canonical = get_master_name(team)
    mapped = TEAM_FOLDER_BY_CANON.get(canonical.casefold())
    if mapped:
        return mapped
    return canonical.lower().replace(" ", "_").replace(".", "").replace("-", "_")

def get_master_name(team):
    name = str(team).strip()
    return TEAM_NAME_TO_CANON.get(name.casefold(), name)

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
            
        target_away = get_master_name(db_away).casefold()
        eligible = df[df['Date'] < match_date].copy()
        opponents = eligible['opponent'].astype(str)
        exact_mask = opponents.str.strip().str.casefold() == target_away
        if exact_mask.any():
            eligible = eligible[exact_mask]
        else:
            canonical_mask = opponents.map(get_master_name).str.casefold() == target_away
            eligible = eligible[canonical_mask]
        hist = eligible.sort_values('Date', ascending=False)
        
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

html = """
<!DOCTYPE html>
<html>
<head>\n


    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Football Prediction Dashboard</title>
    <link rel="stylesheet" href="/dashboard-theme.css">
</head>
<body>\n
<div class="dashboard-toolbar" style="background:#1e1e24; padding:15px; border-radius:8px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; border-left: 4px solid #3b82f6;">
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
    <div class="subtitle">Dibuat: """ + datetime.now().strftime("%Y-%m-%d %H:%M") + """ · Sumber: """ + latest_pred.name + """</div>
    <div class="model-disclaimer" role="note">
        """ + (
            "Model utama/default script: EXP-06 blend; odds bukan fitur model. "
            "Tahap eksplorasi; belum dipakai untuk live bet. "
            + paper_status_text +
            " Tidak ada klaim kesiapan atau profitabilitas."
            if uses_primary_model else
            "Mode B legacy. Persentase adalah estimasi model, bukan odds pasar; "
            "hasil belum dikalibrasi dan tidak menjamin hasil pertandingan. "
            "Jika odds tidak tersedia, fitur odds tetap kosong."
        ) + """
        Hanya pertandingan dengan minimal satu catatan H2H di data historis proyek yang ditampilkan.
    </div>
"""

visible_h2h_match_count = 0
dates = df_pred['date'].dt.date.unique()
for d in dates:
    if pd.isna(d): continue
    daily_matches = df_pred[df_pred['date'].dt.date == d]

    matches_with_h2h = []
    for _, row in daily_matches.iterrows():
        if row['data_status'] not in ['OK', 'OK_WITH_WARNING']: continue

        h2h = get_h2h_from_master(row['home_team'], row['away_team'], row['date'])
        if not h2h or h2h.get('n', 0) < 1:
            continue
        matches_with_h2h.append((row, h2h))

    if not matches_with_h2h:
        continue

    visible_h2h_match_count += len(matches_with_h2h)
    html += f'<h2 data-date="{d.strftime("%Y-%m-%d")}">{d.strftime("%A, %d %B %Y")}</h2>'
    for row, h2h in matches_with_h2h:
        home = row['home_team']
        away = row['away_team']
        match_date = row['date']
        league = LEAGUE_MAP.get(row['league_name'], row['league_name'])
        
        h_stats = get_team_stats(home, True, match_date)
        a_stats = get_team_stats(away, False, match_date)
        
        # Logika untuk teks Prediksi 1X2
        p_h = row.get('p_H', 0)
        p_d = row.get('p_D', 0)
        p_a = row.get('p_A', 0)
        pred_raw = str(row.get('pred_1x2', '')).upper()
        odds_input = str(row.get('used_odds_input', 'none') or 'none').lower()
        odds_labels = {
            "both": "odds 1X2 dan O/U tersedia",
            "1x2": "hanya odds 1X2 tersedia",
            "ou25": "hanya odds O/U tersedia",
            "none": "tanpa input odds",
        }
        row_mode = str(row.get("prediction_mode", "")).strip().upper()
        if row_mode in PRIMARY_MODEL_VALUES:
            prediction_note = (
                "EXP-06 default · estimasi model · eksplorasi, belum live bet"
            )
        else:
            prediction_note = (
                f"Mode B legacy · "
                f"{odds_labels.get(odds_input, 'status odds tidak diketahui')}"
            )
        
        if pred_raw == 'H':
            pred_text = f"Home Win<br><span style='font-size:0.8rem; color:#aaa;'>({p_h*100:.1f}%)</span>"
        elif pred_raw == 'A':
            pred_text = f"Away Win<br><span style='font-size:0.8rem; color:#aaa;'>({p_a*100:.1f}%)</span>"
        elif pred_raw == 'D':
            pred_text = f"Draw<br><span style='font-size:0.8rem; color:#aaa;'>({p_d*100:.1f}%)</span>"
        else:
            pred_text = "Unknown"

        h_display = f"""
            <div class="stat-title">{home} · riwayat kandang</div>
            <div class="stat-val">{h_stats['win_rate']*100:.0f}% win rate historis</div>
            <div style="font-size:0.75rem; color:#aaa;">Avg Gol: {h_stats['avg_gf']:.1f} | Kebobolan: {h_stats['avg_ga']:.1f}</div>
            <div style="font-size:0.7rem; color:#666;">({h_stats['n']} laga)</div>
        """ if h_stats['found'] else f"""
            <div class="stat-title">{home} · riwayat kandang</div>
            <div class="stat-missing">Data tim tidak ada di database</div>
        """
        
        a_display = f"""
            <div class="stat-title">{away} · riwayat tandang</div>
            <div class="stat-val">{a_stats['win_rate']*100:.0f}% win rate historis</div>
            <div style="font-size:0.75rem; color:#aaa;">Avg Gol: {a_stats['avg_gf']:.1f} | Kebobolan: {a_stats['avg_ga']:.1f}</div>
            <div style="font-size:0.7rem; color:#666;">({a_stats['n']} laga)</div>
        """ if a_stats['found'] else f"""
            <div class="stat-title">{away} · riwayat tandang</div>
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
                    <div class="score-label">Pilihan model dengan peluang tertinggi</div>
                </div>
                <div class="team away">{away}</div>
            </div>
            <div class="prediction-note">{prediction_note}</div>
            
            <div class="section-title">Win rate historis — bukan probabilitas model</div>
            <div class="stats-box">
                <div class="stat-home">{h_display}</div>
                <div class="stat-away">{a_display}</div>
            </div>

            {h2h_html}

            <div class="section-title">Probabilitas model 1X2 (Home / Seri / Away; dibulatkan)</div>
            <div class="markets one-x-two">
                <div class="market-item"><span class="market-label">Home Win</span> <span class="market-value">{row['p_H']*100:.1f}%</span></div>
                <div class="market-item"><span class="market-label">Seri (Draw)</span> <span class="market-value">{row['p_D']*100:.1f}%</span></div>
                <div class="market-item"><span class="market-label">Away Win</span> <span class="market-value">{row['p_A']*100:.1f}%</span></div>
            </div>
            <div class="probability-note">Angka ditampilkan hingga 1 desimal; nilai penuh bersumber dari CSV prediksi.</div>

            <div class="section-title">Total Gol 2.5 (estimasi)</div>
            <div class="markets">
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
    var dateFilter = document.getElementById('dateFilter');
    var sortFilter = document.getElementById('sortFilter');
    var headings = Array.from(document.querySelectorAll('body > h2'));
    var groups = [];

    function getDateKey(heading) {
        if (heading.dataset.date) return heading.dataset.date;
        var match = heading.textContent.match(/\\b(\\d{1,2})\\s+([A-Za-z]+)\\s+(\\d{4})$/);
        if (!match) return '';
        var date = new Date(match[2] + ' ' + match[1] + ', ' + match[3]);
        if (Number.isNaN(date.getTime())) return '';
        return match[3] + '-' + String(date.getMonth() + 1).padStart(2, '0') +
            '-' + String(date.getDate()).padStart(2, '0');
    }

    headings.forEach(function(heading) {
        var group = document.createElement('section');
        group.dataset.date = getDateKey(heading);
        heading.parentNode.insertBefore(group, heading);
        group.appendChild(heading);
        while (group.nextElementSibling &&
                group.nextElementSibling.classList.contains('card')) {
            group.appendChild(group.nextElementSibling);
        }
        if (group.querySelector('.card')) {
            groups.push(group);
        } else {
            group.remove();
        }
    });

    if (groups.length) {
        var list = document.createElement('div');
        list.id = 'predictionList';
        groups[0].parentNode.insertBefore(list, groups[0]);
        groups.forEach(function(group) { list.appendChild(group); });
    }

    groups.forEach(function(group) {
        if (!group.dataset.date) return;
        var option = document.createElement('option');
        option.value = group.dataset.date;
        option.textContent = group.querySelector('h2').textContent.trim();
        dateFilter.appendChild(option);
    });

    function updatePredictions() {
        var selectedDate = dateFilter.value;
        var direction = sortFilter.value;
        var orderedGroups = groups.slice();
        if (direction === 'date-asc' || direction === 'date-desc') {
            orderedGroups.sort(function(a, b) {
                var comparison = a.dataset.date.localeCompare(b.dataset.date);
                return direction === 'date-asc' ? comparison : -comparison;
            });
        }
        orderedGroups.forEach(function(group) {
            group.hidden = selectedDate !== 'all' && group.dataset.date !== selectedDate;
            list.appendChild(group);
        });
    }

    dateFilter.addEventListener('change', function() {
        updatePredictions();
    });
    sortFilter.addEventListener('change', updatePredictions);
    updatePredictions();
});

async function startScan() {
    var btn = document.getElementById('btnScan');
    var status = document.getElementById('scanStatus');
    var icon = document.getElementById('scanIcon');
    var text = document.getElementById('scanText');
    btn.disabled = true;
    icon.textContent = '⏳';
    text.textContent = 'Sedang scan...';
    status.textContent = 'Memulai proses...';
    
    try {
        var response = await fetch('/api/scan', { method: 'POST' });
        var result = await response.json().catch(function() { return {}; });
        if (!response.ok) {
            throw new Error(result.message || 'Permintaan scan ditolak.');
        }

        while (true) {
            await new Promise(function(resolve) { setTimeout(resolve, 2000); });
            var statusResponse = await fetch('/api/status', { cache: 'no-store' });
            if (!statusResponse.ok) throw new Error('Gagal membaca status scan.');
            var scan = await statusResponse.json();
            var output = String(scan.last_output || '');
            var lines = output.trim().split(/\\r?\\n/).filter(Boolean);
            var latest = lines.length ? lines[lines.length - 1] : 'Menunggu status scan...';
            status.textContent = latest;

            if (scan.running) continue;
            if (output.indexOf('✅ Semua proses selesai!') !== -1) {
                status.textContent = '✅ Selesai! Memuat ulang...';
                setTimeout(function() { window.location.reload(); }, 1500);
                return;
            }
            throw new Error(latest || 'Scan berhenti tanpa status berhasil.');
        }
    } catch (e) {
        status.textContent = '❌ ' + e.message;
        btn.disabled = false;
        icon.textContent = '🔄';
        text.textContent = 'Scan Ulang Data';
    }
}
</script>
\n</body>
</html>
"""

valid_prediction_count = int(df_pred["data_status"].isin(["OK", "OK_WITH_WARNING"]).sum())
if TEST_OUTPUT:
    hidden_no_h2h_count = max(valid_prediction_count - visible_h2h_match_count, 0)
    banner = (
        '<div id="test-only-banner" role="note" '
        'style="background:#3b2d12;color:#ffe5a1;border:1px solid #9a7224;'
        'border-radius:8px;padding:12px 16px;margin-bottom:14px;font-size:0.9rem;'
        'line-height:1.45;"><strong>HALAMAN UJI — new/index.html</strong><br>'
        f'Sumber: {latest_pred.name} · {valid_prediction_count} prediksi valid; '
        f'{visible_h2h_match_count} kartu dengan H2H ditampilkan; '
        f'{hidden_no_h2h_count} tanpa H2H disembunyikan. '
        'Tombol scan dinonaktifkan; halaman utama tidak diubah.</div>'
    )
    html = html.replace("<body>", "<body>\n" + banner + "\n", 1)
    html = html.replace(
        '<button id="btnScan" onclick="startScan()"',
        '<button id="btnScan" type="button" disabled aria-disabled="true" '
        'title="Scan dinonaktifkan pada halaman uji"',
        1,
    )
    html = html.replace("Scan Ulang Data", "Scan dinonaktifkan", 1)

OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
OUT_HTML.write_text(
    "\n".join(line.rstrip() for line in html.splitlines()) + "\n",
    encoding="utf-8",
)
model_label = "EXP-06 primary" if uses_primary_model else "Mode B legacy"
print(f"✅ Dashboard {model_label} dibuat: {OUT_HTML}")
