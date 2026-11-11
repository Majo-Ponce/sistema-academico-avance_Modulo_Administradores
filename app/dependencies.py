from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.database import conexion_lectura
from app.security import decode_access_token

# Lee el encabezado "Authorization: Bearer <token>" que envía fetchAuth()
# (frontend/auth.js).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ROL_ADMIN = "ADMIN"
ROL_DOCENTE = "DOCENTE"


def obtener_usuario_actual(token: str = Depends(oauth2_scheme)) -> dict:
    """Valida el JWT y devuelve la cuenta activa asociada."""
    error_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise error_credenciales

    nombre_usuario = payload.get("sub")
    rol_token = str(payload.get("rol") or "").strip().upper()
    id_cuenta = payload.get("uid")
    if (
        (not nombre_usuario and not id_cuenta)
        or rol_token not in {ROL_ADMIN, ROL_DOCENTE}
    ):
        raise error_credenciales

    with conexion_lectura() as conexion:
        filtro = (
            "id = ?"
            if isinstance(id_cuenta, int) and id_cuenta > 0
            else "TRIM(usuario) = TRIM(?) COLLATE NOCASE"
        )
        identificador = id_cuenta if filtro == "id = ?" else nombre_usuario
        if rol_token == ROL_ADMIN:
            fila = conexion.execute(
                f"""
                SELECT id, usuario, nombre AS nombre_completo, email, activo,
                       debe_cambiar_password, 'ADMIN' AS rol, NULL AS docente_id
                FROM administradores
                WHERE {filtro}
                """,
                (identificador,),
            ).fetchone()
        else:
            fila = conexion.execute(
                f"""
                SELECT * FROM usuarios
                WHERE {filtro}
                  AND UPPER(TRIM(rol)) = 'DOCENTE'
                """,
                (identificador,),
            ).fetchone()

    if fila is None or not fila["activo"]:
        raise error_credenciales
    usuario = dict(fila)
    if usuario.get("debe_cambiar_password"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe cambiar su contraseña antes de continuar",
        )
    return usuario


def requiere_rol(*roles_permitidos: str):
    """Uso: Depends(requiere_rol("ADMIN")) o Depends(requiere_rol("DOCENTE"))."""

    roles_normalizados = {rol.strip().upper() for rol in roles_permitidos}

    def verificador(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
        # Se normaliza el rol guardado en la fila (mayúsculas/espacios) antes
        # de compararlo, para que un dato cargado o editado manualmente en la
        # base de datos (p. ej. "docente" en vez de "DOCENTE") no provoque un
        # 403 incorrecto para un usuario que sí tiene el rol correcto.
        rol_usuario = str(usuario.get("rol") or "").strip().upper()
        if rol_usuario not in roles_normalizados:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes para esta acción",
            )
        return usuario

    return verificador


solo_admin = requiere_rol(ROL_ADMIN)
solo_docente = requiere_rol(ROL_DOCENTE)
