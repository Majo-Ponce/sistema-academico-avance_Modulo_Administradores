from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.database import conexion_lectura, transaccion
from app.dependencies import solo_docente
from app.helpers import filas_a_lista
from app.schemas import (
    AsistenciaRegistrosEntrada,
    AsistenciaSesionEntrada,
    CalificacionEntrada,
    ParcialEntrada,
    PerfilDocenteEntrada,
)
from app.services.calificaciones import (
    guardar_calificacion as persistir_calificacion,
    guardar_parcial as persistir_parcial,
)


router = APIRouter(
    prefix="/panel-docente",
    tags=["Panel del docente"],
    dependencies=[Depends(solo_docente)],
)


def _docente_id(usuario: dict) -> int:
    docente_id = usuario.get("docente_id")
    if docente_id:
        return docente_id

    with transaccion() as conexion:
        fila = conexion.execute(
            """
            SELECT id FROM docentes
            WHERE LOWER(TRIM(correo)) = LOWER(TRIM(?))
            """,
            (usuario.get("email") or "",),
        ).fetchone()
        if fila is None:
            fila = conexion.execute(
                """
                SELECT id FROM docentes
                WHERE TRIM(nombres || ' ' || apellidos) = TRIM(?) COLLATE NOCASE
                """,
                (usuario["nombre_completo"],),
            ).fetchone()
        if fila is None:
            raise HTTPException(
                409, "Su usuario no está vinculado a ningún docente registrado"
            )
        docente_id = fila["id"]
        conexion.execute(
            "UPDATE usuarios SET docente_id = ? WHERE id = ?",
            (docente_id, usuario["id"]),
        )
    return docente_id


