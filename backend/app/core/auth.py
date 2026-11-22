import base64
import hashlib
import hmac
import os
import time

import jwt
from fastapi import HTTPException, Request

from app.core.config import get_settings

_ALGORITHM = "HS256"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def crear_token(rut: str) -> str:
    settings = get_settings()
    payload = {"rut": rut, "exp": int(time.time()) + settings.JWT_EXP_MIN * 60}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def verificar_token(token: str) -> str | None:
    secret = get_settings().JWT_SECRET
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
        return payload.get("rut")
    except jwt.InvalidTokenError:
        return None


def obtener_rut(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    rut = verificar_token(header[7:].strip())
    if not rut:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return rut


def hash_password(password: str) -> str:
    sal = os.urandom(16)
    derivada = hashlib.scrypt(
        password.encode("utf-8"),
        salt=sal,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    sal_b64 = base64.b64encode(sal).decode("ascii")
    der_b64 = base64.b64encode(derivada).decode("ascii")
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${sal_b64}${der_b64}"


def verificar_password(password: str, guardado: str) -> bool:
    partes = (guardado or "").split("$")
    if len(partes) != 6 or partes[0] != "scrypt":
        return False
    try:
        n = int(partes[1])
        r = int(partes[2])
        p = int(partes[3])
        sal = base64.b64decode(partes[4].encode("ascii"), validate=True)
        esperada = base64.b64decode(partes[5].encode("ascii"), validate=True)
        derivada = hashlib.scrypt(
            password.encode("utf-8"),
            salt=sal,
            n=n,
            r=r,
            p=p,
            dklen=len(esperada),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derivada, esperada)
