import os
import json
import shutil
import subprocess
import threading
from datetime import datetime, timedelta

# === ВНЕШНИЕ ЗАВИСИМОСТИ ===
# pip install speedtest-cli
import speedtest

CONFIG = {
    "data_dir": "speed_data",
    "days_to_keep": 30,
    "test_interval": 3600,  # секунд
    "server_id": None       # например: 12345
}

file_lock = threading.Lock()

# ---------- SPEEDTEST (python) с ретраями ----------
def _speedtest_python(tries=3):
    for attempt in range(1, tries + 1):
        try:
            st = speedtest.Speedtest(secure=True, timeout=10)  # HTTPS + таймаут
            if CONFIG.get("server_id"):
                st.get_servers([CONFIG["server_id"]])
            else:
                st.get_servers()
            best = st.get_best_server()
            down_mbps = st.download() / 1_000_000
            up_mbps   = st.upload() / 1_000_000
            ping_ms   = st.results.ping or best.get("latency")

            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "download": round(down_mbps, 2),
                "upload": round(up_mbps, 2),
                "ping": round(float(ping_ms), 2) if ping_ms is not None else None,
                "server": best.get("host") or best.get("url")
            }
        except speedtest.ConfigRetrievalError as e:
            # Именно твой кейс (403/CF)
            wait = 2 * attempt
            print(f"[WARN] Speedtest config 403/blocked (try {attempt}/{tries}), retry in {wait}s: {e}")
            time.sleep(wait)
        except Exception as e:
            wait = 2 * attempt
            print(f"[WARN] Speedtest failed (try {attempt}/{tries}), retry in {wait}s: {e}")
            time.sleep(wait)
    return None

# ---------- SPEEDTEST (Ookla CLI) fallback ----------
def _speedtest_ookla():
    # Требуется установленный бинарь 'speedtest' (Ookla)
    if not shutil.which("speedtest"):
        return None
    try:
        out = subprocess.check_output(["speedtest", "-f", "json"], timeout=120)
        r = json.loads(out)
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            # bandwidth в байтах/сек -> Мбит/с
            "download": round(r["download"]["bandwidth"] * 8 / 1_000_000, 2),
            "upload":   round(r["upload"]["bandwidth"]   * 8 / 1_000_000, 2),
            "ping":     round(r["ping"]["latency"], 2),
            "server":   r["server"]["host"]
        }
    except Exception as e:
        print(f"[ERR] Ookla CLI failed: {e}")
        return None

def test_speed():
    """Единая точка: python-speedtest -> (если не вышло) Ookla CLI.
       Возвращает dict или None, НИКОГДА не бросает исключения наружу."""
    try:
        r = _speedtest_python()
        if r is None:
            r = _speedtest_ookla()
        return r
    except Exception as e:
        print(f"[ERR] test_speed(): {e}")
        return None

# ---------- ХРАНЕНИЕ ДАННЫХ ----------
def _ensure_dir():
    os.makedirs(CONFIG["data_dir"], exist_ok=True)

def save_data(result: dict):
    """Сохраняет одну запись в файл speed_data/YYYY-MM-DD.json (append)."""
    if not result:
        return
    _ensure_dir()
    date = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(CONFIG["data_dir"], f"{date}.json")
    with file_lock:
        data = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.insert(0, result)  # свежие сверху
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def cleanup_old_data():
    """Удаляет файлы старше days_to_keep."""
    _ensure_dir()
    cutoff = datetime.utcnow() - timedelta(days=CONFIG["days_to_keep"])
    for name in os.listdir(CONFIG["data_dir"]):
        if not name.endswith(".json"):
            continue
        try:
            d = datetime.strptime(name[:-5], "%Y-%m-%d")
            if d < cutoff:
                os.remove(os.path.join(CONFIG["data_dir"], name))
        except Exception:
            continue

def load_data(days=7, max_points=200):
    """Загружает последние 'days' дней, обрезает до max_points на день."""
    _ensure_dir()
    out = []
    today = datetime.utcnow().date()
    for i in range(days):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        path = os.path.join(CONFIG["data_dir"], f"{date}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    day = json.load(f)
                out.append({"date": date, "data": day[:max_points]})
            except Exception:
                continue
    return out
