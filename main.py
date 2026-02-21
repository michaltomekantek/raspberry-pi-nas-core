from flask import Flask
from flask_restx import Api, Resource
import psutil
import subprocess
import re

app = Flask(__name__)
api = Api(app, version='1.1', title='Raspberry Pi Advanced Info API',
          description='Monitorowanie systemu i temperatury dysków SMART')

ns = api.namespace('system', description='Operacje systemowe')

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return f"{int(f.read()) / 1000.0:.1f}°C"
    except:
        return "N/A"

def get_disk_temp(device):
    """Pobiera temperaturę dysku za pomocą smartctl."""
    try:
        # Uruchamiamy smartctl -n standby (żeby nie budzić uśpionych dysków niepotrzebnie)
        result = subprocess.check_output(['sudo', 'smartctl', '-A', device], stderr=subprocess.STDOUT).decode()
        # Szukamy linii z "Temperature_Celsius" lub "Airflow_Temperature_Cel"
        match = re.search(r'(Temperature_Celsius|Airflow_Temperature_Cel).*\s+(\d+)\s+', result)
        if match:
            return f"{match.group(2)}°C"
        return "Brak danych SMART"
    except Exception:
        return "Nieobsługiwany / Brak uprawnień"

@ns.route('/stats')
class RaspberryStats(Resource):
    def get(self):
        disk_info = []
        partitions = psutil.disk_partitions()

        # Słownik, aby nie sprawdzać temperatury kilka razy dla różnych partycji tego samego dysku
        seen_devices = set()

        for partition in partitions:
            if 'loop' in partition.device or not partition.mountpoint:
                continue

            # Wyciągamy nazwę urządzenia (np. /dev/sda1 -> /dev/sda)
            device_base = re.sub(r'\d+$', '', partition.device)

            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "percent_used": f"{usage.percent}%",
                    "temperature": "N/A"
                }

                # Pobieramy temperaturę tylko raz dla fizycznego urządzenia
                if device_base not in seen_devices and device_base.startswith('/dev/sd'):
                    info["temperature"] = get_disk_temp(device_base)
                    seen_devices.add(device_base)
                elif device_base in seen_devices:
                    info["temperature"] = "Patrz wyżej (to samo urządzenie)"

                disk_info.append(info)
            except PermissionError:
                continue

        return {
            "cpu_temperature": get_cpu_temp(),
            "storage_devices": disk_info
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)