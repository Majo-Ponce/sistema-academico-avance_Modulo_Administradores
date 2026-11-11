import pytest


def test_primer_ingreso_obliga_a_cambiar_contrasena(cliente_sin_login):
    import app.database as database

    login = cliente_sin_login.post(
        "/api/v1/auth/login",
        json={"email": "admin@universidad.edu", "password": database.CLAVE_ADMIN_INICIAL},
    )
    assert login.status_code == 200
    assert login.json()["cambiar_password"] is True
    assert login.json()["debe_cambiar_password"] is True
    cabecera = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert cliente_sin_login.get(
        "/api/v1/reportes/dashboard", headers=cabecera
    ).status_code == 403

    cambio = cliente_sin_login.post(
        "/api/v1/auth/cambiar-password",
        headers=cabecera,
        json={
            "clave_actual": database.CLAVE_ADMIN_INICIAL,
            "clave_nueva": "admin-cambiada-1234",
        },
    )
    assert cambio.status_code == 200
    assert cliente_sin_login.get(
        "/api/v1/reportes/dashboard", headers=cabecera
    ).status_code == 200
    database.inicializar_base_datos()
    login_recurrente = cliente_sin_login.post(
        "/api/v1/auth/login",
        json={"email": "admin@universidad.edu", "password": "admin-cambiada-1234"},
    )
    assert login_recurrente.status_code == 200
    assert login_recurrente.json()["cambiar_password"] is False
    assert login_recurrente.json()["debe_cambiar_password"] is False
    with database.conexion_lectura() as conexion:
        bandera_guardada = conexion.execute(
            "SELECT debe_cambiar_password FROM administradores WHERE usuario = 'admin'"
        ).fetchone()["debe_cambiar_password"]
    assert bandera_guardada == 0


def test_migra_claves_temporales_anteriores_sin_reemplazar_claves_personales(
    cliente_sin_login,
):
    import app.database as database

    with database.transaccion() as conexion:
        conexion.execute(
            """
            UPDATE administradores
            SET clave_hash = ?, cambiar_password = 0, debe_cambiar_password = 0
            WHERE usuario = 'admin'
            """,
            (database.hash_clave("passwordadmin123"),),
        )
        conexion.execute(
            """
            UPDATE usuarios
            SET clave_hash = ?, cambiar_password = 0, debe_cambiar_password = 0
            WHERE usuario = 'docente'
            """,
            (database.hash_clave("passworddocente123"),),
        )
        conexion.execute(
            """
            INSERT INTO administradores
                (usuario, nombre, email, clave_hash, activo,
                 cambiar_password, debe_cambiar_password)
            VALUES ('admin-personal', 'Admin Personal',
                    'personal@universidad.edu', ?, 1, 0, 0)
            """,
            (database.hash_clave("clave-personal-5678"),),
        )

    database.crear_tablas()

    for email, password in (
        ("admin@universidad.edu", database.CLAVE_ADMIN_INICIAL),
        ("elias@universidad.edu", database.CLAVE_DOCENTE_INICIAL),
    ):
        respuesta = cliente_sin_login.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["debe_cambiar_password"] is True

    with database.conexion_lectura() as conexion:
        personal = conexion.execute(
            """
            SELECT clave_hash, debe_cambiar_password
            FROM administradores WHERE usuario = 'admin-personal'
            """
        ).fetchone()
    assert personal["clave_hash"] == database.hash_clave("clave-personal-5678")
    assert personal["debe_cambiar_password"] == 0


def test_docentes_existentes_sin_cuenta_pueden_iniciar_con_clave_temporal(
    cliente_sin_login,
):
    import app.database as database

    for correo, nombre, nueva_clave in (
        ("laura@universidad.edu", "Laura Gómez", "laura-segura-123"),
        ("mario@universidad.edu", "Mario Pineda", "mario-segura-123"),
    ):
        login = cliente_sin_login.post(
            "/api/v1/auth/login",
            json={"email": correo, "password": database.CLAVE_DOCENTE_INICIAL},
        )
        assert login.status_code == 200
        assert login.json()["nombre_completo"] == nombre
        assert login.json()["rol"] == "DOCENTE"
        assert login.json()["debe_cambiar_password"] is True

        cabecera = {"Authorization": "Bearer " + login.json()["access_token"]}
        cambio = cliente_sin_login.post(
            "/api/v1/auth/cambiar-password",
            headers=cabecera,
            json={
                "clave_actual": database.CLAVE_DOCENTE_INICIAL,
                "clave_nueva": nueva_clave,
            },
        )
        assert cambio.status_code == 200

        login_recurrente = cliente_sin_login.post(
            "/api/v1/auth/login",
            json={"email": correo, "password": nueva_clave},
        )
        assert login_recurrente.status_code == 200
        assert login_recurrente.json()["debe_cambiar_password"] is False


