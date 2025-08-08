import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO

# -------------------- PyInstaller FIX --------------------
if getattr(sys, "frozen", False):
    BASE_PATH = sys._MEIPASS  # путь к распакованному onefile
else:
    BASE_PATH = os.path.abspath(os.path.dirname(__file__))

# -------------------- ЛОГИ --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s"
)
log = logging.getLogger("web_dashboard")

# -------------------- Flask + Socket.IO --------------------
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_PATH, "templates"),
    static_folder=os.path.join(BASE_PATH, "static"),
)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# -------------------- Настройки --------------------
SETTINGS_PATH = Path("settings.json")
DEFAULT_SETTINGS = {
    "intervalHours": 1,
    "reportLang": "ru",
    "autoRefresh": True,
    "slaDl": 30,
    "slaPing": 100,
    "recentLimit": 12
}

def read_settings():
    if SETTINGS_PATH.exists():
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception as e:
            log.warning("settings.json read failed: %s", e)
    return DEFAULT_SETTINGS.copy()

def write_settings(data: dict):
    tmp = SETTINGS_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(SETTINGS_PATH)

SETTINGS = read_settings()
CONFIG = {"test_interval": int(max(300, min(24*3600, SETTINGS["intervalHours"] * 3600)))}

# -------------------- Импорт утилит --------------------
from utils import test_speed, save_data, cleanup_old_data, load_data

# -------------------- Роуты --------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.get("/api/health")
def api_health():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat() + "Z"})

@app.get("/api/data")
def api_data():
    try:
        days = max(1, min(request.args.get("days", default=7, type=int), 90))
        data = load_data(days=days)
        return jsonify({"data": data})
    except Exception as e:
        log.exception("api_data failed: %s", e)
        return jsonify({"data": []}), 500

@app.post("/api/test-now")
def api_test_now():
    def run_test():
        try:
            result = test_speed()
            if result:
                save_data(result)
                cleanup_old_data()
                log.info("Manual test OK: DL=%.2f UL=%.2f Ping=%.2f",
                         result.get("download", 0), result.get("upload", 0), result.get("ping", 0))
                socketio.emit("new_test", result)
            else:
                log.warning("Manual test failed (no data)")
        except Exception as e:
            log.exception("run_test error: %s", e)

    threading.Thread(target=run_test, name="manual-test", daemon=True).start()
    return jsonify({"success": True})

@app.get("/api/settings")
def api_settings_get():
    return jsonify({**SETTINGS, "test_interval": CONFIG["test_interval"]})

@app.post("/api/settings")
def api_settings_post():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        changed = False
        for k in DEFAULT_SETTINGS:
            if k in payload:
                SETTINGS[k] = payload[k]
                changed = True
        if changed:
            write_settings(SETTINGS)

        ti = int(payload.get("test_interval", SETTINGS["intervalHours"] * 3600))
        ti = max(300, min(ti, 24 * 3600))
        old = CONFIG["test_interval"]
        CONFIG["test_interval"] = ti
        if ti != old:
            log.info("test_interval updated: %s -> %s sec", old, ti)

        return jsonify({"ok": True, "settings": SETTINGS, "test_interval": ti})
    except Exception as e:
        log.exception("api_settings error: %s", e)
        return jsonify({"ok": False, "error": "invalid_payload"}), 400

# -------------------- Планировщик --------------------
_stop_event = threading.Event()

def scheduled_worker():
    log.info("Scheduler started (interval=%ss)", CONFIG["test_interval"])
    while not _stop_event.is_set():
        try:
            result = test_speed()
            if result:
                save_data(result)
                cleanup_old_data()
                log.info("Scheduled test OK: DL=%.2f UL=%.2f Ping=%.2f",
                         result.get("download", 0), result.get("upload", 0), result.get("ping", 0))
                socketio.emit("new_test", result)
            else:
                log.warning("Scheduled test failed (no data)")
        except Exception as e:
            log.exception("scheduled_worker error: %s", e)

        total_sleep = max(1, int(CONFIG["test_interval"]))
        slept = 0
        while slept < total_sleep and not _stop_event.is_set():
            time.sleep(1)
            slept += 1
    log.info("Scheduler stopped")

def start_scheduler_once():
    if getattr(start_scheduler_once, "started", False):
        return
    t = threading.Thread(target=scheduled_worker, name="scheduler", daemon=True)
    t.start()
    start_scheduler_once.started = True

# -------------------- Socket.IO --------------------
@socketio.on("connect")
def on_connect():
    log.info("Client connected")

@socketio.on("disconnect")
def on_disconnect():
    log.info("Client disconnected")

# -------------------- main --------------------
if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        start_scheduler_once()
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)
