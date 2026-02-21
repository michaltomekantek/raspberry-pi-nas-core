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
api = Api(app, version='2.0', title='Raspberry Pi Ultimate API',
          description='Monitoring systemu, dysków i logów backupu')

# Podział na sekcje (Namespaces) w Swaggerze
sys_ns = api.namespace('system', description='Statystyki sprzętowe')
logs_ns = api.namespace('backups', description='Analiza logów backupu')

# --- FUNKCJE POMOCNICZE (Hardware) ---

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
                    return f"{re.search(r'^(\d+)', val).group(1)}°C"
        except: continue
    return "N/A"

# --- ENDPOINTY: SYSTEM ---

@sys_ns.route('/stats')
class SystemStats(Resource):
    def get(self):
        """Zwraca temperaturę CPU, RAM i pogrupowane dyski."""
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

# --- ENDPOINTY: BACKUPS ---

@logs_ns.route('/')
class BackupList(Resource):
    def get(self):
        """Lista wszystkich dostępnych plików logów."""
        files = get_backup_files()
        result = []
        for f in files:
            # Szybki podgląd statusu
            data = parse_backup_log(f)
            result.append({"filename": f, "status": data["status"], "date": data["timestamp"]})
        return result

@logs_ns.route('/<string:filename>')
class BackupDetail(Resource):
    def get(self, filename):
        """Pełne szczegóły wyciągnięte z jednego logu."""
        data = parse_backup_log(filename)
        if not data: return {"error": "Not found"}, 404
        return data

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)