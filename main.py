from flask import Flask
from flask_restx import Api, Resource
import psutil
import subprocess
import re
from datetime import datetime

app = Flask(__name__)
api = Api(app, version='1.3', title='Raspberry Pi NAS Monitor',
          description='Statystyki systemowe: CPU, RAM, Uptime i Dyski (SMART)')

ns = api.namespace('system', description='Statystyki systemowe')

def get_uptime():
    """Zwraca czas działania systemu w czytelnym formacie."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    diff = now - boot_time
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m"

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return f"{int(f.read()) / 1000.0:.1f}°C"
    except:
        return "N/A"

def get_disk_temp(device):
    try:
        result = subprocess.check_output(['sudo', 'smartctl', '-A', device],
                                         stderr=subprocess.STDOUT,
                                         universal_newlines=True)
        for line in result.splitlines():
            if "Temperature_Celsius" in line or "Airflow_Temperature_Cel" in line:
                parts = line.split()
                if len(parts) >= 10:
                    temp_raw = parts[9]
                    temp_only = re.search(r'^(\.?\d+)', temp_raw)
                    if temp_only:
                        return f"{temp_only.group(1)}°C"
        return "Brak danych"
    except Exception:
        return "Nieobsługiwany adapter"

@ns.route('/stats')
class RaspberryStats(Resource):
    def get(self):
        # Statystyki RAM
        ram = psutil.virtual_memory()

        disk_info = []
        partitions = psutil.disk_partitions()
        seen_physical_devices = {}

        for partition in partitions:
            if 'loop' in partition.device or not partition.mountpoint or '/snap/' in partition.mountpoint:
                continue

            device_base = re.sub(r'\d+$', '', partition.device)

            if device_base not in seen_physical_devices:
                if device_base.startswith('/dev/sd') or device_base.startswith('/dev/nvme'):
                    seen_physical_devices[device_base] = get_disk_temp(device_base)
                else:
                    seen_physical_devices[device_base] = "N/A"

            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "partition": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "percent_used": f"{usage.percent}%",
                    "temp": seen_physical_devices[device_base]
                })
            except:
                continue

        return {
            "system_info": {
                "uptime": get_uptime(),
                "cpu_temp": get_cpu_temp(),
                "ram_usage": {
                    "total_gb": round(ram.total / (1024**3), 2),
                    "used_gb": round(ram.used / (1024**3), 2),
                    "percent": f"{ram.percent}%"
                }
            },
            "disks": disk_info
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)