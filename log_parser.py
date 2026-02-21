import json
import os

LOG_DIR = "/home/michal_raspberry/logs"

def get_backup_files():
    """Zwraca listę dostępnych plików JSON z logami."""
    if not os.path.exists(LOG_DIR):
        print(f"DEBUG: Folder {LOG_DIR} nie istnieje!")
        return []

    try:
        # Pobieramy wszystkie pliki .json
        all_files = os.listdir(LOG_DIR)
        # Filtrujemy tylko te od backupu
        backup_files = [f for f in all_files if f.startswith("backup_") and f.endswith(".json")]

        print(f"DEBUG: Znaleziono w folderze: {len(backup_files)} plików JSON")

        backup_files.sort(reverse=True)
        return backup_files
    except Exception as e:
        print(f"DEBUG: Błąd listowania plików: {e}")
        return []

def parse_backup_log(filename):
    """Wczytuje dane z pliku JSON."""
    path = os.path.join(LOG_DIR, filename)

    if not os.path.exists(path):
        return {"error": "Plik nie istnieje", "filename": filename}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            data["filename"] = filename
            return data
    except Exception as e:
        # Jeśli np. nie ma uprawnień do pliku roota
        return {"error": f"Błąd odczytu: {str(e)}", "filename": filename, "status": "Error"}