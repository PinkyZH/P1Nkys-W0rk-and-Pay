from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QWidget, QFormLayout,
    QDoubleSpinBox, QPushButton, QSpinBox, QMessageBox
)
from sqlalchemy.orm import sessionmaker

from core.models import UserProfile
from core.services.wage_service import (
    _load_global_defaults, save_global_defaults, simulate_from_params,
    save_user_overrides, reset_user_overrides
)
from core.services.work_service import list_entries_by_range
from core.utils.i18n import t

SICK_BENEFIT_HOURS = 8.0
SICK_BENEFIT_FACTOR = 0.80


class _Num(QDoubleSpinBox):
    def __init__(self, minv: float, maxv: float, step: float = 0.05, dec: int = 2):
        super().__init__()
        self.setRange(minv, maxv)
        self.setDecimals(dec)
        self.setSingleStep(step)


class WageRulesDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, current_user_id: int,
                 is_admin_or_hr: bool, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_id = current_user_id
        self.is_admin_or_hr = is_admin_or_hr
        self.lang = lang

        self.setWindowTitle(t("rules.wage.title", self.lang)
                            if t("rules.wage.title", self.lang) != "rules.wage.title"
                            else "Lohnregeln")
        self.setSizeGripEnabled(True)
        self._build()
        self.adjustSize()

    # ------------------------- UI -------------------------
    def _build(self):
        root = QVBoxLayout(self)

        tabs = QTabWidget()
        root.addWidget(tabs)

        if self.is_admin_or_hr:
            tabs.addTab(self._make_global_tab(),
                        t("rules.wage.global", self.lang) if t("rules.wage.global", self.lang) != "rules.wage.global"
                        else "Global (Defaults)")
        tabs.addTab(self._make_user_tab(),
                    t("rules.wage.user", self.lang) if t("rules.wage.user", self.lang) != "rules.wage.user"
                    else "Benutzer")

        bar = QHBoxLayout()
        bar.addStretch(1)
        btn_close = QPushButton(t("dialogs.common.close", self.lang)
                                if t("dialogs.common.close", self.lang) != "dialogs.common.close" else "Schließen")
        bar.addWidget(btn_close)
        root.addLayout(bar)
        btn_close.clicked.connect(self.accept)

    # ------------------ Global (Defaults) ------------------
    def _make_global_tab(self) -> QWidget:
        w = QWidget()
        fl = QFormLayout(w)

        d = _load_global_defaults()

        self.g_hourly = _Num(0, 1000);
        self.g_hourly.setValue(d.get("hourly_brutto", 0.0))
        self.g_vac = _Num(0, 100);
        self.g_vac.setValue(d.get("vac_pct", 0.0))
        self.g_hol = _Num(0, 100);
        self.g_hol.setValue(d.get("holiday_pct", 0.0))
        self.g_13 = _Num(0, 100);
        self.g_13.setValue(d.get("thirteenth_pct", 0.0))
        self.g_exp = _Num(0, 1000);
        self.g_exp.setValue(d.get("expenses_per_hour", 0.0))
        self.g_ahv = _Num(0, 100);
        self.g_ahv.setValue(d.get("ahv_pct", 0.0))
        self.g_nbu = _Num(0, 100);
        self.g_nbu.setValue(d.get("nbu_pct", 0.0))
        self.g_ktg = _Num(0, 100);
        self.g_ktg.setValue(d.get("ktg_pct", 0.0))
        self.g_bvg = _Num(0, 100);
        self.g_bvg.setValue(d.get("bvg_pct", 0.0))
        self.g_lgav = _Num(0, 100000);
        self.g_lgav.setValue(d.get("lgav_fixed_monthly", 0.0))
        self.g_week = _Num(0, 100);
        self.g_week.setValue(d.get("weekly_hours", 0.0))
        self.g_sim_hours = QSpinBox();
        self.g_sim_hours.setRange(0, 400);
        self.g_sim_hours.setValue(0)

        def row(lbl, wdg): fl.addRow(lbl, wdg)

        row(t("profile.hourly_wage", self.lang), self.g_hourly)
        row(t("profile.vac_pct_label", self.lang) if t("profile.vac_pct_label",
                                                       self.lang) != "profile.vac_pct_label" else "Feriengeld %",
            self.g_vac)
        row(t("profile.holiday_pct_label", self.lang) if t("profile.holiday_pct_label",
                                                           self.lang) != "profile.holiday_pct_label" else "Feiertage %",
            self.g_hol)
        row(t("profile.thirteenth_pct_label", self.lang) if t("profile.thirteenth_pct_label",
                                                              self.lang) != "profile.thirteenth_pct_label" else "13. Monatslohn %",
            self.g_13)
        row(t("profile.expenses_per_hour_label", self.lang) if t("profile.expenses_per_hour_label",
                                                                 self.lang) != "profile.expenses_per_hour_label" else "Spesen/Std.",
            self.g_exp)
        row("AHV/IV/EO/ALV %", self.g_ahv);
        row("NBU/BU %", self.g_nbu);
        row("KTG %", self.g_ktg);
        row("BVG %", self.g_bvg)
        row("LGAV/Monat", self.g_lgav)
        row(t("profile.weekly_hours_label", self.lang) if t("profile.weekly_hours_label",
                                                            self.lang) != "profile.weekly_hours_label" else "Wochenstunden",
            self.g_week)
        row(t("rules.wage.preview_hours", self.lang) if t("rules.wage.preview_hours",
                                                          self.lang) != "rules.wage.preview_hours" else "Vorschau-Stunden/Monat",
            self.g_sim_hours)

        # Monat/Jahr rechts + „Monat laden“
        mrow = QHBoxLayout()
        self.g_month = QSpinBox();
        self.g_month.setRange(1, 12);
        self.g_month.setValue(date.today().month)
        self.g_year = QSpinBox();
        self.g_year.setRange(2000, 2100);
        self.g_year.setValue(date.today().year)
        btn_load = QPushButton(t("wprev.load_month", self.lang) if t("wprev.load_month",
                                                                     self.lang) != "wprev.load_month" else "Monat laden")
        mrow.addStretch(1)
        mrow.addWidget(QLabel(t("wprev.month_select", self.lang) if t("wprev.month_select",
                                                                      self.lang) != "wprev.month_select" else "Monat/Jahr"))
        mrow.addWidget(self.g_month);
        mrow.addWidget(self.g_year);
        mrow.addWidget(btn_load)
        fl.addRow(mrow)

        # Buttons + Ergebnis
        brow = QHBoxLayout()
        btn_prev = QPushButton(t("rules.wage.preview_btn", self.lang) if t("rules.wage.preview_btn",
                                                                           self.lang) != "rules.wage.preview_btn" else "Vorschau")
        btn_save = QPushButton(t("dialogs.common.save", self.lang) if t("dialogs.common.save",
                                                                        self.lang) != "dialogs.common.save" else "Speichern")
        brow.addWidget(btn_prev);
        brow.addWidget(btn_save)
        fl.addRow(brow)
        self.g_prev = QLabel("-")
        fl.addRow(QLabel(t("dialogs.common.result", self.lang) if t("dialogs.common.result",
                                                                    self.lang) != "dialogs.common.result" else "Ergebnis:"),
                  self.g_prev)

        btn_prev.clicked.connect(self._do_global_preview)
        btn_save.clicked.connect(self._do_global_save)
        btn_load.clicked.connect(self._load_global_hours_from_month)

        return w

    # --------------------- Benutzer-Tab ---------------------
    def _make_user_tab(self) -> QWidget:
        w = QWidget()
        fl = QFormLayout(w)

        # Userprofil holen
        with self.session_factory() as s:
            p = s.query(UserProfile).filter(UserProfile.user_id == self.user_id).one_or_none()

        # Felder – direkt aus dem Profil (falls None -> 0.0)
        self.u_hourly = _Num(0, 1000);
        self.u_hourly.setValue(float(getattr(p, "hourly_brutto", 0.0) or 0.0))
        self.u_vac = _Num(0, 100);
        self.u_vac.setValue(float(getattr(p, "vac_pct", 0.0) or 0.0))
        self.u_hol = _Num(0, 100);
        self.u_hol.setValue(float(getattr(p, "holiday_pct", 0.0) or 0.0))
        self.u_13 = _Num(0, 100);
        self.u_13.setValue(float(getattr(p, "thirteenth_pct", 0.0) or 0.0))
        self.u_exp = _Num(0, 1000);
        self.u_exp.setValue(float(getattr(p, "expenses_per_hour", 0.0) or 0.0))
        self.u_ahv = _Num(0, 100);
        self.u_ahv.setValue(float(getattr(p, "ahv_pct", 0.0) or 0.0))
        self.u_nbu = _Num(0, 100);
        self.u_nbu.setValue(float(getattr(p, "nbu_pct", 0.0) or 0.0))
        self.u_ktg = _Num(0, 100);
        self.u_ktg.setValue(float(getattr(p, "ktg_pct", 0.0) or 0.0))
        self.u_bvg = _Num(0, 100);
        self.u_bvg.setValue(float(getattr(p, "bvg_pct", 0.0) or 0.0))
        self.u_lgav = _Num(0, 100000);
        self.u_lgav.setValue(float(getattr(p, "lgav_fixed_monthly", 0.0) or 0.0))
        self.u_week = _Num(0, 100);
        self.u_week.setValue(float(getattr(p, "weekly_hours", 0.0) or 0.0))

        self.u_sim_hours = QSpinBox();
        self.u_sim_hours.setRange(0, 400);
        self.u_sim_hours.setValue(0)
        self.u_prev = QLabel("-")

        def row(lbl, wdg): fl.addRow(lbl, wdg)

        row(t("profile.hourly_wage", self.lang), self.u_hourly)
        row(t("profile.vac_pct_label", self.lang) if t("profile.vac_pct_label",
                                                       self.lang) != "profile.vac_pct_label" else "Feriengeld %",
            self.u_vac)
        row(t("profile.holiday_pct_label", self.lang) if t("profile.holiday_pct_label",
                                                           self.lang) != "profile.holiday_pct_label" else "Feiertage %",
            self.u_hol)
        row(t("profile.thirteenth_pct_label", self.lang) if t("profile.thirteenth_pct_label",
                                                              self.lang) != "profile.thirteenth_pct_label" else "13. Monatslohn %",
            self.u_13)
        row(t("profile.expenses_per_hour_label", self.lang) if t("profile.expenses_per_hour_label",
                                                                 self.lang) != "profile.expenses_per_hour_label" else "Spesen/Std.",
            self.u_exp)
        row("AHV/IV/EO/ALV %", self.u_ahv);
        row("NBU/BU %", self.u_nbu);
        row("KTG %", self.u_ktg);
        row("BVG %", self.u_bvg)
        row("LGAV/Monat", self.u_lgav)
        row(t("profile.weekly_hours_label", self.lang) if t("profile.weekly_hours_label",
                                                            self.lang) != "profile.weekly_hours_label" else "Wochenstunden",
            self.u_week)

        row(t("rules.wage.preview_hours", self.lang) if t("rules.wage.preview_hours",
                                                          self.lang) != "rules.wage.preview_hours" else "Vorschau-Stunden/Monat",
            self.u_sim_hours)

        # Monatswahl + „Monat laden“
        mrow = QHBoxLayout()
        self.u_month = QSpinBox();
        self.u_month.setRange(1, 12);
        self.u_month.setValue(date.today().month)
        self.u_year = QSpinBox();
        self.u_year.setRange(2000, 2100);
        self.u_year.setValue(date.today().year)
        btn_uload = QPushButton(t("wprev.load_month", self.lang) if t("wprev.load_month",
                                                                      self.lang) != "wprev.load_month" else "Monat laden")
        mrow.addStretch(1)
        mrow.addWidget(QLabel(t("wprev.month_select", self.lang) if t("wprev.month_select",
                                                                      self.lang) != "wprev.month_select" else "Monat/Jahr"))
        mrow.addWidget(self.u_month);
        mrow.addWidget(self.u_year);
        mrow.addWidget(btn_uload)
        fl.addRow(mrow)

        btn_uload.clicked.connect(self._load_user_hours_from_month)

        # Buttons & Ergebnis
        brow = QHBoxLayout()
        btn_prev = QPushButton(t("rules.wage.preview_btn", self.lang) if t("rules.wage.preview_btn",
                                                                           self.lang) != "rules.wage.preview_btn" else "Vorschau")
        btn_save = QPushButton(t("dialogs.common.save", self.lang) if t("dialogs.common.save",
                                                                        self.lang) != "dialogs.common.save" else "Speichern")
        btn_reset = QPushButton(t("rules.wage.reset_user", self.lang) if t("rules.wage.reset_user",
                                                                           self.lang) != "rules.wage.reset_user" else "Reset auf Global")
        brow.addWidget(btn_prev);
        brow.addWidget(btn_save);
        brow.addWidget(btn_reset)
        fl.addRow(brow)
        fl.addRow(QLabel(t("dialogs.common.result", self.lang) if t("dialogs.common.result",
                                                                    self.lang) != "dialogs.common.result" else "Ergebnis:"),
                  self.u_prev)

        # Connects
        btn_prev.clicked.connect(self._do_user_preview)
        btn_save.clicked.connect(self._do_user_save)
        btn_reset.clicked.connect(self._do_user_reset)
        btn_uload.clicked.connect(self._load_user_hours_from_month)

        return w

    # ---------------- Global Aktionen / Helfer ----------------
    def _do_global_preview(self):
        params = {
            "hourly_brutto": self.g_hourly.value(),
            "vac_pct": self.g_vac.value(),
            "holiday_pct": self.g_hol.value(),
            "thirteenth_pct": self.g_13.value(),
            "expenses_per_hour": self.g_exp.value(),
            "ahv_pct": self.g_ahv.value(),
            "nbu_pct": self.g_nbu.value(),
            "ktg_pct": self.g_ktg.value(),
            "bvg_pct": self.g_bvg.value(),
        }
        res = simulate_from_params(params, float(self.g_sim_hours.value()))
        self.g_prev.setText(
            f"{t('dialogs.common.gross_per_hour', self.lang) if t('dialogs.common.gross_per_hour', self.lang) != 'dialogs.common.gross_per_hour' else 'Brutto/Std'}: {res['gross_per_hour']:.2f} | "
            f"{t('dialogs.common.net_per_hour', self.lang) if t('dialogs.common.net_per_hour', self.lang) != 'dialogs.common.net_per_hour' else 'Netto/Std'}: {res['net_per_hour']:.2f} || "
            f"{t('dialogs.common.gross_per_month', self.lang) if t('dialogs.common.gross_per_month', self.lang) != 'dialogs.common.gross_per_month' else 'Brutto/Monat'}: {res['gross_per_month']:.2f} | "
            f"{t('dialogs.common.net_per_month', self.lang) if t('dialogs.common.net_per_month', self.lang) != 'dialogs.common.net_per_month' else 'Netto/Monat'}: {res['net_per_month']:.2f}"
        )

    def _do_global_save(self):
        vals = {
            "hourly_brutto": self.g_hourly.value(),
            "vac_pct": self.g_vac.value(),
            "holiday_pct": self.g_hol.value(),
            "thirteenth_pct": self.g_13.value(),
            "expenses_per_hour": self.g_exp.value(),
            "ahv_pct": self.g_ahv.value(),
            "nbu_pct": self.g_nbu.value(),
            "ktg_pct": self.g_ktg.value(),
            "bvg_pct": self.g_bvg.value(),
            "lgav_fixed_monthly": self.g_lgav.value(),
            "weekly_hours": self.g_week.value(),
        }
        try:
            save_global_defaults(vals)
            QMessageBox.information(self, t("rules.wage.title", self.lang),
                                    t("dialogs.common.saved", self.lang) if t("dialogs.common.saved",
                                                                              self.lang) != "dialogs.common.saved" else "Gespeichert.")
        except Exception as ex:
            QMessageBox.critical(self, t("rules.wage.title", self.lang), str(ex))

    def _load_global_hours_from_month(self):
        if not getattr(self, "user_id", None):
            self.g_prev.setText("—")
            return
        y = int(self.g_year.value());
        m = int(self.g_month.value())
        start = date(y, m, 1)
        end = (date(y + 1, 1, 1) - timedelta(days=1)) if m == 12 else (date(y, m + 1, 1) - timedelta(days=1))
        with self.session_factory() as s:
            entries = list_entries_by_range(s, self.user_id, start, end)
        work = sum(float(e.hours or 0.0) for e in entries if (e.entry_type or "").upper() == "WORK")
        sick = sum(1 for e in entries if (e.entry_type or "").upper() in ("SICK", "ACCIDENT"))
        work += SICK_BENEFIT_FACTOR * SICK_BENEFIT_HOURS * sick
        self.g_sim_hours.setValue(int(round(work)))

    # ---------------- Benutzer Aktionen / Helfer ---------------
    def _do_user_preview(self):
        params = {
            "hourly_brutto": self.u_hourly.value(),
            "vac_pct": self.u_vac.value(),
            "holiday_pct": self.u_hol.value(),
            "thirteenth_pct": self.u_13.value(),
            "expenses_per_hour": self.u_exp.value(),
            "ahv_pct": self.u_ahv.value(),
            "nbu_pct": self.u_nbu.value(),
            "ktg_pct": self.u_ktg.value(),
            "bvg_pct": self.u_bvg.value(),
        }
        res = simulate_from_params(params, float(self.u_sim_hours.value()))
        self.u_prev.setText(
            f"{t('dialogs.common.gross_per_hour', self.lang) if t('dialogs.common.gross_per_hour', self.lang) != 'dialogs.common.gross_per_hour' else 'Brutto/Std'}: {res['gross_per_hour']:.2f} | "
            f"{t('dialogs.common.net_per_hour', self.lang) if t('dialogs.common.net_per_hour', self.lang) != 'dialogs.common.net_per_hour' else 'Netto/Std'}: {res['net_per_hour']:.2f} || "
            f"{t('dialogs.common.gross_per_month', self.lang) if t('dialogs.common.gross_per_month', self.lang) != 'dialogs.common.gross_per_month' else 'Brutto/Monat'}: {res['gross_per_month']:.2f} | "
            f"{t('dialogs.common.net_per_month', self.lang) if t('dialogs.common.net_per_month', self.lang) != 'dialogs.common.net_per_month' else 'Netto/Monat'}: {res['net_per_month']:.2f}"
        )

    def _do_user_save(self):
        vals = {
            "hourly_brutto": self.u_hourly.value(),
            "vac_pct": self.u_vac.value(),
            "holiday_pct": self.u_hol.value(),
            "thirteenth_pct": self.u_13.value(),
            "expenses_per_hour": self.u_exp.value(),
            "ahv_pct": self.u_ahv.value(),
            "nbu_pct": self.u_nbu.value(),
            "ktg_pct": self.u_ktg.value(),
            "bvg_pct": self.u_bvg.value(),
            "lgav_fixed_monthly": self.u_lgav.value(),
            "weekly_hours": self.u_week.value(),
        }
        try:
            save_user_overrides(self.session_factory, self.user_id, vals)
            QMessageBox.information(self, t("rules.wage.title", self.lang),
                                    t("dialogs.common.saved", self.lang) if t("dialogs.common.saved",
                                                                              self.lang) != "dialogs.common.saved" else "Gespeichert.")
        except Exception as ex:
            QMessageBox.critical(self, t("rules.wage.title", self.lang), str(ex))

    def _do_user_reset(self):
        try:
            reset_user_overrides(self.session_factory, self.user_id)
            QMessageBox.information(self, t("rules.wage.title", self.lang),
                                    t("rules.wage.reset_ok", self.lang) if t("rules.wage.reset_ok",
                                                                             self.lang) != "rules.wage.reset_ok" else "Overrides zurückgesetzt.")
        except Exception as ex:
            QMessageBox.critical(self, t("rules.wage.title", self.lang), str(ex))

    def _load_user_hours_from_month(self):
        y = int(self.u_year.value());
        m = int(self.u_month.value())
        start = date(y, m, 1)
        end = (date(y + 1, 1, 1) - timedelta(days=1)) if m == 12 else (date(y, m + 1, 1) - timedelta(days=1))
        with self.session_factory() as s:
            entries = list_entries_by_range(s, self.user_id, start, end)
        work = sum(float(e.hours or 0.0) for e in entries if (e.entry_type or "").upper() == "WORK")
        sick = sum(1 for e in entries if (e.entry_type or "").upper() in ("SICK", "ACCIDENT"))
        work += SICK_BENEFIT_FACTOR * SICK_BENEFIT_HOURS * sick
        self.u_sim_hours.setValue(int(round(work)))
