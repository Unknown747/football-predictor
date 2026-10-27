#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
import threading

BASE = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=None)

# Status global untuk mencegah scan ganda
scan_status = {"running": False, "last_output": ""}

def run_pipeline():
    global scan_status
    scan_status["running"] = True
    scan_status["last_output"] = "Memulai pipeline...\n"
    try:
        # 1. Scrape
        scan_status["last_output"] += "1. Scraping fixtures...\n"
        res1 = subprocess.run([sys.executable, "scrape_fixtures.py"], capture_output=True, text=True, cwd=BASE)
        if res1.returncode != 0:
            scan_status["last_output"] += f"❌ Scrape gagal:\n{res1.stderr}\n"
            return
        
        # 2. Predict
        scan_status["last_output"] += "2. Memprediksi 241 match...\n"
        fixture_path = "predictions/fixtures_7hari/fixture_fotmob_latest.csv"
        res2 = subprocess.run([sys.executable, "predict.py", "--input", fixture_path, "--output-dir", "predictions/"], capture_output=True, text=True, cwd=BASE)
        if res2.returncode != 0:
            scan_status["last_output"] += f"❌ Predict gagal:\n{res2.stderr}\n"
            return
            
        # 3. Build HTML
        scan_status["last_output"] += "3. Membangun Dashboard HTML...\n"
        res3 = subprocess.run([sys.executable, "build_html_dashboard.py"], capture_output=True, text=True, cwd=BASE)
        if res3.returncode != 0:
            scan_status["last_output"] += f"❌ Build HTML gagal:\n{res3.stderr}\n"
            return
            
        scan_status["last_output"] += "✅ Semua proses selesai! Silakan refresh halaman."
    except Exception as e:
        scan_status["last_output"] += f"❌ Error: {str(e)}\n"
    finally:
        scan_status["running"] = False

@app.route('/')
def index():
    return send_from_directory(BASE, 'index.html')

@app.route('/api/scan', methods=['POST'])
def scan():
    if scan_status["running"]:
        return jsonify({"status": "error", "message": "Scan sedang berjalan!"}), 429
    thread = threading.Thread(target=run_pipeline)
    thread.start()
    return jsonify({"status": "started", "message": "Scan dimulai di latar belakang"})

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify(scan_status)


@app.route('/index_simple.html')
def index_simple():
    return send_from_directory(BASE, 'index_simple.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(BASE, filename)

if __name__ == '__main__':
    print("🚀 Server berjalan di http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)
