from fastapi import HTTPException

from app.helpers import obtener_o_404
from app.services.horarios import horarios_se_cruzan


def validar_nueva_matricula(
    conexion,
    estudiante_id: int,
    seccion_id: int,
    matricula_id_excluida: int | None = None,
) -> None:
    estudiante = obtener_o_404(
        conexion, "estudiantes", estudiante_id, "Estudiante"
    )
    seccion = obtener_o_404(conexion, "secciones", seccion_id, "Sección")

    if estudiante["estado"] != "ACTIVO":
        raise HTTPException(409, "Solo los estudiantes activos pueden matricularse")
    if seccion["estado"] != "ABIERTA":
        raise HTTPException(409, "La sección no está abierta para matrícula")

    periodo = obtener_o_404(conexion, "periodos", seccion["periodo_id"], "Período")
    if not periodo["activo"]:
        raise HTTPException(409, "El período de la sección no está activo")

    asignatura = obtener_o_404(
        conexion, "asignaturas", seccion["asignatura_id"], "Asignatura"
    )
    if not asignatura["activo"]:
        raise HTTPException(409, "La asignatura está inactiva")
    carrera_permitida = conexion.execute(
        """
        SELECT 1
        FROM asignaturas_carreras
        WHERE asignatura_id = ? AND carrera_id = ?
        """,
        (asignatura["id"], estudiante["carrera_id"]),
    ).fetchone()
    if carrera_permitida is None and asignatura["carrera_id"] == estudiante["carrera_id"]:
        carrera_permitida = True
    if carrera_permitida is None:
        raise HTTPException(409, "La asignatura no pertenece a la carrera del estudiante")

    ocupados = conexion.execute(
        """
        SELECT COUNT(*) FROM matriculas
        WHERE seccion_id = ? AND estado <> 'CANCELADA'
          AND (? IS NULL OR id <> ?)
        """,
        (seccion_id, matricula_id_excluida, matricula_id_excluida),
    ).fetchone()[0]
    if ocupados >= seccion["cupo_maximo"]:
        raise HTTPException(409, "La sección ya alcanzó su cupo máximo")

    if asignatura["requisito_id"] is not None:
        aprobado = conexion.execute(
            """
            SELECT 1
            FROM matriculas m
            JOIN secciones s ON s.id = m.seccion_id
            JOIN calificaciones c ON c.matricula_id = m.id
            WHERE m.estudiante_id = ?
              AND s.asignatura_id = ?
              AND c.nota_final >= 65
            LIMIT 1
            """,
            (estudiante_id, asignatura["requisito_id"]),
        ).fetchone()
        if aprobado is None:
            requisito = conexion.execute(
                "SELECT codigo FROM asignaturas WHERE id = ?",
                (asignatura["requisito_id"],),
            ).fetchone()
            raise HTTPException(
                409, f"El estudiante todavía no ha aprobado el requisito {requisito['codigo']}"
            )

    otras = conexion.execute(
        """
        SELECT s.codigo, a.codigo AS asignatura_codigo, s.dias,
               s.hora_inicio, s.hora_fin
        FROM matriculas m
        JOIN secciones s ON s.id = m.seccion_id
        JOIN asignaturas a ON a.id = s.asignatura_id
        WHERE m.estudiante_id = ?
          AND s.periodo_id = ?
          AND m.estado = 'MATRICULADA'
          AND s.id <> ?
        """,
        (estudiante_id, seccion["periodo_id"], seccion_id),
    ).fetchall()
    for otra in otras:
        if horarios_se_cruzan(
            seccion["dias"],
            seccion["hora_inicio"],
            seccion["hora_fin"],
            otra["dias"],
            otra["hora_inicio"],
            otra["hora_fin"],
        ):
            raise HTTPException(
                409,
                f"Choque de horario con {otra['asignatura_codigo']} "
                f"sección {otra['codigo']}",
            )

    uv_actuales = conexion.execute(
        """
        SELECT COALESCE(SUM(a.unidades_valorativas), 0)
        FROM matriculas m
        JOIN secciones s ON s.id = m.seccion_id
        JOIN asignaturas a ON a.id = s.asignatura_id
        WHERE m.estudiante_id = ?
          AND s.periodo_id = ?
          AND m.estado = 'MATRICULADA'
          AND s.id <> ?
        """,
        (estudiante_id, seccion["periodo_id"], seccion_id),
    ).fetchone()[0]
    if uv_actuales + asignatura["unidades_valorativas"] > 20:
        raise HTTPException(409, "La matrícula superaría el máximo de 20 UV por período")
