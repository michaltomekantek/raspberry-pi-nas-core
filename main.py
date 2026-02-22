from flask import Flask
from flask_restx import Api, Resource
from flask_cors import CORS
import psutil
import subprocess
import re
import os
import time
from datetime import datetime

# Importujemy nasz parser z osobnego pliku
from log_parser import get_backup_files, parse_backup_log
from script_manager import run_script
from system_manager import shutdown_raspberry, reboot_raspberry

app = Flask(__name__)
CORS(app)
api = Api(app, version='2.2', title='Raspberry Pi NAS Ultimate API',
          description='Monitoring systemu, dysków i logów backupu')

sys_ns = api.namespace('system', description='Statystyki sprzętowe')
logs_ns = api.namespace('backups', description='Analiza logów backupu')
actions_ns = api.namespace('actions', description='Ręczne wywoływanie zadań')
power_ns = api.namespace('power', description='Zarządzanie zasilaniem urządzenia')



# --- FUNKCJE POMOCNICZE ---

# Cache na dane z komendy du
storage_cache = {}

def get_uptime():
    """Zwraca czytelny czas pracy systemu."""
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])

    days = int(uptime_seconds // (24 * 3600))
    hours = int((uptime_seconds % (24 * 3600)) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return f"{int(f.read()) / 1000.0:.1f}°C"
    except: return "N/A"

def get_disk_temp(device):
    configs = [['sudo', 'smartctl', '-A', device], ['sudo', 'smartctl', '-d', 'sat', '-A', device]]
    for cmd in configs:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            for line in result.stdout.splitlines():
                if "Temperature_Celsius" in line or "Airflow_Temperature_Cel" in line:
                    val = line.split()[9]
                    temp_match = re.search(r'^(\d+)', val)
                    return f"{temp_match.group(1)}°C" if temp_match else "N/A"
        except: continue
    return "N/A"

# --- ENDPOINTY: SYSTEM ---

CACHE_TIMEOUT = 600  # 10 minut

def get_mount_details(path):
    """Pobiera wagę folderów i realny rozmiar dla dowolnej ścieżki."""
    now = time.time()

    # Jeśli mamy świeży cache dla tej ścieżki, zwracamy go
    if path in storage_cache and (now - storage_cache[path]["last_update"] < CACHE_TIMEOUT):
        return storage_cache[path]

    try:
        # 1. Pobieramy wagę folderów (max-depth=1)
        # Używamy sudo, aby mieć dostęp do wszystkich podfolderów
        result = subprocess.run(
            f"sudo du -sh {path}/*",
            shell=True, capture_output=True, text=True, timeout=15
        )

        folders = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                size_str = parts[0]
                folder_name = os.path.basename(parts[1])
                folders[folder_name] = size_str

        # 2. Pobieramy dokładną sumę bajtów (dla precyzyjnego used_percent)
        total_res = subprocess.run(['sudo', 'du', '-sb', path], capture_output=True, text=True, timeout=10)
        total_bytes = int(total_res.stdout.split()[0])

        # Zapisujemy do cache
        storage_cache[path] = {
            "folders": folders,
            "used_gb_real": total_bytes / (1024**3),
            "last_update": now
        }
    except Exception as e:
        # W razie błędu (np. pusty dysk) zwracamy puste dane, żeby nie wywalić API
        storage_cache[path] = {
            "folders": {"info": "Brak danych lub dysk pusty"},
            "used_gb_real": 0,
            "last_update": now
        }

    return storage_cache[path]

@sys_ns.route('/stats')
class SystemStats(Resource):
    def get(self):
        ram = psutil.virtual_memory()
        load1, _, _ = os.getloadavg()
        partitions = psutil.disk_partitions()
        grouped_disks = {}

        for part in partitions:
            # Filtrujemy tylko fizyczne dyski SD
            if any(x in part.mountpoint for x in ['/snap', '/docker', '/loop']) or not part.device.startswith('/dev/sd'):
                continue

            dev_base = re.sub(r'\d+$', '', part.device)
            if dev_base not in grouped_disks:
                grouped_disks[dev_base] = {"device": dev_base, "temp": get_disk_temp(dev_base), "partitions": []}

            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = round(usage.total / (1024**3), 2)

                # Pobieramy szczegóły (foldery i realną wagę) dla KAŻDEGO punktu montowania
                details = get_mount_details(part.mountpoint)
                used_gb = details["used_gb_real"]

                # Budujemy JSON w Twoim formacie
                p_data = {
                    "mount": part.mountpoint,
                    "used_percent": f"{round((used_gb / total_gb) * 100, 1)}%",
                    "free_gb": round(total_gb - used_gb, 2),
                    "total_gb": total_gb,
                    "folder_usage": details["folders"]  # Teraz w każdym dysku
                }

                grouped_disks[dev_base]["partitions"].append(p_data)
            except Exception as e:
                print(f"Błąd partycji {part.mountpoint}: {e}")
                continue

        return {
            "system_info": {
                "uptime": get_uptime(),
                "cpu_temp": get_cpu_temp(),
                "cpu_load_1min": round(load1, 2),
                "active_processes": len(psutil.pids())
            },
            "ram": {
                "total_gb": round(ram.total / (1024**3), 2),
                "used_gb": round(ram.used / (1024**3), 2),
                "free_gb": round(ram.available / (1024**3), 2),
                "percent": f"{ram.percent}%"
            },
            "disks": list(grouped_disks.values())
        }
# --- ENDPOINTY: BACKUPS ---

@logs_ns.route('/')
class BackupList(Resource):
    def get(self):
        files = get_backup_files()
        result = []
        for f in files:
            data = parse_backup_log(f)
            if data and "error" in data:
                result.append({"filename": f, "status": "Error/NoAccess", "date": "N/A", "error_detail": data["error"]})
            else:
                result.append({"filename": f, "status": data.get("status", "Unknown"), "date": data.get("timestamp", "N/A")})
        return result

@logs_ns.route('/<string:filename>')
class BackupDetail(Resource):
    def get(self, filename):
        if not filename.endswith('.json'): filename += '.json'
        data = parse_backup_log(filename)
        if not data or "error" in data:
            return {"error": data.get("error", "Plik nie istnieje") if data else "Plik nie istnieje"}, 404
        return data

@actions_ns.route('/run-daily-backup')
class RunDailyBackup(Resource):
    def post(self):
        """Uruchamia codzienny backup (backup.sh)"""
        return run_script("backup.sh")

@actions_ns.route('/run-cold-storage')
class RunColdStorage(Resource):
    def post(self):
        """Uruchamia backup na zimny dysk (cold_storage.sh)"""
        return run_script("cold_storage.sh")

@power_ns.route('/shutdown')
class Shutdown(Resource):
    @api.doc(description='Natychmiastowe wyłączenie Raspberry Pi')
    def post(self):
        try:
            shutdown_raspberry()
            return {'status': 'success', 'message': 'System is shutting down...'}, 200
        except Exception as e:
            return {'status': 'error', 'message': str(e)}, 500

@power_ns.route('/reboot')
class Reboot(Resource):
    @api.doc(description='Natychmiastowy restart Raspberry Pi')
    def post(self):
        try:
            reboot_raspberry()
            return {'status': 'success', 'message': 'System is rebooting...'}, 200
        except Exception as e:
            return {'status': 'error', 'message': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)