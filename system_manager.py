import os
import time

def shutdown_raspberry():
    """Wyłącza Raspberry Pi natychmiast."""
    # -h oznacza halt (zatrzymanie), now oznacza natychmiast
    os.system('sudo shutdown -h now')

def reboot_raspberry():
    """Restartuje Raspberry Pi natychmiast."""
    # -r oznacza reboot
    os.system('sudo shutdown -r now')

# Zmienne do prostej pamięci podręcznej (cache)
_cache_usage = None
_cache_time = 0
CACHE_DURATION = 3600  # Odświeżaj wagę plików raz na godzinę

def get_real_files_usage(path='/mnt/cold_storage'):
    global _cache_usage, _cache_time

    current_time = time.time()
    if _cache_usage and (current_time - _cache_time < CACHE_DURATION):
        return _cache_usage

    total_size = 0
    try:
        # Przechodzimy tylko przez pierwszy poziom folderów dla szybkości
        # lub rekurencyjnie, jeśli potrzebujesz totalnej sumy
        for entry in os.scandir(path):
            if entry.is_file():
                total_size += entry.stat().size
            elif entry.is_dir():
                total_size += get_dir_size(entry.path)

        real_gb = round(total_size / (1024**3), 2)
        _cache_usage = real_gb
        _cache_time = current_time
        return real_gb
    except Exception:
        return "N/A"

def get_dir_size(path):
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
    except PermissionError:
        pass
    return total