import subprocess
import os

SCRIPTS_DIR = "/home/michal_raspberry/scripts"

def run_script(script_name):
    """Uruchamia skrypt bashowy w tle i zwraca informację czy udało się go odpalić."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)

    if not os.path.exists(script_path):
        return {"error": f"Skrypt {script_name} nie istnieje w {SCRIPTS_DIR}"}, 404

    try:
        # Uruchamiamy skrypt jako osobny proces, żeby nie blokować API
        # Wynik logowany jest do standardowego wyjścia systemowego
        subprocess.Popen(["/bin/bash", script_path],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)

        return {
            "status": "Started",
            "message": f"Skrypt {script_name} został uruchomiony w tle.",
            "script": script_name
        }, 202
    except Exception as e:
        return {"error": str(e)}, 500