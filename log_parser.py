import os

LOG_DIR = "/home/michal_raspberry/logs"

def get_backup_files():
    """Zwraca listę wszystkich plików .log z folderu logów."""
    if not os.path.exists(LOG_DIR):
        return []

    try:
        all_files = os.listdir(LOG_DIR)
        # Interesują nas pliki tekstowe .log
        log_files = [f for f in all_files if f.endswith(".log")]
        # Sortujemy od najnowszego (zakładając format daty w nazwie)
        log_files.sort(reverse=True)
        return log_files
    except Exception as e:
        print(f"Błąd listowania plików: {e}")
        return []

def read_backup_log_content(filename):
    """Wczytuje surową treść pliku logu."""
    # Zabezpieczenie przed wychodzeniem poza folder (path traversal)
    safe_filename = os.path.basename(filename)
    path = os.path.join(LOG_DIR, safe_filename)

    if not os.path.exists(path):
        return {"error": "Plik nie istnieje"}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            return {
                "filename": safe_filename,
                "content": content,
                "lines_count": len(content.splitlines())
            }
    except Exception as e:
        return {"error": f"Błąd odczytu: {str(e)}", "filename": safe_filename}