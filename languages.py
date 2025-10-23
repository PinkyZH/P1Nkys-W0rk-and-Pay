# workpay/languages.py
from __future__ import annotations

LANG = {
    "de": {
        "app": {"title": "P1Nky$ W0rk & P@y", "version": "3.3"},
        "login": {
            "title": "Anmeldung", "username":"Benutzername", "password":"Passwort",
            "language":"Sprache", "sign_in":"Anmelden"
        },
        "main": { "menu": {
            "account":"Konto", "profile":"Profil", "admin":"Admin",
            "tools":"Werkzeuge", "hr":"Personal", "payroll":"Abrechnung",
            "account.logout":"Abmelden / Benutzer wechseln…",
            "account.language":"Sprache",
            "profile_edit": "Profil bearbeiten"
        }},
        "calendar": {
            "title":"Kalender",
            "view_day":"Tag","view_week":"Woche","view_month":"Monat","view_year":"Jahr",
            "new_entry":"Neu","edit_entry":"Bearbeiten","delete_entry":"Löschen","refresh":"Aktualisieren",
            "date":"Datum","start":"Beginn","end":"Ende","break":"Pause (Min)","hours":"Stunden","type":"Typ",
            "note":"Notiz","location":"Ort","totals":"Summen","entries":"Einträge",
            "confirm_delete":"Diesen Eintrag wirklich löschen?",
            "type_filter":"Typ-Filter","all":"Alle","search":"Suche Notiz/Ort",
            "export_pdf":"Export PDF","export_xlsx":"Export Excel"
        },
        "admin_users": {
            "title":"Benutzerverwaltung","search":"Suche",
            "username":"Benutzername","role":"Rolle","active":"Aktiv",
            "last_login":"Letzter Login","locale":"Sprache",
            "name":"Name","birthday":"Geburtstag","phone":"Telefon","email":"E-Mail",
            "new":"Neu","edit":"Bearbeiten","delete":"Löschen","refresh":"Aktualisieren",
            "confirm_delete":"Diesen Benutzer wirklich löschen?",
            "cannot_delete_last_admin":"Der letzte ADMIN kann nicht gelöscht werden."
        },
        "payroll": {
            "title":"Monatsabschluss – Abrechnung",
            "recalc":"Berechnen / Aktualisieren",
            "hours_total":"Stunden Total","entries":"Einträge",
            "gross":"Bruttolohn","net":"Nettolohn",
            "lock":"Abschließen","unlock":"Re-Open",
            "reason_prompt":"Begründung für Re-Open (optional)",
            "range_done":"Sie haben von {start} bis {end} erfolgreich abgeschlossen.",
            "range_open":"Sie haben von {start} bis {end} erfolgreich wieder geöffnet."
        },
        "profile": {
            "title":"Mein Profil","save":"Speichern","cancel":"Abbrechen",
            "gender":"Geschlecht","first_name":"Vorname","last_name":"Nachname","birthday":"Geburtstag",
            "civil_status":"Zivilstand","permit_status":"Aufenthaltsstatus","locale":"Sprache",
            "region_code":"Region/Kanton","address":"Adresse","postcode":"Postleitzahl","city":"Ort",
            "email":"E-Mail","phone":"Telefon","iban":"IBAN","avatar":"Avatar","choose_file":"Datei wählen","remove":"Entfernen",
            "bank_name":"Name der Bank","bank_address":"Adresse der Bank","bank_zip":"Postleitzahl der Bank","bank_city":"Ort der Bank",
            "bank_country":"Land der Bank","account_number":"Kontonummer","show_bank":"Bankdaten anzeigen",
            "employee_id":"Mitarbeiter-ID","employee_code":"Kürzel","employer":"Arbeitgeber","employment_start":"Eintrittsdatum",
            "ahv_number":"AHV-Nr.","hourly_wage":"Stundenlohn"
        },
        "abs": {
            "status":{"pending":"Ausstehend","approved":"Bewilligt","denied":"Abgelehnt"},
            "custom_label":"Custom-Label"
        },
        "tools":{"menu":"Werkzeuge","backup_restore":"Backup / Restore","audit_log":"Audit-Log"},
        "files":{"payroll":{"filename":"Abrechnung_{last}-{first}_erstellt-am-{created}_von_{start}_bis_{end}"}}
    },

    "en": {
        "app":{"title":"P1Nky$ W0rk & P@y","version":"3.3"},
        "login":{"title":"Sign in","username":"Username","password":"Password","language":"Language","sign_in":"Sign in"},
        "main":{"menu":{
            "account":"Account","profile":"Profile","admin":"Admin","tools":"Tools","hr":"HR","payroll":"Payroll",
            "account.logout":"Sign out / Switch user…","account.language":"Language","profile_edit": "Profil bearbeiten"
        }},
        "calendar":{"title":"Calendar","view_day":"Day","view_week":"Week","view_month":"Month","view_year":"Year",
            "new_entry":"New","edit_entry":"Edit","delete_entry":"Delete","refresh":"Refresh",
            "date":"Date","start":"Start","end":"End","break":"Break (min)","hours":"Hours","type":"Type",
            "note":"Note","location":"Location","totals":"Totals","entries":"Entries",
            "confirm_delete":"Really delete this entry?","type_filter":"Type filter","all":"All","search":"Search note/location",
            "export_pdf":"Export PDF","export_xlsx":"Export Excel"
        },
        "payroll":{"title":"Payroll","recalc":"Recalculate","hours_total":"Hours total","entries":"Entries",
            "gross":"Gross","net":"Net","lock":"Lock","unlock":"Re-Open","reason_prompt":"Reason (optional)",
            "range_done":"You have successfully closed from {start} to {end}.",
            "range_open":"You have successfully re-opened from {start} to {end}."
        },
        "admin_users":{"title":"User Management","search":"Search","username":"Username","role":"Role","active":"Active","last_login":"Last login","locale":"Language","name":"Name","first_name":"First name","last_name":"Last name","birthday":"Birthday","phone":"Phone","email":"Email","new":"New","edit":"Edit","delete":"Delete","refresh":"Refresh","confirm_delete":"Really delete this user?","cannot_delete_last_admin":"You cannot delete the last ADMIN."},
        "profile":{"title":"My Profile","save":"Save","cancel":"Cancel","gender":"Gender","first_name":"First name","last_name":"Last name","birthday":"Birthday","civil_status":"Civil status","permit_status":"Residence status","locale":"Language","region_code":"Region/Canton","address":"Address","postcode":"Postcode","city":"City","email":"Email","phone":"Phone","iban":"IBAN","avatar":"Avatar","choose_file":"Choose file","remove":"Remove","bank_name":"Bank name","bank_address":"Bank address","bank_zip":"Bank ZIP","bank_city":"Bank city","bank_country":"Bank country","account_number":"Account number","show_bank":"Show bank details","employee_id":"Employee ID","employee_code":"Short code","employer":"Employer","employment_start":"Employment start","ahv_number":"AHV No.","hourly_wage":"Hourly wage"},
        "abs":{"status":{"pending":"Pending","approved":"Approved","denied":"Rejected"},"custom_label":"Custom label"},
        "tools":{"menu":"Tools","backup_restore":"Backup / Restore","audit_log":"Audit log"},
        "files":{"payroll":{"filename":"Payroll_{last}-{first}_created-{created}_from_{start}_to_{end}"}}
    },

    "sr": {
        "app":{"title":"P1Nky$ W0rk & P@y","version":"3.3"},
        "login":{"title":"Prijava","username":"Korisničko ime","password":"Lozinka","language":"Jezik","sign_in":"Prijavi se"},
        "main":{"menu":{
            "account":"Nalog","profile":"Profil","admin":"Admin","tools":"Alati","hr":"Kadrovi","payroll":"Obračun",
            "account.logout":"Odjavi se / Promeni korisnika…","account.language":"Jezik","profile_edit": "Profil bearbeiten"
        }},
        "calendar":{"title":"Kalendar","view_day":"Dan","view_week":"Nedelja","view_month":"Mesec","view_year":"Godina",
            "new_entry":"Novi","edit_entry":"Uredi","delete_entry":"Obriši","refresh":"Osveži",
            "date":"Datum","start":"Početak","end":"Kraj","break":"Pauza (min)","hours":"Sati","type":"Tip",
            "note":"Beleška","location":"Lokacija","totals":"Zbir","entries":"Unosa",
            "confirm_delete":"Zaista obrisati ovaj unos?","type_filter":"Filter tipa","all":"Sve","search":"Pretraga beleške/lokacije",
            "export_pdf":"Izvoz PDF","export_xlsx":"Izvoz Excel"
        },
        "payroll":{"title":"Mesečni obračun","recalc":"Izračunaj","hours_total":"Ukupno sati","entries":"Unosa",
            "gross":"Bruto","net":"Neto","lock":"Zaključa","unlock":"Ponovo otvori",
            "reason_prompt":"Razlog (opciono)","range_done":"Uspešno zatvoreno od {start} do {end}.",
            "range_open":"Uspešno ponovo otvoreno od {start} do {end}."
        },
        "admin_users":{"title":"Upravljanje korisnicima","search":"Pretraga","username":"Korisničko ime","role":"Uloga","active":"Aktivan","last_login":"Poslednja prijava","locale":"Jezik","name":"Ime i prezime","first_name":"Ime","last_name":"Prezime","birthday":"Rođendan","phone":"Telefon","email":"Email","new":"Novi","edit":"Uredi","delete":"Obriši","refresh":"Osveži","confirm_delete":"Zaista obrisati ovog korisnika?","cannot_delete_last_admin":"Ne možete obrisati poslednjeg ADMIN-a."},
        "profile":{"title":"Moj profil","save":"Sačuvaj","cancel":"Otkaži","gender":"Pol","first_name":"Ime","last_name":"Prezime","birthday":"Rođendan","civil_status":"Bračni status","permit_status":"Status boravka","locale":"Jezik","region_code":"Region/Kanton","address":"Adresa","postcode":"Poštanski broj","city":"Mesto","email":"Email","phone":"Telefon","iban":"IBAN","avatar":"Avatar","choose_file":"Izaberi datoteku","remove":"Ukloni","bank_name":"Naziv banke","bank_address":"Adresa banke","bank_zip":"Poštanski broj banke","bank_city":"Grad banke","bank_country":"Država banke","account_number":"Broj računa","show_bank":"Prikaži bankovne podatke","employee_id":"ID zaposlenog","employee_code":"Skraćenica","employer":"Poslodavac","employment_start":"Datum početka","ahv_number":"AHV broj","hourly_wage":"Satnica"},
        "abs":{"status":{"pending":"Na čekanju","approved":"Odobren","denied":"Odbijen"},"custom_label":"Prilagođena oznaka"},
        "tools":{"menu":"Alati","backup_restore":"Backup / Restore","audit_log":"Dnevnik izmena"},
        "files":{"payroll":{"filename":"Obracun_{last}-{first}_kreirano-{created}_od_{start}_do_{end}"}}
    }
}

