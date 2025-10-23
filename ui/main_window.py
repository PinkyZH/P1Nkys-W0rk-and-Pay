from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QMenuBar, QMessageBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal

from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from languages import tr
from config import APP_NAME, APP_VERSION

from .profile_dialog import ProfileDialog
from .user_admin_view import UserAdminDialog
from .calendar_view import CalendarMainWidget
from .payroll_view import PayrollDialog

from core.models import User
from core.services.notification_service import list_unread
from .notification_center import NotificationCenter

# Werkzeuge / HR
from .backup_restore_dialog import BackupRestoreDialog
from .audit_log_view import AuditLogDialog
from .absence_request_dialog import AbsenceRequestDialog
from .absence_admin_dialog import AbsenceAdminDialog
from .wage_preview_dialog import WagePreviewDialog
from .wage_rules_dialog import WageRulesDialog
from .rules_dialog import RulesDialog
from .log_viewer import LogViewerDialog

from core.services.settings_service import get_lang, set_lang
from ui.window_flags import apply_window_controls

# Analytics optional
try:
    from .analytics_view import AnalyticsDialog
    HAS_ANALYTICS = True
except Exception:
    HAS_ANALYTICS = False


class MainWindow(QMainWindow):
    logoutRequested = Signal()

    def __init__(self, session_factory: sessionmaker, user_id: int, username: str, lang: str = "de"):
        super().__init__()
        self.session_factory = session_factory
        self.user_id = user_id
        self.username = username
        self.lang = lang

        self.setWindowTitle(f"{APP_NAME} — v{APP_VERSION}")
        self._role = "USER"; self._is_admin = False
        with self.session_factory() as s:
            u = s.execute(select(User).where(User.id == self.user_id)).scalar_one_or_none()
            if u:
                self._role = (u.role or "").upper()
                self._is_admin = (self._role == "ADMIN")
        self._build()

        try:
            with self.session_factory() as s:
                unread = list_unread(s, self.user_id)
            if unread:
                NotificationCenter(self.session_factory, self.user_id, self.lang, self).exec()
        except Exception:
            pass

    def _build(self):
        menubar = QMenuBar(self); self.setMenuBar(menubar)
        apply_window_controls(self)

        # Konto
        menu_account = menubar.addMenu(tr("main.menu.account", self.lang) if tr("main.menu.account",
                                                                                self.lang) != "main.menu.account" else "Konto")
        act_logout = QAction(tr("main.menu.account.logout", self.lang) if tr("main.menu.account.logout",
                                                                             self.lang) != "main.menu.account.logout" else "Abmelden / Benutzer wechseln…",
                             self)
        menu_account.addAction(act_logout);
        act_logout.triggered.connect(self._do_logout)

        # Sprache
        menu_lang = menu_account.addMenu(tr("main.menu.account.language", self.lang) if tr("main.menu.account.language", self.lang) != "main.menu.account.language" else "Sprache")
        act_lang_de = QAction("Deutsch", self, checkable=True)
        act_lang_en = QAction("English", self, checkable=True)
        act_lang_sr = QAction("Srpski", self, checkable=True)
        menu_lang.addAction(act_lang_de); menu_lang.addAction(act_lang_en); menu_lang.addAction(act_lang_sr)

        cur = get_lang()
        act_lang_de.setChecked(cur=="de"); act_lang_en.setChecked(cur=="en"); act_lang_sr.setChecked(cur=="sr")

        def _set_lang(new_lang: str):
            set_lang(new_lang)
            self.lang = new_lang
            # Menüs neu aufbauen, damit Labels sofort umspringen
            current_size = self.size()
            self.menuBar().clear()
            # Zentral-Widget sichern, damit wir es nicht verlieren
            cw = self.centralWidget()
            # Only rebuild the menubar; keep calendar widget
            self._build()
            self.setCentralWidget(cw)
            self.resize(current_size)
            QMessageBox.information(self, "Info", "Sprache gespeichert. Neue Fenster öffnen in der gewählten Sprache.")

        act_lang_de.triggered.connect(lambda: _set_lang("de"))
        act_lang_en.triggered.connect(lambda: _set_lang("en"))
        act_lang_sr.triggered.connect(lambda: _set_lang("sr"))

        # Profil
        menu_profile = menubar.addMenu(tr("main.menu.profile", self.lang) if tr("main.menu.profile",
                                                                                self.lang) != "main.menu.profile" else "Profil")
        act_my_profile = QAction(tr("main.menu.profile_edit", self.lang) if tr("main.menu.profile_edit",
                                                                               self.lang) != "main.menu.profile_edit" else "Profil bearbeiten",
                                 self)
        act_my_profile.triggered.connect(self._open_my_profile)
        menu_profile.addAction(act_my_profile)

        act_wage_prev = QAction(tr("profile_menu.wage_preview", self.lang) if tr("profile_menu.wage_preview", self.lang) != "profile_menu.wage_preview" else "Lohnvorschau …", self)
        act_wage_prev.triggered.connect(lambda: WagePreviewDialog(self.session_factory, user_id=self.user_id, lang=self.lang, parent=self).exec())
        menu_profile.addAction(act_wage_prev)

        # Admin
        if self._is_admin:
            menu_admin = menubar.addMenu(
                tr("main.menu.admin", self.lang) if tr("main.menu.admin", self.lang) != "main.menu.admin" else "Admin")
            act_users = QAction(tr("main.menu.admin_users", self.lang) if tr("main.menu.admin_users",
                                                                             self.lang) != "main.menu.admin_users" else "Benutzerverwaltung",
                                self)
            act_users.triggered.connect(self._open_user_admin)
            menu_admin.addAction(act_users)

        # Abrechnung
        menu_payroll = menubar.addMenu(tr("payroll.menu", self.lang) if tr("payroll.menu", self.lang) != "payroll.menu" else "Abrechnung")
        act_payroll = QAction(tr("payroll.open", self.lang) if tr("payroll.open", self.lang) != "payroll.open" else "Öffnen", self)
        act_payroll.triggered.connect(lambda: PayrollDialog(self.session_factory, user_id=self.user_id, lang=self.lang, is_admin=self._is_admin, parent=self).exec())
        menu_payroll.addAction(act_payroll)

        # Werkzeuge
        if self._role in ("ADMIN","HR"):
            menu_tools = menubar.addMenu(tr("tools.menu", self.lang) if tr("tools.menu", self.lang) != "tools.menu" else "Werkzeuge")

            act_backup = QAction(tr("tools.backup_restore", self.lang) if tr("tools.backup_restore", self.lang) != "tools.backup_restore" else "Backup / Restore", self)
            act_audit  = QAction(tr("tools.audit_log", self.lang) if tr("tools.audit_log", self.lang) != "tools.audit_log" else "Audit-Log", self)
            act_rules  = QAction("Zuschlagsregeln", self)
            act_wrules = QAction("Lohnregeln", self)
            act_logs   = QAction("Log-Viewer", self)

            menu_tools.addAction(act_backup); menu_tools.addAction(act_audit)
            menu_tools.addAction(act_rules);  menu_tools.addAction(act_wrules); menu_tools.addAction(act_logs)

            if HAS_ANALYTICS:
                act_analytics = QAction("Analytics / Statistik", self)
                menu_tools.addAction(act_analytics)
                act_analytics.triggered.connect(self._open_analytics)

            db_url = "sqlite:///workpay.db"
            act_backup.triggered.connect(lambda: BackupRestoreDialog(self.session_factory, db_url, self.user_id, self._is_admin, self.lang, self).exec())
            act_audit .triggered.connect(lambda: AuditLogDialog(self.session_factory, self.lang, self).exec())
            act_rules .triggered.connect(lambda: RulesDialog(self.session_factory, self.lang, self).exec())
            act_wrules.triggered.connect(lambda: WageRulesDialog(self.session_factory, current_user_id=self.user_id, is_admin_or_hr=True, lang=self.lang, parent=self).exec())
            act_logs  .triggered.connect(lambda: LogViewerDialog(self.session_factory, self.lang, self).exec())

        # Personal
        menu_hr = menubar.addMenu(tr("hr.menu", self.lang) if tr("hr.menu", self.lang) != "hr.menu" else "Personal")
        act_abs_req   = QAction(tr("hr.absence_req", self.lang) if tr("hr.absence_req", self.lang) != "hr.absence_req" else "Abwesenheit beantragen", self)
        act_abs_admin = QAction(tr("hr.absence_admin", self.lang) if tr("hr.absence_admin", self.lang) != "hr.absence_admin" else "Abwesenheiten verwalten", self)
        menu_hr.addAction(act_abs_req); menu_hr.addAction(act_abs_admin)
        is_hr_or_admin = self._role in ("ADMIN", "HR"); act_abs_admin.setEnabled(is_hr_or_admin)
        act_abs_req  .triggered.connect(lambda: AbsenceRequestDialog(self.session_factory, user_id=self.user_id, lang=self.lang, parent=self).exec())
        act_abs_admin.triggered.connect(lambda: AbsenceAdminDialog(self.session_factory, current_user_id=self.user_id, is_admin_or_hr=is_hr_or_admin, lang=self.lang, parent=self).exec())

        # Kalender als Startseite
        self.calendar = CalendarMainWidget(self.session_factory, user_id=self.user_id, lang=self.lang, is_admin=self._is_admin, parent=self)
        self.setCentralWidget(self.calendar)
        self.resize(1280, 840)

    # ---------- Aktionen ----------
    def _do_logout(self):
        self.logoutRequested.emit()
        self.close()

    def _open_my_profile(self):
        dlg = ProfileDialog(self.session_factory, user_id=self.user_id, lang=self.lang, parent=self); dlg.exec()

    def _open_user_admin(self):
        if not self._is_admin:
            QMessageBox.warning(self, tr("main.menu_admin", self.lang), "No permission."); return
        dlg = UserAdminDialog(self.session_factory, lang=self.lang, parent=self, current_user_id=self.user_id)
        dlg.showMaximized(); dlg.exec()

    def _open_analytics(self):
        if not HAS_ANALYTICS:
            QMessageBox.information(self, "Analytics", "Analytics-Modul nicht verfügbar."); return
        dlg = AnalyticsDialog(self.session_factory, self.user_id, self.lang, self)
        dlg.setWindowModality(Qt.NonModal); dlg.showMaximized(); dlg.show()
