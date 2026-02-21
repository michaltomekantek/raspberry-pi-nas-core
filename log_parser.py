import json
import os

LOG_DIR = "/home/michal_raspberry/logs"

def get_backup_files():
    """Zwraca listę dostępnych plików JSON z logami, od najnowszego."""
    try:
        if not os.path.exists(LOG_DIR):
            return []
        # Szukamy plików kończących się na .json
        files = [f for f in os.listdir(LOG_DIR) if f.startswith("backup_20") and f.endswith(".json")]
        files.sort(reverse=True)
        return files
    except Exception:
        return []

def parse_backup_log(filename):
    """Wczytuje gotowe dane z pliku JSON."""
    path = os.path.join(LOG_DIR, filename)
    if not os.path.exists(path):
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Dodajemy nazwę pliku do słownika, żeby frontend wiedział co czyta
        data["filename"] = filename
        return data
    except Exception as e:
        return {"error": f"Błąd odczytu pliku JSON: {str(e)}", "filename": filename}