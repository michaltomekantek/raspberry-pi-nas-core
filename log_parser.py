import os
import re

LOG_DIR = "/home/michal_raspberry/logs"

def get_backup_files():
    """Zwraca listę plików backupu posortowaną od najnowszych."""
    try:
        if not os.path.exists(LOG_DIR):
            return []
        files = [f for f in os.listdir(LOG_DIR) if f.startswith("backup_20") and f.endswith(".log")]
        files.sort(reverse=True)
        return files
    except Exception:
        return []

def parse_backup_log(filename):
    """Wyciąga dane strukturalne z pliku tekstowego logu."""
    path = os.path.join(LOG_DIR, filename)
    if not os.path.exists(path):
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Szukanie konkretnych fraz w logu
        res_date = re.search(r"START BACKUPU IMMICH - ([\d-]+ [\d:]+)", content)
        res_sizes = re.search(r"Zdjęcia: (.*?) \| Miniatury: (.*?) \| Wideo: (.*)", content)
        res_upload = re.search(r"Synchronizacja upload.*?WYNIK: (.*?)\.", content, re.S)
        res_total = re.search(r"Całość na HDD zajmuje teraz: (.*)", content)

        return {
            "filename": filename,
            "status": "Success" if "ZAKOŃCZONO!" in content else "Incomplete",
            "timestamp": res_date.group(1) if res_date else "N/A",
            "details": {
                "photos_size": res_sizes.group(1) if res_sizes else "N/A",
                "thumbs_size": res_sizes.group(2) if res_sizes else "N/A",
                "videos_size": res_sizes.group(3) if res_sizes else "N/A",
                "db_status": "OK" if "OK: Baza zapisana" in content else "Error",
                "sync_result": res_upload.group(1).strip() if res_upload else "Brak danych",
                "total_on_disk": res_total.group(1).strip() if res_total else "N/A"
            }
        }
    except Exception as e:
        return {"error": str(e)}