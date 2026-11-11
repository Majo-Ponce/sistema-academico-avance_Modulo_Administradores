import sqlite3

from fastapi import APIRouter, HTTPException, Query, status

from app.database import conexion_lectura, transaccion
from app.helpers import obtener_o_404
from app.schemas import AsignaturaEntrada, AsignaturaRespuesta, MensajeRespuesta


router = APIRouter(prefix="/asignaturas", tags=["Asignaturas"])


CONSULTA_BASE = """
    SELECT a.id, a.codigo, a.nombre, a.unidades_valorativas, a.carrera_id,
           a.requisito_id, a.activo, c.nombre AS carrera_nombre,
           r.codigo AS requisito_codigo
    FROM asignaturas a
    JOIN carreras c ON c.id = a.carrera_id
    LEFT JOIN asignaturas r ON r.id = a.requisito_id
"""


def _respuestas_asignaturas(conexion, filas) -> list[dict]:
    resultados = [dict(fila) for fila in filas]
    if not resultados:
        return resultados

    asignatura_ids = [fila["id"] for fila in resultados]
    marcadores = ", ".join("?" for _ in asignatura_ids)
    relaciones = conexion.execute(
        f"""
        SELECT ac.asignatura_id, c.id AS carrera_id, c.nombre AS carrera_nombre
        FROM asignaturas_carreras ac
        JOIN carreras c ON c.id = ac.carrera_id
        WHERE ac.asignatura_id IN ({marcadores})
        ORDER BY ac.asignatura_id,
                 CASE WHEN ac.carrera_id = (
                     SELECT carrera_id FROM asignaturas
                     WHERE id = ac.asignatura_id
                 ) THEN 0 ELSE 1 END,
                 c.nombre
        """,
        asignatura_ids,
    ).fetchall()
    por_asignatura: dict[int, list[dict]] = {}
    for relacion in relaciones:
        por_asignatura.setdefault(relacion["asignatura_id"], []).append(
            {
                "id": relacion["carrera_id"],
                "nombre": relacion["carrera_nombre"],
            }
        )

    for fila in resultados:
        carreras = por_asignatura.get(fila["id"], [])
        if not carreras:
            carreras = [{"id": fila["carrera_id"], "nombre": fila["carrera_nombre"]}]
        fila["carrera_ids"] = [carrera["id"] for carrera in carreras]
        fila["carrera_nombres"] = [carrera["nombre"] for carrera in carreras]
        fila["carrera_nombre"] = ", ".join(fila["carrera_nombres"])
    return resultados


def _validar_relaciones(
    conexion,
    carrera_ids: list[int],
    requisito_id: int | None,
    asignatura_id: int | None = None,
) -> None:
    for carrera_id in carrera_ids:
        carrera = obtener_o_404(conexion, "carreras", carrera_id, "Carrera")
        if not carrera["activo"]:
            raise HTTPException(409, "Una de las carreras seleccionadas está inactiva")
    if requisito_id is None:
        return
    if requisito_id == asignatura_id:
        raise HTTPException(409, "Una asignatura no puede ser requisito de sí misma")
    requisito = obtener_o_404(
        conexion, "asignaturas", requisito_id, "Asignatura requisito"
    )
    carreras_requisito = {
        fila["carrera_id"]
        for fila in conexion.execute(
            """
            SELECT carrera_id FROM asignaturas_carreras
            WHERE asignatura_id = ?
            """,
            (requisito_id,),
        ).fetchall()
    }
    if not carreras_requisito:
        carreras_requisito = {requisito["carrera_id"]}
    if not set(carrera_ids).intersection(carreras_requisito):
        raise HTTPException(
            409, "El requisito debe compartir al menos una carrera con la asignatura"
        )

    # Recorre los requisitos existentes para evitar ciclos como A -> B -> A.
    if asignatura_id is not None:
        ciclo = conexion.execute(
            """
            WITH RECURSIVE cadena(id, requisito_id) AS (
                SELECT id, requisito_id FROM asignaturas WHERE id = ?
                UNION ALL
                SELECT a.id, a.requisito_id
                FROM asignaturas a
                JOIN cadena c ON a.id = c.requisito_id
                WHERE c.requisito_id IS NOT NULL
            )
            SELECT 1 FROM cadena WHERE id = ? LIMIT 1
            """,
            (requisito_id, asignatura_id),
        ).fetchone()
        if ciclo:
            raise HTTPException(409, "El requisito produciría una dependencia circular")


