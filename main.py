from flask import Flask
from flask_restx import Api, Resource
from flask_cors import CORS
import psutil
import subprocess
import re
from datetime import datetime

# Importujemy nasz parser z osobnego pliku
from log_parser import get_backup_files, parse_backup_log

app = Flask(__name__)
CORS(app)
api = Api(app, version='2.1', title='Raspberry Pi Ultimate API',
          description='Monitoring systemu, dysków i logów backupu')

sys_ns = api.namespace('system', description='Statystyki sprzętowe')
logs_ns = api.namespace('backups', description='Analiza logów backupu')

# --- HARDWARE FUNCTIONS ---

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return f"{int(f.read()) / 1000.0:.1f}°C"
    except: return "N/A"

def get_disk_temp(device):
    # Próba odczytu dla standardowych dysków i tych za mostkiem USB (sat)
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

# --- ENDPOINTS: SYSTEM ---

@sys_ns.route('/stats')
class SystemStats(Resource):
    def get(self):
        ram = psutil.virtual_memory()
        partitions = psutil.disk_partitions()
        grouped_disks = {}

        for part in partitions:
            if any(x in part.mountpoint for x in ['/snap', '/docker', '/loop']) or not part.device.startswith('/dev/sd'):
                continue
            dev_base = re.sub(r'\d+$', '', part.device)
            if dev_base not in grouped_disks:
                grouped_disks[dev_base] = {"device": dev_base, "temp": get_disk_temp(dev_base), "partitions": []}

            try:
                usage = psutil.disk_usage(part.mountpoint)
                grouped_disks[dev_base]["partitions"].append({
                    "mount": part.mountpoint,
                    "used_percent": f"{usage.percent}%",
                    "free_gb": round(usage.free / (1024**3), 2)
                })
            except: continue
        return {
            "cpu_temp": get_cpu_temp(),
            "ram_percent": f"{ram.percent}%",
            "disks": list(grouped_disks.values())
        }

# --- ENDPOINTS: BACKUPS ---

@logs_ns.route('/')
class BackupList(Resource):
    def get(self):
        """Lista wszystkich raportów JSON."""
        files = get_backup_files()
        result = []
        for f in files:
            data = parse_backup_log(f)
            # Nawet jeśli jest błąd (np. brak uprawnień), pokaż plik na liście
            if data and "error" in data:
                result.append({
                    "filename": f,
                    "status": "Error/NoAccess",
                    "date": "N/A",
                    "error_detail": data["error"]
                })
            else:
                result.append({
                    "filename": f,
                    "status": data.get("status", "Unknown"),
                    "date": data.get("timestamp", "N/A")
                })
        return result

@logs_ns.route('/<string:filename>')
class BackupDetail(Resource):
    def get(self, filename):
        """Pełne dane z konkretnego raportu JSON."""
        if not filename.endswith('.json'):
            filename += '.json'

        data = parse_backup_log(filename)
        if not data or "error" in data:
            # Zwracamy szczegóły błędu zamiast ogólnego 404
            return {"error": data.get("error", "Plik nie istnieje") if data else "Plik nie istnieje"}, 404
        return data

if __name__ == '__main__':
    # Ważne: debug=True ułatwia szukanie błędów, ale restartuje apkę przy zmianach w kodzie
    app.run(host='0.0.0.0', port=5000, debug=True)