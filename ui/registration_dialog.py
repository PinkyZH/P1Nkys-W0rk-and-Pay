from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QHBoxLayout, QPushButton, QMessageBox, QDateEdit
)
from PySide6.QtCore import QDate
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from languages import tr
from core.models import User, UserProfile
from core.services.auth_service import hash_password


class RegistrationDialog(QDialog):
    """
    Selbst-Registrierung mit Pflicht-/Optionalfeldern:
      Pflicht: Benutzername*, Passwort*, Nachname*, Vorname*, Geburtstag*, Geschlecht*, E-Mail*, Telefon*
      Optional: Adresse, Postleitzahl, Ort, AHV-Nr.
      Sprache (für UI) wählbar.
    """
    def __init__(self, session_factory: sessionmaker, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.lang = lang
        self._created_username: str | None = None
        self.setWindowTitle(tr("reg.title", self.lang) if tr("reg.title", self.lang) != "reg.title" else "Registrierung")
        self._build()
        self.adjustSize()

    def _build(self):
        layout = QVBoxLayout(self)
        f = QFormLayout()

        # Pflichtfelder
        self.ed_user = QLineEdit()
        self.ed_pass = QLineEdit(); self.ed_pass.setEchoMode(QLineEdit.Password)
        self.ed_last = QLineEdit()
        self.ed_first = QLineEdit()
        self.dt_birth = QDateEdit(); self.dt_birth.setCalendarPopup(True); self.dt_birth.setDate(QDate(2000,1,1))
        self.cmb_gender = QComboBox()
        # gender choices
        gmap = {"male": tr("profile.gender.male", self.lang) if tr("profile.gender.male", self.lang)!="profile.gender.male" else "Männlich",
                "female": tr("profile.gender.female", self.lang) if tr("profile.gender.female", self.lang)!="profile.gender.female" else "Weiblich"}
        for key, label in gmap.items(): self.cmb_gender.addItem(label, key)
        self.ed_email = QLineEdit()
        self.ed_phone = QLineEdit()

        # Optional
        self.ed_addr = QLineEdit()
        self.ed_zip  = QLineEdit()
        self.ed_city = QLineEdit()
        self.ed_ahv  = QLineEdit()

        # UI Sprache
        self.cmb_lang = QComboBox(); self.cmb_lang.addItems(["de","en","sr"]); self.cmb_lang.setCurrentText(self.lang)

        star = " *"  # Pflichtmarkierung
        f.addRow((tr("reg.username", self.lang) if tr("reg.username", self.lang)!="reg.username" else "Benutzername")+star, self.ed_user)
        f.addRow((tr("reg.password", self.lang) if tr("reg.password", self.lang)!="reg.password" else "Passwort")+star, self.ed_pass)
        f.addRow((tr("reg.last_name", self.lang) if tr("reg.last_name", self.lang)!="reg.last_name" else "Nachname")+star, self.ed_last)
        f.addRow((tr("reg.first_name", self.lang) if tr("reg.first_name", self.lang)!="reg.first_name" else "Vorname")+star, self.ed_first)
        f.addRow((tr("reg.birthday", self.lang) if tr("reg.birthday", self.lang)!="reg.birthday" else "Geburtstag")+star, self.dt_birth)
        f.addRow((tr("reg.gender", self.lang) if tr("reg.gender", self.lang)!="reg.gender" else "Geschlecht")+star, self.cmb_gender)
        f.addRow((tr("reg.email", self.lang) if tr("reg.email", self.lang)!="reg.email" else "E-Mail")+star, self.ed_email)
        f.addRow((tr("reg.phone", self.lang) if tr("reg.phone", self.lang)!="reg.phone" else "Telefon")+star, self.ed_phone)
        f.addRow(tr("profile.address", self.lang) if tr("profile.address", self.lang)!="profile.address" else "Adresse", self.ed_addr)
        f.addRow(tr("profile.postcode", self.lang) if tr("profile.postcode", self.lang)!="profile.postcode" else "Postleitzahl", self.ed_zip)
        f.addRow(tr("profile.city", self.lang) if tr("profile.city", self.lang)!="profile.city" else "Ort", self.ed_city)
        f.addRow(tr("profile.ahv_number", self.lang) if tr("profile.ahv_number", self.lang)!="profile.ahv_number" else "AHV-Nr.", self.ed_ahv)
        f.addRow(tr("reg.language", self.lang) if tr("reg.language", self.lang)!="reg.language" else "Sprache", self.cmb_lang)

        layout.addLayout(f)

        row = QHBoxLayout()
        btn_create = QPushButton(tr("reg.create", self.lang) if tr("reg.create", self.lang) != "reg.create" else "Konto anlegen")
        btn_cancel = QPushButton(tr("reg.cancel", self.lang) if tr("reg.cancel", self.lang) != "reg.cancel" else "Abbrechen")
        row.addWidget(btn_create); row.addWidget(btn_cancel)
        layout.addLayout(row)

        btn_cancel.clicked.connect(self.reject)
        btn_create.clicked.connect(self._create)

    def _create(self):
        # Pflichtvalidierung
        uname = (self.ed_user.text() or "").strip()
        pw    = self.ed_pass.text() or ""
        last  = (self.ed_last.text() or "").strip()
        first = (self.ed_first.text() or "").strip()
        dob_q = self.dt_birth.date()
        gender= self.cmb_gender.currentData()
        email = (self.ed_email.text() or "").strip()
        phone = (self.ed_phone.text() or "").strip()
        lang  = self.cmb_lang.currentText()

        missing = []
        if not uname:  missing.append(tr("reg.username", self.lang) if tr("reg.username", self.lang)!="reg.username" else "Benutzername")
        if not pw:     missing.append(tr("reg.password", self.lang) if tr("reg.password", self.lang)!="reg.password" else "Passwort")
        if not last:   missing.append(tr("reg.last_name", self.lang) if tr("reg.last_name", self.lang)!="reg.last_name" else "Nachname")
        if not first:  missing.append(tr("reg.first_name", self.lang) if tr("reg.first_name", self.lang)!="reg.first_name" else "Vorname")
        if not (dob_q and dob_q.isValid()): missing.append(tr("reg.birthday", self.lang) if tr("reg.birthday", self.lang)!="reg.birthday" else "Geburtstag")
        if not gender: missing.append(tr("reg.gender", self.lang) if tr("reg.gender", self.lang)!="reg.gender" else "Geschlecht")
        if not email:  missing.append(tr("reg.email", self.lang) if tr("reg.email", self.lang)!="reg.email" else "E-Mail")
        if not phone:  missing.append(tr("reg.phone", self.lang) if tr("reg.phone", self.lang)!="reg.phone" else "Telefon")

        if missing:
            QMessageBox.warning(self, tr("reg.title", self.lang),
                                (tr("reg.missing", self.lang) if tr("reg.missing", self.lang)!="reg.missing" else "Pflichtfelder fehlen: ")
                                + ", ".join(missing))
            return

        # Optional
        addr  = (self.ed_addr.text() or "").strip() or None
        zipc  = (self.ed_zip.text() or "").strip() or None
        city  = (self.ed_city.text() or "").strip() or None
        ahv   = (self.ed_ahv.text() or "").strip() or None
        dob   = dob_q.toPython() if dob_q and dob_q.isValid() else None

        with self.session_factory() as s:
            # exists?
            if s.execute(select(User).where(User.username == uname)).scalar_one_or_none():
                QMessageBox.warning(self, tr("reg.title", self.lang),
                                    tr("reg.exists", self.lang) if tr("reg.exists", self.lang)!="reg.exists" else "Benutzername existiert bereits.")
                return

            u = User(username=uname, role="USER")
            if hasattr(u,"is_active"): u.is_active = True
            if hasattr(u,"active"):    u.active = True
            u.password_hash = hash_password(pw)
            s.add(u); s.flush()

            # Profil
            p = UserProfile(user_id=u.id)
            p.first_name = first; p.last_name = last
            p.birthday = dob; p.gender = gender
            p.email = email; p.phone = phone
            p.address = addr; p.postcode = zipc; p.city = city
            p.ahv_number = ahv
            p.locale = lang
            s.add(p); s.commit()
            self._created_username = uname

        QMessageBox.information(self, tr("reg.title", self.lang),
                                tr("reg.ok", self.lang) if tr("reg.ok", self.lang)!="reg.ok" else "Registrierung erfolgreich.")
        self.accept()

    def get_created_username(self) -> str:
        return self._created_username or ""
