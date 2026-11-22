from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.auth import crear_token, obtener_rut, verificar_password
from app.core.db import get_connection

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    rut: str
    password: str


class LoginResponse(BaseModel):
    token: str
    rut: str
    nombre: str
    apellido: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    conn = get_connection()
    row = conn.execute(
        "SELECT rut, password_hash, nombre, apellido FROM usuario WHERE rut = ?",
        (req.rut,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="RUT o contraseña inválidos")

    if not verificar_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="RUT o contraseña inválidos")

    token = crear_token(req.rut)
    return LoginResponse(
        token=token,
        rut=row["rut"],
        nombre=row["nombre"],
        apellido=row["apellido"],
    )


@router.get("/usuario/me")
def usuario_me(request: Request):
    rut = obtener_rut(request)
    conn = get_connection()
    row = conn.execute(
        "SELECT rut, nombre, apellido FROM usuario WHERE rut = ?",
        (rut,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    inscripciones = conn.execute(
        "SELECT i.curso_id, c.cod_ramo, c.nombre, i.seccion, i.puede_capturar "
        "FROM inscripcion i "
        "JOIN curso c ON c.id = i.curso_id "
        "WHERE i.rut = ?",
        (rut,),
    ).fetchall()

    return {
        "rut": row["rut"],
        "nombre": row["nombre"],
        "apellido": row["apellido"],
        "inscripciones": [
            {
                "curso_id": ins["curso_id"],
                "cod_ramo": ins["cod_ramo"],
                "nombre": ins["nombre"],
                "seccion": ins["seccion"],
                "puede_capturar": bool(ins["puede_capturar"]),
            }
            for ins in inscripciones
        ],
    }
