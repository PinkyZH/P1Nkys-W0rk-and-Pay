import base64
import os
from typing import Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Wir kennzeichnen verschlüsselte Strings mit einem Header.
# Format: v1:<nonce_b64>:<ciphertext_b64>
CIPHER_PREFIX = "v1:"


# Schlüssel-Handling: Du kannst den Key aus ENV laden, hier simple Datei/ENV-Var-Strategie
# 32-Byte Key für AES-256-GCM
def _load_key() -> bytes:
    # 1) ENV hat Vorrang
    k = os.environ.get("WORKPAY_AES_KEY")
    if k:
        kb = base64.urlsafe_b64decode(k.encode("utf-8"))
        if len(kb) != 32:
            raise ValueError("WORKPAY_AES_KEY muss 32 Bytes (base64-url) entsprechen.")
        return kb
    # 2) Fallback: fix in dev (NIE für Prod)
    # Generiere EINMALIG und lege ihn als ENV/Config ab.
    return b"\x01" * 32


_KEY = _load_key()


def is_encrypted(value: Union[str, bytes, None]) -> bool:
    if value is None:
        return False
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except Exception:
            return False
    return isinstance(value, str) and value.startswith(CIPHER_PREFIX)


def encrypt(plaintext: Optional[Union[str, bytes]]) -> Optional[str]:
    if plaintext is None:
        return None
    if isinstance(plaintext, bytes):
        plaintext = plaintext.decode("utf-8", errors="ignore")

    aes = AESGCM(_KEY)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return f"{CIPHER_PREFIX}{base64.urlsafe_b64encode(nonce).decode('ascii')}:{base64.urlsafe_b64encode(ct).decode('ascii')}"


def decrypt(ciphertext: Optional[Union[str, bytes]]) -> Optional[bytes]:
    if ciphertext is None:
        return None

    # Fallback: schon Klartext? -> unverändert zurückgeben
    if isinstance(ciphertext, bytes):
        try:
            s = ciphertext.decode("utf-8")
        except Exception:
            # nicht decodierbar => kein verschlüsseltes Format -> gib Bytes zurück
            return ciphertext
    else:
        s = str(ciphertext)

    if not is_encrypted(s):
        # Rückwärtskompatibilität: alter Datensatz im Klartext
        return s.encode("utf-8", errors="ignore")

    try:
        # erwartetes Format: v1:<nonce_b64>:<ct_b64>
        parts = s.split(":")
        if len(parts) != 3 or parts[0] != "v1":
            # unbekanntes Label -> wie Klartext behandeln
            return s.encode("utf-8", errors="ignore")

        _, n_b64, ct_b64 = parts
        nonce = base64.urlsafe_b64decode(n_b64.encode("ascii"))
        ct = base64.urlsafe_b64decode(ct_b64.encode("ascii"))

        aes = AESGCM(_KEY)
        pt = aes.decrypt(nonce, ct, associated_data=None)
        return pt
    except Exception:
        # Fallback: wenn wir es nicht lesen können, behandle es defensiv als Klartext
        return s.encode("utf-8", errors="ignore")
