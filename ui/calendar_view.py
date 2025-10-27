from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, Tuple, Dict, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QDateEdit, QTableWidget,
    QTableWidgetItem, QCalendarWidget, QSplitter, QAbstractItemView, QMessageBox, QLabel, QMenu,
    QLineEdit, QFileDialog, QAbstractButton, QAbstractItemView
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QShortcut, QKeySequence

from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from core.utils.formatting import fmt_money
from core.utils.i18n import t as _t

from languages import tr
from core.models import UserProfile, User
from core.services.work_service import list_entries_by_range, get_entry, delete_entry, create_entry
from config import DEFAULT_WAGE_PRESETS as _W
from .entry_dialog import EntryDialog
from PySide6.QtWidgets import QHeaderView

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    HAS_MPL = True
except Exception:
    HAS_MPL = False
import csv # für CSV-Export
from core.services.settings_service import get_user_pref, set_user_pref  # ← User-Prefs
import json, os
from pathlib import Path as _Path

# ---------- Typ-Farben ----------
TYPE_COLORS = {
    "WORK": QColor(66,133,244),
    "VACATION": QColor(52,168,83),
    "SICK": QColor(234,67,53),
    "ACCIDENT": QColor(234,67,53),
    "HOLIDAY": QColor(251,188,5),
    "OFF": QColor(128,128,128),
    "OTHER": QColor(156,39,176),
}
def _safe_name(s: str) -> str:
    """Ersetzt Leerzeichen/Sonderzeichen durch _ für Dateinamen."""
    import re
    s = (s or "").strip()
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE)
    return re.sub(r"_+", "_", s).strip("_")

def _calendar_export_filename(last: str, first: str, employer: str, ext: str) -> str:
    """Cal-Export_Nachname_Vorname_Arbeitgeber_Datum vom Export YYYY-MM-DD.ext"""
    from datetime import date as _date
    today = _date.today().strftime("%Y-%m-%d")
    return f"Cal-Export_{_safe_name(last)}_{_safe_name(first)}_{_safe_name(employer)}_Datum vom Export {today}.{ext}"

def _analytics_png_filenames(last: str, first: str, employer: str) -> tuple[str, str]:
    """liefert (hours_png, gross_png)"""
    from datetime import date as _date
    today = _date.today().strftime("%Y-%m-%d")
    base = f"Analytics_{_safe_name(last)}_{_safe_name(first)}_{_safe_name(employer)}_{today}"
    return f"{base}_hours.png", f"{base}_gross.png"

def _analytics_base_name(last: str, first: str, employer: str) -> str:
    from datetime import date as _date
    today = _date.today().strftime("%Y-%m-%d")
    return f"Analytics_{_safe_name(last)}_{_safe_name(first)}_{_safe_name(employer)}_{today}"

# === Helper: Dateiname für Exporte =========================================
def _sanitize_name(self, s: str) -> str:
    """Erlaubt nur einfache Zeichen, ersetzt Leerzeichen durch Unterstrich."""
    import re
    s = (s or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_.\-äöüÄÖÜß]", "", s)
    return s or "NA"

def _current_month_year(self):
    """
    Liefert (year, month) des aktuell im Kalender angezeigten Monats.
    Fällt auf 'today' zurück, wenn keine Info vorhanden.
    """
    from datetime import date
    # versuche häufige Feldnamen, die es je nach Version geben kann
    for attr in ("view_year", "view_month", "cur_year", "cur_month", "g_year", "g_month"):
        pass
    try:
        y = int(getattr(self, "view_year", getattr(self, "cur_year", getattr(self, "g_year", 0))))
        m = int(getattr(self, "view_month", getattr(self, "cur_month", getattr(self, "g_month", 0))))
        if y and m:
            return y, m
    except Exception:
        pass
    today = date.today()
    return today.year, today.month

def _export_basename(self) -> str:
    """Baut den Basenamen inkl. Monat + Erstellungsdatum."""
    from datetime import date
    y, m = self._current_month_year()
    created = date.today().isoformat()

    # User-Daten holen
    last_name = "NA"
    first_name = "NA"
    employer = "NA"
    try:
        from sqlalchemy import select
        from core.models import User, UserProfile
        with self.session_factory() as s:
            u = s.execute(select(User).where(User.id == self.view_user_id)).scalar_one_or_none()
            p = s.execute(select(UserProfile).where(UserProfile.user_id == self.view_user_id)).scalar_one_or_none()
            if p:
                last_name = p.last_name or last_name
                first_name = p.first_name or first_name
                employer = p.employer or employer
            if u and (last_name == "NA" and first_name == "NA"):
                # Fallback Name aus Username
                last_name = self._sanitize_name(u.username)
    except Exception:
        pass

    ln = self._sanitize_name(last_name)
    fn = self._sanitize_name(first_name)
    em = self._sanitize_name(employer)

    # „Monat_10-2025“ (bewusst schlicht, robust für FS)
    month_token = f"Monat_{m:02d}-{y}"

    return f"Cal-Export_{ln}_{fn}_{em}_{month_token}_Erstellt_am_{created}"

# ---- Sortierbare Items ----
class DateItem(QTableWidgetItem):
    def __init__(self, d: date):
        super().__init__(d.isoformat() if d else "")
        self._d = d
    def __lt__(self, other):
        try:
            return self._d < other._d
        except Exception:
            return super().__lt__(other)

class NumericItem(QTableWidgetItem):
    def __init__(self, value: float, text: str | None = None):
        super().__init__(text if text is not None else f"{value}")
        self._v = float(value)
    def __lt__(self, other):
        try:
            return self._v < other._v
        except Exception:
            return super().__lt__(other)

def _is_worked(code: str) -> bool:
    return (code or "").upper() == "WORK"

# ---- Fallback Typ-Labels, falls Key fehlt ----
_TYPES_FALLBACK = {
    "de": {"work":"Arbeit","vacation":"Urlaub","sick":"Krank","holiday":"Feiertag","off":"Frei","other":"Sonstiges","appointment":"Arzttermin","hospital":"Spital"},
    "en": {"work":"Work","vacation":"Vacation","sick":"Sick","holiday":"Holiday","off":"Off","other":"Other","appointment":"Appointment","hospital":"Hospital"},
    "sr": {"work":"Rad","vacation":"Odmor","sick":"Bolovanje","holiday":"Praznik","off":"Slobodno","other":"Ostalo","appointment":"Pregled","hospital":"Bolnica"},
}
def _t(lang: str, key: str) -> str:
    val = tr(f"calendar.{key}", lang)
    return val if val != f"calendar.{key}" else {
        "title":"Kalender","view_day":"Tag","view_week":"Woche","view_month":"Monat","view_year":"Jahr",
        "new_entry":"Neu","edit_entry":"Bearbeiten","delete_entry":"Löschen","refresh":"Aktualisieren",
        "date":"Datum","start":"Beginn","end":"Ende","break":"Pause (Min)","hours":"Stunden","type":"Typ",
        "note":"Notiz","location":"Ort","totals":"Summen","entries":"Einträge","confirm_delete":"Diesen Eintrag wirklich löschen?",
        "type_filter":"Typ-Filter","all":"Alle","search":"Suche Notiz/Ort","user":"Nutzer","export_pdf":"Export PDF","export_xlsx":"Export Excel"
    }.get(key, key)

