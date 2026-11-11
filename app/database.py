from contextlib import contextmanager
from pathlib import Path
import hashlib
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


def hash_clave(clave: str) -> str:
    """Hash simple de la contraseña (fines didácticos).

    En un sistema real se usaría una librería como passlib/bcrypt, que además
    agrega 'sal' a cada contraseña. Aquí se mantiene sencillo para que el
    estudiante pueda leer y explicar el código completo.
    """
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


CLAVE_ADMIN_INICIAL = "password.admin"
CLAVE_DOCENTE_INICIAL = "password.docente"

CLAVES_ADMIN_ANTERIORES = ("passwordadmin123", "admin123")
CLAVES_DOCENTE_ANTERIORES = ("passworddocente123", "docente123")


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "sistema_academico.db"


def obtener_conexion() -> sqlite3.Connection:
    """Crea una conexión y hace que cada fila se comporte como diccionario."""
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


@contextmanager
def conexion_lectura():
    """Entrega una conexión de consulta y garantiza que siempre se cierre."""
    conexion = obtener_conexion()
    try:
        yield conexion
    finally:
        conexion.close()


@contextmanager
def transaccion():
    """Confirma todos los cambios o los revierte cuando ocurre un error."""
    conexion = obtener_conexion()
    try:
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def crear_tablas() -> None:
    esquema = """
    CREATE TABLE IF NOT EXISTS carreras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL UNIQUE,
        duracion_anios INTEGER NOT NULL CHECK (duracion_anios BETWEEN 1 AND 10),
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta TEXT NOT NULL UNIQUE,
        nombres TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        correo TEXT NOT NULL UNIQUE,
        telefono TEXT,
        fecha_nacimiento TEXT NOT NULL,
        carrera_id INTEGER NOT NULL,
        estado TEXT NOT NULL DEFAULT 'ACTIVO'
            CHECK (estado IN ('ACTIVO', 'INACTIVO', 'GRADUADO')),
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS docentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_empleado TEXT NOT NULL UNIQUE,
        nombres TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        correo TEXT NOT NULL UNIQUE,
        especialidad TEXT NOT NULL,
        numero_identidad TEXT,
        fecha_nacimiento TEXT,
        nacionalidad TEXT,
        tipo_nacionalidad TEXT,
        fecha_ingreso TEXT,
        foto_perfil TEXT,
        estado TEXT NOT NULL DEFAULT 'ACTIVO'
            CHECK (estado IN ('ACTIVO', 'INACTIVO')),
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS asignaturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        unidades_valorativas INTEGER NOT NULL
            CHECK (unidades_valorativas BETWEEN 1 AND 8),
        carrera_id INTEGER NOT NULL,
        requisito_id INTEGER,
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE RESTRICT,
        FOREIGN KEY (requisito_id) REFERENCES asignaturas(id) ON DELETE SET NULL,
        CHECK (requisito_id IS NULL OR requisito_id <> id)
    );

    CREATE TABLE IF NOT EXISTS asignaturas_carreras (
        asignatura_id INTEGER NOT NULL,
        carrera_id INTEGER NOT NULL,
        PRIMARY KEY (asignatura_id, carrera_id),
        FOREIGN KEY (asignatura_id) REFERENCES asignaturas(id) ON DELETE CASCADE,
        FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS periodos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anio INTEGER NOT NULL CHECK (anio BETWEEN 2020 AND 2100),
        numero INTEGER NOT NULL CHECK (numero BETWEEN 1 AND 4),
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT NOT NULL,
        activo INTEGER NOT NULL DEFAULT 0 CHECK (activo IN (0, 1)),
        UNIQUE (anio, numero),
        CHECK (fecha_fin > fecha_inicio)
    );

    CREATE TABLE IF NOT EXISTS aulas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        edificio TEXT NOT NULL,
        capacidad INTEGER NOT NULL CHECK (capacidad BETWEEN 1 AND 200),
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
    );

    CREATE TABLE IF NOT EXISTS secciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL,
        asignatura_id INTEGER NOT NULL,
        docente_id INTEGER NOT NULL,
        periodo_id INTEGER NOT NULL,
        aula_id INTEGER,
        dias TEXT NOT NULL,
        hora_inicio TEXT NOT NULL,
        hora_fin TEXT NOT NULL,
        cupo_maximo INTEGER NOT NULL CHECK (cupo_maximo BETWEEN 1 AND 200),
        estado TEXT NOT NULL DEFAULT 'ABIERTA'
            CHECK (estado IN ('ABIERTA', 'CERRADA', 'FINALIZADA')),
        FOREIGN KEY (asignatura_id) REFERENCES asignaturas(id) ON DELETE RESTRICT,
        FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE RESTRICT,
        FOREIGN KEY (periodo_id) REFERENCES periodos(id) ON DELETE RESTRICT,
        FOREIGN KEY (aula_id) REFERENCES aulas(id) ON DELETE SET NULL,
        UNIQUE (asignatura_id, periodo_id, codigo),
        CHECK (hora_fin > hora_inicio)
    );

    CREATE TABLE IF NOT EXISTS matriculas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        seccion_id INTEGER NOT NULL,
        fecha_matricula TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        estado TEXT NOT NULL DEFAULT 'MATRICULADA'
            CHECK (estado IN ('MATRICULADA', 'CANCELADA')),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE RESTRICT,
        FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE RESTRICT,
        UNIQUE (estudiante_id, seccion_id)
    );

    CREATE TABLE IF NOT EXISTS calificaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        matricula_id INTEGER NOT NULL UNIQUE,
        primer_parcial REAL NOT NULL CHECK (primer_parcial BETWEEN 0 AND 100),
        segundo_parcial REAL NOT NULL CHECK (segundo_parcial BETWEEN 0 AND 100),
        tercer_parcial REAL NOT NULL CHECK (tercer_parcial BETWEEN 0 AND 100),
        nota_final REAL NOT NULL CHECK (nota_final BETWEEN 0 AND 100),
        observacion TEXT,
        primer_parcial_registrado INTEGER NOT NULL DEFAULT 1
            CHECK (primer_parcial_registrado IN (0, 1)),
        segundo_parcial_registrado INTEGER NOT NULL DEFAULT 1
            CHECK (segundo_parcial_registrado IN (0, 1)),
        tercer_parcial_registrado INTEGER NOT NULL DEFAULT 1
            CHECK (tercer_parcial_registrado IN (0, 1)),
        actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (matricula_id) REFERENCES matriculas(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS asistencia_sesiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seccion_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE CASCADE,
        UNIQUE (seccion_id, fecha)
    );

    CREATE TABLE IF NOT EXISTS asistencia_registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sesion_id INTEGER NOT NULL,
        matricula_id INTEGER NOT NULL,
        estado TEXT CHECK (
            estado IS NULL OR estado IN (
                'PRESENTE', 'AUSENTE', 'TARDANZA', 'JUSTIFICADO'
            )
        ),
        actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sesion_id) REFERENCES asistencia_sesiones(id) ON DELETE CASCADE,
        FOREIGN KEY (matricula_id) REFERENCES matriculas(id) ON DELETE CASCADE,
        UNIQUE (sesion_id, matricula_id)
    );

    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL UNIQUE,
        email TEXT,
        nombre_completo TEXT NOT NULL,
        clave_hash TEXT NOT NULL,
        rol TEXT NOT NULL DEFAULT 'DOCENTE' CHECK (rol IN ('ADMIN', 'DOCENTE')),
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        cambiar_password INTEGER NOT NULL DEFAULT 0
            CHECK (cambiar_password IN (0, 1)),
        debe_cambiar_password INTEGER NOT NULL DEFAULT 1
            CHECK (debe_cambiar_password IN (0, 1)),
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS administradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL,
        clave_hash TEXT NOT NULL,
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        cambiar_password INTEGER NOT NULL DEFAULT 1
            CHECK (cambiar_password IN (0, 1)),
        debe_cambiar_password INTEGER NOT NULL DEFAULT 1
            CHECK (debe_cambiar_password IN (0, 1)),
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_estudiantes_carrera
        ON estudiantes(carrera_id);
    CREATE INDEX IF NOT EXISTS idx_secciones_periodo
        ON secciones(periodo_id);
    CREATE INDEX IF NOT EXISTS idx_matriculas_estudiante
        ON matriculas(estudiante_id);
    CREATE INDEX IF NOT EXISTS idx_matriculas_seccion
        ON matriculas(seccion_id);
    """
    with transaccion() as conexion:
        conexion.executescript(esquema)
        columnas_docentes = {
            columna["name"]
            for columna in conexion.execute("PRAGMA table_info(docentes)")
        }
        for campo in (
            "numero_identidad",
            "fecha_nacimiento",
            "nacionalidad",
            "tipo_nacionalidad",
            "fecha_ingreso",
            "foto_perfil",
        ):
            if campo not in columnas_docentes:
                conexion.execute(f"ALTER TABLE docentes ADD COLUMN {campo} TEXT")
        columnas_calificaciones = {
            columna["name"]
            for columna in conexion.execute("PRAGMA table_info(calificaciones)")
        }
        for campo in (
            "primer_parcial_registrado",
            "segundo_parcial_registrado",
            "tercer_parcial_registrado",
        ):
            if campo not in columnas_calificaciones:
                conexion.execute(
                    f"ALTER TABLE calificaciones ADD COLUMN {campo} "
                    "INTEGER NOT NULL DEFAULT 1 CHECK (" + campo + " IN (0, 1))"
                )
        esquema_matriculas = conexion.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'matriculas'"
        ).fetchone()["sql"]
        if "APROBADA" in esquema_matriculas or "REPROBADA" in esquema_matriculas:
            conexion.execute("PRAGMA foreign_keys = OFF")
            conexion.execute(
                """
                CREATE TABLE matriculas_nueva (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    estudiante_id INTEGER NOT NULL,
                    seccion_id INTEGER NOT NULL,
                    fecha_matricula TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    estado TEXT NOT NULL DEFAULT 'MATRICULADA'
                        CHECK (estado IN ('MATRICULADA', 'CANCELADA')),
                    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE RESTRICT,
                    FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE RESTRICT,
                    UNIQUE (estudiante_id, seccion_id)
                )
                """
            )
            conexion.execute(
                """
                INSERT INTO matriculas_nueva
                    (id, estudiante_id, seccion_id, fecha_matricula, estado)
                SELECT id, estudiante_id, seccion_id, fecha_matricula,
                       CASE WHEN estado = 'CANCELADA'
                            THEN 'CANCELADA' ELSE 'MATRICULADA' END
                FROM matriculas
                """
            )
            conexion.execute("DROP TABLE matriculas")
            conexion.execute(
                "ALTER TABLE matriculas_nueva RENAME TO matriculas"
            )
            conexion.execute("PRAGMA foreign_keys = ON")
            conexion.execute("CREATE INDEX IF NOT EXISTS idx_matriculas_estudiante ON matriculas(estudiante_id)")
            conexion.execute("CREATE INDEX IF NOT EXISTS idx_matriculas_seccion ON matriculas(seccion_id)")
        columnas_usuarios = {
            columna["name"]
            for columna in conexion.execute("PRAGMA table_info(usuarios)")
        }
        if "email" not in columnas_usuarios:
            conexion.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")
        if "cambiar_password" not in columnas_usuarios:
            conexion.execute(
                "ALTER TABLE usuarios ADD COLUMN cambiar_password INTEGER "
                "NOT NULL DEFAULT 0 CHECK (cambiar_password IN (0, 1))"
            )
        if "debe_cambiar_password" not in columnas_usuarios:
            conexion.execute(
                "ALTER TABLE usuarios ADD COLUMN debe_cambiar_password INTEGER "
                "NOT NULL DEFAULT 1 CHECK (debe_cambiar_password IN (0, 1))"
            )
            conexion.execute(
                """
                UPDATE usuarios
                SET debe_cambiar_password = cambiar_password
                """
            )
            conexion.execute(
                """
                UPDATE usuarios
                SET debe_cambiar_password = 1, cambiar_password = 1
                WHERE clave_hash = ?
                """,
                (hash_clave(CLAVE_DOCENTE_INICIAL),),
            )
        columnas_administradores = {
            columna["name"]
            for columna in conexion.execute("PRAGMA table_info(administradores)")
        }
        if "debe_cambiar_password" not in columnas_administradores:
            conexion.execute(
                "ALTER TABLE administradores ADD COLUMN debe_cambiar_password INTEGER "
                "NOT NULL DEFAULT 1 CHECK (debe_cambiar_password IN (0, 1))"
            )
            if "cambiar_password" in columnas_administradores:
                conexion.execute(
                    """
                    UPDATE administradores
                    SET debe_cambiar_password = cambiar_password
                    """
                )
            conexion.execute(
                """
                UPDATE administradores
                SET debe_cambiar_password = 1, cambiar_password = 1
                WHERE clave_hash = ?
                """,
                (hash_clave(CLAVE_ADMIN_INICIAL),),
            )
        marcadores_admin = ", ".join("?" for _ in CLAVES_ADMIN_ANTERIORES)
        conexion.execute(
            f"""
            UPDATE usuarios
            SET clave_hash = CASE
                    WHEN UPPER(TRIM(rol)) = 'ADMIN' THEN ?
                    ELSE ?
                END,
                cambiar_password = 1,
                debe_cambiar_password = 1
            WHERE (
                (UPPER(TRIM(rol)) = 'ADMIN' AND clave_hash IN ({marcadores_admin}))
                OR
                (UPPER(TRIM(rol)) = 'DOCENTE' AND clave_hash IN (
                    {", ".join("?" for _ in CLAVES_DOCENTE_ANTERIORES)}
                ))
            )
            """,
            (
                hash_clave(CLAVE_ADMIN_INICIAL),
                hash_clave(CLAVE_DOCENTE_INICIAL),
                *(hash_clave(clave) for clave in CLAVES_ADMIN_ANTERIORES),
                *(hash_clave(clave) for clave in CLAVES_DOCENTE_ANTERIORES),
            ),
        )
        conexion.execute(
            f"""
            UPDATE administradores
            SET clave_hash = ?, cambiar_password = 1, debe_cambiar_password = 1
            WHERE clave_hash IN ({marcadores_admin})
            """,
            (
                hash_clave(CLAVE_ADMIN_INICIAL),
                *(hash_clave(clave) for clave in CLAVES_ADMIN_ANTERIORES),
            ),
        )
        conexion.execute(
            """
            UPDATE usuarios
            SET debe_cambiar_password = 0, cambiar_password = 0
            WHERE debe_cambiar_password = 1 AND clave_hash <> ?
            """,
            (hash_clave(CLAVE_DOCENTE_INICIAL),),
        )
        conexion.execute(
            """
            UPDATE usuarios
            SET cambiar_password = debe_cambiar_password
            WHERE cambiar_password <> debe_cambiar_password
            """
        )
        conexion.execute(
            """
            UPDATE administradores
            SET debe_cambiar_password = 0, cambiar_password = 0
            WHERE debe_cambiar_password = 1 AND clave_hash <> ?
            """,
            (hash_clave(CLAVE_ADMIN_INICIAL),),
        )
        conexion.execute(
            """
            UPDATE administradores
            SET cambiar_password = debe_cambiar_password
            WHERE cambiar_password <> debe_cambiar_password
            """
        )
        conexion.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email_ci
            ON usuarios(LOWER(TRIM(email)))
            WHERE email IS NOT NULL AND TRIM(email) <> ''
            """
        )
        conexion.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_administradores_email_ci
            ON administradores(LOWER(TRIM(email)))
            """
        )
        conexion.execute(
            """
            UPDATE usuarios
            SET email = 'admin@universidad.edu'
            WHERE usuario = 'admin' AND rol = 'ADMIN' AND email IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM usuarios existente
                  WHERE LOWER(TRIM(existente.email)) = 'admin@universidad.edu'
              )
            """
        )
        conexion.execute(
            """
            INSERT OR IGNORE INTO asignaturas_carreras (asignatura_id, carrera_id)
            SELECT id, carrera_id FROM asignaturas
            """
        )
    _migrar_restriccion_periodos()


