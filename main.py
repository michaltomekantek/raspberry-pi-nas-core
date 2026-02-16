import sys
import os

def main():
    print("Hello, Raspberry Pi!")
    print("-" * 20)

    # Wyświetlenie wersji Pythona
    print(f"Python version: {sys.version.split()[0]}")

    # Wyświetlenie nazwy użytkownika i ścieżki
    user = os.getenv('USER') or os.getenv('USERNAME')
    print(f"Current user: {user}")

    print("-" * 20)
    print("Gotowy do pracy nad NAS-em!")

if __name__ == "__main__":
    main()