LANG["de"].update({
  "dialogs": {
    "common": {
      "ok": "OK",
      "cancel": "Abbrechen",
      "close": "Schließen",
      "save": "Speichern",
      "load": "Laden",
      "refresh": "Aktualisieren",
      "result": "Ergebnis:",
      "saved": "Gespeichert.",
      "gross_per_hour": "Brutto/Std",
      "net_per_hour": "Netto/Std",
      "gross_per_month": "Brutto/Monat",
      "net_per_month": "Netto/Monat"
    }
  },
  "analytics": {
    "title":"Analytics / Statistik",
    "from":"Von",
    "to":"Bis",
    "apply":"Übernehmen",
    "hours_per_day":"Stunden pro Tag",
    "gross_per_month":"Brutto (Total) pro Monat",
    "export_pdf":"Analytics PDF exportieren",
    "export_xlsx":"Analytics Excel exportieren",
    "export_png": "Analytics PNG exportieren",
    "show": "Analytics anzeigen"
  }
})

LANG["de"].setdefault("login", {})
LANG["de"]["login"]["register"] = "Registrieren…"
LANG["de"]["login"]["register_button"] = "Registrieren"

LANG["de"]["reg"] = {
    "title": "Registrierung",
    "username": "Benutzername",
    "password": "Passwort",
    "language": "Sprache",
    "create": "Konto anlegen",
    "cancel": "Abbrechen",
    "ok": "Registrierung erfolgreich.",
    "exists": "Benutzername existiert bereits.",
    "weak": "Bitte Passwort eingeben."
}
LANG["de"].setdefault("reg", {})
LANG["de"]["reg"].update({
  "title":"Registrierung",
  "username":"Benutzername", "password":"Passwort",
  "language":"Sprache", "create":"Konto anlegen", "cancel":"Abbrechen",
  "ok":"Registrierung erfolgreich.", "exists":"Benutzername existiert bereits.",
  "weak":"Bitte Passwort eingeben.", "missing":"Pflichtfelder fehlen: ",
  "last_name":"Nachname", "first_name":"Vorname", "birthday":"Geburtstag",
  "gender":"Geschlecht", "email":"E-Mail", "phone":"Telefon"
})
# DE
LANG["de"]["wprev"] = {
  "title": "Lohnvorschau – Szenarien & Prognose",
  "header": "Vergleich links: IST  •  rechts: WAS-WÄRE-WENN",
  "ist": "IST",
  "whatif": "Was-wäre-wenn",
  "results": "Ergebnis – IST vs. Was-wäre-wenn",
  "col_ist": "IST",
  "col_if": "Was-wäre-wenn",
  "gph": "Brutto/Std",
  "nph": "Netto/Std",
  "gpm": "Brutto/Monat (174h)",
  "npm": "Netto/Monat (174h)",
  "delta_m": "Δ / Monat",
  "forecast": "Prognose",
  "this_week": "Diese Woche",
  "next_week": "Nächste Woche",
  "this_month": "Dieser Monat",
  "next_month": "Nächster Monat",
  "extra_hours": "Zusatzstunden (±) / Monat",
  "extra_hours_tip": "Wird zu 174h addiert/subtrahiert für den Was-wäre-wenn-Monatswert."
}
LANG["de"].setdefault("wprev", {})
LANG["de"]["wprev"].update({
  "quick.title":"Schnell-Vergleich (nur Lohn & Stunden)",
  "hours":"Stunden"
})

