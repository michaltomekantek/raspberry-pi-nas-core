from flask import Flask
from flask_restx import Api, Resource
import psutil
import subprocess
import re

app = Flask(__name__)
# Konfiguracja Swaggera
api = Api(app, version='1.2', title='Raspberry Pi NAS Monitor',
          description='Monitorowanie temperatury CPU/Dysków oraz zajętości miejsca')

ns = api.namespace('system', description='Statystyki systemowe')

def get_cpu_temp():
    """Pobiera temperaturę procesora malinki."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return f"{int(f.read()) / 1000.0:.1f}°C"
    except:
        return "N/A"

def get_disk_temp(device):
    """Wyciąga realną temperaturę z kolumny RAW_VALUE narzędzia smartctl."""
    try:
        # Wywołujemy smartctl dla konkretnego urządzenia
        result = subprocess.check_output(['sudo', 'smartctl', '-A', device],
                                         stderr=subprocess.STDOUT,
                                         universal_newlines=True)

        # Szukamy linii z Temperature_Celsius lub Airflow_Temperature_Cel
        # Szukamy ostatniej liczby w linii (RAW_VALUE)
        for line in result.splitlines():
            if "Temperature_Celsius" in line or "Airflow_Temperature_Cel" in line:
                parts = line.split()
                if len(parts) >= 10:
                    # RAW_VALUE to zazwyczaj 10. kolumna w wyjściu smartctl -A
                    temp_raw = parts[9]
                    # Czasami raw value zawiera dodatkowe info (np. 43 (Min/Max 41/44)), bierzemy tylko cyfry
                    temp_only = re.search(r'^(\.?\d+)', temp_raw)
                    if temp_only:
                        return f"{temp_only.group(1)}°C"

        return "Brak danych SMART"
    except Exception:
        return "Nieobsługiwany / Brak uprawnień"

@ns.route('/stats')
class RaspberryStats(Resource):
    @ns.doc('get_all_stats')
    def get(self):
        """Zwraca dane o CPU i wszystkich podłączonych dyskach."""
        disk_info = []
        partitions = psutil.disk_partitions()

        # Zbiór, żeby nie sprawdzać tego samego fizycznego dysku wielokrotnie (partycje sda1, sda2 itp.)
        seen_physical_devices = {}

        for partition in partitions:
            # Ignorujemy wirtualne systemy plików
            if 'loop' in partition.device or not partition.mountpoint or '/snap/' in partition.mountpoint:
                continue

            # Znajdujemy nazwę bazową dysku (np. /dev/sdb z /dev/sdb1)
            device_base = re.sub(r'\d+$', '', partition.device)

            # Pobieramy temperaturę tylko raz dla całego fizycznego nośnika
            if device_base not in seen_physical_devices:
                if device_base.startswith('/dev/sd') or device_base.startswith('/dev/nvme'):
                    seen_physical_devices[device_base] = get_disk_temp(device_base)
                else:
                    seen_physical_devices[device_base] = "N/A (SD Card/Internal)"

            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "partition": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "percent_used": f"{usage.percent}%",
                    "device_temp": seen_physical_devices[device_base]
                })
            except PermissionError:
                continue

        return {
            "cpu_temperature": get_cpu_temp(),
            "disks": disk_info
        }

if __name__ == '__main__':
    # Uruchomienie: sudo .venv/bin/python main.py
    app.run(host='0.0.0.0', port=5000, debug=True)