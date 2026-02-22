import json
import os

LOG_DIR = "/home/michal_raspberry/logs"

def get_backup_files():
    """Zwraca listę wszystkich plików .json z folderu logów."""
    if not os.path.exists(LOG_DIR):
        return []

    try:
        all_files = os.listdir(LOG_DIR)
        # Pobieramy wszystko, co kończy się na .json
        json_files = [f for f in all_files if f.endswith(".json")]
        json_files.sort(reverse=True)
        return json_files
    except Exception as e:
        print(f"Błąd listowania plików: {e}")
        return []

def parse_backup_log(filename):
    """Wczytuje dane z konkretnego pliku JSON."""
    path = os.path.join(LOG_DIR, filename)
    if not os.path.exists(path):
        return {"error": "Plik nie istnieje"}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Dodajemy nazwę pliku do słownika dla frontendu
            data["filename"] = filename
            return data
    except Exception as e:
        return {"error": f"Błąd odczytu: {str(e)}", "filename": filename}