LANG["de"].setdefault("rules", {})
LANG["de"]["rules"].update({
  "overtime.title":"Überstunden (anteilig)",
  "duration":"Dauer (h)"
})
# de
LANG["de"].setdefault("rules", {})
LANG["de"]["rules"].update({
  "title": "Zuschlagsregeln",
  "enabled": "Zuschläge aktivieren",
  "active": "aktiv",
  "overtime.title": "Überstunden (anteilig)",
  "weekend.title": "Wochenende (voll)",
  "holiday.title": "Feiertag (voll)",
  "from": "von",
  "to": "bis",
  "duration": "Dauer (h)"
})
# de
LANG["de"].setdefault("calendar", {})
LANG["de"]["calendar"].update({
    "day_pay_gross": "Tagessold (Brutto)",
    "day_pay_net":   "Tagessold (Netto)"
})



# en
LANG["en"].setdefault("calendar", {})
LANG["en"]["calendar"].update({
    "day_pay_gross": "Day pay (Gross)",
    "day_pay_net":   "Day pay (Net)"
})

LANG["en"].setdefault("dialogs",{}); LANG["en"]["dialogs"]["common"] = {
  "ok":"OK","cancel":"Cancel","close":"Close","save":"Save","load":"Load","refresh":"Refresh",
  "result":"Result:","saved":"Saved.","gross_per_hour":"Gross/hr","net_per_hour":"Net/hr",
  "gross_per_month":"Gross/month","net_per_month":"Net/month"
}
LANG["en"]["analytics"] = {
  "title":"Analytics / Statistics","from":"From","to":"To","apply":"Apply",
  "hours_per_day":"Hours per Day","gross_per_month":"Gross (Total) per Month",
  "export_pdf":"Export Analytics PDF","export_xlsx":"Export Analytics Excel", "export_png": "Export Analytics PNG", "show": "Show analytics"
}
LANG["en"].setdefault("login", {})
LANG["en"]["login"]["register"] = "Sign up…"
LANG["en"]["login"]["register_button"] = "Sign up"

