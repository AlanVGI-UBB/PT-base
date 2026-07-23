import hashlib
import time

import jwt

from app.core.config import get_settings

_ALGORITHM = "HS256"


def crear_token(rut: str) -> str:
    secret = get_settings().JWT_SECRET
    payload = {"rut": rut, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def verificar_token(token: str) -> str | None:
    secret = get_settings().JWT_SECRET
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
        return payload.get("rut")
    except jwt.InvalidTokenError:
        return None


def hash_password(password: str) -> str:
    return hashlib.sha256((password + "puente_lsch_salt").encode()).hexdigest()
