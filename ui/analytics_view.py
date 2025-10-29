# workpay/ui/analytics_view.py
from __future__ import annotations

from datetime import date

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, \
    QValueAxis
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QDateEdit, QPushButton
from sqlalchemy.orm import sessionmaker

from core.services.payroll_service import compute_month
from core.services.work_service import list_entries_by_range
from ui.window_flags import apply_window_controls


class AnalyticsDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_id = user_id
        self.lang = lang
        self.setWindowTitle("Analytics / Statistik")
        self.setSizeGripEnabled(True)
        self._build();
        self.adjustSize()
        # Vollbild / maximiert starten:
        self.showMaximized()
        # oder alternativ: self.showMaximized() (falls als Fenster, nicht modal, verwendet)

    def _build(self):
        self.showMaximized()
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.d_from = QDateEdit();
        self.d_from.setCalendarPopup(True);
        self.d_from.setDate(QDate.currentDate().addMonths(-1))
        self.d_to = QDateEdit();
        self.d_to.setCalendarPopup(True);
        self.d_to.setDate(QDate.currentDate())
        btn = QPushButton("Aktualisieren")
        for w in (self.d_from, self.d_to, btn): row.addWidget(w)
        layout.addLayout(row)

        # Charts
        self.chart_hours = QChart();
        self.chart_hours.setTitle("Stunden pro Tag")
        self.view_hours = QChartView(self.chart_hours);
        layout.addWidget(self.view_hours)

        self.chart_types = QChart();
        self.chart_types.setTitle("Typ-Verteilung (Stunden)")
        self.view_types = QChartView(self.chart_types);
        layout.addWidget(self.view_types)

        self.chart_gross = QChart();
        self.chart_gross.setTitle("Brutto (Total) pro Monat")
        self.view_gross = QChartView(self.chart_gross);
        layout.addWidget(self.view_gross)

        btn.clicked.connect(self._reload)
        self._reload()
        apply_window_controls(self)

    def _reload(self):
        d1 = self.d_from.date().toPython()
        d2 = self.d_to.date().toPython()
        # Linie: Stunden/Tag
        with self.session_factory() as s:
            entries = list_entries_by_range(s, self.user_id, d1, d2)
        days = {}
        types_hours = {}
        y_m = {}
        for e in entries:
            d = e.date
            days[d] = days.get(d, 0.0) + float(e.hours or 0.0)
            t = (e.entry_type or "WORK").upper()
            types_hours[t] = types_hours.get(t, 0.0) + float(e.hours or 0.0)

        # Stunden pro Tag als Linie
        s_line = QLineSeries()
        for k in sorted(days.keys()):
            # X als Ordinalindex
            s_line.append(float((k - d1).days), float(days[k]))
        self.chart_hours.removeAllSeries();
        self.chart_hours.addSeries(s_line)
        axX = QValueAxis();
        axX.setTitleText("Tage");
        axY = QValueAxis();
        axY.setTitleText("Stunden")
        self.chart_hours.createDefaultAxes();
        self.chart_hours.setAxisX(axX, s_line);
        self.chart_hours.setAxisY(axY, s_line)

        # Typ-Pie
        pie = QPieSeries()
        for k, v in types_hours.items():
            pie.append(k, v)
        self.chart_types.removeAllSeries();
        self.chart_types.addSeries(pie)

        # Brutto pro Monat (über compute_month)
        months = []
        cur = date(d1.year, d1.month, 1)
        while cur <= d2:
            months.append((cur.year, cur.month))
            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)

        bar = QBarSeries()
        sset = QBarSet("Brutto (Total)")
        cats = []
        with self.session_factory() as s:
            for (yy, mm) in months:
                data = compute_month(s, self.user_id, yy, mm)
                sset.append(float(data["gross_total"]))
                cats.append(f"{yy}-{mm:02d}")
        bar.append(sset)
        self.chart_gross.removeAllSeries();
        self.chart_gross.addSeries(bar)
        axC = QBarCategoryAxis();
        axC.append(cats)
        axV = QValueAxis();
        axV.setTitleText("CHF")
        self.chart_gross.createDefaultAxes();
        self.chart_gross.setAxisX(axC, bar);
        self.chart_gross.setAxisY(axV, bar)
