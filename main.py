from flask import Flask
from flask_restx import Api, Resource
import psutil
import os

app = Flask(__name__)
# Konfiguracja Swaggera
api = Api(app, version='1.0', title='Raspberry Pi Info API',
          description='Endpointy do monitorowania stanu malinki')

ns = api.namespace('system', description='Operacje systemowe')

def get_temp():
    """Pobiera temperaturę procesora na Raspberry Pi."""
    try:
        # Standardowa ścieżka w Raspberry Pi OS
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000.0
            return f"{temp:.1f}°C"
    except:
        return "N/A (Czy to na pewno Raspberry Pi?)"

@ns.route('/stats')
class RaspberryStats(Resource):
    @ns.doc('get_stats')
    def get(self):
        """Zwraca temperaturę i informacje o dyskach"""

        # Informacje o dyskach i zajętym miejscu
        disk_info = []
        partitions = psutil.disk_partitions()

        for partition in partitions:
            # Pomijamy pętle i partycje systemowe o zerowej pojemności
            if 'loop' in partition.device or not partition.mountpoint:
                continue

            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent_used": f"{usage.percent}%"
                })
            except PermissionError:
                continue

        return {
            "raspberry_pi_stats": {
                "cpu_temperature": get_temp(),
                "storage": disk_info
            }
        }

if __name__ == '__main__':
    # Uruchamiamy na porcie 5000, dostępnym w sieci lokalnej (0.0.0.0)
    app.run(host='0.0.0.0', port=5000, debug=True)