LANG["en"]["reg"] = {
    "title": "Sign up",
    "username": "Username",
    "password": "Password",
    "language": "Language",
    "create": "Create account",
    "cancel": "Cancel",
    "ok": "Registration successful.",
    "exists": "Username already exists.",
    "weak": "Please enter a password."
}
# EN
LANG["en"]["wprev"] = {
  "title":"Wage Preview – Scenarios & Forecast",
  "header":"Left: CURRENT  •  Right: WHAT-IF",
  "ist":"Current","whatif":"What-if","results":"Result – Current vs What-if",
  "col_ist":"Current","col_if":"What-if","gph":"Gross/hr","nph":"Net/hr",
  "gpm":"Gross/month (174h)","npm":"Net/month (174h)","delta_m":"Δ / month",
  "forecast":"Forecast","this_week":"This week","next_week":"Next week","this_month":"This month","next_month":"Next month",
  "extra_hours":"Extra hours (±) / month","extra_hours_tip":"Added to 174h for what-if monthly value."
}



LANG["sr"].setdefault("dialogs",{}); LANG["sr"]["dialogs"]["common"] = {
  "ok":"OK","cancel":"Otkaži","close":"Zatvori","save":"Sačuvaj","load":"Učitaj","refresh":"Osveži",
  "result":"Rezultat:","saved":"Sačuvano.","gross_per_hour":"Bruto/sat","net_per_hour":"Neto/sat",
  "gross_per_month":"Bruto/mesec","net_per_month":"Neto/mesec"
}
LANG["sr"]["analytics"] = {
  "title":"Analitika / Statistika","from":"Od","to":"Do","apply":"Primeni",
  "hours_per_day":"Sati po danu","gross_per_month":"Bruto (ukupno) po mesecu",
  "export_pdf":"Izvoz Analytics PDF","export_xlsx":"Izvoz Analytics Excel", "export_png": "Izvoz Analytics PNG", "show": "Prikaži analitiku"
}
LANG["sr"].setdefault("login", {})
LANG["sr"]["login"]["register"] = "Registruj se…"
LANG["sr"]["login"]["register_button"] = "Registruj se"

