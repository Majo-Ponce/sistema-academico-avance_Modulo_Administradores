from fastapi import APIRouter, Depends, HTTPException

from app.database import (
    CLAVE_ADMIN_INICIAL,
    CLAVE_DOCENTE_INICIAL,
    conexion_lectura,
    hash_clave,
    transaccion,
)
from app.dependencies import oauth2_scheme
from app.schemas import (
    CambioPasswordEntrada,
    LoginRespuesta,
    MensajeRespuesta,
    UsuarioLogin,
)
from app.security import create_access_token, decode_access_token
from jose import JWTError


router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _buscar_cuenta(conexion, identificador: str):
    administrador = conexion.execute(
        """
        SELECT id, usuario, nombre, email, clave_hash, activo,
               debe_cambiar_password
        FROM administradores
        WHERE TRIM(usuario) = TRIM(?) COLLATE NOCASE
           OR TRIM(email) = TRIM(?) COLLATE NOCASE
        ORDER BY CASE WHEN TRIM(email) = TRIM(?) COLLATE NOCASE THEN 0 ELSE 1 END
        LIMIT 1
        """,
        (identificador, identificador, identificador),
    ).fetchone()
    if administrador is not None:
        return {
            "id": administrador["id"],
            "usuario": administrador["usuario"],
            "nombre_completo": administrador["nombre"],
            "email": administrador["email"],
            "clave_hash": administrador["clave_hash"],
            "activo": administrador["activo"],
            "debe_cambiar_password": administrador["debe_cambiar_password"],
            "rol": "ADMIN",
            "docente_id": None,
        }

    docente = conexion.execute(
        """
        SELECT * FROM usuarios
        WHERE UPPER(TRIM(rol)) = 'DOCENTE'
          AND (
              TRIM(usuario) = TRIM(?) COLLATE NOCASE
              OR TRIM(COALESCE(email, '')) = TRIM(?) COLLATE NOCASE
          )
        ORDER BY CASE
            WHEN TRIM(COALESCE(email, '')) = TRIM(?) COLLATE NOCASE THEN 0
            ELSE 1
        END
        LIMIT 1
        """,
        (identificador, identificador, identificador),
    ).fetchone()
    return dict(docente) if docente is not None else None


@router.post("/login", response_model=LoginRespuesta)
def iniciar_sesion(datos: UsuarioLogin):
    with conexion_lectura() as conexion:
        fila = _buscar_cuenta(conexion, datos.usuario)

    if fila is None or fila["clave_hash"] != hash_clave(datos.clave):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if not fila["activo"]:
        raise HTTPException(status_code=403, detail="Este usuario está inactivo")

    docente_id = fila.get("docente_id")
    rol = str(fila["rol"]).strip().upper()
    clave_temporal = (
        CLAVE_ADMIN_INICIAL if rol == "ADMIN" else CLAVE_DOCENTE_INICIAL
    )
    debe_cambiar_password = bool(fila.get("debe_cambiar_password", 0)) and (
        fila["clave_hash"] == hash_clave(clave_temporal)
    )
    if not debe_cambiar_password and fila.get("debe_cambiar_password", 0):
        tabla = "administradores" if rol == "ADMIN" else "usuarios"
        with transaccion() as conexion:
            conexion.execute(
                f"""
                UPDATE {tabla}
                SET debe_cambiar_password = 0, cambiar_password = 0
                WHERE id = ?
                """,
                (fila["id"],),
            )
    if rol == "DOCENTE":
        with transaccion() as conexion:
            docente = None
            if docente_id:
                docente = conexion.execute(
                    "SELECT id, estado FROM docentes WHERE id = ?", (docente_id,)
                ).fetchone()
            else:
                docente = conexion.execute(
                    """
                    SELECT id, estado FROM docentes
                    WHERE LOWER(TRIM(correo)) = LOWER(TRIM(?))
                    """,
                    (fila.get("email") or "",),
                ).fetchone()
                if docente is None:
                    docente = conexion.execute(
                        """
                        SELECT id, estado FROM docentes
                        WHERE TRIM(nombres || ' ' || apellidos) =
                              TRIM(?) COLLATE NOCASE
                        """,
                        (fila["nombre_completo"],),
                    ).fetchone()
                if docente is not None:
                    docente_id = docente["id"]
                    conexion.execute(
                        "UPDATE usuarios SET docente_id = ? WHERE id = ?",
                        (docente_id, fila["id"]),
                    )

        if docente is None:
            raise HTTPException(
                status_code=403,
                detail="La cuenta no está vinculada a un docente registrado",
            )
        if docente["estado"] != "ACTIVO":
            raise HTTPException(status_code=403, detail="Este docente está inactivo")

    token = create_access_token(
        data={"sub": fila["usuario"], "uid": fila["id"], "rol": rol}
    )
    return {
        "id": fila["id"],
        "usuario": fila["usuario"],
        "nombre_completo": fila["nombre_completo"],
        "rol": rol,
        "docente_id": docente_id,
        "cambiar_password": debe_cambiar_password,
        "debe_cambiar_password": debe_cambiar_password,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/cambiar-password", response_model=MensajeRespuesta)
def cambiar_password(datos: CambioPasswordEntrada, token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
    except JWTError as error:
        raise HTTPException(status_code=401, detail="Sesión no válida") from error

    usuario = payload.get("sub")
    rol = str(payload.get("rol") or "").strip().upper()
    id_cuenta = payload.get("uid")
    if not usuario or rol not in {"ADMIN", "DOCENTE"}:
        raise HTTPException(status_code=401, detail="Sesión no válida")

    tabla = "administradores" if rol == "ADMIN" else "usuarios"
    filtro = "id = ?" if isinstance(id_cuenta, int) and id_cuenta > 0 else (
        "TRIM(usuario) = TRIM(?) COLLATE NOCASE"
    )
    identificador = id_cuenta if filtro == "id = ?" else usuario
    with transaccion() as conexion:
        fila = conexion.execute(
            f"""
            SELECT id, clave_hash, activo FROM {tabla}
            WHERE {filtro}
            {"AND UPPER(TRIM(rol)) = 'DOCENTE'" if rol == "DOCENTE" else ""}
            """,
            (identificador,),
        ).fetchone()
        if fila is None or not fila["activo"]:
            raise HTTPException(status_code=401, detail="Cuenta no disponible")
        if fila["clave_hash"] != hash_clave(datos.clave_actual):
            raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
        if datos.clave_actual == datos.clave_nueva:
            raise HTTPException(
                status_code=422,
                detail="La nueva contraseña debe ser diferente a la actual",
            )
        conexion.execute(
            f"""
            UPDATE {tabla}
            SET clave_hash = ?, debe_cambiar_password = 0, cambiar_password = 0
            WHERE id = ?
            """,
            (hash_clave(datos.clave_nueva), fila["id"]),
        )
    return {"mensaje": "Contraseña actualizada correctamente"}
