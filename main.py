from flask import Flask
from flask_restx import Api, Resource
from flask_cors import CORS
import psutil
import subprocess
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

api = Api(app, version='1.7', title='Raspberry Pi NAS API',
          description='Grupowanie partycji per fizyczny dysk')

ns = api.namespace('system', description='Statystyki systemowe')

def get_uptime():
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    diff = datetime.now() - boot_time
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

def parse_smartctl_output(output):
    for line in output.splitlines():
        if "Temperature_Celsius" in line or "Airflow_Temperature_Cel" in line:
            parts = line.split()
            if len(parts) >= 10:
                temp_raw = parts[9]
                temp_match = re.search(r'^(\d+)', temp_raw)
                if temp_match:
                    return f"{temp_match.group(1)}°C"
    return None

def get_disk_temp(device):
    configs = [
        ['sudo', 'smartctl', '-A', device],
        ['sudo', 'smartctl', '-d', 'sat', '-A', device]
    ]
    for cmd in configs:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            temp = parse_smartctl_output(result.stdout)
            if temp: return temp
        except: continue
    return "N/A"

@ns.route('/stats')
class RaspberryStats(Resource):
    def get(self):
        ram = psutil.virtual_memory()
        partitions = psutil.disk_partitions()

        # Słownik na pogrupowane dane: { '/dev/sda': { 'temp': '36°C', 'partitions': [...] } }
        grouped_disks = {}

        for part in partitions:
            # Filtry systemowe
            if any(x in part.mountpoint for x in ['/snap', '/docker', '/loop']):
                continue
            if not part.device.startswith('/dev/sd') and not part.device.startswith('/dev/nvme'):
                continue

            # Wyciągamy bazę (np. /dev/sda) usuwając cyfry z końca
            dev_base = re.sub(r'\d+$', '', part.device)

            # Jeśli pierwszy raz widzimy ten dysk fizyczny, zainicjuj go
            if dev_base not in grouped_disks:
                grouped_disks[dev_base] = {
                    "physical_device": dev_base,
                    "temperature": get_disk_temp(dev_base),
                    "partitions": []
                }

            try:
                usage = psutil.disk_usage(part.mountpoint)
                grouped_disks[dev_base]["partitions"].append({
                    "partition_name": part.device,
                    "mountpoint": part.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "percent_used": f"{usage.percent}%"
                })
            except:
                continue

        # Zamieniamy słownik na listę dla ładniejszego JSONa
        disks_list = list(grouped_disks.values())

        return {
            "system": {
                "uptime": get_uptime(),
                "cpu_temp": get_cpu_temp(),
                "ram_percent": f"{ram.percent}%"
            },
            "physical_disks": disks_list
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)