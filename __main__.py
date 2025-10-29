import sys

def main():
    # Import erst zur Laufzeit, damit PySide6 sauber initialisiert wird
    from p1nkyw0rkpy.app import main as app_main
    return app_main()

if __name__ == "__main__":
    sys.exit(main())