def _migrar_restriccion_periodos() -> None:
    conexion = obtener_conexion()
    try:
        esquema_periodos = conexion.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'periodos'"
        ).fetchone()["sql"]
        if "BETWEEN 1 AND 3" not in esquema_periodos:
            return

        conexion.execute("PRAGMA foreign_keys = OFF")
        conexion.execute("BEGIN")
        conexion.execute(
            """
            CREATE TABLE periodos_nuevo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anio INTEGER NOT NULL CHECK (anio BETWEEN 2020 AND 2100),
                numero INTEGER NOT NULL CHECK (numero BETWEEN 1 AND 4),
                fecha_inicio TEXT NOT NULL,
                fecha_fin TEXT NOT NULL,
                activo INTEGER NOT NULL DEFAULT 0 CHECK (activo IN (0, 1)),
                UNIQUE (anio, numero),
                CHECK (fecha_fin > fecha_inicio)
            )
            """
        )
        conexion.execute(
            """
            INSERT INTO periodos_nuevo (id, anio, numero, fecha_inicio, fecha_fin, activo)
            SELECT id, anio, numero, fecha_inicio, fecha_fin, activo
            FROM periodos
            """
        )
        conexion.execute("DROP TABLE periodos")
        conexion.execute("ALTER TABLE periodos_nuevo RENAME TO periodos")
        conexion.commit()
        conexion.execute("PRAGMA foreign_keys = ON")
        errores_fk = conexion.execute("PRAGMA foreign_key_check").fetchall()
        if errores_fk:
            raise sqlite3.IntegrityError(
                "La migración de períodos dejó referencias foráneas inválidas"
            )
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def cargar_datos_demostracion() -> None:
    """Inserta datos una sola vez para que la API no aparezca vacía."""
    with transaccion() as conexion:
        cantidad = conexion.execute("SELECT COUNT(*) FROM carreras").fetchone()[0]
        if cantidad > 0:
            return

        conexion.executescript(
            """
            INSERT INTO carreras (id, codigo, nombre, duracion_anios) VALUES
                (1, 'IS', 'Ingeniería en Sistemas', 5),
                (2, 'AE', 'Administración de Empresas', 4);

            INSERT INTO estudiantes
                (id, cuenta, nombres, apellidos, correo, telefono,
                 fecha_nacimiento, carrera_id, estado)
            VALUES
                (1, '20261001', 'Ana', 'Martínez', 'ana@universidad.edu',
                 '9999-1001', '2005-04-12', 1, 'ACTIVO'),
                (2, '20261002', 'Carlos', 'López', 'carlos@universidad.edu',
                 '9999-1002', '2004-11-08', 1, 'ACTIVO'),
                (3, '20261003', 'Sofía', 'Hernández', 'sofia@universidad.edu',
                 '9999-1003', '2005-01-20', 1, 'ACTIVO'),
                (4, '20261004', 'Luis', 'Rivera', 'luis@universidad.edu',
                 '9999-1004', '2003-09-16', 2, 'ACTIVO'),
                (5, '20251015', 'María', 'Mejía', 'maria@universidad.edu',
                 NULL, '2002-07-03', 1, 'INACTIVO');

            INSERT INTO docentes
                (id, numero_empleado, nombres, apellidos, correo,
                 especialidad, estado)
            VALUES
                (1, 'DOC-001', 'Elías', 'Flores', 'elias@universidad.edu',
                 'Programación y bases de datos', 'ACTIVO'),
                (2, 'DOC-002', 'Laura', 'Gómez', 'laura@universidad.edu',
                 'Redes y seguridad', 'ACTIVO'),
                (3, 'DOC-003', 'Mario', 'Pineda', 'mario@universidad.edu',
                 'Gestión empresarial', 'ACTIVO');

            INSERT INTO asignaturas
                (id, codigo, nombre, unidades_valorativas, carrera_id,
                 requisito_id, activo)
            VALUES
                (1, 'IS-110', 'Programación I', 4, 1, NULL, 1),
                (2, 'IS-210', 'Programación II', 4, 1, 1, 1),
                (3, 'IS-310', 'Estructura de Datos', 4, 1, 2, 1),
                (4, 'IS-220', 'Bases de Datos I', 4, 1, 1, 1),
                (5, 'AE-101', 'Administración I', 4, 2, NULL, 1);

            INSERT INTO periodos
                (id, anio, numero, fecha_inicio, fecha_fin, activo)
            VALUES
                (1, 2026, 1, '2026-01-15', '2026-04-30', 0),
                (2, 2026, 3, '2026-09-01', '2026-12-15', 1);

            INSERT INTO aulas (id, codigo, edificio, capacidad, activo) VALUES
                (1, 'LAB-01', 'Edificio A', 30, 1),
                (2, 'LAB-02', 'Edificio A', 25, 1),
                (3, 'AULA-05', 'Edificio B', 40, 1);

            INSERT INTO secciones
                (id, codigo, asignatura_id, docente_id, periodo_id, aula_id,
                 dias, hora_inicio, hora_fin, cupo_maximo, estado)
            VALUES
                (1, '0700', 1, 1, 1, 1, 'LU-MI', '07:00', '09:00', 25,
                 'FINALIZADA'),
                (2, '0700', 2, 1, 2, 1, 'LU-MI', '07:00', '09:00', 25,
                 'ABIERTA'),
                (3, '0900', 4, 1, 2, 2, 'LU-MI', '09:00', '11:00', 25,
                 'ABIERTA'),
                (4, '1300', 3, 2, 2, 1, 'MA-JU', '13:00', '15:00', 25,
                 'ABIERTA'),
                (5, '1800', 5, 3, 2, 3, 'MA-JU', '18:00', '20:00', 35,
                 'ABIERTA');

            INSERT INTO matriculas
                (id, estudiante_id, seccion_id, estado)
            VALUES
                (1, 1, 1, 'MATRICULADA'),
                (2, 2, 1, 'MATRICULADA'),
                (3, 1, 2, 'MATRICULADA'),
                (4, 2, 2, 'MATRICULADA'),
                (5, 3, 3, 'MATRICULADA'),
                (6, 4, 5, 'MATRICULADA');

            INSERT INTO calificaciones
                (id, matricula_id, primer_parcial, segundo_parcial,
                 tercer_parcial, nota_final, observacion)
            VALUES
                (1, 1, 80, 75, 85, 80, 'Aprobó Programación I'),
                (2, 2, 70, 68, 72, 70, 'Aprobó Programación I');
            """
        )

        conexion.execute(
            """
            INSERT INTO usuarios
                (usuario, email, nombre_completo, clave_hash, rol, cambiar_password)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                "admin",
                "admin@universidad.edu",
                "Administrador del Sistema",
                hash_clave(CLAVE_ADMIN_INICIAL),
                "ADMIN",
            ),
        )
        conexion.execute(
            """
            INSERT INTO usuarios
                (usuario, email, nombre_completo, clave_hash, rol, cambiar_password)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                "docente",
                "elias@universidad.edu",
                "Elías Flores",
                hash_clave(CLAVE_DOCENTE_INICIAL),
                "DOCENTE",
            ),
        )


