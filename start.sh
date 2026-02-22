#!/bin/bash

# Przejście do katalogu projektu
cd /home/michal_raspberry/services/raspberry-pi-nas-core

# Opcjonalne logowanie startu do pliku (dla debugowania)
echo "Uruchamiam NAS Core: $(date)" >> startup.log

# Uruchomienie aplikacji z venv
# Używamy exec, aby Python przejął proces powłoki
exec /home/michal_raspberry/services/raspberry-pi-nas-core/.venv/bin/python main.py
