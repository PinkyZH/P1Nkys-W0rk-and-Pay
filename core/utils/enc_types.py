# core/utils/enc_types.py
from datetime import date
from typing import Optional

from sqlalchemy.types import TypeDecorator, String

from core.security.crypto import encrypt, decrypt, is_encrypted


# Basistypen mit transparenter Ver-/Entschlüsselung

class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, length: int = 255, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.impl.length = length

    def process_bind_param(self, value: Optional[str], dialect):
        if value is None:
            return None
        # vermeide Doppelverschlüsselung
        if isinstance(value, str) and is_encrypted(value):
            return value
        return encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            pt = decrypt(value)
            return pt.decode("utf-8") if pt is not None else None
        except Exception:
            # Fallback: gib Original zurück (legacy Klartext)
            return value


class EncryptedText(EncryptedString):
    # identisch, nur größere Länge sinnvoll
    impl = String

    def __init__(self, *args, **kwargs):
        super().__init__(length=4096, *args, **kwargs)


class EncryptedDate(TypeDecorator):
    impl = String  # speichern als enc-String
    cache_ok = True

    def process_bind_param(self, value: Optional[date], dialect):
        if value is None:
            return None
        s = value.isoformat()
        return encrypt(s)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            pt = decrypt(value)
            s = pt.decode("utf-8")
            # robustes Parsen
            return date.fromisoformat(s)
        except Exception:
            # Fallback: versuche direkt zu parsen (legacy Klartext)
            try:
                return date.fromisoformat(str(value))
            except Exception:
                return None


class EncryptedFloat(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[float], dialect):
        if value is None:
            return None
        s = repr(float(value))
        return encrypt(s)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            pt = decrypt(value)
            return float(pt.decode("utf-8"))
        except Exception:
            try:
                return float(value)
            except Exception:
                return None
