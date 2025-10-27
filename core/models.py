from __future__ import annotations
from datetime import datetime, date, time

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Date, Time, Float, Text, Index, func
)
from sqlalchemy.orm import relationship

# Nur EIN Base – aus core.db importieren!
from .db import Base


# -----------------------------
# User
# -----------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    role = Column(String(20), default="USER")               # USER / HR / ADMIN
    is_active = Column(Boolean, default=True)               # manche Codes nutzen 'active'; wir nehmen is_active
    password_hash = Column(String(255))
    must_change_password = Column(Boolean, default=False)
    last_login = Column(DateTime)

    # Gegenbeziehungen
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

    profile = relationship(
        "UserProfile",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # in class User(Base):
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    absences = relationship(
        "AbsenceRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # Abwesenheiten, die dieser User BEANTRAGT hat
    absences = relationship(
        "AbsenceRequest",
        foreign_keys="AbsenceRequest.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Abwesenheiten, die dieser User ENTSCHIEDEN hat (HR/Admin)
    absences_decided = relationship(
        "AbsenceRequest",
        foreign_keys="AbsenceRequest.decided_by",
        back_populates="decider",
        lazy="selectin",
    )

# -----------------------------
# UserProfile
# -----------------------------
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Admin-/Beschäftigungsdaten
    employee_id = Column(String(50))
    employee_code = Column(String(50))
    employer = Column(String(150))
    employment_start = Column(Date)

    # Persönlich
    first_name = Column(String(100))
    last_name = Column(String(100))
    birthday = Column(Date)
    gender = Column(String(20))             # male/female ...
    civil_status = Column(String(50))
    permit_status = Column(String(100))
    locale = Column(String(5), default="de")  # de/en/sr

    # Kontakt/Adresse
    region_code = Column(String(50))
    address = Column(String(255))
    postcode = Column(String(20))
    city = Column(String(100))
    email = Column(String(150))
    phone = Column(String(50))

    # Bank
    iban = Column(String(60))
    bank_name = Column(String(150))
    bank_address = Column(String(255))
    bank_zip = Column(String(20))
    bank_city = Column(String(100))
    bank_country = Column(String(80))
    account_number = Column(String(60))

    # AHV
    ahv_number = Column(String(50))

    # Lohnparameter (individuell mit Fallback auf Defaults)
    hourly_brutto = Column(Float)           # CHF/Std
    vac_pct = Column(Float)                 # %
    holiday_pct = Column(Float)             # %
    thirteenth_pct = Column(Float)          # %
    expenses_per_hour = Column(Float)       # CHF/Std
    ahv_pct = Column(Float)                 # %
    nbu_pct = Column(Float)                 # %
    ktg_pct = Column(Float)                 # %
    bvg_pct = Column(Float)                 # %
    weekly_hours = Column(Float)            # z. B. 42

    # Media / Avatar
    avatar_path = Column(String(255))

    user = relationship("User", back_populates="profile")
    lgav_fixed_monthly = Column(Float)  # CHF/Monat (optional)


# -----------------------------
# WorkEntry
# -----------------------------
class WorkEntry(Base):
    __tablename__ = "work_entries"

    id = Column(Integer, primary_key=True)

    # KEINE index=True hier – wir nutzen den zusammengesetzten Index unten
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)

    start_time = Column(Time)
    end_time = Column(Time)
    break_minutes = Column(Integer, default=0)
    hours = Column(Float, default=0.0)
    entry_type = Column(String(20))         # WORK / SICK / VACATION / HOLIDAY / OFF / OTHER ...
    note = Column(String(255))
    location = Column(String(255))
    hourly_override = Column(Float)  # optionaler Stundenlohn-Override
    pay_rate_override = Column(Float)  # optional, 1.0=100%, 0.9=90% ... -1 für "Unbezahlt"

    __table_args__ = (
        Index("ix_work_entries_user_date", "user_id", "date"),
    )

    user = relationship("User", back_populates="work_entries")
    # in class WorkEntry(Base):
    hourly_override = Column(Float)  # optionaler Std.-Lohn (Override)
    pay_rate_override = Column(
        Float)  # Bezahlungs-Override (1.0=100%, 0.0=unbez., -2.0 benutzerdefiniert -> Dialog setzt Wert)
    overtime_hours = Column(Float)  # explizit erfasste Überstunden (optional)

# -----------------------------
# PayrollRun (Monatslauf je User)
# -----------------------------
class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period_year = Column(Integer, nullable=False, index=True)
    period_month = Column(Integer, nullable=False, index=True)

    # Aggregierte Kennzahlen
    hours_total = Column(Float, default=0.0)
    entries_count = Column(Integer, default=0)

    # Summen (Brutto/Netto)
    gross_total = Column(Float, default=0.0)
    net_total = Column(Float, default=0.0)

    # Breakdown nach Typen als JSON (z. B. {"WORK":{"hours":..., "count":...}, "SICK":...})
    type_breakdown_json = Column(Text)

    is_locked = Column(Boolean, default=False)
    locked_by = Column(Integer)         # user_id desjenigen, der abgeschlossen hat
    locked_at = Column(DateTime)

    __table_args__ = (
        Index("ix_payroll_user_period", "user_id", "period_year", "period_month"),
    )

    user = relationship("User", back_populates="payroll_runs")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    body  = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)

    action = Column(String(50), nullable=False)       # z.B. CREATE / UPDATE / DELETE
    entity = Column(String(100), nullable=False)      # z.B. "WorkEntry"
    entity_id = Column(String(64))                    # z.B. "123"
    before_json = Column(Text)                        # JSON-String
    after_json  = Column(Text)                        # JSON-String
    ip_addr = Column(String(64))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user_created", "user_id", "created_at"),
    )

class AbsenceRequest(Base):
    __tablename__ = "absence_requests"

    id = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True,  index=True)

    type = Column(String(50), nullable=False)
    custom_label = Column(String(100))
    date_from = Column(Date, nullable=False)
    date_to   = Column(Date, nullable=False)
    reason = Column(Text)
    status = Column(String(20), default="PENDING", nullable=False)

    decided_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # eindeutige FK-Zuordnung:
    user    = relationship("User", foreign_keys=[user_id],    back_populates="absences")
    decider = relationship("User", foreign_keys=[decided_by], back_populates="absences_decided")

    __table_args__ = (
        Index("ix_absence_user_fromto", "user_id", "date_from", "date_to"),
    )