def vincular_usuarios_docentes() -> None:
    """Vincula o provisiona cuentas DOCENTE para los registros existentes."""
    with transaccion() as conexion:
        columnas = [c["name"] for c in conexion.execute("PRAGMA table_info(usuarios)")]
        if "docente_id" not in columnas:
            conexion.execute(
                "ALTER TABLE usuarios ADD COLUMN docente_id INTEGER "
                "REFERENCES docentes(id) ON DELETE SET NULL"
            )
        conexion.execute(
            """
            UPDATE usuarios
            SET docente_id = (
                SELECT d.id FROM docentes d
                WHERE LOWER(TRIM(d.correo)) = LOWER(TRIM(usuarios.email))
            )
            WHERE rol = 'DOCENTE' AND docente_id IS NULL
              AND EXISTS (
                  SELECT 1 FROM docentes d
                  WHERE LOWER(TRIM(d.correo)) = LOWER(TRIM(usuarios.email))
              )
            """
        )
        # Enlaza por nombre completo (usuario 'docente' = Elías Flores).
        conexion.execute(
            """
            UPDATE usuarios
            SET docente_id = (
                SELECT d.id FROM docentes d
                WHERE d.nombres || ' ' || d.apellidos = usuarios.nombre_completo
            )
            WHERE rol = 'DOCENTE' AND docente_id IS NULL
            """
        )
        docentes = conexion.execute(
            """
            SELECT id, correo, nombres, apellidos, estado
            FROM docentes
            ORDER BY id
            """
        ).fetchall()
        for docente in docentes:
            correo = str(docente["correo"]).strip().lower()
            cuenta = conexion.execute(
                "SELECT id, usuario, rol, docente_id FROM usuarios WHERE docente_id = ?",
                (docente["id"],),
            ).fetchone()
            if cuenta is None:
                cuenta = conexion.execute(
                    """
                    SELECT id, usuario, rol, docente_id FROM usuarios
                    WHERE LOWER(TRIM(COALESCE(email, ''))) = LOWER(TRIM(?))
                    """,
                    (correo,),
                ).fetchone()

            if cuenta is not None:
                if (
                    str(cuenta["rol"]).strip().upper() != "DOCENTE"
                    or cuenta["docente_id"] not in (None, docente["id"])
                ):
                    raise RuntimeError(
                        f"El correo {correo} está asociado a otra cuenta y no "
                        "puede vincularse con el docente registrado."
                    )
                conexion.execute(
                    """
                    UPDATE usuarios
                    SET email = ?, nombre_completo = ?, activo = ?, docente_id = ?
                    WHERE id = ?
                    """,
                    (
                        correo,
                        f"{docente['nombres']} {docente['apellidos']}",
                        int(docente["estado"] == "ACTIVO"),
                        docente["id"],
                        cuenta["id"],
                    ),
                )
                continue

            usuario_existente = conexion.execute(
                "SELECT 1 FROM usuarios WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(?))",
                (correo,),
            ).fetchone()
            nombre_usuario = correo
            if usuario_existente is not None:
                base_usuario = f"docente-{docente['id']}"
                nombre_usuario = base_usuario
                sufijo = 1
                while conexion.execute(
                    "SELECT 1 FROM usuarios WHERE usuario = ?", (nombre_usuario,)
                ).fetchone():
                    nombre_usuario = f"{base_usuario}-{sufijo}"
                    sufijo += 1
            conexion.execute(
                """
                INSERT INTO usuarios
                    (usuario, email, nombre_completo, clave_hash, rol, activo,
                     cambiar_password, debe_cambiar_password, docente_id)
                VALUES (?, ?, ?, ?, 'DOCENTE', ?, 1, 1, ?)
                """,
                (
                    nombre_usuario,
                    correo,
                    f"{docente['nombres']} {docente['apellidos']}",
                    hash_clave(CLAVE_DOCENTE_INICIAL),
                    int(docente["estado"] == "ACTIVO"),
                    docente["id"],
                ),
            )
        conexion.execute(
            """
            UPDATE usuarios
            SET email = (
                SELECT d.correo FROM docentes d
                WHERE d.id = usuarios.docente_id
            )
            WHERE usuario = 'docente' AND rol = 'DOCENTE'
              AND email = 'docente@universidad.edu'
              AND docente_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM usuarios existente
                  WHERE existente.id <> usuarios.id
                    AND LOWER(TRIM(existente.email)) = LOWER(TRIM((
                        SELECT d.correo FROM docentes d
                        WHERE d.id = usuarios.docente_id
                    )))
              )
            """
        )


