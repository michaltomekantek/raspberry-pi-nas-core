import subprocess
import os

SCRIPTS_DIR = "/home/michal_raspberry/scripts"

def run_script(script_name):
    script_path = os.path.join(SCRIPTS_DIR, script_name)

    if not os.path.exists(script_path):
        return {"error": f"Skrypt {script_name} nie istnieje"}, 404

    try:
        # Usuwamy stdout=DEVNULL, żeby Bash mógł sam zarządzać logowaniem przez 'exec' wewnątrz skryptu
        subprocess.Popen(
            ["/bin/bash", script_path],
            start_new_session=True,
            # Nie przechwytujemy wyjścia tutaj, bo skrypt sam zapisuje do logu
            stdout=None,
            stderr=None
        )

        return {
            "status": "Started",
            "message": "Skrypt ruszył. Logi są generowane dynamicznie w folderze logów."
        }, 202
    except Exception as e:
        return {"error": str(e)}, 500