import os

def shutdown_raspberry():
    """Wyłącza Raspberry Pi natychmiast."""
    # -h oznacza halt (zatrzymanie), now oznacza natychmiast
    os.system('sudo shutdown -h now')

def reboot_raspberry():
    """Restartuje Raspberry Pi natychmiast."""
    # -r oznacza reboot
    os.system('sudo shutdown -r now')