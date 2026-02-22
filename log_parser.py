import json
import os

LOG_DIR = "/home/michal_raspberry/logs"

def get_backup_files():
    """Zwraca listę wszystkich plików .json z folderu logów."""
    if not os.path.exists(LOG_DIR):
        return []

    try:
        # Pobieramy wszystko, co kończy się na .json
        all_files = os.listdir(LOG_DIR)
        json_files = [f for f in all_files if f.endswith(".json")]

        # Sortujemy malejąco, żeby najnowsze daty były na górze
        json_files.sort(reverse=True)
        return json_files
    except Exception as e:
        print(f"Błąd listowania plików: {e}")
        return []

# Reszta pliku (parse_backup_log) zostaje bez zmian