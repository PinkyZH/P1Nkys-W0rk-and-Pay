from __future__ import annotations
from typing import Dict, Tuple
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QLineEdit,
    QSpinBox, QDoubleSpinBox, QPushButton, QGroupBox, QGridLayout, QWidget
)
from PySide6.QtCore import Qt, QDate
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from core.models import UserProfile
from core.services.wage_service import _load_global_defaults
from core.services.work_service import list_entries_by_range
from languages import tr

# ---- SICK-Regel: 80% von 8h pro Eintrag ----
SICK_BENEFIT_HOURS = 8.0
SICK_BENEFIT_FACTOR = 0.80


class _RO(QLineEdit):
    def __init__(self, text: str = ""):
        super().__init__(text)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("QLineEdit{ background:#f7f7f7; }")


class WagePreviewDialog(QDialog):
    """
    Lohnvorschau mit Szenario-Vergleich (IST vs. WAS-WÄRE-WENN)
    und Lohnprognosen (diese/kommende Woche, dieser/nächster Monat).
    """
    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_id = user_id
        self.lang = lang

        self.setWindowTitle(tr("wprev.title", self.lang) if tr("wprev.title", self.lang) != "wprev.title"
                            else "Lohnvorschau – Szenarien & Prognose")
        self.setSizeGripEnabled(True)
        self._build()
        self._load_effective_params()
        self._recalc_all()
        self.adjustSize()

    # ------------- UI -------------
    def _build(self):
        root = QVBoxLayout(self)

        # --- Parameterblöcke: links IST (read-only), rechts WHAT-IF (editierbar) ---
        grid = QGridLayout()
        root.addLayout(grid)

        # Linke Spalte (IST, Readonly)
        grp_ist = QGroupBox(tr("wprev.ist", self.lang) if tr("wprev.ist", self.lang) != "wprev.ist" else "IST")
        fL = QFormLayout(grp_ist)
        self.ro_hourly = _RO()
        self.ro_vac = _RO();
        self.ro_hol = _RO();
        self.ro_13 = _RO()
        self.ro_exp = _RO()
        self.ro_ahv = _RO();
        self.ro_nbu = _RO();
        self.ro_ktg = _RO();
        self.ro_bvg = _RO()
        self.ro_week = _RO()
        for label, w in [
            (tr("profile.hourly_wage", self.lang), self.ro_hourly),
            (tr("profile.vac_pct_label", self.lang) if tr("profile.vac_pct_label",
                                                          self.lang) != "profile.vac_pct_label" else "Feriengeld %",
             self.ro_vac),
            (tr("profile.holiday_pct_label", self.lang) if tr("profile.holiday_pct_label",
                                                              self.lang) != "profile.holiday_pct_label" else "Feiertage %",
             self.ro_hol),
            (tr("profile.thirteenth_pct_label", self.lang) if tr("profile.thirteenth_pct_label",
                                                                 self.lang) != "profile.thirteenth_pct_label" else "13. Monatslohn %",
             self.ro_13),
            (tr("profile.expenses_per_hour_label", self.lang) if tr("profile.expenses_per_hour_label",
                                                                    self.lang) != "profile.expenses_per_hour_label" else "Spesen/Std.",
             self.ro_exp),
            ("AHV/IV/EO/ALV %", self.ro_ahv), ("NBU/BU %", self.ro_nbu), ("KTG %", self.ro_ktg), ("BVG %", self.ro_bvg),
            (tr("profile.weekly_hours_label", self.lang) if tr("profile.weekly_hours_label",
                                                               self.lang) != "profile.weekly_hours_label" else "Wochenstunden",
             self.ro_week),
        ]:
            fL.addRow(label, w)

        # Rechte Spalte (WHAT-IF, editierbar + Delta-Stunden)
        grp_if = QGroupBox(
            tr("wprev.whatif", self.lang) if tr("wprev.whatif", self.lang) != "wprev.whatif" else "Was-wäre-wenn")
        fR = QFormLayout(grp_if)
        self.if_hourly = QDoubleSpinBox();
        self.if_hourly.setRange(0, 1000);
        self.if_hourly.setDecimals(2)
        self.if_vac = QDoubleSpinBox();
        self.if_vac.setRange(0, 100);
        self.if_vac.setDecimals(2)
        self.if_hol = QDoubleSpinBox();
        self.if_hol.setRange(0, 100);
        self.if_hol.setDecimals(2)
        self.if_13 = QDoubleSpinBox();
        self.if_13.setRange(0, 100);
        self.if_13.setDecimals(2)
        self.if_exp = QDoubleSpinBox();
        self.if_exp.setRange(0, 1000);
        self.if_exp.setDecimals(2)
        self.if_ahv = QDoubleSpinBox();
        self.if_ahv.setRange(0, 100);
        self.if_ahv.setDecimals(2)
        self.if_nbu = QDoubleSpinBox();
        self.if_nbu.setRange(0, 100);
        self.if_nbu.setDecimals(2)
        self.if_ktg = QDoubleSpinBox();
        self.if_ktg.setRange(0, 100);
        self.if_ktg.setDecimals(2)
        self.if_bvg = QDoubleSpinBox();
        self.if_bvg.setRange(0, 100);
        self.if_bvg.setDecimals(2)
        self.if_week = QDoubleSpinBox();
        self.if_week.setRange(0, 100);
        self.if_week.setDecimals(2)

        self.if_extra_hours = QDoubleSpinBox();
        self.if_extra_hours.setRange(-300, 300);
        self.if_extra_hours.setDecimals(2)
        self.if_extra_hours.setToolTip(tr("wprev.extra_hours_tip", self.lang) if tr("wprev.extra_hours_tip",
                                                                                    self.lang) != "wprev.extra_hours_tip" else "Zusatzstunden (±) für Monatsvergleich")

        for label, w in [
            (tr("profile.hourly_wage", self.lang), self.if_hourly),
            (tr("profile.vac_pct_label", self.lang) if tr("profile.vac_pct_label",
                                                          self.lang) != "profile.vac_pct_label" else "Feriengeld %",
             self.if_vac),
            (tr("profile.holiday_pct_label", self.lang) if tr("profile.holiday_pct_label",
                                                              self.lang) != "profile.holiday_pct_label" else "Feiertage %",
             self.if_hol),
            (tr("profile.thirteenth_pct_label", self.lang) if tr("profile.thirteenth_pct_label",
                                                                 self.lang) != "profile.thirteenth_pct_label" else "13. Monatslohn %",
             self.if_13),
            (tr("profile.expenses_per_hour_label", self.lang) if tr("profile.expenses_per_hour_label",
                                                                    self.lang) != "profile.expenses_per_hour_label" else "Spesen/Std.",
             self.if_exp),
            ("AHV/IV/EO/ALV %", self.if_ahv), ("NBU/BU %", self.if_nbu), ("KTG %", self.if_ktg), ("BVG %", self.if_bvg),
            (tr("profile.weekly_hours_label", self.lang) if tr("profile.weekly_hours_label",
                                                               self.lang) != "profile.weekly_hours_label" else "Wochenstunden",
             self.if_week),
            (tr("wprev.extra_hours", self.lang) if tr("wprev.extra_hours",
                                                      self.lang) != "wprev.extra_hours" else "Zusatzstunden (±) / Monat",
             self.if_extra_hours),
        ]:
            fR.addRow(label, w)

        grid.addWidget(grp_ist, 0, 0)
        grid.addWidget(grp_if, 0, 1)

        # --- Prognose-Block (unterhalb Buttons) ---
        grp_res = QGroupBox(tr("wprev.results", self.lang) if tr("wprev.results", self.lang) != "wprev.results"
                            else "Ergebnis – IST vs. Was-wäre-wenn")
        g = QGridLayout(grp_res)
        g.addWidget(QLabel(""), 0, 0)
        g.addWidget(
            QLabel(tr("wprev.col_ist", self.lang) if tr("wprev.col_ist", self.lang) != "wprev.col_ist" else "IST"), 0,
            1, alignment=Qt.AlignCenter)
        g.addWidget(QLabel(
            tr("wprev.col_if", self.lang) if tr("wprev.col_if", self.lang) != "wprev.col_if" else "Was-wäre-wenn"), 0,
                    2, alignment=Qt.AlignCenter)

        rows = [
            ("wprev.gph", "Brutto/Std"),
            ("wprev.nph", "Netto/Std"),
            ("wprev.gpm", "Brutto/Monat (174h)"),
            ("wprev.npm", "Netto/Monat (174h)"),
            ("wprev.delta_m", "Δ / Monat"),
        ]
        self.out = {}
        r = 1
        for key, fallback in rows:
            g.addWidget(QLabel(tr(key, self.lang) if tr(key, self.lang) != key else fallback), r, 0)
            l_ist = QLabel("-");
            l_if = QLabel("-")
            l_ist.setAlignment(Qt.AlignRight);
            l_if.setAlignment(Qt.AlignRight)
            g.addWidget(l_ist, r, 1);
            g.addWidget(l_if, r, 2)
            self.out[key] = (l_ist, l_if);
            r += 1
        root.addWidget(grp_res)

        grp_fc = QGroupBox(
            tr("wprev.forecast", self.lang) if tr("wprev.forecast", self.lang) != "wprev.forecast" else "Prognose")
        fcl = QGridLayout(grp_fc)
        fcl.addWidget(QLabel(tr("wprev.this_week", self.lang) if tr("wprev.this_week",
                                                                    self.lang) != "wprev.this_week" else "Diese Woche"),
                      0, 0)
        self.fc_tw_g = QLabel("-");
        self.fc_tw_n = QLabel("-")
        fcl.addWidget(self.fc_tw_g, 0, 1);
        fcl.addWidget(self.fc_tw_n, 0, 2)

        fcl.addWidget(QLabel(tr("wprev.next_week", self.lang) if tr("wprev.next_week",
                                                                    self.lang) != "wprev.next_week" else "Nächste Woche"),
                      1, 0)
        self.fc_nw_g = QLabel("-");
        self.fc_nw_n = QLabel("-")
        fcl.addWidget(self.fc_nw_g, 1, 1);
        fcl.addWidget(self.fc_nw_n, 1, 2)

        fcl.addWidget(QLabel(tr("wprev.this_month", self.lang) if tr("wprev.this_month",
                                                                     self.lang) != "wprev.this_month" else "Dieser Monat"),
                      2, 0)
        self.fc_tm_g = QLabel("-");
        self.fc_tm_n = QLabel("-")
        fcl.addWidget(self.fc_tm_g, 2, 1);
        fcl.addWidget(self.fc_tm_n, 2, 2)

        fcl.addWidget(QLabel(tr("wprev.next_month", self.lang) if tr("wprev.next_month",
                                                                     self.lang) != "wprev.next_month" else "Nächster Monat"),
                      3, 0)
        self.fc_nm_g = QLabel("-");
        self.fc_nm_n = QLabel("-")
        fcl.addWidget(self.fc_nm_g, 3, 1);
        fcl.addWidget(self.fc_nm_n, 3, 2)
        root.addWidget(grp_fc)

        # --- Schnell-Vergleich: IST vs. Was-wäre-wenn (nur Lohn & Stunden) ---
        grp_quick = QGroupBox(
            tr("wprev.quick.title", self.lang) if tr("wprev.quick.title", self.lang) != "wprev.quick.title"
            else "Schnell-Vergleich (nur Lohn & Stunden)")
        ql = QGridLayout(grp_quick)
        ql.addWidget(QLabel(""), 0, 0)
        ql.addWidget(
            QLabel(tr("wprev.col_ist", self.lang) if tr("wprev.col_ist", self.lang) != "wprev.col_ist" else "IST"), 0,
            1, alignment=Qt.AlignCenter)
        ql.addWidget(QLabel(
            tr("wprev.col_if", self.lang) if tr("wprev.col_if", self.lang) != "wprev.col_if" else "Was-wäre-wenn"), 0,
            2, alignment=Qt.AlignCenter)

        # Zeile 1: Stundenlohn
        ql.addWidget(QLabel(tr("profile.hourly_wage", self.lang)), 1, 0)
        self.q_ist_wage = QDoubleSpinBox();
        self.q_ist_wage.setRange(0, 1000);
        self.q_ist_wage.setDecimals(2)
        self.q_if_wage = QDoubleSpinBox();
        self.q_if_wage.setRange(0, 1000);
        self.q_if_wage.setDecimals(2)
        ql.addWidget(self.q_ist_wage, 1, 1);
        ql.addWidget(self.q_if_wage, 1, 2)

        # Zeile 2: Stunden
        ql.addWidget(
            QLabel(tr("wprev.hours", self.lang) if tr("wprev.hours", self.lang) != "wprev.hours" else "Stunden"), 2, 0)
        self.q_ist_hours = QDoubleSpinBox();
        self.q_ist_hours.setRange(0, 10000);
        self.q_ist_hours.setDecimals(2)
        self.q_if_hours = QDoubleSpinBox();
        self.q_if_hours.setRange(0, 10000);
        self.q_if_hours.setDecimals(2)
        ql.addWidget(self.q_ist_hours, 2, 1);
        ql.addWidget(self.q_if_hours, 2, 2)

        # Zeile 3/4: Ergebnis Brutto/Netto (farbig)
        def _mk_label(color_hex: str):
            lab = QLabel("-");
            lab.setAlignment(Qt.AlignRight)
            lab.setStyleSheet(f"font-weight:600; color:{color_hex};")
            return lab

        ql.addWidget(QLabel(
            tr("payroll.gross", self.lang) if tr("payroll.gross", self.lang) != "payroll.gross" else "Bruttolohn"), 3,
            0)
        self.q_ist_g = _mk_label("#d93025")  # rot
        self.q_if_g = _mk_label("#d93025")
        ql.addWidget(self.q_ist_g, 3, 1);
        ql.addWidget(self.q_if_g, 3, 2)

        ql.addWidget(
            QLabel(tr("payroll.net", self.lang) if tr("payroll.net", self.lang) != "payroll.net" else "Nettolohn"), 4,
            0)
        self.q_ist_n = _mk_label("#137333")  # grün
        self.q_if_n = _mk_label("#137333")
        ql.addWidget(self.q_ist_n, 4, 1);
        ql.addWidget(self.q_if_n, 4, 2)

        root.addWidget(grp_quick)

        # Buttonleiste + Monat rechts – Neuberechnen
        row_btn = QHBoxLayout()
        row_btn.addStretch(1)  # links: Platz

        # rechts: Monat (IST laden) + Aktualisieren
        self.q_month = QSpinBox();
        self.q_month.setRange(1, 12);
        self.q_month.setValue(date.today().month)
        self.q_year = QSpinBox();
        self.q_year.setRange(2000, 2100);
        self.q_year.setValue(date.today().year)
        btn_load = QPushButton(tr("wprev.load_month", self.lang) if tr("wprev.load_month",
                                                                       self.lang) != "wprev.load_month" else "Monat laden")
        btn_apply = QPushButton(tr("dialogs.common.refresh", self.lang) if tr("dialogs.common.refresh",
                                                                              self.lang) != "dialogs.common.refresh" else "Aktualisieren")

        row_btn.addWidget(QLabel(tr("wprev.month_select", self.lang) if tr("wprev.month_select",
                                                                           self.lang) != "wprev.month_select" else "Monat/Jahr"))
        row_btn.addWidget(self.q_month)
        row_btn.addWidget(self.q_year)
        row_btn.addWidget(btn_load)
        row_btn.addWidget(btn_apply)

        root.addLayout(row_btn)

        btn_load.clicked.connect(self._load_hours_from_month)
        btn_apply.clicked.connect(self._recalc_all)

        # Recalc trigger (erst JETZT, nachdem Widgets existieren)
        for w in (self.if_hourly, self.if_vac, self.if_hol, self.if_13, self.if_exp, self.if_ahv,
                  self.if_nbu, self.if_ktg, self.if_bvg, self.if_week, self.if_extra_hours):
            w.valueChanged.connect(self._recalc_all)
        for w in (self.q_ist_wage, self.q_if_wage, self.q_ist_hours, self.q_if_hours):
            w.valueChanged.connect(self._recalc_quick)
    # ------------- Daten laden -------------
    def _load_effective_params(self):
        dfl = _load_global_defaults()
        with self.session_factory() as s:
            p = s.execute(select(UserProfile).where(UserProfile.user_id == self.user_id)).scalar_one_or_none()

        def eff(name: str) -> float:
            return float(getattr(p, name)) if (p and getattr(p, name) is not None) else float(dfl.get(name, 0.0))

        self._ist_params = {
            "hourly_brutto": eff("hourly_brutto"),
            "vac_pct": eff("vac_pct"),
            "holiday_pct": eff("holiday_pct"),
            "thirteenth_pct": eff("thirteenth_pct"),
            "expenses_per_hour": eff("expenses_per_hour"),
            "ahv_pct": eff("ahv_pct"),
            "nbu_pct": eff("nbu_pct"),
            "ktg_pct": eff("ktg_pct"),
            "bvg_pct": eff("bvg_pct"),
            "weekly_hours": eff("weekly_hours"),
        }

        self.ro_hourly.setText(f"{self._ist_params['hourly_brutto']:.2f}")
        self.ro_vac.setText(f"{self._ist_params['vac_pct']:.2f}")
        self.ro_hol.setText(f"{self._ist_params['holiday_pct']:.2f}")
        self.ro_13.setText(f"{self._ist_params['thirteenth_pct']:.2f}")
        self.ro_exp.setText(f"{self._ist_params['expenses_per_hour']:.2f}")
        self.ro_ahv.setText(f"{self._ist_params['ahv_pct']:.2f}")
        self.ro_nbu.setText(f"{self._ist_params['nbu_pct']:.2f}")
        self.ro_ktg.setText(f"{self._ist_params['ktg_pct']:.2f}")
        self.ro_bvg.setText(f"{self._ist_params['bvg_pct']:.2f}")
        self.ro_week.setText(f"{self._ist_params['weekly_hours']:.2f}")

        # What-If auf IST setzen
        self.if_hourly.setValue(self._ist_params['hourly_brutto'])
        self.if_vac.setValue(self._ist_params['vac_pct'])
        self.if_hol.setValue(self._ist_params['holiday_pct'])
        self.if_13.setValue(self._ist_params['thirteenth_pct'])
        self.if_exp.setValue(self._ist_params['expenses_per_hour'])
        self.if_ahv.setValue(self._ist_params['ahv_pct'])
        self.if_nbu.setValue(self._ist_params['nbu_pct'])
        self.if_ktg.setValue(self._ist_params['ktg_pct'])
        self.if_bvg.setValue(self._ist_params['bvg_pct'])
        self.if_week.setValue(self._ist_params['weekly_hours'])
        self.if_extra_hours.setValue(0.0)

        # Schnell-Vergleich vorbelegen
        self.q_ist_wage.setValue(self._ist_params['hourly_brutto'])
        self.q_if_wage.setValue(self._ist_params['hourly_brutto'])
        self.q_ist_hours.setValue(0.0)
        self.q_if_hours.setValue(0.0)

    # ------------- Rechnen -------------
    def _effective_rates_from(self, params: Dict[str, float]) -> Tuple[float, float]:
        """Gibt (brutto/Std, netto/Std) zurück – inkl. Zuschläge/Abzüge & Spesen."""
        hb = params["hourly_brutto"]
        vac = params["vac_pct"]; hol = params["holiday_pct"]; m13 = params["thirteenth_pct"]
        exp = params["expenses_per_hour"]
        ahv = params["ahv_pct"]; nbu = params["nbu_pct"]; ktg = params["ktg_pct"]; bvg = params.get("bvg_pct", 0.0)
        gph = hb * (1 + (vac + hol + m13) / 100.0) + exp
        nph = hb * (1 + (vac + hol + m13) / 100.0) * (1 - (ahv + nbu + ktg + bvg) / 100.0) + exp
        return gph, nph

    def _recalc_all(self):
        # IST (Basis 174h)
        gph_ist, nph_ist = self._effective_rates_from(self._ist_params)
        gpm_ist = gph_ist * 174.0
        npm_ist = nph_ist * 174.0

        # IF aus UI
        if_params = dict(self._ist_params)
        if_params["hourly_brutto"] = float(self.if_hourly.value())
        for k, w in [("vac_pct", self.if_vac), ("holiday_pct", self.if_hol), ("thirteenth_pct", self.if_13),
                     ("expenses_per_hour", self.if_exp), ("ahv_pct", self.if_ahv), ("nbu_pct", self.if_nbu),
                     ("ktg_pct", self.if_ktg), ("bvg_pct", self.if_bvg), ("weekly_hours", self.if_week)]:
            if_params[k] = float(w.value())
        gph_if, nph_if = self._effective_rates_from(if_params)

        extra = float(self.if_extra_hours.value())
        gpm_if = gph_if * (174.0 + extra)
        npm_if = nph_if * (174.0 + extra)

        self.out["wprev.gph"][0].setText(f"{gph_ist:.2f}");  self.out["wprev.gph"][1].setText(f"{gph_if:.2f}")
        self.out["wprev.nph"][0].setText(f"{nph_ist:.2f}");  self.out["wprev.nph"][1].setText(f"{nph_if:.2f}")
        self.out["wprev.gpm"][0].setText(f"{gpm_ist:.2f}");  self.out["wprev.gpm"][1].setText(f"{gpm_if:.2f}")
        self.out["wprev.npm"][0].setText(f"{npm_ist:.2f}");  self.out["wprev.npm"][1].setText(f"{npm_if:.2f}")
        self.out["wprev.delta_m"][0].setText("—")
        self.out["wprev.delta_m"][1].setText(f"{(gpm_if - npm_if):.2f}")

        self._recalc_forecasts(gph_ist, nph_ist)  # Prognosen
        self._recalc_quick()                      # Schnell-Vergleich

    def _recalc_quick(self):
        # IST
        ist_params = dict(self._ist_params)
        ist_params["hourly_brutto"] = float(self.q_ist_wage.value())
        gph_ist, nph_ist = self._effective_rates_from(ist_params)
        h_ist = float(self.q_ist_hours.value())
        g_ist = gph_ist * h_ist; n_ist = nph_ist * h_ist

        # IF
        if_params = dict(self._ist_params)
        if_params["hourly_brutto"] = float(self.q_if_wage.value())
        gph_if, nph_if = self._effective_rates_from(if_params)
        h_if = float(self.q_if_hours.value())
        g_if = gph_if * h_if; n_if = nph_if * h_if

        self.q_ist_g.setText(f"{g_ist:.2f}"); self.q_if_g.setText(f"{g_if:.2f}")
        self.q_ist_n.setText(f"{n_ist:.2f}"); self.q_if_n.setText(f"{n_if:.2f}")

    # ----- Forecasts -----
    def _recalc_forecasts(self, gph: float, nph: float):
        today = date.today()
        start_w = today - timedelta(days=today.weekday()); end_w = start_w + timedelta(days=6)
        start_w2 = end_w + timedelta(days=1);               end_w2 = start_w2 + timedelta(days=6)
        start_m = today.replace(day=1)
        end_m   = (date(today.year + 1, 1, 1) - timedelta(days=1)) if today.month == 12 else (date(today.year, today.month + 1, 1) - timedelta(days=1))
        nm_start = end_m + timedelta(days=1)
        nm_end   = (date(nm_start.year + 1, 1, 1) - timedelta(days=1)) if nm_start.month == 12 else (date(nm_start.year, nm_start.month + 1, 1) - timedelta(days=1))

        def period_total(d1: date, d2: date) -> Tuple[float, float]:
            with self.session_factory() as s:
                entries = list_entries_by_range(s, self.user_id, d1, d2)
            work_hours = sum(float(e.hours or 0.0) for e in entries if (e.entry_type or "").upper() == "WORK")
            sick_days  = sum(1 for e in entries if (e.entry_type or "").upper() in ("SICK", "ACCIDENT"))
            gross = gph * work_hours + SICK_BENEFIT_FACTOR * SICK_BENEFIT_HOURS * gph * sick_days
            net   = nph * work_hours + SICK_BENEFIT_FACTOR * SICK_BENEFIT_HOURS * nph * sick_days
            return gross, net

        g_tw, n_tw = period_total(start_w,  end_w)
        g_nw, n_nw = period_total(start_w2, end_w2)
        g_tm, n_tm = period_total(start_m,  end_m)
        g_nm, n_nm = period_total(nm_start, nm_end)

        self.fc_tw_g.setText(f"{g_tw:.2f}"); self.fc_tw_n.setText(f"{n_tw:.2f}")
        self.fc_nw_g.setText(f"{g_nw:.2f}"); self.fc_nw_n.setText(f"{n_nw:.2f}")
        self.fc_tm_g.setText(f"{g_tm:.2f}"); self.fc_tm_n.setText(f"{n_tm:.2f}")
        self.fc_nm_g.setText(f"{g_nm:.2f}"); self.fc_nm_n.setText(f"{n_nm:.2f}")

    def _load_hours_from_month(self):
        # Nur tatsächliche Arbeitsstunden (ENTRY_TYPE == WORK) zählen.
        # Krank/Unfall werden NICHT zu den Stunden addiert.
        y = int(self.q_year.value())
        m = int(self.q_month.value())
        start = date(y, m, 1)
        if m == 12:
            end = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(y, m + 1, 1) - timedelta(days=1)

        with self.session_factory() as s:
            entries = list_entries_by_range(s, self.user_id, start, end)

        # Summe NUR aus WORK-Einträgen
        work_hours = sum(float(e.hours or 0.0) for e in entries if (e.entry_type or "").upper() == "WORK")

        # KEIN Hochrechnen / KEIN Zuschlag für SICK/ACCIDENT hier!
        self.q_ist_hours.setValue(work_hours)

        # Direkt den Schnell-Vergleich aktualisieren
        self._recalc_quick()