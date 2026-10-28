#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path
from flask import Flask, send_from_directory, jsonify
import threading

BASE = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=None)

# Status global untuk mencegah scan ganda
scan_status = {"running": False, "last_output": ""}
scan_lock = threading.Lock()

def run_and_stream(command):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=BASE,
    )
    for line in process.stdout:
        scan_status["last_output"] = (scan_status["last_output"] + line)[-20000:]
    return process.wait()


def run_pipeline():
    global scan_status
    try:
        scan_status["running"] = True
        scan_status["last_output"] = "Memulai pipeline...\n"
        # 1. Scrape
        scan_status["last_output"] += "1. Scraping fixtures...\n"
        scrape_code = run_and_stream([sys.executable, "-u", "scrape_fixtures.py"])
        if scrape_code != 0:
            scan_status["last_output"] += f"❌ Scrape gagal (exit code {scrape_code}).\n"
            return
        
        # 2. Predict
        scan_status["last_output"] += "2. Memprediksi pertandingan...\n"
        fixture_path = "predictions/fixtures_7hari/fixture_fotmob_latest.csv"
        predict_code = run_and_stream(
            [sys.executable, "-u", "predict.py", "--input", fixture_path, "--output-dir", "predictions/"]
        )
        if predict_code != 0:
            scan_status["last_output"] += f"❌ Predict gagal (exit code {predict_code}).\n"
            return
            
        # 3. Build HTML
        scan_status["last_output"] += "3. Membangun Dashboard HTML...\n"
        build_code = run_and_stream([sys.executable, "-u", "build_html_dashboard.py"])
        if build_code != 0:
            scan_status["last_output"] += f"❌ Build HTML gagal (exit code {build_code}).\n"
            return
            
        scan_status["last_output"] += "✅ Semua proses selesai! Silakan refresh halaman."
    except Exception as e:
        scan_status["last_output"] += f"❌ Error: {str(e)}\n"
    finally:
        scan_status["running"] = False
        scan_lock.release()

@app.route('/')
def index():
    response = send_from_directory(BASE, 'index.html')
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/api/scan', methods=['POST'])
def scan():
    if not scan_lock.acquire(blocking=False):
        return jsonify({"status": "error", "message": "Scan sedang berjalan!"}), 429
    scan_status["running"] = True
    scan_status["last_output"] = "Memulai pipeline...\n"
    try:
        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()
    except Exception as e:
        scan_status["running"] = False
        scan_status["last_output"] = f"❌ Gagal memulai scan: {e}"
        scan_lock.release()
        return jsonify({"status": "error", "message": scan_status["last_output"]}), 500
    return jsonify({"status": "started", "message": "Scan dimulai di latar belakang"})

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify(scan_status)
@app.route('/<path:filename>')
def serve_static(filename):
    response = send_from_directory(BASE, filename)
    if filename == "index.html":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    port = 5000
    print(f"Server berjalan di http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
