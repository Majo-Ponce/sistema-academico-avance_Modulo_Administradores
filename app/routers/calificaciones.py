from fastapi import APIRouter, HTTPException, Query, status

from app.database import conexion_lectura, transaccion
from app.helpers import filas_a_lista, obtener_o_404
from app.schemas import (
    CalificacionEntrada,
    CalificacionRespuesta,
    MensajeRespuesta,
)
from app.services.calificaciones import guardar_calificacion as persistir_calificacion


router = APIRouter(prefix="/calificaciones", tags=["Calificaciones"])


def _respuesta_calificacion(fila) -> dict:
    datos = dict(fila)
    registrados = [
        datos.get("primer_parcial_registrado", 1),
        datos.get("segundo_parcial_registrado", 1),
        datos.get("tercer_parcial_registrado", 1),
    ]
    for indice, nombre in enumerate(
        ("primer_parcial", "segundo_parcial", "tercer_parcial")
    ):
        if not registrados[indice]:
            datos[nombre] = None
    completa = all(registrados)
    if not completa:
        datos["nota_final"] = None
    datos["resultado"] = (
        None
        if datos["nota_final"] is None
        else "APROBADA"
        if datos["nota_final"] >= 65
        else "REPROBADA"
    )
    return datos


@router.get("", response_model=list[CalificacionRespuesta])
def listar_calificaciones(seccion_id: int | None = Query(default=None, gt=0)):
    parametros: list[object] = []
    where = ""
    if seccion_id:
        where = "WHERE m.seccion_id = ?"
        parametros.append(seccion_id)
    with conexion_lectura() as conexion:
        filas = conexion.execute(
            f"""
            SELECT c.id, c.matricula_id, c.primer_parcial,
                   c.segundo_parcial, c.tercer_parcial, c.nota_final,
                   c.observacion, c.primer_parcial_registrado,
                   c.segundo_parcial_registrado, c.tercer_parcial_registrado
            FROM calificaciones c
            JOIN matriculas m ON m.id = c.matricula_id
            {where}
            ORDER BY c.id
            """,
            parametros,
        ).fetchall()
    return [_respuesta_calificacion(fila) for fila in filas]


@router.get(
    "/matricula/{matricula_id}", response_model=CalificacionRespuesta
)
def obtener_calificacion(matricula_id: int):
    with conexion_lectura() as conexion:
        fila = conexion.execute(
            "SELECT * FROM calificaciones WHERE matricula_id = ?", (matricula_id,)
        ).fetchone()
    if fila is None:
        raise HTTPException(404, "La matrícula todavía no tiene calificaciones")
    return _respuesta_calificacion(fila)


@router.put(
    "/matricula/{matricula_id}",
    response_model=CalificacionRespuesta,
    status_code=status.HTTP_200_OK,
)
def guardar_calificacion(matricula_id: int, datos: CalificacionEntrada):
    with transaccion() as conexion:
        return persistir_calificacion(conexion, matricula_id, datos)


@router.delete("/matricula/{matricula_id}", response_model=MensajeRespuesta)
def eliminar_calificacion(matricula_id: int):
    with transaccion() as conexion:
        obtener_o_404(conexion, "matriculas", matricula_id, "Matrícula")
        cursor = conexion.execute(
            "DELETE FROM calificaciones WHERE matricula_id = ?", (matricula_id,)
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "La matrícula no tenía calificaciones")
    return {"mensaje": "Calificación eliminada; se conservó el estado de la matrícula"}
