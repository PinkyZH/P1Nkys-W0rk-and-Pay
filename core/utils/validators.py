
from __future__ import annotations
import re

_email_re = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_phone_re = re.compile(r'^[0-9+()\-\s]{6,}$')
_postcode_re = re.compile(r'^[0-9A-Za-z\-\s]{2,10}$')

def validate_email(value: str|None) -> bool:
    if not value: return True
    return bool(_email_re.match(value))

def validate_phone(value: str|None) -> bool:
    if not value: return True
    return bool(_phone_re.match(value))

def validate_postcode(value: str|None) -> bool:
    if not value: return True
    return bool(_postcode_re.match(value))

# Basic IBAN check (letter->number replacement + mod97)
def validate_iban(iban: str|None) -> bool:
    if not iban: return True
    iban = iban.replace(" ", "").upper()
    if len(iban) < 4: return False
    # move first 4 chars to end, convert letters
    rearr = iban[4:] + iban[:4]
    def char_value(c):
        if c.isdigit(): return int(c)
        return ord(c) - 55  # 'A' -> 10
    digits = ""
    for ch in rearr:
        if ch.isalnum():
            if ch.isdigit():
                digits += ch
            else:
                digits += str(char_value(ch))
        else:
            return False
    # compute mod 97 iteratively
    remainder = 0
    for i in range(0, len(digits), 9):
        block = int(str(remainder) + digits[i:i+9])
        remainder = block % 97
    return remainder == 1