LANG["sr"]["reg"] = {
    "title": "Registracija",
    "username": "Korisničko ime",
    "password": "Lozinka",
    "language": "Jezik",
    "create": "Kreiraj nalog",
    "cancel": "Otkaži",
    "ok": "Uspešna registracija.",
    "exists": "Korisničko ime već postoji.",
    "weak": "Unesite lozinku."
}
# SR
LANG["sr"]["wprev"] = {
  "title":"Pregled plate – Scenariji i prognoza",
  "header":"Levo: TRENUTNO  •  Desno: ŠTA-AKO",
  "ist":"Trenutno","whatif":"Šta-ako","results":"Rezultat – Trenutno vs Šta-ako",
  "col_ist":"Trenutno","col_if":"Šta-ako","gph":"Bruto/sat","nph":"Neto/sat",
  "gpm":"Bruto/mesec (174h)","npm":"Neto/mesec (174h)","delta_m":"Δ / mesec",
  "forecast":"Prognoza","this_week":"Ove nedelje","next_week":"Sledeće nedelje","this_month":"Ovaj mesec","next_month":"Sledeći mesec",
  "extra_hours":"Dodatni sati (±) / mesec","extra_hours_tip":"Dodaje se na 174h za šta-ako mesečnu vrednost."
}
# sr
LANG["sr"].setdefault("calendar", {})
LANG["sr"]["calendar"].update({
    "day_pay_gross": "Dnevna zarada (bruto)",
    "day_pay_net":   "Dnevna zarada (neto)"
})


# de
LANG["de"].setdefault("rules", {})
LANG["de"]["rules"].update({
  "next_day": "nächster Tag",
  "next_day_tip": "Wenn aktiv: 'bis' liegt am Folgetag (über Mitternacht)."
})
# en
LANG["en"].setdefault("rules", {})
LANG["en"]["rules"].update({
  "next_day": "next day",
  "next_day_tip": "If enabled: 'to' is on the following day (overnight)."
})
# sr
LANG["sr"].setdefault("rules", {})
LANG["sr"]["rules"].update({
  "next_day": "sledeći dan",
  "next_day_tip": "Ako je uključeno: 'do' je sledećeg dana (preko ponoći)."
})


def tr(key: str, lang: str = "de") -> str:
    d = LANG.get(lang, LANG["de"])
    cur: object = d
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return key
    return cur if isinstance(cur, str) else key