@router.get("", response_model=list[AsignaturaRespuesta])
def listar_asignaturas(
    buscar: str | None = Query(default=None, max_length=100),
    carrera_id: int | None = Query(default=None, gt=0),
    solo_activas: bool = False,
):
    condiciones: list[str] = []
    parametros: list[object] = []
    if buscar:
        condiciones.append("(a.codigo LIKE ? OR a.nombre LIKE ?)")
        patron = f"%{buscar}%"
        parametros.extend([patron, patron])
    if carrera_id:
        condiciones.append(
            """
            EXISTS (
                SELECT 1 FROM asignaturas_carreras ac
                WHERE ac.asignatura_id = a.id AND ac.carrera_id = ?
            )
            """
        )
        parametros.append(carrera_id)
    if solo_activas:
        condiciones.append("a.activo = 1")
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    with conexion_lectura() as conexion:
        filas = conexion.execute(
            f"{CONSULTA_BASE} {where} ORDER BY a.codigo", parametros
        ).fetchall()
        return _respuestas_asignaturas(conexion, filas)


@router.get("/{asignatura_id}", response_model=AsignaturaRespuesta)
def obtener_asignatura(asignatura_id: int):
    with conexion_lectura() as conexion:
        fila = conexion.execute(
            f"{CONSULTA_BASE} WHERE a.id = ?", (asignatura_id,)
        ).fetchone()
        if fila is None:
            raise HTTPException(404, "Asignatura no encontrada")
        return _respuestas_asignaturas(conexion, [fila])[0]


@router.post(
    "", response_model=AsignaturaRespuesta, status_code=status.HTTP_201_CREATED
)
def crear_asignatura(datos: AsignaturaEntrada):
    try:
        with transaccion() as conexion:
            _validar_relaciones(conexion, datos.carrera_ids, datos.requisito_id)
            cursor = conexion.execute(
                """
                INSERT INTO asignaturas
                    (codigo, nombre, unidades_valorativas, carrera_id,
                     requisito_id, activo)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datos.codigo.upper(),
                    datos.nombre,
                    datos.unidades_valorativas,
                    datos.carrera_id,
                    datos.requisito_id,
                    datos.activo,
                ),
            )
            conexion.executemany(
                """
                INSERT INTO asignaturas_carreras (asignatura_id, carrera_id)
                VALUES (?, ?)
                """,
                [
                    (cursor.lastrowid, carrera_id)
                    for carrera_id in datos.carrera_ids
                ],
            )
            fila = conexion.execute(
                f"{CONSULTA_BASE} WHERE a.id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _respuestas_asignaturas(conexion, [fila])[0]
    except sqlite3.IntegrityError as error:
        raise HTTPException(409, "El código de la asignatura ya existe") from error


@router.put("/{asignatura_id}", response_model=AsignaturaRespuesta)
def actualizar_asignatura(asignatura_id: int, datos: AsignaturaEntrada):
    try:
        with transaccion() as conexion:
            obtener_o_404(conexion, "asignaturas", asignatura_id, "Asignatura")
            _validar_relaciones(
                conexion, datos.carrera_ids, datos.requisito_id, asignatura_id
            )
            conexion.execute(
                """
                UPDATE asignaturas
                SET codigo = ?, nombre = ?, unidades_valorativas = ?,
                    carrera_id = ?, requisito_id = ?, activo = ?
                WHERE id = ?
                """,
                (
                    datos.codigo.upper(),
                    datos.nombre,
                    datos.unidades_valorativas,
                    datos.carrera_id,
                    datos.requisito_id,
                    datos.activo,
                    asignatura_id,
                ),
            )
            conexion.execute(
                "DELETE FROM asignaturas_carreras WHERE asignatura_id = ?",
                (asignatura_id,),
            )
            conexion.executemany(
                """
                INSERT INTO asignaturas_carreras (asignatura_id, carrera_id)
                VALUES (?, ?)
                """,
                [
                    (asignatura_id, carrera_id)
                    for carrera_id in datos.carrera_ids
                ],
            )
            fila = conexion.execute(
                f"{CONSULTA_BASE} WHERE a.id = ?", (asignatura_id,)
            ).fetchone()
            return _respuestas_asignaturas(conexion, [fila])[0]
    except sqlite3.IntegrityError as error:
        raise HTTPException(409, "El código pertenece a otra asignatura") from error


@router.delete("/{asignatura_id}", response_model=MensajeRespuesta)
def eliminar_asignatura(asignatura_id: int):
    try:
        with transaccion() as conexion:
            obtener_o_404(conexion, "asignaturas", asignatura_id, "Asignatura")
            conexion.execute("DELETE FROM asignaturas WHERE id = ?", (asignatura_id,))
        return {"mensaje": "Asignatura eliminada correctamente"}
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            409, "No se puede eliminar: la asignatura tiene secciones"
        ) from error
