from fastapi import HTTPException

from app.helpers import obtener_o_404
from app.schemas import CalificacionEntrada


def guardar_calificacion(conexion, matricula_id: int, datos: CalificacionEntrada) -> dict:
    matricula = obtener_o_404(conexion, "matriculas", matricula_id, "Matrícula")
    if matricula["estado"] == "CANCELADA":
        raise HTTPException(409, "No se puede calificar una matrícula cancelada")

    nota_final = round(
        (datos.primer_parcial + datos.segundo_parcial + datos.tercer_parcial) / 3,
        2,
    )
    resultado = "APROBADA" if nota_final >= 65 else "REPROBADA"

    existente = conexion.execute(
        "SELECT id FROM calificaciones WHERE matricula_id = ?", (matricula_id,)
    ).fetchone()
    if existente:
        conexion.execute(
            """
            UPDATE calificaciones
            SET primer_parcial = ?, segundo_parcial = ?, tercer_parcial = ?,
                nota_final = ?, observacion = ?,
                primer_parcial_registrado = 1,
                segundo_parcial_registrado = 1,
                tercer_parcial_registrado = 1,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE matricula_id = ?
            """,
            (
                datos.primer_parcial,
                datos.segundo_parcial,
                datos.tercer_parcial,
                nota_final,
                datos.observacion,
                matricula_id,
            ),
        )
    else:
        conexion.execute(
            """
            INSERT INTO calificaciones
                (matricula_id, primer_parcial, segundo_parcial,
                 tercer_parcial, nota_final, observacion,
                 primer_parcial_registrado, segundo_parcial_registrado,
                 tercer_parcial_registrado)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1, 1)
            """,
            (
                matricula_id,
                datos.primer_parcial,
                datos.segundo_parcial,
                datos.tercer_parcial,
                nota_final,
                datos.observacion,
            ),
        )

    fila = conexion.execute(
        "SELECT * FROM calificaciones WHERE matricula_id = ?", (matricula_id,)
    ).fetchone()
    respuesta = dict(fila)
    respuesta["resultado"] = resultado
    return respuesta


def guardar_parcial(conexion, matricula_id: int, parcial: int, nota: float) -> dict:
    matricula = obtener_o_404(conexion, "matriculas", matricula_id, "Matrícula")
    if matricula["estado"] == "CANCELADA":
        raise HTTPException(409, "No se puede calificar una matrícula cancelada")

    columnas = {
        1: ("primer_parcial", "primer_parcial_registrado"),
        2: ("segundo_parcial", "segundo_parcial_registrado"),
        3: ("tercer_parcial", "tercer_parcial_registrado"),
    }
    campo_nota, campo_registrado = columnas[parcial]
    existente = conexion.execute(
        "SELECT id FROM calificaciones WHERE matricula_id = ?", (matricula_id,)
    ).fetchone()
    if existente is None:
        conexion.execute(
            """
            INSERT INTO calificaciones
                (matricula_id, primer_parcial, segundo_parcial, tercer_parcial,
                 nota_final, observacion, primer_parcial_registrado,
                 segundo_parcial_registrado, tercer_parcial_registrado)
            VALUES (?, 0, 0, 0, 0, NULL, 0, 0, 0)
            """,
            (matricula_id,),
        )

    conexion.execute(
        f"""
        UPDATE calificaciones
        SET {campo_nota} = ?, {campo_registrado} = 1,
            actualizado_en = CURRENT_TIMESTAMP
        WHERE matricula_id = ?
        """,
        (nota, matricula_id),
    )
    fila = dict(
        conexion.execute(
            "SELECT * FROM calificaciones WHERE matricula_id = ?", (matricula_id,)
        ).fetchone()
    )
    registrados = [
        fila["primer_parcial_registrado"],
        fila["segundo_parcial_registrado"],
        fila["tercer_parcial_registrado"],
    ]
    notas = [fila["primer_parcial"], fila["segundo_parcial"], fila["tercer_parcial"]]
    if all(registrados):
        nota_final = round(sum(notas) / 3, 2)
        conexion.execute(
            "UPDATE calificaciones SET nota_final = ? WHERE matricula_id = ?",
            (nota_final, matricula_id),
        )
        fila["nota_final"] = nota_final
        fila["resultado"] = "APROBADA" if nota_final >= 65 else "REPROBADA"
        fila["estado_academico"] = "Aprobado" if nota_final >= 65 else "Reprobado"
    else:
        fila["nota_final"] = None
        fila["resultado"] = None
        fila["estado_academico"] = "Activo"

    for indice, nombre in enumerate(
        ("primer_parcial", "segundo_parcial", "tercer_parcial")
    ):
        if not registrados[indice]:
            fila[nombre] = None
    return fila