def _type_label(lang: str, code: str) -> str:
    if not code: return ""
    key = (code or "").lower()
    txt = tr(f"calendar.entry_types.{key}", lang)
    if txt == f"calendar.entry_types.{key}":
        return _TYPES_FALLBACK.get(lang, _TYPES_FALLBACK["de"]).get(key, code)
    return txt

def qdate_to_date(qd: QDate):
    return None if (not qd or not qd.isValid()) else qd.toPython()

# --------- Calendar (nur Rahmen, kein grüner Fill) ---------
class MarkingCalendar(QCalendarWidget):
    """
    Zeichnet:
      - Heute: grauer Rahmen
      - Auswahl: roter Rahmen
      - Typmarker: mehrere kleine Punkte rechts neben der Tageszahl (oben rechts),
                   falls mehrere Typen am Tag vorkommen.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._marks: set[QDate] = set()
        self._color_map_multi: Dict[QDate, List[QColor]] = {}  # mehrere Farben pro Tag
        self._today = QDate.currentDate()

    def set_marked(self, dates_set, color_map_multi: Dict[QDate, List[QColor]] | None = None):
        # dates_set: set(QDate) – alle Tage, die markiert werden sollen
        # color_map_multi: QDate -> [QColor, QColor, ...]  (Reihenfolge = Malreihenfolge)
        self._marks = set(dates_set or set())
        self._color_map_multi = color_map_multi or {}
        self.update()

    def paintCell(self, painter: QPainter, rect, date: QDate):
        super().paintCell(painter, rect, date)

        # Heute-Rahmen
        if date == self._today:
            pen = QPen(QColor(120, 120, 120)); pen.setWidth(1)
            painter.setPen(pen); painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))

        # Auswahl-Rahmen
        if date == self.selectedDate():
            pen = QPen(QColor(220, 0, 0)); pen.setWidth(2)
            painter.setPen(pen); painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))

        # Typ-Punkte (rechts oben, mehrere möglich)
        if date in self._marks:
            colors = self._color_map_multi.get(date, [])
            if not colors:
                return
            # Layout: rechts oben; mehrere Punkte nebeneinander nach links
            margin = 3
            diameter = 5
            gap = 2
            x_right = rect.right() - margin
            y_top = rect.top() + margin + 2  # leicht unterhalb der Zahl

            # von rechts nach links malen
            for i, col in enumerate(colors[:6]):  # Sicherheitslimit
                x = x_right - i * (diameter + gap) - diameter
                painter.setBrush(col)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(x, y_top, diameter, diameter)


class CalendarMainWidget(QWidget):
    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str = "de", is_admin: bool = False, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_id = user_id
        self.view_user_id = user_id
        self.lang = lang
        self.is_admin = is_admin
        self._build()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Nach jeder Größenänderung einmal breit ziehen
        try:
            self._auto_widen_note_location()
        except Exception:
            pass
    def _auto_widen_note_location(self):
        """Verteilt die Restbreite im Verhältnis 5:3 auf Notiz (col 6) und Ort (col 7)."""
        # Indizes laut deiner Tabelle:
        COL_NOTE = 6
        COL_LOC = 7
        COL_FIRST = 0
        COL_LAST = self.table.columnCount() - 1

        # Breiten aller fixen Spalten aufsummieren (alles außer Notiz/Ort)
        fixed_cols = [i for i in range(self.table.columnCount()) if i not in (COL_NOTE, COL_LOC)]
        fixed_total = sum(self.table.columnWidth(i) for i in fixed_cols)

        # Verfügbare Innenbreite der Viewport-Fläche
        viewport_w = self.table.viewport().width()
        # Falls Vertikalscrollbar sichtbar, etwas abziehen
        try:
            if self.table.verticalScrollBar().isVisible():
                viewport_w -= self.table.verticalScrollBar().width()
        except Exception:
            pass

        remaining = max(0, viewport_w - fixed_total)
        if remaining <= 0:
            return

        # 5 : 3-Verteilung
        note_w = int(remaining * 5 / 8)
        loc_w = remaining - note_w

        # Setzen
        self.table.setColumnWidth(COL_NOTE, note_w)
        self.table.setColumnWidth(COL_LOC, loc_w)

    def _calendar_export_filename(self, ext: str) -> str:
        """Cal-Export_Nachname_Vorname_Arbeitgeber_YYYY-MM-DD.ext"""
        from datetime import date as _date
        with self.session_factory() as s:
            u = s.get(User, self.view_user_id)
            p = s.query(UserProfile).filter(UserProfile.user_id == self.view_user_id).one_or_none()
        last = _safe_name(p.last_name if p else "")
        first = _safe_name(p.first_name if p else (u.username if u else ""))
        employer = _safe_name(p.employer if p and p.employer else "—")
        today = _date.today().strftime("%Y-%m-%d")
        return f"Cal-Export_{last}_{first}_{employer}_{today}.{ext}"

    def _export_analytics_pdf(self):
        if not HAS_MPL:
            QMessageBox.information(self, "PDF", "Charts sind deaktiviert (matplotlib nicht installiert).")
            return

        # Profil holen und Dateinamen vorbereiten
        with self.session_factory() as s:
            u = s.get(User, self.view_user_id)
            p = s.query(UserProfile).filter(UserProfile.user_id == self.view_user_id).one_or_none()
        last = (p.last_name or "") if p else ""
        first = (p.first_name or (u.username if u else ""))
        employer = (p.employer or "—") if p else "—"
        base = _analytics_base_name(last, first, employer)
        path, _ = QFileDialog.getSaveFileName(
            self, "Analytics PDF speichern", f"{base}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet
            from tempfile import NamedTemporaryFile
        except ImportError:
            QMessageBox.warning(self, "PDF", "reportlab ist nicht installiert.\nBitte: pip install reportlab")
            return

        # Charts temporär als PNG sichern
        tmp_hours = NamedTemporaryFile(suffix=".png", delete=False)
        tmp_gross = NamedTemporaryFile(suffix=".png", delete=False)
        self.fig_hours.savefig(tmp_hours.name, dpi=150, bbox_inches="tight")
        self.fig_gross.savefig(tmp_gross.name, dpi=150, bbox_inches="tight")

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(path, pagesize=A4, title="Analytics")
        elems = [
            Paragraph(tr("analytics.title", self.lang)
                      if tr("analytics.title", self.lang) != "analytics.title"
                      else "Analytics / Statistik", styles["Title"]),
            Spacer(1, 12),
            Image(tmp_hours.name, width=480, height=180),
            Spacer(1, 12),
            Image(tmp_gross.name, width=480, height=180),
        ]
        doc.build(elems)

        tmp_hours.close();
        tmp_gross.close()
        os.unlink(tmp_hours.name);
        os.unlink(tmp_gross.name)
        QMessageBox.information(self, "PDF", f"Exportiert: {path}")

    def _export_analytics_xlsx(self):
        if not HAS_MPL:
            QMessageBox.information(self, "Excel", "Charts sind deaktiviert (matplotlib nicht installiert).")
            return

        # Profil holen und Dateinamen vorbereiten
        with self.session_factory() as s:
            u = s.get(User, self.view_user_id)
            p = s.query(UserProfile).filter(UserProfile.user_id == self.view_user_id).one_or_none()
        last = (p.last_name or "") if p else ""
        first = (p.first_name or (u.username if u else ""))
        employer = (p.employer or "—") if p else "—"
        base = _analytics_base_name(last, first, employer)
        path, _ = QFileDialog.getSaveFileName(
            self, "Analytics Excel speichern", f"{base}.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            import openpyxl
            from openpyxl.drawing.image import Image as XLImage
            from tempfile import NamedTemporaryFile
        except ImportError:
            QMessageBox.warning(self, "Excel", "openpyxl ist nicht installiert.\nBitte: pip install openpyxl")
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Analytics"

        # Charts als temporäre PNGs exportieren
        tmp_hours = NamedTemporaryFile(suffix=".png", delete=False)
        tmp_gross = NamedTemporaryFile(suffix=".png", delete=False)
        self.fig_hours.savefig(tmp_hours.name, dpi=150, bbox_inches="tight")
        self.fig_gross.savefig(tmp_gross.name, dpi=150, bbox_inches="tight")

        ws["A1"] = tr("analytics.hours_per_day", self.lang) or "Stunden pro Tag"
        img1 = XLImage(tmp_hours.name);
        ws.add_image(img1, "A2")
        ws["A20"] = tr("analytics.gross_per_month", self.lang) or "Brutto (Total) pro Monat"
        img2 = XLImage(tmp_gross.name);
        ws.add_image(img2, "A21")

        wb.save(path)
        tmp_hours.close();
        tmp_gross.close()
        os.unlink(tmp_hours.name);
        os.unlink(tmp_gross.name)
        QMessageBox.information(self, "Excel", f"Exportiert: {path}")
    def _export_analytics_png(self):
        """Speichert die beiden Analytics-Charts als PNGs."""
        if not HAS_MPL:
            QMessageBox.information(self, "PNG", "Charts sind deaktiviert (matplotlib nicht installiert).")
            return

        # Nutzer/Profil ermitteln für Dateinamensbestandteile
        with self.session_factory() as s:
            u = s.get(User, self.view_user_id)
            p = s.query(UserProfile).filter(UserProfile.user_id == self.view_user_id).one_or_none()
        last = (p.last_name or "") if p else ""
        first = (p.first_name or (u.username if u else ""))
        employer = (p.employer or "—") if p else "—"

        # Standardvorschläge (2 Dateien)
        fname_hours, fname_gross = _analytics_png_filenames(last, first, employer)

        # Datei für "Hours per Day"
        path_hours, _ = QFileDialog.getSaveFileName(
            self, "PNG speichern (Stunden/Tag)", fname_hours, "PNG (*.png)"
        )
        if path_hours:
            try:
                self.fig_hours.savefig(path_hours, dpi=150, bbox_inches="tight")
            except Exception as ex:
                QMessageBox.critical(self, "PNG", f"Fehler beim Speichern (Stunden/Tag): {ex}")

        # Datei für "Gross per Month"
        path_gross, _ = QFileDialog.getSaveFileName(
            self, "PNG speichern (Brutto/Monat)", fname_gross, "PNG (*.png)"
        )
        if path_gross:
            try:
                self.fig_gross.savefig(path_gross, dpi=150, bbox_inches="tight")
            except Exception as ex:
                QMessageBox.critical(self, "PNG", f"Fehler beim Speichern (Brutto/Monat): {ex}")

        if path_hours or path_gross:
            QMessageBox.information(self, "PNG", "PNG Export abgeschlossen.")

    def _build(self):
        self._marks_cache = {}
        layout = QVBoxLayout(self)

        # Stylesheet: keine grüne Selektion
        self.setStyleSheet("""
        QCalendarWidget QWidget#qt_calendar_calendarview {
            selection-background-color: transparent;
            selection-color: black;
        }
        """)

        # Topbar
        top = QHBoxLayout()
        if self.is_admin:
            self.user_combo = QComboBox()
            self._load_users_into_combo()
            top.addWidget(QLabel(_t(self.lang,"user"))); top.addWidget(self.user_combo)
            self.user_combo.currentIndexChanged.connect(lambda *_: self._on_user_changed())
        else:
            self.user_combo = None

        self.combo_view = QComboBox(); self.combo_view.addItems([_t(self.lang,"view_day"), _t(self.lang,"view_week"), _t(self.lang,"view_month"), _t(self.lang,"view_year")])
        self.date_picker = QDateEdit(); self.date_picker.setCalendarPopup(True); self.date_picker.setDate(QDate.currentDate())

        self.combo_type_filter = QComboBox()
        self.combo_type_filter.addItem(_t(self.lang,"all"), "ALL")
        for code in ["WORK","VACATION","SICK","HOLIDAY","OFF","OTHER"]:
            self.combo_type_filter.addItem(_type_label(self.lang, code), code)
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText(_t(self.lang,"search"))

        btn_prev = QPushButton("◀"); btn_next = QPushButton("▶")
        btn_refresh = QPushButton(_t(self.lang,"refresh"))
        btn_new = QPushButton(_t(self.lang,"new_entry"))
        btn_edit = QPushButton(_t(self.lang,"edit_entry"))
        btn_delete = QPushButton(_t(self.lang,"delete_entry"))
        btn_import_csv = QPushButton("CSV import")
        btn_export_csv = QPushButton("CSV export")  # ← NEU
        btn_pdf = QPushButton(_t(self.lang,"export_pdf"))
        btn_xlsx = QPushButton(_t(self.lang,"export_xlsx"))

        # Analytics Sichtbarkeit (persistiert)
        from PySide6.QtWidgets import QCheckBox
        self.chk_anx = QCheckBox(tr("analytics.show", self.lang) if tr("analytics.show",
                                                                       self.lang) != "analytics.show" else "Analytics anzeigen")
        self.chk_anx.setChecked(bool(get_user_pref(self.view_user_id, "analytics_visible", True)))
        self.chk_anx.toggled.connect(lambda v: self._toggle_analytics(bool(v)))

        for w in [self.combo_view, self.date_picker, self.combo_type_filter, self.search_edit,
                  btn_prev, btn_next, btn_refresh, btn_new, btn_edit, btn_delete,
                  btn_import_csv, btn_export_csv,  # ← Export CSV hier
                  btn_pdf, btn_xlsx, self.chk_anx]:  # ← Analytics anzeigen
            top.addWidget(w)
        layout.addLayout(top)

        # Splitter: links Kalender, rechts Tabelle
        split = QSplitter(self)
        self.calendar = MarkingCalendar();
        self.calendar.setGridVisible(True)
        try:
            self.calendar.currentPageChanged.connect(lambda *_: self._refresh_month_marks())
        except Exception:
            pass

        self.table = QTableWidget(0, 10)  # +2 Spalten: Brutto & Netto
        headers = [
            _t(self.lang, "date"),
            _t(self.lang, "start"),
            _t(self.lang, "end"),
            _t(self.lang, "break"),
            _t(self.lang, "hours"),
            _t(self.lang, "type"),
            _t(self.lang, "note"),
            _t(self.lang, "location"),
            (tr("calendar.day_pay_gross", self.lang) if tr("calendar.day_pay_gross",
                                                           self.lang) != "calendar.day_pay_gross" else "Tagessold (Brutto)"),
            (tr("calendar.day_pay_net", self.lang) if tr("calendar.day_pay_net",
                                                         self.lang) != "calendar.day_pay_net" else "Tagessold (Netto)"),
        ]
        self.table.setHorizontalHeaderLabels(headers)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)  # wir steuern selbst
        hdr.setSectionResizeMode(QHeaderView.Interactive)  # feste Breiten übernehmen

        self.table.setSortingEnabled(True)

        split.addWidget(self.calendar)
        split.addWidget(self.table)

        # Reihenfolge im Layout: Splitter (groß) -> Totals (zentriert) -> Analytics (groß)
        layout.addWidget(split, stretch=5)

        # Summen ZENTRIERT direkt unter dem Splitter
        self.lbl_totals = QLabel()
        self.lbl_totals.setAlignment(Qt.AlignHCenter)
        self.lbl_totals.setTextFormat(Qt.RichText)
        layout.addWidget(self.lbl_totals)

        # --- Analytics / Statistik (nur Diagramme, eigener Zeitraum) ---
        from PySide6.QtWidgets import QGroupBox
        self.analytics_box = QGroupBox(tr("analytics.title", self.lang) if tr("analytics.title",
                                                                              self.lang) != "analytics.title" else "Analytics / Statistik")
        abox = QVBoxLayout(self.analytics_box)

        row_range = QHBoxLayout()
        self.analytics_from = QDateEdit();
        self.analytics_from.setCalendarPopup(True)
        self.analytics_to = QDateEdit();
        self.analytics_to.setCalendarPopup(True)
        self.analytics_to.setDate(QDate.currentDate())
        self.analytics_from.setDate(QDate.currentDate().addDays(-30))
        btn_apply_range = QPushButton(
            tr("analytics.apply", self.lang) if tr("analytics.apply", self.lang) != "analytics.apply" else "Übernehmen")
        row_range.addWidget(
            QLabel(tr("analytics.from", self.lang) if tr("analytics.from", self.lang) != "analytics.from" else "Von"))
        row_range.addWidget(self.analytics_from)
        row_range.addWidget(
            QLabel(tr("analytics.to", self.lang) if tr("analytics.to", self.lang) != "analytics.to" else "Bis"))
        row_range.addWidget(self.analytics_to)
        row_range.addWidget(btn_apply_range)  # Button direkt daneben
        row_range.addStretch(1)
        abox.addLayout(row_range)

        # Charts (ohne Tabellen)
        if HAS_MPL:
            self.fig_hours = Figure(figsize=(6, 2.4));
            self.canvas_hours = FigureCanvas(self.fig_hours);
            abox.addWidget(self.canvas_hours)
            self.fig_gross = Figure(figsize=(6, 2.4));
            self.canvas_gross = FigureCanvas(self.fig_gross);
            abox.addWidget(self.canvas_gross)
        else:
            info = QLabel("Charts sind deaktiviert (matplotlib nicht installiert).")
            info.setStyleSheet("color:#888;")
            abox.addWidget(info)
            self.fig_hours = self.canvas_hours = None
            self.fig_gross = self.canvas_gross = None

        # Export (unten)
        row_ex = QHBoxLayout()
        btn_anx_pdf = QPushButton(tr("analytics.export_pdf", self.lang) if tr("analytics.export_pdf",
                                                                              self.lang) != "analytics.export_pdf" else "Analytics PDF exportieren")
        btn_anx_xlsx = QPushButton(tr("analytics.export_xlsx", self.lang) if tr("analytics.export_xlsx",
                                                                                self.lang) != "analytics.export_xlsx" else "Analytics Excel exportieren")
        btn_anx_png = QPushButton(tr("analytics.export_png", self.lang) if tr("analytics.export_png",
                                                                              self.lang) != "analytics.export_png" else "Analytics PNG exportieren")
        row_ex.addWidget(btn_anx_pdf);
        row_ex.addWidget(btn_anx_xlsx);
        row_ex.addWidget(btn_anx_png);
        row_ex.addStretch(1)
        abox.addLayout(row_ex)

        layout.addWidget(self.analytics_box, stretch=4)  # Analytics nimmt den verbleibenden Raum

        btn_apply_range.clicked.connect(lambda *_: self._rebuild_analytics())
        btn_anx_pdf.clicked.connect(self._export_analytics_pdf)
        btn_anx_xlsx.clicked.connect(self._export_analytics_xlsx)
        btn_anx_png.clicked.connect(self._export_analytics_png)

        # Signals & Actions
        self.calendar.selectionChanged.connect(self._on_date_changed)
        self.date_picker.dateChanged.connect(lambda *_: self._sync_calendar_to_picker())
        self.combo_view.currentIndexChanged.connect(lambda *_: self._reload())
        self.combo_type_filter.currentIndexChanged.connect(lambda *_: self._reload())
        self.search_edit.textChanged.connect(lambda *_: self._reload())
        btn_prev.clicked.connect(self._go_prev); btn_next.clicked.connect(self._go_next)
        btn_refresh.clicked.connect(lambda *_: self._reload())
        btn_new.clicked.connect(self._new_entry); btn_edit.clicked.connect(self._edit_entry); btn_delete.clicked.connect(self._delete_entry)
        btn_import_csv.clicked.connect(self._import_csv_entries)
        btn_export_csv.clicked.connect(self._export_csv)
        btn_pdf.clicked.connect(self._export_pdf); btn_xlsx.clicked.connect(self._export_xlsx)

        # Shortcuts
        QShortcut(QKeySequence("N"), self, activated=self._new_entry)
        QShortcut(QKeySequence("E"), self, activated=self._edit_entry)
        QShortcut(QKeySequence("Delete"), self, activated=self._delete_entry)
        QShortcut(QKeySequence("H"), self, activated=lambda: self.calendar.setSelectedDate(QDate.currentDate()))
        QShortcut(QKeySequence("F5"), self, activated=lambda *_: self._reload())

        self._reload(initial=True)
        # Sichtbarkeit nach User-Pref
        self._toggle_analytics(self.chk_anx.isChecked(), initial=True)

    # ----- Admin user list -----
    def _load_users_into_combo(self):
        self.user_combo.clear()
        with self.session_factory() as s:
            users = s.execute(select(User).order_by(User.username.asc())).scalars().all()
            profs = {p.user_id: p for p in s.execute(select(UserProfile)).scalars().all()}
        for u in users:
            p = profs.get(u.id)
            last = (p.last_name or "") if p else ""
            first = (p.first_name or "") if p else ""
            employer = (p.employer or "—") if p else "—"
            role = (u.role or "").upper()
            label = f"{last} {first} - {employer} ({role})".strip()
            self.user_combo.addItem(label, u.id)
        idx = self.user_combo.findData(self.user_id)
        if idx >= 0: self.user_combo.setCurrentIndex(idx)

    def _on_user_changed(self):
        self.view_user_id = self.user_combo.currentData() or self.user_id
        # Analytics-Checkbox/Box an die Präferenz des neuen Users anpassen
        vis = bool(get_user_pref(self.view_user_id, "analytics_visible", True))
        self.chk_anx.blockSignals(True)
        self.chk_anx.setChecked(vis)
        self.chk_anx.blockSignals(False)
        self._toggle_analytics(vis, initial=True)

        self._marks_cache.clear()
        self._reload()

        vis = bool(get_user_pref(self.view_user_id, "analytics_visible", True))
        self.chk_anx.blockSignals(True)
        self.chk_anx.setChecked(vis)
        self.chk_anx.blockSignals(False)
        self._toggle_analytics(vis, initial=True)

    # ----- View/Navigation -----
    def _view_mode(self) -> str:
        return ["DAY","WEEK","MONTH","YEAR"][self.combo_view.currentIndex()]

    def _selected_date(self) -> date:
        return qdate_to_date(self.calendar.selectedDate()) or date.today()

    def _sync_calendar_to_picker(self):
        d = self.date_picker.date()
        if d and d.isValid():
            self.calendar.setSelectedDate(d)
            self._reload()

    def _on_date_changed(self):
        self.date_picker.setDate(self.calendar.selectedDate())
        self._reload()

    def _range_for_view(self) -> tuple[date,date]:
        d = self._selected_date(); vm = self._view_mode()
        if vm=="DAY": return (d,d)
        if vm=="WEEK":
            start = d - timedelta(days=d.weekday()); return (start, start+timedelta(days=6))
        if vm=="MONTH":
            start = d.replace(day=1)
            if start.month == 12: end = start.replace(year=start.year+1, month=1, day=1) - timedelta(days=1)
            else: end = start.replace(month=start.month+1, day=1) - timedelta(days=1)
            return (start, end)
        return (d.replace(month=1, day=1), d.replace(month=12, day=31))

    def _go_prev(self):
        d=self._selected_date(); vm=self._view_mode()
        if vm=="MONTH": self.calendar.setSelectedDate(QDate(d.year, d.month, d.day).addMonths(-1)); return
        if vm=="YEAR":  self.calendar.setSelectedDate(QDate(d.year, d.month, d.day).addYears(-1)); return
        self.calendar.setSelectedDate(QDate(d.year, d.month, d.day).addDays(- (7 if vm=="WEEK" else 1)))

    def _go_next(self):
        d=self._selected_date(); vm=self._view_mode()
        if vm=="MONTH": self.calendar.setSelectedDate(QDate(d.year, d.month, d.day).addMonths(1)); return
        if vm=="YEAR":  self.calendar.setSelectedDate(QDate(d.year, d.month, d.day).addYears(1)); return
        self.calendar.setSelectedDate(QDate(d.year, d.month, d.day).addDays(7 if vm=="WEEK" else 1))

    # ----- Lohnberechnung -----
    def _period_wages(self, hours_sum: float) -> Tuple[float, float]:
        with self.session_factory() as s:
            p = s.query(UserProfile).filter(UserProfile.user_id==self.view_user_id).one_or_none()
        def _v(name: str, default: float = 0.0) -> float:
            return float(getattr(p, name)) if (p and getattr(p, name) is not None) else float(_W.get(name, default))
        hb=_v("hourly_brutto"); vac=_v("vac_pct"); hol=_v("holiday_pct"); m13=_v("thirteenth_pct")
        exp=_v("expenses_per_hour"); ahv=_v("ahv_pct"); nbu=_v("nbu_pct"); ktg=_v("ktg_pct"); bvg=_v("bvg_pct", 0.0)
        gross_hr = hb*(1+(vac+hol+m13)/100.0) + exp
        net_hr   = hb*(1+(vac+hol+m13)/100.0)*(1-(ahv+nbu+ktg+bvg)/100.0) + exp
        h = float(hours_sum or 0.0)
        return (gross_hr * h, net_hr * h)

    # ----- RELOAD -----
    def _reload(self, initial: bool=False):
        start, end = self._range_for_view()
        with self.session_factory() as s:
            entries = list_entries_by_range(s, self.view_user_id, start, end)

        vm = self._view_mode()
        q = (self.search_edit.text() or "").strip().lower()
        type_code = self.combo_type_filter.currentData()

        def _match(e):
            if type_code and type_code != "ALL" and (e.entry_type or "").upper() != type_code:
                return False
            if q and (q not in (e.note or "").lower()) and (q not in (e.location or "").lower()):
                return False
            return True

        selected_d = self._selected_date()
        base_list = entries if vm in ("WEEK","MONTH","YEAR") else [e for e in entries if e.date == selected_d]
        show_list = [e for e in base_list if _match(e)]

        hours_sum_filtered = sum(float(e.hours or 0.0) for e in show_list if _is_worked(e.entry_type))
        gross_total, net_total = self._period_wages(hours_sum_filtered)

        # --- SICK-Benefit: 80% von 8h pro Krankentag ---
        sick_days  = sum(1 for e in entries if (e.entry_type or "").upper() in ("SICK","ACCIDENT"))
        if sick_days:
            gross_hr, net_hr = self._period_wages(1.0)  # Satz pro Stunde
            sick_gross = 0.80 * 8.0 * gross_hr * sick_days
            sick_net = 0.80 * 8.0 * net_hr * sick_days
            gross_total += sick_gross
            net_total += sick_net

        was_sorting = self.table.isSortingEnabled()
        if was_sorting: self.table.setSortingEnabled(False)

        self.table.setRowCount(0)
        for e in show_list:
            row = self.table.rowCount()
            self.table.insertRow(row)

            it_date = DateItem(e.date)
            it_date.setData(Qt.ItemDataRole.UserRole, e.id)  # entry id für CRUD
            self.table.setItem(row, 0, it_date)

            self.table.setItem(row, 1, QTableWidgetItem(e.start_time.strftime("%H:%M") if e.start_time else ""))
            self.table.setItem(row, 2, QTableWidgetItem(e.end_time.strftime("%H:%M") if e.end_time else ""))

            pause_val = int(e.break_minutes or 0)
            self.table.setItem(row, 3, NumericItem(pause_val, str(pause_val)))

            hours_val = float(e.hours or 0.0)
            self.table.setItem(row, 4, NumericItem(hours_val, f"{hours_val:.2f}"))

            typ_text = _type_label(self.lang, e.entry_type)
            typ_item = QTableWidgetItem(typ_text)
            typ_code = (e.entry_type or "OTHER").upper()
            typ_item.setForeground(TYPE_COLORS.get(typ_code, QColor(60, 60, 60)))
            self.table.setItem(row, 5, typ_item)

            self.table.setItem(row, 6, QTableWidgetItem(e.note or ""))
            self.table.setItem(row, 7, QTableWidgetItem(e.location or ""))

            # --- Tagessold Brutto/Netto pro Zeile ---
            gross_per_hour, net_per_hour = self._period_wages(1.0)  # 1.0h -> (brutto/std, netto/std)

            typ_code = (e.entry_type or "").upper()
            hours_val = float(e.hours or 0.0)

            if typ_code == "WORK":
                day_gross = gross_per_hour * hours_val
                day_net = net_per_hour * hours_val
            elif typ_code in ("SICK","ACCIDENT"):
                day_gross = 0.80 * 8.0 * gross_per_hour
                day_net   = 0.80 * 8.0 * net_per_hour
            else:
                day_gross = 0.0
                day_net = 0.0

            it_g = QTableWidgetItem(f"{day_gross:.2f}")
            it_g.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_g.setForeground(QColor("#d93025"))  # rot = Brutto
            self.table.setItem(row, 8, it_g)

            it_n = QTableWidgetItem(f"{day_net:.2f}")
            it_n.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_n.setForeground(QColor("#137333"))  # grün = Netto
            self.table.setItem(row, 9, it_n)

        if was_sorting: self.table.setSortingEnabled(True)

        self._refresh_month_marks()
        self.table.resizeColumnsToContents()
        self._auto_widen_note_location()

        self.lbl_totals.setTextFormat(Qt.RichText)
        self.lbl_totals.setText(
            f"<b>{_t(self.lang, 'totals')}:</b> "
            f"{_t(self.lang, 'hours')} <b>{hours_sum_filtered:.2f}</b> | "
            f"{_t(self.lang, 'entries')}: <b>{len(show_list)}</b> — "
            f"<b><span style='color:#d93025;'>{tr('payroll.gross', self.lang) if tr('payroll.gross', self.lang) != 'payroll.gross' else 'Bruttolohn'}: {fmt_money(gross_total)}</span></b> | "
            f"<b><span style='color:#137333;'>{tr('payroll.net', self.lang) if tr('payroll.net', self.lang) != 'payroll.net' else 'Nettolohn'}: {fmt_money(net_total)}</span></b>"
        )

        sick_like_days = sum(1 for e in show_list if (e.entry_type or "").upper() in ("SICK", "ACCIDENT"))
        if sick_like_days:
            g_hr, n_hr = self._period_wages(1.0)
            gross_total += 0.80 * 8.0 * g_hr * sick_like_days
            net_total += 0.80 * 8.0 * n_hr * sick_like_days

        # Analytics auf Basis des aktuellen Analytics-Zeitraums neu erstellen
        self._rebuild_analytics()

    # ----- Markierungen im Monatskalender (Dots/Farbpunkt pro Tag) -----
    def _refresh_month_marks(self):
        """
        Bestimmt für den sichtbaren Monat alle Tage mit Einträgen und erzeugt
        pro Tag eine Liste von Typfarben (max. 6), die rechts neben der Datumzahl
        als Punkte angezeigt werden.
        """
        y = self.calendar.yearShown()
        m = self.calendar.monthShown()
        key = (self.view_user_id, y, m)

        if key not in self._marks_cache:
            start = date(y, m, 1)
            if m == 12:
                end = start.replace(year=y + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=m + 1, day=1) - timedelta(days=1)

            with self.session_factory() as s:
                entries = list_entries_by_range(s, self.view_user_id, start, end)

            # Typmengen je Tag sammeln
            types_by_day: Dict[date, set[str]] = {}
            for e in entries:
                typ = (e.entry_type or "WORK").upper()
                d = e.date
                types_by_day.setdefault(d, set()).add(typ)

            # Farbenlisten erzeugen (feste Reihenfolge der Typen, dann Rest alphabetisch)
            PRIORITY = ["WORK", "VACATION", "SICK", "ACCIDENT", "HOLIDAY", "OFF", "OTHER"]
            marks_set: set[QDate] = set()
            color_map_multi: Dict[QDate, List[QColor]] = {}

            for d, type_set in types_by_day.items():
                qd = QDate(d.year, d.month, d.day)
                marks_set.add(qd)
                ordered = [t for t in PRIORITY if t in type_set] + sorted([t for t in type_set if t not in PRIORITY])
                colors = [TYPE_COLORS.get(t, QColor(60, 60, 60)) for t in ordered]
                color_map_multi[qd] = colors

            self._marks_cache[key] = (marks_set, color_map_multi)

        marks_set, color_map_multi = self._marks_cache[key]
        self.calendar.set_marked(marks_set, color_map_multi)

    # ----- CRUD -----
    def _selected_entry_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0: return None
        it = self.table.item(row, 0)
        if not it: return None
        entry_id = it.data(Qt.ItemDataRole.UserRole)
        return int(entry_id) if entry_id is not None else None

    def _selected_entry_ids(self) -> list[int]:
        rows = sorted({ix.row() for ix in self.table.selectedIndexes()})
        ids: list[int] = []
        for r in rows:
            it = self.table.item(r, 0)
            if not it: continue
            eid = it.data(Qt.ItemDataRole.UserRole)
            if eid is not None:
                ids.append(int(eid))
        return ids

    def _new_entry(self):
        dlg = EntryDialog(self.session_factory, user_id=self.view_user_id, lang=self.lang, entry=None, parent=self)
        if dlg.exec(): self._reload()

    def _edit_entry(self):
        eid = self._selected_entry_id()
        if eid is None: return
        with self.session_factory() as s:
            e = get_entry(s, eid)
        if not e:
            QMessageBox.warning(self, _t(self.lang,"title"), "Entry not found."); self._reload(); return
        dlg = EntryDialog(self.session_factory, user_id=self.view_user_id, lang=self.lang, entry=e, parent=self)
        if dlg.exec(): self._reload()

    def _delete_entry(self):
        ids = self._selected_entry_ids()
        if not ids:
            return
        if QMessageBox.question(self, _t(self.lang, "title"),
                                _t(self.lang, "confirm_delete")) != QMessageBox.StandardButton.Yes:
            return
        with self.session_factory() as s:
            for eid in ids:
                delete_entry(s, eid)
        self._reload()

    # ----- Export -----
    def _current_view_entries(self) -> List:
        start, end = self._range_for_view()
        with self.session_factory() as s: entries = list_entries_by_range(s, self.view_user_id, start, end)
        vm = self._view_mode(); selected_d = self._selected_date()
        if vm == "DAY": entries = [e for e in entries if e.date == selected_d]
        q = (self.search_edit.text() or "").strip().lower(); type_code = self.combo_type_filter.currentData()
        out=[];
        for e in entries:
            if type_code and type_code!="ALL" and (e.entry_type or "").upper()!=type_code: continue
            if q and (q not in (e.note or "").lower()) and (q not in (e.location or "").lower()): continue
            out.append(e)
        return out

    def _export_pdf(self):
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            QMessageBox.warning(self, "PDF",
                                "reportlab ist nicht installiert.\nBitte ausführen: pip install reportlab");
            return

        entries = self._current_view_entries()
        if not entries:
            QMessageBox.information(self, "PDF", "Keine Daten für Export.")
            return

        # ---- vorgeschlagenen Dateinamen zusammenbauen (mit Monat/Jahr) ----
        from datetime import date as _date
        import re
        from sqlalchemy import select
        try:
            y = entries[0].date.year
            m = entries[0].date.month
        except Exception:
            today = _date.today()
            y, m = today.year, today.month

        # User-Daten für sprechenden Namen
        ln, fn, em = "NA", "NA", "NA"
        try:
            from core.models import User, UserProfile
            with self.session_factory() as s:
                p = s.execute(select(UserProfile).where(UserProfile.user_id == self.view_user_id)).scalar_one_or_none()
                if p:
                    ln = p.last_name or ln
                    fn = p.first_name or fn
                    em = p.employer or em
                else:
                    u = s.execute(select(User).where(User.id == self.view_user_id)).scalar_one_or_none()
                    if u:
                        ln = (u.username or "NA")
        except Exception:
            pass

        def _san(s: str) -> str:
            s = (s or "").strip()
            s = re.sub(r"\s+", "_", s)
            return re.sub(r"[^A-Za-z0-9_.\-äöüÄÖÜß]", "", s) or "NA"

        base = f"Cal-Export_{_san(ln)}_{_san(fn)}_{_san(em)}_Monat_{m:02d}-{y}_Erstellt_am_{_date.today().isoformat()}"
        suggested = f"{base}.pdf"
        # -------------------------------------------------------------------

        path, _ = QFileDialog.getSaveFileName(self, "PDF speichern", suggested, "PDF (*.pdf)")
        if not path:
            return

        data = [[_t(self.lang, "date"), _t(self.lang, "start"), _t(self.lang, "end"), _t(self.lang, "break"),
                 _t(self.lang, "hours"), _t(self.lang, "type"), _t(self.lang, "note"), _t(self.lang, "location")]]
        for e in entries:
            data.append([
                e.date.isoformat(),
                e.start_time.strftime("%H:%M") if e.start_time else "",
                e.end_time.strftime("%H:%M") if e.end_time else "",
                str(int(e.break_minutes or 0)),
                f"{float(e.hours or 0):.2f}",
                _type_label(self.lang, e.entry_type),
                e.note or "",
                e.location or ""
            ])

        hours = sum(float(e.hours or 0.0) for e in entries if _is_worked(e.entry_type))
        gross, net = self._period_wages(hours)
        data.append([
            "", "", "", "", f"{hours:.2f}", "—",
            f"{tr('payroll.gross', self.lang) if tr('payroll.gross', self.lang) != 'payroll.gross' else 'Bruttolohn'}: {gross:.2f}",
            f"{tr('payroll.net', self.lang) if tr('payroll.net', self.lang) != 'payroll.net' else 'Nettolohn'}: {net:.2f}"
        ])

        doc = SimpleDocTemplate(path, pagesize=landscape(A4), title=_t(self.lang, "title"))
        styles = getSampleStyleSheet()
        elems = [Paragraph(_t(self.lang, "title"), styles["Title"]), Spacer(1, 6)]
        table = Table(data, repeatRows=1)
        table.setStyle([
            ("BACKGROUND", (0, 0), (-1, 0), "#eeeeee"),
            ("GRID", (0, 0), (-1, -1), 0.25, "gray"),
            ("ALIGN", (1, 1), (4, -1), "CENTER"),
            ("ALIGN", (5, 1), (5, -1), "LEFT"),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold")
        ])
        elems.append(table)
        doc.build(elems)
        QMessageBox.information(self, "PDF", f"Exportiert: {path}")

    def _export_xlsx(self):
        try:
            import openpyxl
            from openpyxl.styles import Font
        except ImportError:
            QMessageBox.warning(self, "Excel",
                                "openpyxl ist nicht installiert.\nBitte ausführen: pip install openpyxl");
            return

        entries = self._current_view_entries()
        if not entries:
            QMessageBox.information(self, "Excel", "Keine Daten für Export.")
            return

        # ---- vorgeschlagenen Dateinamen zusammenbauen (mit Monat/Jahr) ----
        from datetime import date as _date
        import re
        from sqlalchemy import select
        try:
            y = entries[0].date.year
            m = entries[0].date.month
        except Exception:
            today = _date.today()
            y, m = today.year, today.month

        ln, fn, em = "NA", "NA", "NA"
        try:
            from core.models import User, UserProfile
            with self.session_factory() as s:
                p = s.execute(select(UserProfile).where(UserProfile.user_id == self.view_user_id)).scalar_one_or_none()
                if p:
                    ln = p.last_name or ln
                    fn = p.first_name or fn
                    em = p.employer or em
                else:
                    u = s.execute(select(User).where(User.id == self.view_user_id)).scalar_one_or_none()
                    if u:
                        ln = (u.username or "NA")
        except Exception:
            pass

        def _san(s: str) -> str:
            s = (s or "").strip()
            s = re.sub(r"\s+", "_", s)
            return re.sub(r"[^A-Za-z0-9_.\-äöüÄÖÜß]", "", s) or "NA"

        base = f"Cal-Export_{_san(ln)}_{_san(fn)}_{_san(em)}_Monat_{m:02d}-{y}_Erstellt_am_{_date.today().isoformat()}"
        suggested = f"{base}.xlsx"
        # -------------------------------------------------------------------

        path, _ = QFileDialog.getSaveFileName(self, "Excel speichern", suggested, "Excel (*.xlsx)")
        if not path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Calendar"

        headers = [_t(self.lang, "date"), _t(self.lang, "start"), _t(self.lang, "end"), _t(self.lang, "break"),
                   _t(self.lang, "hours"), _t(self.lang, "type"), _t(self.lang, "note"), _t(self.lang, "location")]
        ws.append(headers)
        bold = Font(bold=True)
        for col in range(1, len(headers) + 1):
            ws.cell(row=1, column=col).font = bold

        for e in entries:
            ws.append([
                e.date.isoformat(),
                e.start_time.strftime("%H:%M") if e.start_time else "",
                e.end_time.strftime("%H:%M") if e.end_time else "",
                int(e.break_minutes or 0),
                float(e.hours or 0.0),
                _type_label(self.lang, e.entry_type),
                e.note or "",
                e.location or ""
            ])

        wb.save(path)
        QMessageBox.information(self, "Excel", f"Exportiert: {path}")

    # --- CSV Import/Export robust ---
    def _import_csv_entries(self):
        """CSV-Import: erkennt Delimiter automatisch (',' oder ';') und akzeptiert Spalten-Aliase."""
        try:
            path, _ = QFileDialog.getOpenFileName(self, "CSV importieren", "", "CSV (*.csv)")
            if not path:
                return

            # Datei einlesen & Delimiter erkennen
            with open(path, "r", encoding="utf-8") as f:
                sample = f.read(2048)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=";,")
                    delim = dialect.delimiter
                except Exception:
                    # Fallback: zuerst ';', sonst ','
                    delim = ";" if ";" in sample else ","
                reader = csv.DictReader(f, delimiter=delim)
                if not reader.fieldnames:
                    raise ValueError("Leere CSV oder keine Kopfzeile.")

                # Kopfzeilen normieren
                cols_lc = {c.strip().lower(): c for c in reader.fieldnames}

                # Aliase -> Zielspalte
                alias = {
                    "date": ["date", "datum"],
                    "start": ["start", "beginn"],
                    "end": ["end", "ende"],
                    "break_minutes": ["break_minutes", "break", "pause", "pause (min)"],
                    "hours": ["hours", "stunden"],
                    "type": ["type", "typ"],
                    "note": ["note", "notiz"],
                    "location": ["location", "ort"],
                }

                def get(row, key):
                    for a in alias[key]:
                        if a in cols_lc:
                            return (row.get(cols_lc[a]) or "").strip()
                    return ""

                created = 0
                with self.session_factory() as s:
                    for row in reader:
                        try:
                            d_txt = get(row, "date")
                            if not d_txt:
                                continue
                            d = date.fromisoformat(d_txt)

                            st = get(row, "start");
                            et = get(row, "end")
                            start_t = None if not st else (
                                None if len(st) < 4 else __import__("datetime").time(int(st[:2]), int(st[3:5])))
                            end_t = None if not et else (
                                None if len(et) < 4 else __import__("datetime").time(int(et[:2]), int(et[3:5])))

                            brk = get(row, "break_minutes");
                            brk_i = int(brk) if brk else 0
                            hrs = get(row, "hours");
                            hrs_f = float(hrs.replace(",", ".")) if hrs else 0.0
                            typ = (get(row, "type") or "WORK").upper()
                            note = get(row, "note") or None
                            loc = get(row, "location") or None

                            create_entry(s, self.view_user_id, date=d, start_time=start_t, end_time=end_t,
                                         break_minutes=brk_i, hours=hrs_f, entry_type=typ, note=note, location=loc)
                            created += 1
                        except Exception:
                            # Zeile überspringen; optional loggen
                            continue
            QMessageBox.information(self, "CSV", f"{created} Einträge importiert.")
            self._reload()
        except Exception as ex:
            QMessageBox.critical(self, "CSV", str(ex))

    def _export_csv(self):
        with self.session_factory() as s:
            u = s.get(User, self.view_user_id)
            p = s.query(UserProfile).filter(UserProfile.user_id == self.view_user_id).one_or_none()
        last = (p.last_name or "") if p else ""; first = (p.first_name or (u.username if u else "")); employer = (p.employer or "—") if p else "—"
        path, _ = QFileDialog.getSaveFileName(self, "CSV speichern", _calendar_export_filename(last, first, employer, "csv"), "CSV (*.csv)")
        if not path: return
        entries = self._current_view_entries()
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                # KANONISCHE Header
                w.writerow(["date","start","end","break_minutes","hours","type","note","location"])
                for e in entries:
                    w.writerow([
                        e.date.isoformat(),
                        e.start_time.strftime("%H:%M") if e.start_time else "",
                        e.end_time.strftime("%H:%M") if e.end_time else "",
                        int(e.break_minutes or 0),
                        f"{float(e.hours or 0.0):.2f}",
                        (e.entry_type or ""),
                        e.note or "",
                        e.location or ""
                    ])
            QMessageBox.information(self, "CSV", f"Exportiert: {path}")
        except Exception as ex:
            QMessageBox.critical(self, "CSV", str(ex))

    def _rebuild_analytics(self):
        if not (self.analytics_from.date().isValid() and self.analytics_to.date().isValid()):
            return
        d_from = self.analytics_from.date().toPython()
        d_to = self.analytics_to.date().toPython()
        if d_to < d_from: d_from, d_to = d_to, d_from

        with self.session_factory() as s:
            entries = list_entries_by_range(s, self.view_user_id, d_from, d_to)

        # Stunden pro Tag
        hours_by_day: Dict[date, float] = {}
        for e in entries:
            if _is_worked(e.entry_type):
                hours_by_day[e.date] = hours_by_day.get(e.date, 0.0) + float(e.hours or 0.0)

        # Brutto pro Monat
        gross_per_hour, _ = self._period_wages(1.0)
        gross_by_month: Dict[str, float] = {}
        for e in entries:
            if _is_worked(e.entry_type):
                ym = f"{e.date.year}-{e.date.month:02d}"
                gross_by_month[ym] = gross_by_month.get(ym, 0.0) + float(e.hours or 0.0) * gross_per_hour

        # Charts zeichnen (falls matplotlib vorhanden)
        self._draw_analytics_charts(hours_by_day, gross_by_month)

    def _draw_analytics_charts(self, hours_by_day: Dict[date, float], gross_by_month: Dict[str, float]):
        if not HAS_MPL:
            return

        # Linie: Stunden/Tag (schwarz)
        self.fig_hours.clear();
        ax1 = self.fig_hours.add_subplot(111)
        if hours_by_day: xs = sorted(hours_by_day.keys()); ys = [hours_by_day[d] for d in xs]; ax1.plot(xs, ys)
        ax1.set_title(tr("analytics.hours_per_day", self.lang) if tr("analytics.hours_per_day",
                                                                     self.lang) != "analytics.hours_per_day" else "Stunden pro Tag")
        ax1.set_xlabel(_t(self.lang, "date"));
        ax1.set_ylabel(_t(self.lang, "hours"));
        self.fig_hours.tight_layout();
        self.canvas_hours.draw()

        # Balken: Brutto/Monat (rot)
        self.fig_gross.clear();
        ax2 = self.fig_gross.add_subplot(111)
        if gross_by_month: xs = sorted(gross_by_month.keys()); ys = [gross_by_month[k] for k in xs]; ax2.bar(xs, ys,
                                                                                                             color="#d93025")
        ax2.set_title(tr("analytics.gross_per_month", self.lang) if tr("analytics.gross_per_month",
                                                                       self.lang) != "analytics.gross_per_month" else "Brutto (Total) pro Monat")
        ax2.set_xlabel(tr("payroll.menu", self.lang) if tr("payroll.menu", self.lang) != "payroll.menu" else "Monat");
        ax2.set_ylabel(
            tr("payroll.gross", self.lang) if tr("payroll.gross", self.lang) != "payroll.gross" else "Bruttolohn")
        self.fig_gross.tight_layout();
        self.canvas_gross.draw()

    def _toggle_analytics(self, visible: bool, initial: bool = False):
        self.analytics_box.setVisible(bool(visible))
        if not initial:
            set_user_pref(self.view_user_id, "analytics_visible", bool(visible))