def _respuesta_perfil_docente(docente) -> dict:
    fecha_nacimiento = docente["fecha_nacimiento"]
    edad = None
    if fecha_nacimiento:
        nacimiento = date.fromisoformat(fecha_nacimiento)
        hoy = date.today()
        edad = hoy.year - nacimiento.year - (
            (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
        )
    return {
        "id": docente["id"],
        "nombres": docente["nombres"],
        "apellidos": docente["apellidos"],
        "nombre_completo": f"{docente['nombres']} {docente['apellidos']}",
        "numero_identidad": docente["numero_identidad"],
        "fecha_nacimiento": fecha_nacimiento,
        "edad": edad,
        "nacionalidad": docente["nacionalidad"],
        "tipo_nacionalidad": docente["tipo_nacionalidad"],
        "fecha_ingreso": docente["fecha_ingreso"],
        "foto_perfil": docente["foto_perfil"],
    }


def _obtener_seccion_activa(conexion, seccion_id: int, docente_id: int):
    seccion = conexion.execute(
        """
        SELECT s.id
        FROM secciones s
        JOIN periodos p ON p.id = s.periodo_id
        WHERE s.id = ? AND s.docente_id = ? AND p.activo = 1
        """,
        (seccion_id, docente_id),
    ).fetchone()
    if seccion is None:
        raise HTTPException(404, "Sección no encontrada en el período activo")
    return seccion


def _obtener_sesion_asistencia(
    conexion, seccion_id: int, sesion_id: int, docente_id: int
):
    sesion = conexion.execute(
        """
        SELECT a.id, a.seccion_id, a.fecha
        FROM asistencia_sesiones a
        JOIN secciones s ON s.id = a.seccion_id
        JOIN periodos p ON p.id = s.periodo_id
        WHERE a.id = ? AND s.id = ? AND s.docente_id = ? AND p.activo = 1
        """,
        (sesion_id, seccion_id, docente_id),
    ).fetchone()
    if sesion is None:
        raise HTTPException(404, "Sesión de asistencia no encontrada")
    return sesion


@router.get("/perfil")
def obtener_perfil_docente(usuario: dict = Depends(solo_docente)):
    docente_id = _docente_id(usuario)
    with conexion_lectura() as conexion:
        docente = conexion.execute(
            """
            SELECT id, nombres, apellidos, numero_identidad, fecha_nacimiento,
                   nacionalidad, tipo_nacionalidad, fecha_ingreso, foto_perfil
            FROM docentes WHERE id = ?
            """,
            (docente_id,),
        ).fetchone()
    if docente is None:
        raise HTTPException(409, "El docente vinculado ya no está registrado")
    return _respuesta_perfil_docente(docente)


@router.put("/perfil")
def actualizar_perfil_docente(
    datos: PerfilDocenteEntrada,
    usuario: dict = Depends(solo_docente),
):
    docente_id = _docente_id(usuario)
    nombre_completo = f"{datos.nombres.strip()} {datos.apellidos.strip()}"
    with transaccion() as conexion:
        docente = conexion.execute(
            "SELECT id FROM docentes WHERE id = ?", (docente_id,)
        ).fetchone()
        if docente is None:
            raise HTTPException(409, "El docente vinculado ya no está registrado")
        conexion.execute(
            """
            UPDATE docentes
            SET nombres = ?, apellidos = ?, numero_identidad = ?,
                fecha_nacimiento = ?, nacionalidad = ?, tipo_nacionalidad = ?,
                fecha_ingreso = ?, foto_perfil = ?
            WHERE id = ?
            """,
            (
                datos.nombres.strip(),
                datos.apellidos.strip(),
                datos.numero_identidad,
                datos.fecha_nacimiento.isoformat() if datos.fecha_nacimiento else None,
                datos.nacionalidad,
                datos.tipo_nacionalidad,
                datos.fecha_ingreso.isoformat() if datos.fecha_ingreso else None,
                datos.foto_perfil,
                docente_id,
            ),
        )
        conexion.execute(
            "UPDATE usuarios SET nombre_completo = ? WHERE docente_id = ?",
            (nombre_completo, docente_id),
        )
        actualizado = conexion.execute(
            """
            SELECT id, nombres, apellidos, numero_identidad, fecha_nacimiento,
                   nacionalidad, tipo_nacionalidad, fecha_ingreso, foto_perfil
            FROM docentes WHERE id = ?
            """,
            (docente_id,),
        ).fetchone()
    return _respuesta_perfil_docente(actualizado)


@router.get("/resumen")
def resumen_docente(usuario: dict = Depends(solo_docente)):
    docente_id = _docente_id(usuario)
    with conexion_lectura() as conexion:
        docente = conexion.execute(
            "SELECT * FROM docentes WHERE id = ?", (docente_id,)
        ).fetchone()
        secciones = conexion.execute(
            """
            SELECT COUNT(*) FROM secciones s
            JOIN periodos p ON p.id = s.periodo_id
            WHERE s.docente_id = ? AND p.activo = 1 AND s.estado = 'ABIERTA'
            """,
            (docente_id,),
        ).fetchone()[0]
        estudiantes = conexion.execute(
            """
            SELECT COUNT(*) FROM matriculas m
            JOIN secciones s ON s.id = m.seccion_id
            JOIN periodos p ON p.id = s.periodo_id
            WHERE s.docente_id = ? AND p.activo = 1
              AND m.estado = 'MATRICULADA'
            """,
            (docente_id,),
        ).fetchone()[0]
        periodo = conexion.execute(
            """
            SELECT anio || '-' || numero FROM periodos
            WHERE activo = 1 ORDER BY anio DESC, numero DESC LIMIT 1
            """
        ).fetchone()

    if docente is None:
        raise HTTPException(409, "El docente vinculado ya no está registrado")
    return {
        "docente_id": docente_id,
        "docente_nombre": f"{docente['nombres']} {docente['apellidos']}",
        "especialidad": docente["especialidad"],
        "mis_secciones": secciones,
        "mis_estudiantes": estudiantes,
        "periodo_activo": periodo[0] if periodo else None,
    }


@router.get("/mis-secciones")
def mis_secciones(usuario: dict = Depends(solo_docente)):
    docente_id = _docente_id(usuario)
    with conexion_lectura() as conexion:
        filas = conexion.execute(
            """
            SELECT s.id, s.codigo, a.codigo AS asignatura_codigo,
                   a.nombre AS asignatura_nombre,
                   p.anio || '-' || p.numero AS periodo_nombre,
                   au.codigo AS aula_codigo, au.edificio AS aula_edificio,
                   s.dias, s.hora_inicio, s.hora_fin, s.cupo_maximo, s.estado,
                   COUNT(CASE WHEN m.estado = 'MATRICULADA' THEN 1 END) AS matriculados
            FROM secciones s
            JOIN asignaturas a ON a.id = s.asignatura_id
            JOIN periodos p ON p.id = s.periodo_id
            LEFT JOIN aulas au ON au.id = s.aula_id
            LEFT JOIN matriculas m ON m.seccion_id = s.id
            WHERE s.docente_id = ? AND p.activo = 1
            GROUP BY s.id
            ORDER BY p.anio DESC, p.numero DESC, s.hora_inicio, s.codigo
            """,
            (docente_id,),
        ).fetchall()
    return filas_a_lista(filas)


@router.get("/mis-secciones/{seccion_id}/asistencia")
def listar_sesiones_asistencia(
    seccion_id: int,
    usuario: dict = Depends(solo_docente),
):
    docente_id = _docente_id(usuario)
    with conexion_lectura() as conexion:
        _obtener_seccion_activa(conexion, seccion_id, docente_id)
        sesiones = conexion.execute(
            """
            SELECT s.id, s.fecha,
                   COUNT(r.estado) AS registros_completados
            FROM asistencia_sesiones s
            LEFT JOIN asistencia_registros r ON r.sesion_id = s.id
            WHERE s.seccion_id = ?
            GROUP BY s.id
            ORDER BY s.fecha DESC, s.id DESC
            """,
            (seccion_id,),
        ).fetchall()
    return filas_a_lista(sesiones)


@router.post("/mis-secciones/{seccion_id}/asistencia", status_code=201)
def crear_sesion_asistencia(
    seccion_id: int,
    datos: AsistenciaSesionEntrada,
    usuario: dict = Depends(solo_docente),
):
    docente_id = _docente_id(usuario)
    with transaccion() as conexion:
        _obtener_seccion_activa(conexion, seccion_id, docente_id)
        fecha = datos.fecha.isoformat()
        existente = conexion.execute(
            """
            SELECT id FROM asistencia_sesiones
            WHERE seccion_id = ? AND fecha = ?
            """,
            (seccion_id, fecha),
        ).fetchone()
        if existente is not None:
            raise HTTPException(409, "Ya existe una sesión de asistencia para esa fecha")
        cursor = conexion.execute(
            "INSERT INTO asistencia_sesiones (seccion_id, fecha) VALUES (?, ?)",
            (seccion_id, fecha),
        )
        return {"id": cursor.lastrowid, "seccion_id": seccion_id, "fecha": fecha}


@router.get("/mis-secciones/{seccion_id}/asistencia/{sesion_id}")
def obtener_registros_asistencia(
    seccion_id: int,
    sesion_id: int,
    usuario: dict = Depends(solo_docente),
):
    docente_id = _docente_id(usuario)
    with conexion_lectura() as conexion:
        sesion = _obtener_sesion_asistencia(
            conexion, seccion_id, sesion_id, docente_id
        )
        registros = conexion.execute(
            """
            SELECT m.id AS matricula_id, e.cuenta,
                   e.nombres || ' ' || e.apellidos AS estudiante_nombre,
                   r.estado
            FROM matriculas m
            JOIN estudiantes e ON e.id = m.estudiante_id
            LEFT JOIN asistencia_registros r
              ON r.sesion_id = ? AND r.matricula_id = m.id
            WHERE m.seccion_id = ? AND m.estado = 'MATRICULADA'
            ORDER BY e.apellidos, e.nombres, e.cuenta
            """,
            (sesion_id, seccion_id),
        ).fetchall()
    return {"sesion": dict(sesion), "registros": filas_a_lista(registros)}


@router.put("/mis-secciones/{seccion_id}/asistencia/{sesion_id}")
def guardar_registros_asistencia(
    seccion_id: int,
    sesion_id: int,
    datos: AsistenciaRegistrosEntrada,
    usuario: dict = Depends(solo_docente),
):
    docente_id = _docente_id(usuario)
    matricula_ids = [registro.matricula_id for registro in datos.registros]
    if len(matricula_ids) != len(set(matricula_ids)):
        raise HTTPException(422, "No se puede repetir una matrícula en el registro")

    with transaccion() as conexion:
        _obtener_sesion_asistencia(conexion, seccion_id, sesion_id, docente_id)
        matriculas_activas = {
            fila["id"]
            for fila in conexion.execute(
                """
                SELECT id FROM matriculas
                WHERE seccion_id = ? AND estado = 'MATRICULADA'
                """,
                (seccion_id,),
            ).fetchall()
        }
        if set(matricula_ids) != matriculas_activas:
            raise HTTPException(
                422,
                "El registro debe incluir exactamente las matrículas activas de la sección",
            )
        conexion.executemany(
            """
            INSERT INTO asistencia_registros (sesion_id, matricula_id, estado)
            VALUES (?, ?, ?)
            ON CONFLICT (sesion_id, matricula_id) DO UPDATE
            SET estado = excluded.estado, actualizado_en = CURRENT_TIMESTAMP
            """,
            [
                (sesion_id, registro.matricula_id, registro.estado)
                for registro in datos.registros
            ],
        )
        return {"sesion_id": sesion_id, "registros_guardados": len(datos.registros)}


@router.get("/mis-secciones/{seccion_id}/estudiantes")
def estudiantes_de_seccion(
    seccion_id: int,
    usuario: dict = Depends(solo_docente),
):
    docente_id = _docente_id(usuario)
    with conexion_lectura() as conexion:
        seccion = conexion.execute(
            """
            SELECT s.id, s.codigo, a.codigo AS asignatura_codigo,
                   a.nombre AS asignatura_nombre,
                   p.anio || '-' || p.numero AS periodo
            FROM secciones s
            JOIN asignaturas a ON a.id = s.asignatura_id
            JOIN periodos p ON p.id = s.periodo_id
            WHERE s.id = ? AND s.docente_id = ? AND p.activo = 1
            """,
            (seccion_id, docente_id),
        ).fetchone()
        if seccion is None:
            raise HTTPException(404, "Sección no encontrada en el período activo")

        filas = conexion.execute(
            """
            SELECT m.id AS matricula_id, e.cuenta,
                   e.nombres || ' ' || e.apellidos AS estudiante_nombre,
                   e.correo, ca.nombre AS carrera_nombre,
                   m.estado AS estado_matricula,
                   CASE WHEN c.primer_parcial_registrado = 1
                        THEN c.primer_parcial END AS primer_parcial,
                   CASE WHEN c.segundo_parcial_registrado = 1
                        THEN c.segundo_parcial END AS segundo_parcial,
                   CASE WHEN c.tercer_parcial_registrado = 1
                        THEN c.tercer_parcial END AS tercer_parcial,
                   CASE WHEN c.primer_parcial_registrado = 1
                         AND c.segundo_parcial_registrado = 1
                         AND c.tercer_parcial_registrado = 1
                        THEN c.nota_final END AS nota_final,
                   CASE WHEN c.id IS NOT NULL
                         AND c.primer_parcial_registrado = 1
                         AND c.segundo_parcial_registrado = 1
                         AND c.tercer_parcial_registrado = 1
                        THEN 1 ELSE 0 END AS calificacion_completa
            FROM matriculas m
            JOIN estudiantes e ON e.id = m.estudiante_id
            JOIN carreras ca ON ca.id = e.carrera_id
            LEFT JOIN calificaciones c ON c.matricula_id = m.id
            WHERE m.seccion_id = ? AND m.estado = 'MATRICULADA'
            ORDER BY e.apellidos, e.nombres, e.cuenta
            """,
            (seccion_id,),
        ).fetchall()

    estudiantes = []
    for fila in filas:
        estudiante = dict(fila)
        nota_final = estudiante["nota_final"]
        estudiante["estado_academico"] = (
            ("Aprobado" if nota_final >= 65 else "Reprobado")
            if estudiante["calificacion_completa"]
            else "Activo"
        )
        estudiantes.append(estudiante)
    return {"seccion": dict(seccion), "estudiantes": estudiantes}


@router.put("/mis-secciones/{seccion_id}/estudiantes/{matricula_id}/parcial")
def actualizar_parcial_docente(
    seccion_id: int,
    matricula_id: int,
    datos: ParcialEntrada,
    usuario: dict = Depends(solo_docente),
):
    docente_id = _docente_id(usuario)
    with transaccion() as conexion:
        matricula = conexion.execute(
            """
            SELECT m.id
            FROM matriculas m
            JOIN secciones s ON s.id = m.seccion_id
            JOIN periodos p ON p.id = s.periodo_id
            WHERE m.id = ? AND s.id = ? AND s.docente_id = ?
              AND p.activo = 1 AND m.estado = 'MATRICULADA'
            """,
            (matricula_id, seccion_id, docente_id),
        ).fetchone()
        if matricula is None:
            raise HTTPException(404, "Matrícula no encontrada en esta sección")
        return persistir_parcial(conexion, matricula_id, datos.parcial, datos.nota)


@router.get("/mis-estudiantes")
def mis_estudiantes(usuario: dict = Depends(solo_docente)):
    docente_id = _docente_id(usuario)
    with conexion_lectura() as conexion:
        filas = conexion.execute(
            """
            SELECT m.id AS matricula_id, e.cuenta,
                   e.nombres || ' ' || e.apellidos AS estudiante_nombre,
                   e.correo, a.codigo AS asignatura_codigo,
                   a.nombre AS asignatura_nombre, s.codigo AS seccion_codigo,
                   p.anio || '-' || p.numero AS periodo_nombre,
                   m.estado, c.primer_parcial, c.segundo_parcial,
                   c.tercer_parcial, c.nota_final, c.observacion
            FROM matriculas m
            JOIN estudiantes e ON e.id = m.estudiante_id
            JOIN secciones s ON s.id = m.seccion_id
            JOIN asignaturas a ON a.id = s.asignatura_id
            JOIN periodos p ON p.id = s.periodo_id
            LEFT JOIN calificaciones c ON c.matricula_id = m.id
            WHERE s.docente_id = ? AND p.activo = 1
              AND m.estado = 'MATRICULADA'
            ORDER BY p.anio DESC, p.numero DESC, a.codigo, e.apellidos
            """,
            (docente_id,),
        ).fetchall()
    return filas_a_lista(filas)


@router.put("/mis-estudiantes/{matricula_id}/calificacion")
def actualizar_calificacion_docente(
    matricula_id: int,
    datos: CalificacionEntrada,
    usuario: dict = Depends(solo_docente),
):
    docente_id = _docente_id(usuario)
    with transaccion() as conexion:
        matricula = conexion.execute(
            """
            SELECT m.id
            FROM matriculas m
            JOIN secciones s ON s.id = m.seccion_id
            JOIN periodos p ON p.id = s.periodo_id
            WHERE m.id = ? AND s.docente_id = ? AND p.activo = 1
            """,
            (matricula_id, docente_id),
        ).fetchone()
        if matricula is None:
            raise HTTPException(404, "Matrícula no encontrada en sus secciones")
        return persistir_calificacion(conexion, matricula_id, datos)
