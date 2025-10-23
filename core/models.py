
from __future__ import annotations
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Date, Time, Float, func, Index, CheckConstraint
)
from sqlalchemy.orm import relationship  # <- KORREKT!

from .db import Base
# --- v2.5: Audit-Log ---
from sqlalchemy import Text

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(16), nullable=False, default="USER")
    is_active = Column(Boolean, nullable=False, default=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime, nullable=True)
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    # Basic
    locale = Column(String(8), nullable=True)
    gender = Column(String(16), nullable=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    birthday = Column(Date, nullable=True)
    civil_status = Column(String(32), nullable=True)
    permit_status = Column(String(64), nullable=True)
    region_code = Column(String(32), nullable=True)
    address = Column(String(128), nullable=True)
    postcode = Column(String(16), nullable=True)
    city = Column(String(64), nullable=True)
    email = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)
    avatar_path = Column(String(256), nullable=True)

    # Admin-only / employment
    employee_id = Column(String(32), nullable=True)
    employee_code = Column(String(32), nullable=True)
    employer = Column(String(128), nullable=True)
    employment_start = Column(Date, nullable=True)

    # Wage (per-user)
    hourly_brutto = Column(Float, nullable=True, default=None)
    vac_pct = Column(Float, nullable=True, default=None)
    holiday_pct = Column(Float, nullable=True, default=None)
    thirteenth_pct = Column(Float, nullable=True, default=None)
    expenses_per_hour = Column(Float, nullable=True, default=None)
    ahv_pct = Column(Float, nullable=True, default=None)
    nbu_pct = Column(Float, nullable=True, default=None)
    ktg_pct = Column(Float, nullable=True, default=None)
    bvg_pct = Column(Float, nullable=True, default=None)
    lgav_fixed_monthly = Column(Float, nullable=True, default=None)
    weekly_hours = Column(Float, nullable=True, default=None)

    # Bank
    bank_name = Column(String(128), nullable=True)
    bank_address = Column(String(128), nullable=True)
    bank_zip = Column(String(16), nullable=True)
    bank_city = Column(String(64), nullable=True)
    bank_country = Column(String(64), nullable=True)
    account_number = Column(String(64), nullable=True)
    iban = Column(String(34), nullable=True)
    ahv_number = Column(String(64), nullable=True)

    user = relationship("User", back_populates="profile")

    # Backwards-compat property if older code used 'hourly_rate'
    @property
    def hourly_rate(self):
        return self.hourly_brutto
    @hourly_rate.setter
    def hourly_rate(self, v):
        self.hourly_brutto = v


# --- Step 2.1/2.2: Work entries for calendar ---
class WorkEntry(Base):
    __tablename__ = "work_entries"

    id = Column(Integer, primary_key=True)

    # WICHTIG: hier KEIN index=True lassen!
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)

    start_time = Column(Time)
    end_time   = Column(Time)
    break_minutes = Column(Integer, default=0)
    hours = Column(Float, default=0.0)
    entry_type = Column(String(20))     # WORK / SICK / VACATION / ...
    note = Column(String(255))
    location = Column(String(255))

    __table_args__ = (
        # genau EIN zusammengesetzter Index:
        Index("ix_work_entries_user_date", "user_id", "date"),
    )

    user = relationship("User", back_populates="work_entries")

class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period_year = Column(Integer, nullable=False, index=True)
    period_month = Column(Integer, nullable=False, index=True)
    # … weitere Spalten …
    __table_args__ = (
        Index("ix_payroll_user_period", "user_id", "period_year", "period_month"),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(64), nullable=False)              # z.B. CREATE, UPDATE, DELETE, LOGIN, BACKUP, RESTORE
    entity = Column(String(64), nullable=False)              # z.B. WorkEntry, UserProfile, PayrollRun, System
    entity_id = Column(String(64), nullable=True)            # optional: ID als Text
    before_json = Column(Text, nullable=True)                # JSON→ Zustand davor
    after_json = Column(Text, nullable=True)                 # JSON→ Zustand danach
    ip_addr = Column(String(64), nullable=True)              # optional, falls du später eine IP loggen willst
    created_at = Column(DateTime, nullable=False, default=func.now())

class AbsenceRequest(Base):
    __tablename__ = "absence_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(32), nullable=False)      # VACATION / SICK / HOLIDAY / OFF / APPOINTMENT / HOSPITAL / CUSTOM:...
    custom_label = Column(String(128), nullable=True)
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="PENDING")  # PENDING/APPROVED/DENIED
    decided_by = Column(Integer, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

# --- v2.7: Benachrichtigungen ---
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String(128), nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())


# Prozentfelder (0..100) – weiche Validierung (SQLite ignoriert streng, aber dokumentiert Intent):
UserProfile.__table__.append_constraint(CheckConstraint("vac_pct       >= 0 AND vac_pct       <= 100", name="ck_profile_vac_pct"))
UserProfile.__table__.append_constraint(CheckConstraint("holiday_pct   >= 0 AND holiday_pct   <= 100", name="ck_profile_holiday_pct"))
UserProfile.__table__.append_constraint(CheckConstraint("thirteenth_pct>= 0 AND thirteenth_pct<= 100", name="ck_profile_13_pct"))
UserProfile.__table__.append_constraint(CheckConstraint("ahv_pct       >= 0 AND ahv_pct       <= 100", name="ck_profile_ahv_pct"))
UserProfile.__table__.append_constraint(CheckConstraint("nbu_pct       >= 0 AND nbu_pct       <= 100", name="ck_profile_nbu_pct"))
UserProfile.__table__.append_constraint(CheckConstraint("ktg_pct       >= 0 AND ktg_pct       <= 100", name="ck_profile_ktg_pct"))
UserProfile.__table__.append_constraint(CheckConstraint("bvg_pct       >= 0 AND bvg_pct       <= 100", name="ck_profile_bvg_pct"))