def test_inicio_y_dashboard(cliente):
    # La raíz "/" ahora sirve el frontend (login + dashboard) desde la
    # carpeta frontend/, en vez de devolver un JSON de bienvenida.
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]

    salud = cliente.get("/salud")
    assert salud.status_code == 200
    assert salud.json()["estado"] == "OK"

    dashboard = cliente.get("/api/v1/reportes/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["estudiantes_activos"] == 4
    assert dashboard.json()["periodo_activo"] == "2026-3"


def test_login_correcto_e_incorrecto(cliente):
    correcto = cliente.post(
        "/api/v1/auth/login", json={"usuario": "admin", "clave": "admin-test-1234"}
    )
    assert correcto.status_code == 200
    assert correcto.json()["rol"] == "ADMIN"

    incorrecto = cliente.post(
        "/api/v1/auth/login", json={"usuario": "admin", "clave": "clave-mala"}
    )
    assert incorrecto.status_code == 401


def test_login_multiadministrador_por_correo(cliente):
    import app.database as database

    with database.transaccion() as conexion:
        conexion.execute(
            """
            INSERT INTO administradores
                (usuario, email, nombre, clave_hash, activo, cambiar_password)
            VALUES (?, ?, ?, ?, 1, 0)
            """,
            (
                "admin-secundario",
                "otra.admin@universidad.edu",
                "María Ponce",
                database.hash_clave("clave-admin-456"),
            ),
        )

    respuesta = cliente.post(
        "/api/v1/auth/login",
        json={"email": "OTRA.ADMIN@universidad.edu", "password": "clave-admin-456"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre_completo"] == "María Ponce"
    assert respuesta.json()["rol"] == "ADMIN"
    catalogo = cliente.get(
        "/api/v1/carreras",
        headers={"Authorization": f"Bearer {respuesta.json()['access_token']}"},
    )
    assert catalogo.status_code == 200


def test_crud_administradores_y_bloqueo_hasta_cambio(cliente):
    administrador_actual = next(
        cuenta
        for cuenta in cliente.get("/api/v1/administradores").json()
        if cuenta["usuario"] == "admin"
    )
    intento_desactivar_propia = cliente.put(
        f"/api/v1/administradores/{administrador_actual['id']}",
        json={
            "usuario": "admin",
            "nombre": "Administrador del Sistema",
            "email": "admin@universidad.edu",
            "activo": False,
        },
    )
    assert intento_desactivar_propia.status_code == 409
    assert cliente.delete(
        f"/api/v1/administradores/{administrador_actual['id']}"
    ).status_code == 409

    creado = cliente.post(
        "/api/v1/administradores",
        json={
            "usuario": "admin-nuevo",
            "nombre": "Admin Nuevo",
            "email": "admin.nuevo@universidad.edu",
        },
    )
    assert creado.status_code == 201
    cuenta = creado.json()
    assert cuenta["cambiar_password"] is True
    assert cuenta["debe_cambiar_password"] is True
    assert "clave_hash" not in cuenta

    login = cliente.post(
        "/api/v1/auth/login",
        json={
            "email": "admin.nuevo@universidad.edu",
            "password": "password.admin",
        },
    )
    assert login.status_code == 200
    cabecera = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert cliente.get(
        "/api/v1/reportes/dashboard", headers=cabecera
    ).status_code == 403
    cambio = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers=cabecera,
        json={
            "clave_actual": "password.admin",
            "clave_nueva": "admin-nuevo-1234",
        },
    )
    assert cambio.status_code == 200
    assert cliente.get(
        "/api/v1/reportes/dashboard", headers=cabecera
    ).status_code == 200

    actualizado = cliente.put(
        f"/api/v1/administradores/{cuenta['id']}",
        json={
            "usuario": "admin-nuevo",
            "nombre": "Admin Actualizado",
            "email": "admin.nuevo@universidad.edu",
            "activo": False,
        },
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["cambiar_password"] is False
    assert cliente.post(
        "/api/v1/auth/login",
        json={
            "email": "admin.nuevo@universidad.edu",
            "password": "admin-nuevo-1234",
        },
    ).status_code == 403
    assert cliente.delete(
        f"/api/v1/administradores/{cuenta['id']}"
    ).status_code == 200


def test_administrador_rechaza_contrasena_en_el_formulario(cliente):
    creado = cliente.post(
        "/api/v1/administradores",
        json={
            "usuario": "admin-personal",
            "nombre": "Admin Personal",
            "email": "admin.personal@universidad.edu",
            "clave": "admin-personal-5678",
        },
    )
    assert creado.status_code == 422


def test_migrar_correo_en_base_legacy(tmp_path, monkeypatch):
    import sqlite3
    import app.database as database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "legacy.db")
    with sqlite3.connect(database.DB_PATH) as conexion:
        conexion.execute(
            """
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                nombre_completo TEXT NOT NULL,
                clave_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'DOCENTE',
                activo INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conexion.execute(
            """
            INSERT INTO usuarios (usuario, nombre_completo, clave_hash, rol)
            VALUES ('admin', 'Administrador del Sistema', 'hash', 'ADMIN')
            """
        )

    database.crear_tablas()

    with database.conexion_lectura() as conexion:
        columnas = {
            columna["name"]
            for columna in conexion.execute("PRAGMA table_info(usuarios)")
        }
        admin = conexion.execute(
            "SELECT email FROM usuarios WHERE usuario = 'admin'"
        ).fetchone()
    assert "email" in columnas
    assert admin["email"] == "admin@universidad.edu"


def test_modulos_catalogo_administrador(cliente):
    carrera = cliente.post(
        "/api/v1/carreras",
        json={
            "codigo": "ARQ",
            "nombre": "Arquitectura",
            "duracion_anios": 5,
            "activo": True,
        },
    )
    assert carrera.status_code == 201
    carrera_id = carrera.json()["id"]
    assert any(item["id"] == carrera_id for item in cliente.get("/api/v1/carreras").json())

    carrera_editada = cliente.put(
        f"/api/v1/carreras/{carrera_id}",
        json={
            "codigo": "ARQ",
            "nombre": "Arquitectura y Diseño",
            "duracion_anios": 5,
            "activo": False,
        },
    )
    assert carrera_editada.status_code == 200
    assert carrera_editada.json()["activo"] is False

    periodo = cliente.post(
        "/api/v1/periodos",
        json={
            "anio": 2027,
            "numero": 2,
            "fecha_inicio": "2027-05-01",
            "fecha_fin": "2027-08-31",
            "activo": False,
        },
    )
    assert periodo.status_code == 201
    periodo_id = periodo.json()["id"]
    periodo_editado = cliente.put(
        f"/api/v1/periodos/{periodo_id}",
        json={
            "anio": 2027,
            "numero": 2,
            "fecha_inicio": "2027-05-01",
            "fecha_fin": "2027-08-31",
            "activo": True,
        },
    )
    assert periodo_editado.status_code == 200
    assert periodo_editado.json()["activo"] is True
    assert periodo_editado.json()["nombre"] == "2027-2"

    cuarto_periodo = cliente.post(
        "/api/v1/periodos",
        json={
            "anio": 2027,
            "numero": 4,
            "fecha_inicio": "2027-11-01",
            "fecha_fin": "2028-01-31",
            "activo": False,
        },
    )
    assert cuarto_periodo.status_code == 201
    assert cuarto_periodo.json()["nombre"] == "2027-4"
    periodo_fuera_de_rango = cliente.post(
        "/api/v1/periodos",
        json={
            "anio": 2027,
            "numero": 5,
            "fecha_inicio": "2028-02-01",
            "fecha_fin": "2028-04-30",
            "activo": False,
        },
    )
    assert periodo_fuera_de_rango.status_code == 422

    aula = cliente.post(
        "/api/v1/aulas",
        json={"codigo": "LAB-TEST", "edificio": "Edificio C", "capacidad": 35},
    )
    assert aula.status_code == 201
    aula_id = aula.json()["id"]
    aula_editada = cliente.put(
        f"/api/v1/aulas/{aula_id}",
        json={
            "codigo": "LAB-TEST",
            "edificio": "Edificio C",
            "capacidad": 35,
            "activo": False,
        },
    )
    assert aula_editada.status_code == 200
    assert aula_editada.json()["activo"] is False
    assert any(item["id"] == aula_id for item in cliente.get("/api/v1/aulas").json())


def test_datos_iniciales_y_relaciones(cliente):
    respuesta = cliente.get("/api/v1/secciones")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 5
    assert respuesta.json()[0]["asignatura_codigo"]
    assert "cupos_disponibles" in respuesta.json()[0]
    asignaturas = cliente.get("/api/v1/asignaturas").json()
    inicial = next(item for item in asignaturas if item["codigo"] == "IS-110")
    assert inicial["carrera_ids"] == [1]
    assert inicial["carrera_nombres"] == ["Ingeniería en Sistemas"]


def test_crear_y_consultar_estudiante(cliente):
    nuevo = {
        "cuenta": "20262020",
        "nombres": "Pedro",
        "apellidos": "Castillo",
        "correo": "pedro@universidad.edu",
        "telefono": "9999-2020",
        "fecha_nacimiento": "2004-06-15",
        "carrera_id": 1,
        "estado": "ACTIVO",
    }
    creada = cliente.post("/api/v1/estudiantes", json=nuevo)
    assert creada.status_code == 201
    estudiante_id = creada.json()["id"]
    assert creada.json()["carrera_codigo"] == "IS"

    consulta = cliente.get(f"/api/v1/estudiantes/{estudiante_id}")
    assert consulta.status_code == 200
    assert consulta.json()["cuenta"] == "20262020"


def test_editar_docente_y_asignatura(cliente):
    docente = cliente.post(
        "/api/v1/docentes",
        json={
            "numero_empleado": "DOC-TEST",
            "nombres": "Elena",
            "apellidos": "Vargas",
            "correo": "elena.vargas@universidad.edu",
            "especialidad": "Matemáticas",
            "estado": "ACTIVO",
            "clave": "elena-segura-123",
        },
    )
    assert docente.status_code == 201
    docente_id = docente.json()["id"]
    docente_actualizado = cliente.put(
        f"/api/v1/docentes/{docente_id}",
        json={
            "numero_empleado": "DOC-TEST",
            "nombres": "Elena",
            "apellidos": "Vargas",
            "correo": "elena.vargas@universidad.edu",
            "especialidad": "Matemáticas aplicadas",
            "estado": "INACTIVO",
        },
    )
    assert docente_actualizado.status_code == 200
    assert docente_actualizado.json()["especialidad"] == "Matemáticas aplicadas"
    assert docente_actualizado.json()["estado"] == "INACTIVO"

    asignatura = cliente.post(
        "/api/v1/asignaturas",
        json={
            "codigo": "IS-TEST",
            "nombre": "Asignatura de prueba",
            "unidades_valorativas": 3,
            "carrera_id": 1,
            "requisito_id": 1,
            "activo": True,
        },
    )
    assert asignatura.status_code == 201
    asignatura_id = asignatura.json()["id"]
    asignatura_actualizada = cliente.put(
        f"/api/v1/asignaturas/{asignatura_id}",
        json={
            "codigo": "IS-TEST",
            "nombre": "Asignatura editada",
            "unidades_valorativas": 4,
            "carrera_id": 1,
            "requisito_id": 2,
            "activo": True,
        },
    )
    assert asignatura_actualizada.status_code == 200
    assert asignatura_actualizada.json()["requisito_id"] == 2
    assert asignatura_actualizada.json()["nombre"] == "Asignatura editada"


def test_asignatura_asociada_a_varias_carreras(cliente):
    segunda_carrera = cliente.post(
        "/api/v1/carreras",
        json={
            "codigo": "IND",
            "nombre": "Ingeniería Industrial",
            "duracion_anios": 5,
            "activo": True,
        },
    )
    assert segunda_carrera.status_code == 201
    carrera_id = segunda_carrera.json()["id"]

    creada = cliente.post(
        "/api/v1/asignaturas",
        json={
            "codigo": "MAT-COM",
            "nombre": "Matemática compartida",
            "unidades_valorativas": 4,
            "carrera_ids": [1, carrera_id],
            "activo": True,
        },
    )
    assert creada.status_code == 201
    assert set(creada.json()["carrera_ids"]) == {1, carrera_id}
    assert set(creada.json()["carrera_nombres"]) == {
        "Ingeniería en Sistemas",
        "Ingeniería Industrial",
    }

    filtrada = cliente.get(f"/api/v1/asignaturas?carrera_id={carrera_id}")
    assert any(item["id"] == creada.json()["id"] for item in filtrada.json())

    actualizada = cliente.put(
        f"/api/v1/asignaturas/{creada.json()['id']}",
        json={
            "codigo": "MAT-COM",
            "nombre": "Matemática compartida",
            "unidades_valorativas": 4,
            "carrera_ids": [carrera_id],
            "activo": True,
        },
    )
    assert actualizada.status_code == 200
    assert actualizada.json()["carrera_ids"] == [carrera_id]


def test_matricular_estudiante_de_carrera_secundaria_en_asignatura_multicarrera(cliente):
    asignatura = cliente.post(
        "/api/v1/asignaturas",
        json={
            "codigo": "MAT-MULTI",
            "nombre": "Asignatura multicarrera",
            "unidades_valorativas": 3,
            "carrera_ids": [1, 2],
            "activo": True,
        },
    )
    assert asignatura.status_code == 201

    seccion = cliente.post(
        "/api/v1/secciones",
        json={
            "codigo": "1600",
            "asignatura_id": asignatura.json()["id"],
            "docente_id": 2,
            "periodo_id": 2,
            "aula_id": None,
            "dias": "VI",
            "hora_inicio": "14:00",
            "hora_fin": "16:00",
            "cupo_maximo": 25,
            "estado": "ABIERTA",
        },
    )
    assert seccion.status_code == 201

    matricula = cliente.post(
        "/api/v1/matriculas",
        json={"estudiante_id": 4, "seccion_id": seccion.json()["id"]},
    )
    assert matricula.status_code == 201
    assert matricula.json()["estudiante_id"] == 4
    assert matricula.json()["asignatura_codigo"] == "MAT-MULTI"


def test_migra_periodos_con_referencias_a_limite_de_cuatro(tmp_path, monkeypatch):
    import sqlite3
    import app.database as database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "periodos_legacy.db")
    with sqlite3.connect(database.DB_PATH) as conexion:
        conexion.execute(
            """
            CREATE TABLE periodos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anio INTEGER NOT NULL CHECK (anio BETWEEN 2020 AND 2100),
                numero INTEGER NOT NULL CHECK (numero BETWEEN 1 AND 3),
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
            CREATE TABLE secciones (
                id INTEGER PRIMARY KEY,
                periodo_id INTEGER NOT NULL REFERENCES periodos(id)
            )
            """
        )
        conexion.execute(
            """
            INSERT INTO periodos
                (id, anio, numero, fecha_inicio, fecha_fin, activo)
            VALUES (10, 2026, 3, '2026-09-01', '2026-12-15', 1)
            """
        )
        conexion.execute(
            "INSERT INTO secciones (id, periodo_id) VALUES (1, 10)"
        )

    database._migrar_restriccion_periodos()

    with database.obtener_conexion() as conexion:
        conexion.execute(
            """
            INSERT INTO periodos
                (anio, numero, fecha_inicio, fecha_fin, activo)
            VALUES (2027, 4, '2027-11-01', '2028-01-31', 0)
            """
        )
        assert conexion.execute(
            "SELECT periodo_id FROM secciones WHERE id = 1"
        ).fetchone()["periodo_id"] == 10
        assert conexion.execute("PRAGMA foreign_key_check").fetchall() == []


def test_rechazar_cuenta_duplicada(cliente):
    duplicado = {
        "cuenta": "20261001",
        "nombres": "Otra",
        "apellidos": "Persona",
        "correo": "otra@universidad.edu",
        "fecha_nacimiento": "2003-01-01",
        "carrera_id": 1,
        "estado": "ACTIVO",
    }
    respuesta = cliente.post("/api/v1/estudiantes", json=duplicado)
    assert respuesta.status_code == 409


def test_matricula_valida_y_duplicada(cliente):
    # Ana aprobó IS-110 y puede matricular Bases de Datos I, que lo exige.
    respuesta = cliente.post(
        "/api/v1/matriculas", json={"estudiante_id": 1, "seccion_id": 3}
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["asignatura_codigo"] == "IS-220"

    repetida = cliente.post(
        "/api/v1/matriculas", json={"estudiante_id": 1, "seccion_id": 3}
    )
    assert repetida.status_code == 409


def test_editar_matricula_y_anular_registro_cancelado(cliente):
    seccion = cliente.post(
        "/api/v1/secciones",
        json={
            "codigo": "1500",
            "asignatura_id": 2,
            "docente_id": 1,
            "periodo_id": 2,
            "aula_id": None,
            "dias": "VI",
            "hora_inicio": "14:00",
            "hora_fin": "16:00",
            "cupo_maximo": 25,
            "estado": "ABIERTA",
        },
    )
    assert seccion.status_code == 201

    calificacion = cliente.put(
        "/api/v1/calificaciones/matricula/3",
        json={
            "primer_parcial": 90,
            "segundo_parcial": 90,
            "tercer_parcial": 90,
        },
    )
    assert calificacion.status_code == 200

    editada = cliente.put(
        "/api/v1/matriculas/3",
        json={"estudiante_id": 1, "seccion_id": seccion.json()["id"]},
    )
    assert editada.status_code == 200
    assert editada.json()["seccion_id"] == seccion.json()["id"]
    assert editada.json()["estado"] == "MATRICULADA"
    assert cliente.get("/api/v1/calificaciones/matricula/3").status_code == 404

    anulada = cliente.patch("/api/v1/matriculas/3/cancelar")
    assert anulada.status_code == 200
    editada_cancelada = cliente.put(
        "/api/v1/matriculas/3",
        json={"estudiante_id": 3, "seccion_id": seccion.json()["id"]},
    )
    assert editada_cancelada.status_code == 200
    assert editada_cancelada.json()["estado"] == "CANCELADA"
    assert editada_cancelada.json()["estudiante_id"] == 3

    anular_de_nuevo = cliente.patch("/api/v1/matriculas/3/cancelar")
    assert anular_de_nuevo.status_code == 200
    assert "ya estaba cancelada" in anular_de_nuevo.json()["mensaje"]


def test_reactivar_matricula_conserva_historial_y_calificacion(cliente):
    calificacion = cliente.put(
        "/api/v1/calificaciones/matricula/3",
        json={
            "primer_parcial": 90,
            "segundo_parcial": 80,
            "tercer_parcial": 70,
        },
    )
    assert calificacion.status_code == 200
    fecha_original = cliente.get("/api/v1/matriculas/3").json()["fecha_matricula"]

    cancelada = cliente.patch("/api/v1/matriculas/3/cancelar")
    assert cancelada.status_code == 200

    reactivada = cliente.patch("/api/v1/matriculas/3/reactivar")
    assert reactivada.status_code == 200
    assert reactivada.json()["mensaje"] == "Matrícula reactivada correctamente"
    matricula = cliente.get("/api/v1/matriculas/3")
    assert matricula.status_code == 200
    assert matricula.json()["estado"] == "MATRICULADA"
    assert matricula.json()["fecha_matricula"] == fecha_original
    assert cliente.get("/api/v1/calificaciones/matricula/3").json()["nota_final"] == 80


def test_reactivar_matricula_rechaza_seccion_sin_cupo(cliente):
    import app.database as database

    with database.transaccion() as conexion:
        conexion.execute(
            "UPDATE secciones SET cupo_maximo = 1 WHERE id = 2"
        )
    cancelada = cliente.patch("/api/v1/matriculas/3/cancelar")
    assert cancelada.status_code == 200

    reactivada = cliente.patch("/api/v1/matriculas/3/reactivar")
    assert reactivada.status_code == 409
    assert "cupo" in reactivada.json()["detail"].lower()
    assert cliente.get("/api/v1/matriculas/3").json()["estado"] == "CANCELADA"


def test_rechazar_requisito_pendiente(cliente):
    # Sofía no tiene aprobada Programación I.
    respuesta = cliente.post(
        "/api/v1/matriculas", json={"estudiante_id": 3, "seccion_id": 2}
    )
    assert respuesta.status_code == 409
    assert "requisito" in respuesta.json()["detail"].lower()


def test_rechazar_choque_de_horario(cliente):
    nueva_seccion = {
        "codigo": "0800",
        "asignatura_id": 1,
        "docente_id": 2,
        "periodo_id": 2,
        "aula_id": 3,
        "dias": "LU-MI",
        "hora_inicio": "08:00",
        "hora_fin": "10:00",
        "cupo_maximo": 30,
        "estado": "ABIERTA",
    }
    seccion = cliente.post("/api/v1/secciones", json=nueva_seccion)
    assert seccion.status_code == 201

    respuesta = cliente.post(
        "/api/v1/matriculas",
        json={"estudiante_id": 1, "seccion_id": seccion.json()["id"]},
    )
    assert respuesta.status_code == 409
    assert "choque" in respuesta.json()["detail"].lower()


def test_calificar_no_cambia_estado_de_matricula(cliente):
    respuesta = cliente.put(
        "/api/v1/calificaciones/matricula/3",
        json={
            "primer_parcial": 80,
            "segundo_parcial": 70,
            "tercer_parcial": 60,
            "observacion": "Promedio calculado por la API",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nota_final"] == 70
    assert respuesta.json()["resultado"] == "APROBADA"

    matricula = cliente.get("/api/v1/matriculas/3")
    assert matricula.json()["estado"] == "MATRICULADA"


def test_estados_matricula_solo_permiten_matriculada_o_cancelada(cliente):
    estados = cliente.get("/api/v1/matriculas").json()
    assert {matricula["estado"] for matricula in estados} == {"MATRICULADA"}

    filtro_aprobada = cliente.get("/api/v1/matriculas?estado=APROBADA")
    filtro_reprobada = cliente.get("/api/v1/matriculas?estado=REPROBADA")
    assert filtro_aprobada.status_code == 422
    assert filtro_reprobada.status_code == 422


def test_migrar_estados_legacy_de_matriculas(tmp_path, monkeypatch):
    import sqlite3
    import app.database as database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "estados_legacy.db")
    with sqlite3.connect(database.DB_PATH) as conexion:
        conexion.executescript(
            """
            CREATE TABLE estudiantes (id INTEGER PRIMARY KEY, carrera_id INTEGER);
            INSERT INTO estudiantes (id, carrera_id) VALUES (1, 1);
            CREATE TABLE secciones (id INTEGER PRIMARY KEY, periodo_id INTEGER);
            INSERT INTO secciones (id, periodo_id) VALUES (1, 1), (2, 1);
            CREATE TABLE matriculas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estudiante_id INTEGER NOT NULL,
                seccion_id INTEGER NOT NULL,
                fecha_matricula TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                estado TEXT NOT NULL DEFAULT 'MATRICULADA'
                    CHECK (estado IN ('MATRICULADA', 'CANCELADA', 'APROBADA', 'REPROBADA')),
                FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE RESTRICT,
                FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE RESTRICT,
                UNIQUE (estudiante_id, seccion_id)
            );
            INSERT INTO matriculas (id, estudiante_id, seccion_id, estado)
            VALUES (1, 1, 1, 'APROBADA'), (2, 1, 2, 'CANCELADA');
            CREATE TABLE calificaciones (
                id INTEGER PRIMARY KEY,
                matricula_id INTEGER NOT NULL UNIQUE,
                FOREIGN KEY (matricula_id) REFERENCES matriculas(id) ON DELETE CASCADE
            );
            INSERT INTO calificaciones (id, matricula_id) VALUES (10, 1);
            """
        )

    database.crear_tablas()

    with database.conexion_lectura() as conexion:
        estados = conexion.execute(
            "SELECT id, estado FROM matriculas ORDER BY id"
        ).fetchall()
        esquema = conexion.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'matriculas'"
        ).fetchone()["sql"]
        nota = conexion.execute(
            "SELECT matricula_id FROM calificaciones WHERE id = 10"
        ).fetchone()["matricula_id"]
        referencias_invalidas = conexion.execute("PRAGMA foreign_key_check").fetchall()
    assert [tuple(fila) for fila in estados] == [
        (1, "MATRICULADA"),
        (2, "CANCELADA"),
    ]
    assert "'APROBADA'" not in esquema
    assert "'REPROBADA'" not in esquema
    assert nota == 1
    assert referencias_invalidas == []

    with pytest.raises(sqlite3.IntegrityError):
        with database.transaccion() as conexion:
            conexion.execute(
                "UPDATE matriculas SET estado = 'APROBADA' WHERE id = 1"
            )


def test_docente_califica_solo_matriculas_de_sus_secciones(cliente):
    login = cliente.post(
        "/api/v1/auth/login",
        json={"usuario": "docente", "clave": "password.docente"},
    )
    cabecera_docente = {"Authorization": f"Bearer {login.json()['access_token']}"}

    cambio = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers=cabecera_docente,
        json={
            "clave_actual": "password.docente",
            "clave_nueva": "docente-test-1234",
        },
    )
    assert cambio.status_code == 200

    guardada = cliente.put(
        "/api/v1/panel-docente/mis-estudiantes/3/calificacion",
        headers=cabecera_docente,
        json={
            "primer_parcial": 90,
            "segundo_parcial": 80,
            "tercer_parcial": 70,
        },
    )
    assert guardada.status_code == 200
    assert guardada.json()["nota_final"] == 80
    assert guardada.json()["resultado"] == "APROBADA"

    estudiantes = cliente.get(
        "/api/v1/panel-docente/mis-estudiantes", headers=cabecera_docente
    )
    matricula = next(
        estudiante
        for estudiante in estudiantes.json()
        if estudiante["matricula_id"] == 3
    )
    assert matricula["primer_parcial"] == 90
    assert matricula["nota_final"] == 80

    ajena = cliente.put(
        "/api/v1/panel-docente/mis-estudiantes/6/calificacion",
        headers=cabecera_docente,
        json={
            "primer_parcial": 90,
            "segundo_parcial": 80,
            "tercer_parcial": 70,
        },
    )
    assert ajena.status_code == 404


def test_cuenta_docente_creada_desde_administracion(cliente):
    sin_clave = cliente.post(
        "/api/v1/docentes",
        json={
            "numero_empleado": "DOC-CUENTA",
            "nombres": "Paula",
            "apellidos": "Santos",
            "correo": "paula.santos@universidad.edu",
            "especialidad": "Cálculo",
            "estado": "ACTIVO",
        },
    )
    assert sin_clave.status_code == 201
    docente = sin_clave
    assert docente.status_code == 201
    assert "clave" not in docente.json()

    login = cliente.post(
        "/api/v1/auth/login",
        json={
            "email": "PAULA.SANTOS@universidad.edu",
            "password": "password.docente",
        },
    )
    assert login.status_code == 200
    assert login.json()["cambiar_password"] is True
    assert login.json()["debe_cambiar_password"] is True
    assert login.json()["docente_id"] == docente.json()["id"]
    assert login.json()["nombre_completo"] == "Paula Santos"
    cabecera_docente = {"Authorization": "Bearer " + login.json()["access_token"]}
    cambio = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers=cabecera_docente,
        json={
            "clave_actual": "password.docente",
            "clave_nueva": "docente-seguro-123",
        },
    )
    assert cambio.status_code == 200
    segundo_login = cliente.post(
        "/api/v1/auth/login",
        json={
            "email": "PAULA.SANTOS@universidad.edu",
            "password": "docente-seguro-123",
        },
    )
    assert segundo_login.status_code == 200
    assert segundo_login.json()["debe_cambiar_password"] is False

    actualizado = cliente.put(
        f"/api/v1/docentes/{docente.json()['id']}",
        json={
            "numero_empleado": "DOC-CUENTA",
            "nombres": "Paula",
            "apellidos": "Santos",
            "correo": "paula.actualizada@universidad.edu",
            "especialidad": "Cálculo",
            "estado": "ACTIVO",
        },
    )
    assert actualizado.status_code == 200
    nuevo_login = cliente.post(
        "/api/v1/auth/login",
        json={
            "email": "paula.actualizada@universidad.edu",
            "password": "docente-seguro-123",
        },
    )
    assert nuevo_login.status_code == 200
    assert cliente.post(
        "/api/v1/auth/login",
        json={
            "email": "paula.santos@universidad.edu",
            "password": "docente-seguro-123",
        },
    ).status_code == 401


def test_panel_docente_filtra_periodo_y_califica_parciales_individuales(cliente):
    login = cliente.post(
        "/api/v1/auth/login",
        json={"email": "elias@universidad.edu", "password": "password.docente"},
    )
    assert login.status_code == 200
    assert login.json()["docente_id"] == 1
    cabecera = {"Authorization": f"Bearer {login.json()['access_token']}"}

    cambio = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers=cabecera,
        json={
            "clave_actual": "password.docente",
            "clave_nueva": "docente-test-1234",
        },
    )
    assert cambio.status_code == 200
    secciones = cliente.get(
        "/api/v1/panel-docente/mis-secciones", headers=cabecera
    )
    assert secciones.status_code == 200
    assert {seccion["id"] for seccion in secciones.json()} == {2, 3}
    resumen = cliente.get("/api/v1/panel-docente/resumen", headers=cabecera)
    assert resumen.status_code == 200
    assert resumen.json()["mis_secciones"] == 2
    assert resumen.json()["mis_estudiantes"] == 3

    estudiantes = cliente.get(
        "/api/v1/panel-docente/mis-secciones/2/estudiantes", headers=cabecera
    )
    assert estudiantes.status_code == 200
    assert len(estudiantes.json()["estudiantes"]) == 2
    assert estudiantes.json()["estudiantes"][0]["estado_academico"] == "Activo"
    assert estudiantes.json()["estudiantes"][0]["carrera_nombre"] == "Ingeniería en Sistemas"

    parcial_inicial = cliente.put(
        "/api/v1/panel-docente/mis-secciones/2/estudiantes/3/parcial",
        headers=cabecera,
        json={"parcial": 1, "nota": 90},
    )
    assert parcial_inicial.status_code == 200

    admin = cliente.post(
        "/api/v1/auth/login", json={"usuario": "admin", "clave": "admin-test-1234"}
    )
    cabecera_admin = {"Authorization": f"Bearer {admin.json()['access_token']}"}
    calificaciones = cliente.get(
        "/api/v1/calificaciones?seccion_id=2", headers=cabecera_admin
    )
    matricula_parcial = next(
        item for item in calificaciones.json() if item["matricula_id"] == 3
    )
    assert matricula_parcial["primer_parcial"] == 90
    assert matricula_parcial["segundo_parcial"] is None
    assert matricula_parcial["nota_final"] is None
    assert matricula_parcial["resultado"] is None
    historial = cliente.get(
        "/api/v1/reportes/historial-estudiante/1", headers=cabecera_admin
    )
    registro = next(
        item for item in historial.json()["historial"]
        if item["asignatura_codigo"] == "IS-210"
    )
    assert registro["nota_final"] is None

    for parcial, nota in ((2, 80), (3, 70)):
        guardada = cliente.put(
            f"/api/v1/panel-docente/mis-secciones/2/estudiantes/3/parcial",
            headers=cabecera,
            json={"parcial": parcial, "nota": nota},
        )
        assert guardada.status_code == 200

    estudiantes = cliente.get(
        "/api/v1/panel-docente/mis-secciones/2/estudiantes", headers=cabecera
    ).json()["estudiantes"]
    estudiante = next(item for item in estudiantes if item["matricula_id"] == 3)
    assert estudiante["nota_final"] == 80
    assert estudiante["estado_academico"] == "Aprobado"

    matricula_ajena = cliente.put(
        "/api/v1/panel-docente/mis-secciones/2/estudiantes/6/parcial",
        headers=cabecera,
        json={"parcial": 1, "nota": 90},
    )
    assert matricula_ajena.status_code == 404


def test_docente_administra_asistencia_solo_en_sus_secciones_activas(cliente):
    login = cliente.post(
        "/api/v1/auth/login",
        json={"email": "elias@universidad.edu", "password": "password.docente"},
    )
    assert login.status_code == 200
    cabecera = {"Authorization": f"Bearer {login.json()['access_token']}"}
    cambio = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers=cabecera,
        json={
            "clave_actual": "password.docente",
            "clave_nueva": "docente-asistencia-123",
        },
    )
    assert cambio.status_code == 200

    nueva_sesion = cliente.post(
        "/api/v1/panel-docente/mis-secciones/2/asistencia",
        headers=cabecera,
        json={"fecha": "2026-03-16"},
    )
    assert nueva_sesion.status_code == 201
    sesion_id = nueva_sesion.json()["id"]

    sesiones = cliente.get(
        "/api/v1/panel-docente/mis-secciones/2/asistencia",
        headers=cabecera,
    )
    assert sesiones.status_code == 200
    assert sesiones.json()[0]["fecha"] == "2026-03-16"
    assert sesiones.json()[0]["registros_completados"] == 0

    registros = cliente.get(
        f"/api/v1/panel-docente/mis-secciones/2/asistencia/{sesion_id}",
        headers=cabecera,
    )
    assert registros.status_code == 200
    assert len(registros.json()["registros"]) == 2
    assert all(registro["estado"] is None for registro in registros.json()["registros"])
    matricula_ids = [
        registro["matricula_id"] for registro in registros.json()["registros"]
    ]

    guardado = cliente.put(
        f"/api/v1/panel-docente/mis-secciones/2/asistencia/{sesion_id}",
        headers=cabecera,
        json={
            "registros": [
                {"matricula_id": matricula_ids[0], "estado": "PRESENTE"},
                {"matricula_id": matricula_ids[1], "estado": "TARDANZA"},
            ]
        },
    )
    assert guardado.status_code == 200
    assert guardado.json()["registros_guardados"] == 2
    actualizados = cliente.get(
        f"/api/v1/panel-docente/mis-secciones/2/asistencia/{sesion_id}",
        headers=cabecera,
    )
    assert {registro["estado"] for registro in actualizados.json()["registros"]} == {
        "PRESENTE",
        "TARDANZA",
    }

    duplicada = cliente.post(
        "/api/v1/panel-docente/mis-secciones/2/asistencia",
        headers=cabecera,
        json={"fecha": "2026-03-16"},
    )
    assert duplicada.status_code == 409
    seccion_ajena = cliente.get(
        f"/api/v1/panel-docente/mis-secciones/1/asistencia/{sesion_id}",
        headers=cabecera,
    )
    assert seccion_ajena.status_code == 404
    admin_no_autorizado = cliente.get(
        "/api/v1/panel-docente/mis-secciones/2/asistencia"
    )
    assert admin_no_autorizado.status_code == 403


def test_cancelar_matricula_libera_cupo(cliente):
    antes = cliente.get("/api/v1/secciones/2").json()["cupos_disponibles"]
    cancelada = cliente.patch("/api/v1/matriculas/3/cancelar")
    assert cancelada.status_code == 200
    despues = cliente.get("/api/v1/secciones/2").json()["cupos_disponibles"]
    assert despues == antes + 1


def test_reportes_de_historial_y_lista(cliente):
    historial = cliente.get("/api/v1/reportes/historial-estudiante/1")
    assert historial.status_code == 200
    assert historial.json()["resumen"]["unidades_valorativas_aprobadas"] == 4

    lista = cliente.get("/api/v1/reportes/lista-seccion/2")
    assert lista.status_code == 200
    assert lista.json()["cantidad_matriculados"] == 2


def test_docente_consulta_y_actualiza_su_perfil_personal(cliente):
    login = cliente.post(
        "/api/v1/auth/login",
        json={"email": "elias@universidad.edu", "password": "password.docente"},
    )
    assert login.status_code == 200
    cabecera = {"Authorization": f"Bearer {login.json()['access_token']}"}
    cambio = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers=cabecera,
        json={
            "clave_actual": "password.docente",
            "clave_nueva": "docente-perfil-test-123",
        },
    )
    assert cambio.status_code == 200

    guardado = cliente.put(
        "/api/v1/panel-docente/perfil",
        headers=cabecera,
        json={
            "nombres": "Elías",
            "apellidos": "Flores",
            "numero_identidad": "0801199000001",
            "fecha_nacimiento": "1990-06-15",
            "nacionalidad": "Hondureña",
            "tipo_nacionalidad": "Por nacimiento",
            "fecha_ingreso": "2020-02-01",
            "foto_perfil": None,
        },
    )
    assert guardado.status_code == 200
    assert guardado.json()["nombre_completo"] == "Elías Flores"
    assert guardado.json()["numero_identidad"] == "0801199000001"
    assert guardado.json()["nacionalidad"] == "Hondureña"
    assert guardado.json()["fecha_ingreso"] == "2020-02-01"
    assert guardado.json()["edad"] is not None

    perfil = cliente.get("/api/v1/panel-docente/perfil", headers=cabecera)
    assert perfil.status_code == 200
    assert perfil.json()["fecha_nacimiento"] == "1990-06-15"
    assert perfil.json()["tipo_nacionalidad"] == "Por nacimiento"
    assert perfil.json()["foto_perfil"] is None

    invalido = cliente.put(
        "/api/v1/panel-docente/perfil",
        headers=cabecera,
        json={
            "nombres": "Elías",
            "apellidos": "Flores",
            "foto_perfil": "data:image/png;base64,ZmFrZQ==",
        },
    )
    assert invalido.status_code == 422


def test_migra_columnas_perfil_en_tabla_docente_existente(tmp_path, monkeypatch):
    import sqlite3
    import app.database as database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "docentes_legacy.db")
    with sqlite3.connect(database.DB_PATH) as conexion:
        conexion.execute(
            """
            CREATE TABLE docentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_empleado TEXT NOT NULL UNIQUE,
                nombres TEXT NOT NULL,
                apellidos TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE,
                especialidad TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'ACTIVO',
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conexion.execute(
            """
            INSERT INTO docentes
                (numero_empleado, nombres, apellidos, correo, especialidad)
            VALUES ('DOC-LEGACY', 'Ana', 'López', 'ana@universidad.edu', 'Ciencias')
            """
        )

    database.crear_tablas()

    with database.conexion_lectura() as conexion:
        columnas = {
            fila["name"] for fila in conexion.execute("PRAGMA table_info(docentes)")
        }
        docente = conexion.execute(
            "SELECT nombres, numero_identidad, foto_perfil FROM docentes WHERE id = 1"
        ).fetchone()
    assert {
        "numero_identidad",
        "fecha_nacimiento",
        "nacionalidad",
        "tipo_nacionalidad",
        "fecha_ingreso",
        "foto_perfil",
    }.issubset(columnas)
    assert tuple(docente) == ("Ana", None, None)


def test_separacion_de_roles(cliente):
    login = cliente.post(
        "/api/v1/auth/login",
        json={"usuario": "docente", "clave": "password.docente"},
    )
    cabecera_docente = {"Authorization": f"Bearer {login.json()['access_token']}"}

    cambio = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers=cabecera_docente,
        json={
            "clave_actual": "password.docente",
            "clave_nueva": "docente-test-1234",
        },
    )
    assert cambio.status_code == 200

    # El docente NO puede usar los módulos globales del administrador.
    assert cliente.get("/api/v1/estudiantes", headers=cabecera_docente).status_code == 403
    assert cliente.get("/api/v1/reportes/dashboard", headers=cabecera_docente).status_code == 403

    # El docente solo ve sus secciones del período activo (2026-3).
    secciones = cliente.get("/api/v1/panel-docente/mis-secciones", headers=cabecera_docente)
    assert secciones.status_code == 200
    assert {seccion["id"] for seccion in secciones.json()} == {2, 3}
    estudiantes = cliente.get("/api/v1/panel-docente/mis-estudiantes", headers=cabecera_docente)
    assert estudiantes.status_code == 200

    # El administrador NO entra al panel del docente.
    assert cliente.get("/api/v1/panel-docente/mis-secciones").status_code == 403

    # Sin token: 401.
    assert cliente.get("/api/v1/estudiantes", headers={"Authorization": ""}).status_code == 401


def test_validacion_pydantic_devuelve_422(cliente):
    invalido = {
        "cuenta": "12345",
        "nombres": "A",
        "apellidos": "B",
        "correo": "esto-no-es-correo",
        "fecha_nacimiento": "2030-01-01",
        "carrera_id": 1,
    }
    respuesta = cliente.post("/api/v1/estudiantes", json=invalido)
    assert respuesta.status_code == 422
