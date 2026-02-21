from flask import Flask
from flask_restx import Api, Resource
from flask_cors import CORS
import psutil
import subprocess
import re
import json
from datetime import datetime

app = Flask(__name__)
# CORS(app) pozwala na zapytania z dowolnego źródła (np. Twojego frontendu na porcie 32110)
CORS(app)

api = Api(app, version='1.6', title='Raspberry Pi NAS API',
          description='Monitoring systemu i dysków z obsługą CORS i SMART')

ns = api.namespace('system', description='Statystyki systemowe')

def get_uptime():
    """Oblicza czas działania systemu."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    diff = datetime.now() - boot_time
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m"

def get_cpu_temp():
    """Odczyt temperatury procesora."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return f"{int(f.read()) / 1000.0:.1f}°C"
    except:
        return "N/A"

def parse_smartctl_output(output):
    """Parsuje tekst z smartctl w poszukiwaniu temperatury w kolumnie RAW_VALUE."""
    for line in output.splitlines():
        if "Temperature_Celsius" in line or "Airflow_Temperature_Cel" in line:
            parts = line.split()
            if len(parts) >= 10:
                # RAW_VALUE to zazwyczaj 10-ty element (index 9)
                temp_raw = parts[9]
                # Wyciągamy tylko cyfry (obsługa formatów typu '43 (Min/Max 41/44)')
                temp_match = re.search(r'^(\d+)', temp_raw)
                if temp_match:
                    return f"{temp_match.group(1)}°C"
    return None

def get_disk_temp(device):
    """Próbuje odczytać temperaturę dysku różnymi metodami."""
    # Metoda 1: Standardowa, Metoda 2: Wymuszenie SAT (dla mostków USB)
    configs = [
        ['sudo', 'smartctl', '-A', device],
        ['sudo', 'smartctl', '-d', 'sat', '-A', device]
    ]

    for cmd in configs:
        try:
            # check=False zapobiega rzucaniu błędu przy nieudanej pierwszej próbie
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            temp = parse_smartctl_output(result.stdout)
            if temp:
                return temp
        except:
            continue
    return "Nieobsługiwany"

@ns.route('/stats')
class RaspberryStats(Resource):
    def get(self):
        """Endpoint zwracający komplet statystyk."""
        ram = psutil.virtual_memory()
        disk_info = []
        partitions = psutil.disk_partitions()

        # Zapamiętujemy temp dla fizycznego urządzenia, by nie pytać 5 razy o ten sam dysk
        physical_temps = {}

        for part in partitions:
            # Filtrujemy niepotrzebne systemy plików
            if any(x in part.mountpoint for x in ['/snap', '/docker', '/loop']):
                continue
            if not part.device.startswith('/dev/sd') and not part.device.startswith('/dev/nvme'):
                # Możesz tu dodać obsługę karty SD, ale ona zazwyczaj nie ma czujnika
                continue

            # Wyciągamy bazę urządzenia, np. /dev/sda
            dev_base = re.sub(r'\d+$', '', part.device)

            if dev_base not in physical_temps:
                physical_temps[dev_base] = get_disk_temp(dev_base)

            try:
                usage = psutil.disk_usage(part.mountpoint)
                disk_info.append({
                    "partition": part.device,
                    "mountpoint": part.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "percent_used": f"{usage.percent}%",
                    "temp": physical_temps[dev_base]
                })
            except:
                continue

        return {
            "system": {
                "uptime": get_uptime(),
                "cpu_temp": get_cpu_temp(),
                "ram": {
                    "total_gb": round(ram.total / (1024**3), 2),
                    "used_gb": round(ram.used / (1024**3), 2),
                    "percent": f"{ram.percent}%"
                }
            },
            "disks": disk_info
        }

if __name__ == '__main__':
    # Ważne: 0.0.0.0 pozwala na dostęp z innych urządzeń w sieci
    app.run(host='0.0.0.0', port=5000, debug=True)