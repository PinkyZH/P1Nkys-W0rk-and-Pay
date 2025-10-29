# core/migrate_encrypt.py
from __future__ import annotations

from sqlalchemy import select

from core.models import UserProfile, WorkEntry


def needs_encryption_probe(val):
    # Wenn Feld bereits b"\x76\x31..." (b'v1' Prefix) ist -> schon verschlüsselt
    if val is None: return False
    if isinstance(val, (bytes, bytearray)):
        return val[:2] != b"v1"
    # String etc. -> unverschlüsselt
    return True


def migrate_encrypt(session):
    """Liest unverschlüsselte Werte und schreibt sie über ORM neu,
    wodurch TypeDecorator sie verschlüsselt bindet."""
    # UserProfile
    profs = session.execute(select(UserProfile)).scalars().all()
    changed = 0
    for p in profs:
        dirty = False
        for attr in (
        "first_name", "last_name", "birthday", "phone", "email", "address", "postal_code", "city", "ahv_number",
        "employer", "employee_id"):
            try:
                v = getattr(p, attr)
            except Exception:
                continue
            # Wenn Spalte bereits EncryptedType nutzt, reicht ein Neusetzen
            if v is not None:
                setattr(p, attr, v)
                dirty = True
        if dirty:
            changed += 1

    # WorkEntry
    ents = session.execute(select(WorkEntry)).scalars().all()
    for e in ents:
        dirty = False
        for attr in ("note", "location"):
            v = getattr(e, attr, None)
            if v is not None:
                setattr(e, attr, v)
                dirty = True
        if dirty:
            changed += 1

    if changed:
        session.commit()
    return changed
