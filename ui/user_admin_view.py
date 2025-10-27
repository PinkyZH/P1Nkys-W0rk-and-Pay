from __future__ import annotations
from datetime import date as _date, datetime as _dt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from languages import tr
from core.models import User, UserProfile
from .user_edit_dialog import UserEditDialog
from ui.window_flags import apply_window_controls

from PySide6.QtWidgets import QAbstractItemView
from core.services.user_service import delete_user
from .registration_dialog import RegistrationDialog
class UserAdminDialog(QDialog):
    """
    Benutzerverwaltung (Admin) – Spaltenreihenfolge:
    ID | Benutzername | Rolle | Aktiv | Letzter Login | Sprache | Name | Geburtstag | Telefon | E-Mail | Mitarbeiter-ID | Arbeitgeber | AHV-Nr.
    """

    COL_ID=0; COL_USERNAME=1; COL_ROLE=2; COL_ACTIVE=3; COL_LASTLOGIN=4; COL_LOCALE=5
    COL_NAME=6; COL_BDAY=7; COL_PHONE=8; COL_EMAIL=9; COL_EMP_ID=10; COL_EMPLOYER=11; COL_AHV=12

    def __init__(self, session_factory: sessionmaker, lang: str="de", parent=None, current_user_id: int | None=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.lang = lang
        self.current_user_id = current_user_id
        self.setWindowTitle(tr("admin_users.title", self.lang) if tr("admin_users.title", self.lang) != "admin_users.title" else "Benutzerverwaltung")
        self.setSizeGripEnabled(True)
        self._build()
        self._reload()
        self.adjustSize()
        self.setSizeGripEnabled(True)  # manuelles Resizing bleibt möglich
        self.resize(max(self.sizeHint().width(), 1484),  # mind. ~980px Startbreite
                    self.sizeHint().height())

    def _build(self):
        apply_window_controls(self)
        root = QVBoxLayout(self)

        # Suche + Buttons
        row = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText(tr("admin_users.search", self.lang) if tr("admin_users.search", self.lang) != "admin_users.search" else "Suche")
        btn_refresh = QPushButton(tr("admin_users.refresh", self.lang) if tr("admin_users.refresh", self.lang) != "admin_users.refresh" else "Aktualisieren")
        btn_new     = QPushButton(tr("admin_users.new", self.lang) if tr("admin_users.new", self.lang) != "admin_users.new" else "Neu")
        btn_edit    = QPushButton(tr("admin_users.edit", self.lang) if tr("admin_users.edit", self.lang) != "admin_users.edit" else "Bearbeiten")
        btn_delete  = QPushButton(tr("admin_users.delete", self.lang) if tr("admin_users.delete", self.lang) != "admin_users.delete" else "Löschen")
        row.addWidget(self.ed_search); row.addWidget(btn_refresh); row.addWidget(btn_new); row.addWidget(btn_edit); row.addWidget(btn_delete)
        root.addLayout(row)

        # Tabelle
        headers = [
            "ID",
            tr("admin_users.username", self.lang) if tr("admin_users.username", self.lang) != "admin_users.username" else "Benutzername",
            tr("admin_users.role", self.lang) if tr("admin_users.role", self.lang) != "admin_users.role" else "Rolle",
            tr("admin_users.active", self.lang) if tr("admin_users.active", self.lang) != "admin_users.active" else "Aktiv",
            tr("admin_users.last_login", self.lang) if tr("admin_users.last_login", self.lang) != "admin_users.last_login" else "Letzter Login",
            tr("admin_users.locale", self.lang) if tr("admin_users.locale", self.lang) != "admin_users.locale" else "Sprache",
            tr("admin_users.first_name", self.lang) if tr("admin_users.first_name", self.lang) != "admin_users.first_name" else "Vorname",
            tr("admin_users.last_name", self.lang) if tr("admin_users.last_name", self.lang) != "admin_users.last_name" else "Nachname",
            tr("admin_users.birthday", self.lang) if tr("admin_users.birthday", self.lang) != "admin_users.birthday" else "Geburtstag",
            tr("admin_users.phone", self.lang) if tr("admin_users.phone", self.lang) != "admin_users.phone" else "Telefon",
            tr("admin_users.email", self.lang) if tr("admin_users.email", self.lang) != "admin_users.email" else "E-Mail",
            tr("profile.employee_id", self.lang) if tr("profile.employee_id", self.lang) != "profile.employee_id" else "Mitarbeiter-ID",
            tr("profile.employer", self.lang) if tr("profile.employer", self.lang) != "profile.employer" else "Arbeitgeber",
            tr("profile.ahv_number", self.lang) if tr("profile.ahv_number", self.lang) != "profile.ahv_number" else "AHV-Nr."
        ]

        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.SingleSelection)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        # Signals
        btn_refresh.clicked.connect(self._reload)
        btn_new.clicked.connect(self._new)
        btn_edit.clicked.connect(self._edit_selected)
        btn_delete.clicked.connect(self._delete_selected)
        self.ed_search.textChanged.connect(self._reload)

    def _reload(self):
        q = (self.ed_search.text() or "").strip().lower()

        with self.session_factory() as s:
            users = s.execute(select(User).order_by(User.id.asc())).scalars().all()
            profs = {p.user_id: p for p in s.execute(select(UserProfile)).scalars().all()}

        self.table.setRowCount(0)

        for u in users:
            p = profs.get(u.id)

            # "Letzter Login" sauber formatieren
            ll = getattr(u, "last_login", None)
            if isinstance(ll, _dt):
                last_login_text = ll.strftime("%Y-%m-%d %H:%M")
            elif ll:
                last_login_text = str(ll)
            else:
                last_login_text = ""

            row = [
                str(u.id),
                u.username or "",
                (u.role or "").upper(),
                "1" if getattr(u, "is_active", True) else "0",
                last_login_text,
                (p.locale if p else "") or "",
                (p.first_name if p else "") or "",
                (p.last_name if p else "") or "",
                (p.birthday.isoformat() if (p and p.birthday) else ""),
                (p.phone or "") if p else "",
                (p.email or "") if p else "",
                (str(p.employee_id) if (p and p.employee_id is not None) else ""),
                (p.employer or "") if p else "",
                (p.ahv_number or "") if p else "",
            ]

            # Filter
            if q and not any(q in (v or "").lower() for v in row):
                continue

            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, val in enumerate(row):
                it = QTableWidgetItem(val)
                if c == 0:  # ID in UserRole mitschleppen
                    it.setData(Qt.UserRole, u.id)
                self.table.setItem(r, c, it)

        self.table.resizeColumnsToContents()

    def _selected_ids(self) -> list[int]:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        ids = []
        for r in rows:
            it = self.table.item(r, 0)
            if it and it.data(Qt.ItemDataRole.UserRole) is not None:
                ids.append(int(it.data(Qt.ItemDataRole.UserRole)))
        return ids

    def _current_user_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0: return None
        it = self.table.item(r, 0)
        return int(it.data(Qt.UserRole)) if it else None

    def _new(self):
        dlg = RegistrationDialog(self.session_factory, lang=self.lang, parent=self)
        if dlg.exec():
            self._reload()

    def _load(self):
        hdr = self.table.horizontalHeader()
        sort_col, sort_order = hdr.sortIndicatorSection(), hdr.sortIndicatorOrder()
        sorting_on = self.table.isSortingEnabled()
        if sorting_on: self.table.setSortingEnabled(False)

        q = (self.edit_search.text() or "").strip().lower()
        with self.session_factory() as s:
            users = s.execute(select(User)).scalars().all()
            profs = {p.user_id: p for p in s.execute(select(UserProfile)).scalars().all()}

        rows=[]
        for u in users:
            p = profs.get(u.id)
            if q:
                cand = " ".join([u.username or "", (p.last_name or ""), (p.first_name or ""), (p.email or ""), (p.employer or "")]).lower()
                if q not in cand: continue
            rows.append((u,p))

        self.table.setRowCount(0)

        def _fmt_bday_and_sort(p: UserProfile | None)->tuple[str,int]:
            if not p or getattr(p,"birthday",None) is None: return ("",0)
            val = p.birthday
            if isinstance(val,_date): return (val.strftime("%Y-%m-%d"), int(val.strftime("%Y%m%d")))
            try:
                s=str(val)
                if len(s)==8 and s.isdigit(): return (f"{s[:4]}-{s[4:6]}-{s[6:8]}", int(s))
            except Exception: pass
            return (str(val),0)

        def _fmt_last_login(val)->tuple[str,str]:
            if val is None: return ("","")
            if isinstance(val,_dt): return (val.strftime("%Y-%m-%d %H:%M"), val.isoformat())
            s=str(val); return (s,s)

        for u,p in rows:
            r=self.table.rowCount(); self.table.insertRow(r)
            def set_item(c:int, txt:str, sort_val=None):
                it=QTableWidgetItem(txt if txt is not None else "")
                if sort_val is not None: it.setData(Qt.EditRole, sort_val)
                self.table.setItem(r,c,it)

            # Füllen in gewünschter Reihenfolge
            set_item(self.COL_ID, str(u.id), int(u.id))
            set_item(self.COL_USERNAME, u.username or "")
            set_item(self.COL_ROLE, (u.role or "").upper())
            active = getattr(u,"is_active", getattr(u,"active",True))
            set_item(self.COL_ACTIVE, "Ja" if active else "Nein", 1 if active else 0)
            disp_login, sort_login = _fmt_last_login(getattr(u,"last_login",None))
            set_item(self.COL_LASTLOGIN, disp_login, sort_login)
            set_item(self.COL_LOCALE, p.locale if p and p.locale else "")
            full_name = f"{(p.last_name or '')} {(p.first_name or '')}".strip() if p else ""
            set_item(self.COL_NAME, full_name)
            disp_bday, ymd = _fmt_bday_and_sort(p)
            set_item(self.COL_BDAY, disp_bday, ymd)
            set_item(self.COL_PHONE, p.phone if p else "")
            set_item(self.COL_EMAIL, p.email if p else "")
            set_item(self.COL_EMP_ID, p.employee_id if p else "")
            set_item(self.COL_EMPLOYER, p.employer if p else "")
            set_item(self.COL_AHV, getattr(p,"ahv_number","") if p else "")

        self.table.resizeColumnsToContents()
        if sorting_on:
            self.table.setSortingEnabled(True)
            try: self.table.sortItems(sort_col, sort_order)
            except Exception: pass

    # --- Aktionen (inkl. „Neuer Benutzer“) ---
    def _current_selected_user_id(self)->int|None:
        r=self.table.currentRow()
        if r<0: return None
        it=self.table.item(r,self.COL_ID)
        return int(it.text()) if it else None


    def _new_user(self):
        # Einfache Prompts für Username, Rolle, Passwort
        uname, ok = QInputDialog.getText(self, tr("admin_users.new", self.lang), tr("admin_users.username", self.lang) if tr("admin_users.username", self.lang)!="admin_users.username" else "Benutzername:")
        if not ok or not uname.strip(): return
        role, ok = QInputDialog.getText(self, tr("admin_users.new", self.lang), tr("admin_users.role", self.lang) if tr("admin_users.role", self.lang)!="admin_users.role" else "Rolle (USER/HR/ADMIN):")
        if not ok or not role.strip(): role="USER"
        role = role.strip().upper()
        if role not in ("USER","HR","ADMIN"): role="USER"
        pw, ok = QInputDialog.getText(self, tr("admin_users.new", self.lang), "Temporäres Passwort:")
        if not ok or not pw: return

        from core.services.log_service import log_error
        try:
            with self.session_factory() as s:
                # existiert?
                if s.execute(select(User).where(User.username==uname)).scalar_one_or_none():
                    QMessageBox.warning(self, tr("admin_users.title", self.lang), "Benutzername existiert bereits.")
                    return
                u = User(username=uname, role=role)
                # Aktiv setzen
                if hasattr(u,"is_active"): u.is_active=True
                if hasattr(u,"active"): u.active=True
                # Must change PW on first login (falls Feld vorhanden)
                if hasattr(u,"must_change_password"): u.must_change_password=True

                # Passwort setzen (robust)
                try:
                    from core.services.auth_service import set_password as _set_pw
                    _set_pw(s, u, pw)
                except Exception:
                    try:
                        from core.services.auth_service import hash_password as _hash
                        u.password_hash = _hash(pw)
                    except Exception as ex:
                        log_error("Passwort-Hashing fehlgeschlagen", exc=ex)
                        u.password_hash = None  # als Notfall: wird beim ersten Login zum Reset gezwungen

                s.add(u); s.flush()
                # Profil anlegen
                if not s.execute(select(UserProfile).where(UserProfile.user_id==u.id)).scalar_one_or_none():
                    s.add(UserProfile(user_id=u.id))
                s.commit()
            QMessageBox.information(self, tr("admin_users.title", self.lang), "Benutzer angelegt.")
            self._load()
        except Exception as ex:
            log_error("Fehler beim Anlegen eines neuen Benutzers", exc=ex)
            QMessageBox.critical(self, tr("admin_users.title", self.lang), str(ex))

    def _edit_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        for uid in ids:
            dlg = UserEditDialog(self.session_factory, user_id=uid, lang=self.lang, parent=self)
            if dlg.exec():
                pass
        self._reload()

    def _delete_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        if QMessageBox.question(self, self.windowTitle(), f"{len(ids)} {tr('admin_users.delete', self.lang) if tr('admin_users.delete', self.lang)!='admin_users.delete' else 'löschen'}?") != QMessageBox.StandardButton.Yes:
            return
        with self.session_factory() as s:
            for uid in ids:
                delete_user(s, uid)
        self._reload()
