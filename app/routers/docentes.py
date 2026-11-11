import sqlite3

from fastapi import APIRouter, HTTPException, Query, status

from app.database import (
    CLAVE_DOCENTE_INICIAL,
    conexion_lectura,
    hash_clave,
    transaccion,
)
from app.helpers import filas_a_lista, obtener_o_404
from app.schemas import DocenteEntrada, DocenteRespuesta, MensajeRespuesta


router = APIRouter(prefix="/docentes", tags=["Docentes"])


def _sincronizar_cuenta_docente(conexion, docente_id: int, datos: DocenteEntrada):
    correo = str(datos.correo).strip().lower()
    nombre = f"{datos.nombres} {datos.apellidos}"
    usuario = conexion.execute(
        "SELECT * FROM usuarios WHERE docente_id = ?", (docente_id,)
    ).fetchone()
    if usuario is None:
        usuario = conexion.execute(
            """
            SELECT * FROM usuarios
            WHERE LOWER(TRIM(COALESCE(email, ''))) = LOWER(TRIM(?))
            """,
            (correo,),
        ).fetchone()
        if usuario is not None and (
            str(usuario["rol"]).strip().upper() != "DOCENTE"
            or usuario["docente_id"] not in (None, docente_id)
        ):
            raise HTTPException(409, "El correo ya está asociado a otra cuenta")

    if usuario is None:
        conexion.execute(
            """
            INSERT INTO usuarios
                (usuario, email, nombre_completo, clave_hash, rol, activo,
                 cambiar_password, debe_cambiar_password, docente_id)
            VALUES (?, ?, ?, ?, 'DOCENTE', ?, ?, ?, ?)
            """,
            (
                correo,
                correo,
                nombre,
                hash_clave(datos.clave or CLAVE_DOCENTE_INICIAL),
                int(datos.estado == "ACTIVO"),
                int(datos.clave is None),
                int(datos.clave is None),
                docente_id,
            ),
        )
        return

    actualizaciones = [
        "email = ?",
        "nombre_completo = ?",
        "activo = ?",
        "docente_id = ?",
    ]
    valores: list[object] = [
        correo,
        nombre,
        int(datos.estado == "ACTIVO"),
        docente_id,
    ]
    if str(usuario["usuario"]).strip().lower() == str(
        usuario["email"] or ""
    ).strip().lower():
        actualizaciones.append("usuario = ?")
        valores.append(correo)
    if datos.clave is not None:
        actualizaciones.append("clave_hash = ?")
        valores.append(hash_clave(datos.clave))
        es_clave_temporal = (
            hash_clave(datos.clave) == hash_clave(CLAVE_DOCENTE_INICIAL)
        )
        actualizaciones.extend(
            ["cambiar_password = ?", "debe_cambiar_password = ?"]
        )
        valores.extend([int(es_clave_temporal), int(es_clave_temporal)])
    valores.append(usuario["id"])
    conexion.execute(
        f"UPDATE usuarios SET {', '.join(actualizaciones)} WHERE id = ?",
        valores,
    )


@router.get("", response_model=list[DocenteRespuesta])
def listar_docentes(
    buscar: str | None = Query(default=None, max_length=100),
    estado: str | None = Query(default=None, pattern="^(ACTIVO|INACTIVO)$"),
):
    condiciones: list[str] = []
    parametros: list[object] = []
    if buscar:
        condiciones.append(
            "(numero_empleado LIKE ? OR nombres LIKE ? OR apellidos LIKE ? "
            "OR especialidad LIKE ?)"
        )
        patron = f"%{buscar}%"
        parametros.extend([patron] * 4)
    if estado:
        condiciones.append("estado = ?")
        parametros.append(estado)

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    with conexion_lectura() as conexion:
        filas = conexion.execute(
            f"""
            SELECT id, numero_empleado, nombres, apellidos, correo,
                   especialidad, estado
            FROM docentes {where}
            ORDER BY apellidos, nombres
            """,
            parametros,
        ).fetchall()
    return filas_a_lista(filas)


@router.get("/{docente_id}", response_model=DocenteRespuesta)
def obtener_docente(docente_id: int):
    with conexion_lectura() as conexion:
        return dict(obtener_o_404(conexion, "docentes", docente_id, "Docente"))


@router.post("", response_model=DocenteRespuesta, status_code=status.HTTP_201_CREATED)
def crear_docente(datos: DocenteEntrada):
    try:
        with transaccion() as conexion:
            cursor = conexion.execute(
                """
                INSERT INTO docentes
                    (numero_empleado, nombres, apellidos, correo, especialidad, estado)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datos.numero_empleado.upper(),
                    datos.nombres,
                    datos.apellidos,
                    str(datos.correo).lower(),
                    datos.especialidad,
                    datos.estado,
                ),
            )
            _sincronizar_cuenta_docente(conexion, cursor.lastrowid, datos)
            return dict(
                conexion.execute(
                    "SELECT * FROM docentes WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
            )
    except sqlite3.IntegrityError as error:
        raise HTTPException(409, "El número de empleado o correo ya existe") from error


@router.put("/{docente_id}", response_model=DocenteRespuesta)
def actualizar_docente(docente_id: int, datos: DocenteEntrada):
    try:
        with transaccion() as conexion:
            obtener_o_404(conexion, "docentes", docente_id, "Docente")
            conexion.execute(
                """
                UPDATE docentes
                SET numero_empleado = ?, nombres = ?, apellidos = ?, correo = ?,
                    especialidad = ?, estado = ?
                WHERE id = ?
                """,
                (
                    datos.numero_empleado.upper(),
                    datos.nombres,
                    datos.apellidos,
                    str(datos.correo).lower(),
                    datos.especialidad,
                    datos.estado,
                    docente_id,
                ),
            )
            _sincronizar_cuenta_docente(conexion, docente_id, datos)
            return dict(
                conexion.execute(
                    "SELECT * FROM docentes WHERE id = ?", (docente_id,)
                ).fetchone()
            )
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            409, "El número de empleado o correo pertenece a otro docente"
        ) from error


@router.delete("/{docente_id}", response_model=MensajeRespuesta)
def eliminar_docente(docente_id: int):
    try:
        with transaccion() as conexion:
            obtener_o_404(conexion, "docentes", docente_id, "Docente")
            conexion.execute(
                "UPDATE usuarios SET activo = 0 WHERE docente_id = ?", (docente_id,)
            )
            conexion.execute("DELETE FROM docentes WHERE id = ?", (docente_id,))
        return {"mensaje": "Docente eliminado correctamente"}
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            409, "No se puede eliminar: el docente tiene secciones asignadas"
        ) from error
