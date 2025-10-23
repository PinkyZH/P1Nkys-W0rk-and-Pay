from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QGroupBox,
    QLabel, QCheckBox, QDoubleSpinBox, QTimeEdit, QPushButton, QMessageBox, QWidget
)
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QHBoxLayout as HBox
from languages import tr
from sqlalchemy.orm import sessionmaker

# Regeln laden/speichern
from core.services.rules_service import current_rules, save_rules, is_enabled


class RulesDialog(QDialog):
    """
    Zuschlagsregeln:
      - Überstunden (anteilig)  [früher: Nacht]
      - Wochenende (voll)
      - Feiertag (voll)
    Anzeigen: Prozent + von/bis (für Überstunden) + berechnete Dauer (h)
    """
    def __init__(self, session_factory: sessionmaker, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.lang = lang
        self.setWindowTitle(tr("rules.title", self.lang) if tr("rules.title", self.lang) != "rules.title" else "Zuschlagsregeln")
        self.setSizeGripEnabled(True)
        self._build()
        self.adjustSize()

    # ---------------- UI ----------------
    def _build(self):
        layout = QVBoxLayout(self)

        # Zuschläge global aktiv?
        self.chk_enabled = QCheckBox(tr("rules.enabled", self.lang) if tr("rules.enabled", self.lang) != "rules.enabled" else "Zuschläge aktivieren")
        self.chk_enabled.setChecked(bool(is_enabled()))
        layout.addWidget(self.chk_enabled)

        rules = current_rules() or {}
        night = rules.get("NIGHT", {})

        # --- ÜBERSTUNDEN (anteilig) – ersetzt NIGHT ---
        grp_n = QGroupBox(tr("rules.overtime.title", self.lang) if tr("rules.overtime.title", self.lang) != "rules.overtime.title" else "Überstunden (anteilig)")
        g1 = QGridLayout()

        self.n_chk = QCheckBox(tr("rules.active", self.lang) if tr("rules.active", self.lang) != "rules.active" else "aktiv")
        self.n_chk.setChecked(night.get("enabled", True))

        self.n_pct = QDoubleSpinBox(); self.n_pct.setRange(0, 500); self.n_pct.setDecimals(2)
        self.n_pct.setValue(float(night.get("percent", 25.0)))

        # Standardstart 16:30, Ende 06:00 (über Mitternacht möglich)
        self.n_from = QTimeEdit(); self.n_from.setDisplayFormat("HH:mm")
        self.n_to   = QTimeEdit(); self.n_to.setDisplayFormat("HH:mm")
        self.n_from.setTime(QTime.fromString(night.get("from_time", "16:30"), "HH:mm"))
        self.n_to.setTime(QTime.fromString(night.get("to_time", "06:00"), "HH:mm"))

        # 'nächster Tag' neben 'bis'
        bis_cell = QWidget(); bis_row = HBox(bis_cell); bis_row.setContentsMargins(0,0,0,0)
        self.chk_nextday = QCheckBox(tr("rules.next_day", self.lang) if tr("rules.next_day", self.lang) != "rules.next_day" else "nächster Tag")
        self.chk_nextday.setToolTip(tr("rules.next_day_tip", self.lang) if tr("rules.next_day_tip", self.lang) != "rules.next_day_tip"
                                    else "Wenn aktiv: 'bis' liegt am Folgetag (über Mitternacht).")
        bis_row.addWidget(self.n_to, 0)
        bis_row.addWidget(self.chk_nextday, 0)

        # Dauer (h)
        self.lbl_n_duration = QLabel("-")

        g1.addWidget(self.n_chk, 0, 0)
        g1.addWidget(QLabel("%"), 0, 1); g1.addWidget(self.n_pct, 0, 2)

        g1.addWidget(QLabel(tr("rules.from", self.lang) if tr("rules.from", self.lang) != "rules.from" else "von"), 1, 0)
        g1.addWidget(self.n_from, 1, 1)
        g1.addWidget(QLabel(tr("rules.to", self.lang) if tr("rules.to", self.lang) != "rules.to" else "bis"), 1, 2)
        g1.addWidget(bis_cell, 1, 3)

        g1.addWidget(QLabel(tr("rules.duration", self.lang) if tr("rules.duration", self.lang) != "rules.duration" else "Dauer (h)"), 2, 0)
        g1.addWidget(self.lbl_n_duration, 2, 1, 1, 3)

        grp_n.setLayout(g1)
        layout.addWidget(grp_n)

        # --- Wochenende (voll) ---
        grp_w = QGroupBox(tr("rules.weekend.title", self.lang) if tr("rules.weekend.title", self.lang) != "rules.weekend.title" else "Wochenende (voll)")
        g2 = QFormLayout()
        self.w_chk = QCheckBox(tr("rules.active", self.lang) if tr("rules.active", self.lang) != "rules.active" else "aktiv")
        self.w_chk.setChecked(rules.get("WEEKEND", {}).get("enabled", True))
        self.w_pct = QDoubleSpinBox(); self.w_pct.setRange(0, 500); self.w_pct.setDecimals(2)
        self.w_pct.setValue(float(rules.get("WEEKEND", {}).get("percent", 50.0)))
        g2.addRow(self.w_chk)
        g2.addRow(QLabel("%"), self.w_pct)
        grp_w.setLayout(g2)
        layout.addWidget(grp_w)

        # --- Feiertag (voll) ---
        grp_h = QGroupBox(tr("rules.holiday.title", self.lang) if tr("rules.holiday.title", self.lang) != "rules.holiday.title" else "Feiertag (voll)")
        g3 = QFormLayout()
        self.h_chk = QCheckBox(tr("rules.active", self.lang) if tr("rules.active", self.lang) != "rules.active" else "aktiv")
        self.h_chk.setChecked(rules.get("HOLIDAY", {}).get("enabled", True))
        self.h_pct = QDoubleSpinBox(); self.h_pct.setRange(0, 500); self.h_pct.setDecimals(2)
        self.h_pct.setValue(float(rules.get("HOLIDAY", {}).get("percent", 100.0)))
        g3.addRow(self.h_chk)
        g3.addRow(QLabel("%"), self.h_pct)
        grp_h.setLayout(g3)
        layout.addWidget(grp_h)

        # Buttons
        row = QHBoxLayout()
        btn_save = QPushButton(tr("dialogs.common.save", self.lang) if tr("dialogs.common.save", self.lang) != "dialogs.common.save" else "Speichern")
        btn_cancel = QPushButton(tr("dialogs.common.cancel", self.lang) if tr("dialogs.common.cancel", self.lang) != "dialogs.common.cancel" else "Abbrechen")
        row.addStretch(1); row.addWidget(btn_save); row.addWidget(btn_cancel)
        layout.addLayout(row)

        # --- initiale Werte für 'nächster Tag' & Dauer (h) ---
        self.chk_nextday.setChecked(bool(night.get("to_next_day", False)))
        self._update_overtime_duration()

        # Signale EINMAL verbinden (nicht in _update_overtime_duration!)
        self.chk_nextday.toggled.connect(self._update_overtime_duration)
        self.n_from.timeChanged.connect(self._update_overtime_duration)
        self.n_to.timeChanged.connect(self._update_overtime_duration)

        btn_save.clicked.connect(self._save)
        btn_cancel.clicked.connect(self.reject)

    # --------------- Actions ---------------
    def _update_overtime_duration(self):
        """
        Berechnet Dauer (h) aus von/bis.
        - Ist 'nächster Tag' aktiv, rechnen wir über Mitternacht.
        - Sonst: wenn bis < von, Checkbox automatisch setzen (kann man wieder ausmachen).
        """
        t1 = self.n_from.time()
        t2 = self.n_to.time()
        m1 = t1.hour() * 60 + t1.minute()
        m2 = t2.hour() * 60 + t2.minute()

        # Automatik: wenn bis < von und 'nächster Tag' noch nicht aktiv → aktivieren
        if m2 < m1 and not self.chk_nextday.isChecked():
            self.chk_nextday.blockSignals(True)
            self.chk_nextday.setChecked(True)
            self.chk_nextday.blockSignals(False)

        if self.chk_nextday.isChecked():
            dur_min = (m2 - m1) if m2 >= m1 else (24 * 60 - (m1 - m2))
        else:
            dur_min = max(0, m2 - m1)

        self.lbl_n_duration.setText(f"{dur_min / 60.0:.2f}")

    def _save(self):
        """
        Speichert die Regeln und invalidiert ggf. Caches im rules_service,
        damit current_rules() neu lädt; danach verifizieren wir.
        """
        rules = {
            "NIGHT": {
                "enabled": bool(self.n_chk.isChecked()),
                "percent": float(self.n_pct.value()),
                "from_time": self.n_from.time().toString("HH:mm"),
                "to_time": self.n_to.time().toString("HH:mm"),
                "to_next_day": bool(self.chk_nextday.isChecked()),
            },
            "WEEKEND": {
                "enabled": bool(self.w_chk.isChecked()),
                "percent": float(self.w_pct.value()),
            },
            "HOLIDAY": {
                "enabled": bool(self.h_chk.isChecked()),
                "percent": float(self.h_pct.value()),
            },
        }
        enabled_flag = bool(self.chk_enabled.isChecked())

        try:
            from core.services import rules_service as _rs
            _rs.save_rules(rules, enabled=enabled_flag)

            # Cache/Modul reloaden, damit current_rules neu liest
            import importlib
            _rs = importlib.reload(_rs)

            # Re-Read + Verifikation
            reread = _rs.current_rules() or {}
            reread_enabled = bool(getattr(_rs, "is_enabled", lambda: False)())

            if isinstance(reread, dict) and "rules" in reread:
                loaded_rules = reread.get("rules", {})
                loaded_enabled = bool(reread.get("enabled", reread_enabled))
            else:
                loaded_rules = reread
                loaded_enabled = reread_enabled

            def _norm(d: dict) -> dict:
                out = {}
                for k, v in (d or {}).items():
                    if isinstance(v, dict):
                        out[k] = _norm(v)
                    else:
                        out[k] = float(v) if isinstance(v, (int, float)) else v
                return out

            ok = (_norm(rules) == _norm(loaded_rules)) and (enabled_flag == loaded_enabled)

            if ok:
                QMessageBox.information(self,
                                        tr("rules.title", self.lang) if tr("rules.title", self.lang) != "rules.title" else "Zuschlagsregeln",
                                        tr("dialogs.common.saved", self.lang) if tr("dialogs.common.saved", self.lang) != "dialogs.common.saved" else "Gespeichert.")
                self.accept()
            else:
                import json
                QMessageBox.warning(self, "Hinweis",
                                    "Gespeichert, aber geladene Werte weichen ab.\n\n"
                                    f"Gesendet:\n{json.dumps(rules, ensure_ascii=False, indent=2)}\n\n"
                                    f"Gelesen:\n{json.dumps({'enabled': loaded_enabled, 'rules': loaded_rules}, ensure_ascii=False, indent=2)}")
                self.accept()

        except Exception as ex:
            QMessageBox.critical(self,
                                 tr("rules.title", self.lang) if tr("rules.title", self.lang) != "rules.title" else "Zuschlagsregeln",
                                 f"Speichern fehlgeschlagen: {ex}")
