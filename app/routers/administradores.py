import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import (
    CLAVE_ADMIN_INICIAL,
    conexion_lectura,
    hash_clave,
    transaccion,
)
from app.dependencies import solo_admin
from app.schemas import AdministradorEntrada, AdministradorRespuesta, MensajeRespuesta


router = APIRouter(prefix="/administradores", tags=["Administradores"])


def _correo_en_uso(conexion, correo: str, administrador_id: int | None = None) -> bool:
    existente = conexion.execute(
        """
        SELECT id FROM administradores
        WHERE (
            LOWER(TRIM(email)) = LOWER(TRIM(?))
            OR LOWER(TRIM(usuario)) = LOWER(TRIM(?))
        ) AND id <> COALESCE(?, -1)
        """,
        (correo, correo, administrador_id),
    ).fetchone()
    if existente:
        return True
    existente = conexion.execute(
        """
        SELECT id FROM docentes
        WHERE LOWER(TRIM(correo)) = LOWER(TRIM(?))
        """,
        (correo,),
    ).fetchone()
    if existente:
        return True
    existente = conexion.execute(
        """
        SELECT id FROM usuarios
        WHERE LOWER(TRIM(COALESCE(email, ''))) = LOWER(TRIM(?))
           OR LOWER(TRIM(usuario)) = LOWER(TRIM(?))
        """,
        (correo, correo),
    ).fetchone()
    return existente is not None


def _usuario_en_uso(conexion, usuario: str, administrador_id: int | None = None) -> bool:
    existente = conexion.execute(
        """
        SELECT id FROM administradores
        WHERE (
            LOWER(TRIM(usuario)) = LOWER(TRIM(?))
            OR LOWER(TRIM(email)) = LOWER(TRIM(?))
        ) AND id <> COALESCE(?, -1)
        """,
        (usuario, usuario, administrador_id),
    ).fetchone()
    if existente:
        return True
    existente = conexion.execute(
        """
        SELECT id FROM usuarios
        WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(?))
           OR LOWER(TRIM(COALESCE(email, ''))) = LOWER(TRIM(?))
        """,
        (usuario, usuario),
    ).fetchone()
    return existente is not None


@router.get("", response_model=list[AdministradorRespuesta])
def listar_administradores():
    with conexion_lectura() as conexion:
        filas = conexion.execute(
            """
            SELECT id, usuario, nombre, email, activo, cambiar_password,
                   debe_cambiar_password
            FROM administradores
            ORDER BY nombre, email
            """
        ).fetchall()
    return [dict(fila) for fila in filas]


@router.post(
    "",
    response_model=AdministradorRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_administrador(datos: AdministradorEntrada):
    correo = str(datos.email).strip().lower()
    try:
        with transaccion() as conexion:
            if _correo_en_uso(conexion, correo):
                raise HTTPException(409, "El correo ya está asociado a otra cuenta")
            if _usuario_en_uso(conexion, datos.usuario):
                raise HTTPException(409, "El nombre de usuario ya existe")
            cursor = conexion.execute(
                """
                INSERT INTO administradores
                    (usuario, nombre, email, clave_hash, activo, cambiar_password,
                     debe_cambiar_password)
                VALUES (?, ?, ?, ?, ?, 1, 1)
                """,
                (
                    datos.usuario.strip(),
                    datos.nombre.strip(),
                    correo,
                    hash_clave(CLAVE_ADMIN_INICIAL),
                    int(datos.activo),
                ),
            )
            fila = conexion.execute(
                """
                SELECT id, usuario, nombre, email, activo, cambiar_password,
                       debe_cambiar_password
                FROM administradores WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            return dict(fila)
    except sqlite3.IntegrityError as error:
        raise HTTPException(409, "El correo o usuario ya existe") from error


@router.put("/{administrador_id}", response_model=AdministradorRespuesta)
def actualizar_administrador(
    administrador_id: int,
    datos: AdministradorEntrada,
    usuario_actual: dict = Depends(solo_admin),
):
    correo = str(datos.email).strip().lower()
    try:
        with transaccion() as conexion:
            actual = conexion.execute(
                "SELECT * FROM administradores WHERE id = ?", (administrador_id,)
            ).fetchone()
            if actual is None:
                raise HTTPException(404, "Administrador no encontrado")
            if _correo_en_uso(conexion, correo, administrador_id):
                raise HTTPException(409, "El correo ya está asociado a otra cuenta")
            if _usuario_en_uso(conexion, datos.usuario, administrador_id):
                raise HTTPException(409, "El nombre de usuario ya existe")

            es_cuenta_actual = actual["id"] == usuario_actual["id"]
            if es_cuenta_actual and not datos.activo:
                raise HTTPException(409, "No puede desactivar su propia cuenta")
            activos = conexion.execute(
                "SELECT COUNT(*) FROM administradores WHERE activo = 1"
            ).fetchone()[0]
            if actual["activo"] and not datos.activo and activos <= 1:
                raise HTTPException(409, "Debe conservar al menos un administrador activo")

            cambios = [
                "usuario = ?",
                "nombre = ?",
                "email = ?",
                "activo = ?",
            ]
            valores: list[object] = [
                datos.usuario.strip(),
                datos.nombre.strip(),
                correo,
                int(datos.activo),
            ]
            valores.append(administrador_id)
            conexion.execute(
                f"UPDATE administradores SET {', '.join(cambios)} WHERE id = ?",
                valores,
            )
            return dict(
                conexion.execute(
                    """
                    SELECT id, usuario, nombre, email, activo, cambiar_password,
                           debe_cambiar_password
                    FROM administradores WHERE id = ?
                    """,
                    (administrador_id,),
                ).fetchone()
            )
    except sqlite3.IntegrityError as error:
        raise HTTPException(409, "El correo o usuario ya existe") from error


@router.delete("/{administrador_id}", response_model=MensajeRespuesta)
def eliminar_administrador(
    administrador_id: int,
    usuario_actual: dict = Depends(solo_admin),
):
    with transaccion() as conexion:
        actual = conexion.execute(
            "SELECT id, activo FROM administradores WHERE id = ?",
            (administrador_id,),
        ).fetchone()
        if actual is None:
            raise HTTPException(404, "Administrador no encontrado")
        if actual["id"] == usuario_actual["id"]:
            raise HTTPException(409, "No puede eliminar su propia cuenta")
        activos = conexion.execute(
            "SELECT COUNT(*) FROM administradores WHERE activo = 1"
        ).fetchone()[0]
        if actual["activo"] and activos <= 1:
            raise HTTPException(409, "Debe conservar al menos un administrador activo")
        conexion.execute(
            "DELETE FROM administradores WHERE id = ?", (administrador_id,)
        )
    return {"mensaje": "Administrador eliminado correctamente"}
