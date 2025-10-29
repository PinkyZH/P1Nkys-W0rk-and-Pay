# zentrale App-Konstanten (neu)
APP_NAME = "P1Nky$ W0rk & P@y"
APP_VERSION = "4.0"

DEFAULT_WAGE_PRESETS = {
    "hourly_brutto": 21.65,
    "vac_pct": 10.64,
    "holiday_pct": 3.59,
    "thirteenth_pct": 8.33,
    "expenses_per_hour": 2.00,
    "ahv_pct": 6.40,
    "nbu_pct": 2.25,
    "ktg_pct": 1.50,
    "lgav_fixed_monthly": 20.00,
    "weekly_hours": 41.0,
    # BVG prozentual lassen wir 0.0 als Default (abhängig von Schwellen)
}
DEFAULT_ADMIN = {"username": "admin", "password": "admin", "locale": "de"}

# -------- Zuschläge (Option C) --------
# Aktivieren/Deaktivieren
ENABLE_SURCHARGES = True

# Prozentaufschläge (auf Lohn/Std)
SURCHARGE_RULES = {
    "NIGHT": {  # 22:00 - 06:00 (anteilig)
        "enabled": True,
        "percent": 25.0,
        "from_time": "22:00",
        "to_time": "06:00",
    },
    "WEEKEND": {  # Samstag/Sonntag (voll)
        "enabled": True,
        "percent": 50.0,
    },
    "HOLIDAY": {  # Feiertag (voll)
        "enabled": True,
        "percent": 100.0,
    },
}

# (Optional) Feiertage für einfache Erkennung (YYYY-MM-DD), bis Option-B Holiday-Tabelle aktiv ist.
# Beispiel:
HOLIDAYS_STATIC = set([
    # "2025-01-01",
])

# ===== Branding & Format (v2.5 – F) =====
COMPANY_NAME = "P1Nky$ W0rk & P@y"  # nur für interne PDFs, kann leer bleiben
COMPANY_LOGO_PATH = "data/branding/logo.png"  # optional, wenn vorhanden wird im PDF-Kopf angezeigt
CURRENCY = "CHF"
ROUND_TO_0_05 = True  # Betrag auf 0.05 runden (CH-typisch)
THOUSANDS_SEP = "’"  # Tausendertrennzeichen (z. B. 12’345.55)
DECIMAL_SEP = "."  # Dezimalpunkt

ENABLE_ABSENCE = False
ENABLE_NOTIFICATIONS = False
