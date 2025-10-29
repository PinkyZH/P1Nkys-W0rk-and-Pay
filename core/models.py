from __future__ import annotations

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Date, Time, Float, Text, Index, func
)
from sqlalchemy.orm import relationship, synonym

# Verschlüsselte Typen
from core.utils.enc_types import EncryptedString, EncryptedText, EncryptedDate, EncryptedFloat
# Einheitliches Base aus core.db
from .db import Base


# =========================
# User
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    role = Column(String(20), default="USER")  # USER / HR / ADMIN
    is_active = Column(Boolean, default=True)
    password_hash = Column(String(255))
    must_change_password = Column(Boolean, default=False)
    last_login = Column(DateTime)

    # Beziehungen
    profile = relationship(
        "UserProfile",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    work_entries = relationship(
        "WorkEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    payroll_runs = relationship(
        "PayrollRun",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

# =========================
# UserProfile (verschlüsselt wo sinnvoll)
# =========================
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Persönliche Daten
    first_name = Column(EncryptedString, nullable=True)
    last_name = Column(EncryptedString, nullable=True)
    birthday = Column(EncryptedDate, nullable=True)
    gender = Column(String(20))  # male/female/diverse (nicht sensibel -> plain)
    civil_status = Column(String(50))
    permit_status = Column(String(100))
    locale = Column(String(5), default="de")  # de/en/sr

    # Kontakt/Adresse
    phone = Column(EncryptedString, nullable=True)
    email = Column(EncryptedString, nullable=True)
    address = Column(EncryptedText, nullable=True)
    postal_code = Column(EncryptedString, nullable=True)
    # Alias für Altcode, damit p.postcode UND p.postal_code funktionieren:
    postcode = synonym("postal_code")
    city = Column(EncryptedString, nullable=True)
    region_code = Column(String(50))  # optionaler Code (plain)

    # Arbeitgeber/Anstellung
    employer = Column(EncryptedString, nullable=True)
    employee_id = Column(EncryptedString, nullable=True)
    employee_code = Column(String(50))
    employment_start = Column(Date)

    # Bankdaten (sensibel -> verschlüsselt)
    iban = Column(EncryptedString, nullable=True)
    bank_name = Column(EncryptedString, nullable=True)
    bank_address = Column(EncryptedText, nullable=True)
    bank_zip = Column(EncryptedString, nullable=True)
    bank_city = Column(EncryptedString, nullable=True)
    bank_country = Column(EncryptedString, nullable=True)
    account_number = Column(EncryptedString, nullable=True)

    # AHV
    ahv_number = Column(EncryptedString, nullable=True)

    # Lohnparameter (dürfen verschlüsselt sein; Berechnungen passieren in Python)
    hourly_brutto = Column(EncryptedFloat, nullable=True)  # CHF/Std
    vac_pct = Column(EncryptedFloat, nullable=True)  # %
    holiday_pct = Column(EncryptedFloat, nullable=True)  # %
    thirteenth_pct = Column(EncryptedFloat, nullable=True)  # %
    expenses_per_hour = Column(EncryptedFloat, nullable=True)  # CHF/Std
    ahv_pct = Column(EncryptedFloat, nullable=True)  # %
    nbu_pct = Column(EncryptedFloat, nullable=True)  # %
    ktg_pct = Column(EncryptedFloat, nullable=True)  # %
    bvg_pct = Column(EncryptedFloat, nullable=True)  # %
    weekly_hours = Column(EncryptedFloat, nullable=True)  # z. B. 42
    lgav_fixed_monthly = Column(EncryptedFloat, nullable=True)  # CHF/Monat (optional)

    # Media / Avatar (Pfad – nicht sensibel)
    avatar_path = Column(String(255))

    user = relationship("User", back_populates="profile")


# =========================
# WorkEntry
# =========================
class WorkEntry(Base):
    __tablename__ = "work_entries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # für Filter/Analytics unverschlüsselt
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    break_minutes = Column(Integer, default=0)
    hours = Column(Float, default=0.0)
    entry_type = Column(String(32), nullable=True, index=True)

    # sensibel
    note = Column(EncryptedText, nullable=True)
    location = Column(EncryptedString, nullable=True)

    # optionale Overrides (plain reicht)
    hourly_override = Column(Float, nullable=True)  # optionaler Stundenlohn-Override
    pay_rate_override = Column(Float, nullable=True)  # 1.0=100%, 0.9=90%, 0.0=unbezahlt, -2.0=benutzerdefiniert
    overtime_hours = Column(Float, nullable=True)  # explizite Überstunden (optional)

    __table_args__ = (
        Index("ix_work_entries_user_date", "user_id", "date"),
    )

    user = relationship("User", back_populates="work_entries")


# =========================
# PayrollRun (Monatslauf je User)
# =========================
class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period_year = Column(Integer, nullable=False, index=True)
    period_month = Column(Integer, nullable=False, index=True)

    # Aggregierte Kennzahlen
    hours_total = Column(Float, default=0.0)
    entries_count = Column(Integer, default=0)

    # Summen
    gross_total = Column(Float, default=0.0)
    net_total = Column(Float, default=0.0)

    # Breakdown JSON
    type_breakdown_json = Column(Text)

    is_locked = Column(Boolean, default=False)
    locked_by = Column(Integer)  # user_id desjenigen, der abgeschlossen hat
    locked_at = Column(DateTime)

    __table_args__ = (
        Index("ix_payroll_user_period", "user_id", "period_year", "period_month"),
    )

    user = relationship("User", back_populates="payroll_runs")


# =========================
# AuditLog
# =========================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)

    action = Column(String(50), nullable=False)  # CREATE / UPDATE / DELETE
    entity = Column(String(100), nullable=False)  # z. B. "WorkEntry"
    entity_id = Column(String(64))
    before_json = Column(Text)  # JSON
    after_json = Column(Text)  # JSON
    ip_addr = Column(String(64))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user_created", "user_id", "created_at"),
    )