def inicializar_base_datos() -> None:
    crear_tablas()
    cargar_datos_demostracion()
    _sincronizar_carreras_asignaturas()
    sincronizar_administradores()
    vincular_usuarios_docentes()


def _sincronizar_carreras_asignaturas() -> None:
    with transaccion() as conexion:
        conexion.execute(
            """
            INSERT OR IGNORE INTO asignaturas_carreras (asignatura_id, carrera_id)
            SELECT id, carrera_id FROM asignaturas
            """
        )


def sincronizar_administradores() -> None:
    """Migra cuentas ADMIN existentes a la tabla autoritativa de administradores."""
    with transaccion() as conexion:
        conexion.execute(
            """
            INSERT INTO administradores
                (usuario, nombre, email, clave_hash, activo, cambiar_password)
            SELECT u.usuario, u.nombre_completo, COALESCE(u.email, u.usuario),
                   u.clave_hash, u.activo, u.cambiar_password
            FROM usuarios u
            WHERE UPPER(TRIM(u.rol)) = 'ADMIN'
              AND NOT EXISTS (
                  SELECT 1 FROM administradores a
                  WHERE LOWER(TRIM(a.usuario)) = LOWER(TRIM(u.usuario))
                     OR LOWER(TRIM(a.email)) =
                        LOWER(TRIM(COALESCE(u.email, u.usuario)))
              )
            """
        )
        conexion.execute(
            """
            UPDATE administradores
            SET clave_hash = ?, cambiar_password = 1, debe_cambiar_password = 1
            WHERE usuario = 'admin' AND clave_hash = ?
            """,
            (hash_clave(CLAVE_ADMIN_INICIAL), hash_clave("admin123")),
        )
        conexion.execute(
            """
            UPDATE usuarios
            SET clave_hash = ?, cambiar_password = 1, debe_cambiar_password = 1
            WHERE usuario = 'docente' AND rol = 'DOCENTE'
              AND clave_hash = ?
            """,
            (hash_clave(CLAVE_DOCENTE_INICIAL), hash_clave("docente123")),
        )
        conexion.execute("DELETE FROM usuarios WHERE UPPER(TRIM(rol)) = 'ADMIN'")



# --- Configuración de SQLAlchemy para el módulo de Autenticación ---

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()