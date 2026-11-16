import pytest

URL = "/api/v1/estudiantes"


def estudiante_base(**cambios):
    datos = {
        "cuenta": "20269999",
        "nombres": "María José",
        "apellidos": "Pérez-López",
        "correo": "maria.perez@universidad.edu",
        "telefono": "9999-2020",
        "fecha_nacimiento": "2004-06-15",
        "carrera_id": 1,
        "estado": "ACTIVO",
    }
    datos.update(cambios)
    return datos


def test_acepta_estudiante_valido(cliente):
    respuesta = cliente.post(URL, json=estudiante_base())
    assert respuesta.status_code == 201


def test_quita_espacios_sobrantes_en_nombres(cliente):
    respuesta = cliente.post(URL, json=estudiante_base(nombres="  Ana  "))
    assert respuesta.status_code == 201
    assert respuesta.json()["nombres"] == "Ana"


@pytest.mark.parametrize("nombre", ["1234", "Ana123", "   ", "Ana@"])
def test_rechaza_nombres_invalidos(cliente, nombre):
    respuesta = cliente.post(URL, json=estudiante_base(nombres=nombre))
    assert respuesta.status_code == 422


@pytest.mark.parametrize("telefono", ["abc", "!!!!!!!", "12"])
def test_rechaza_telefonos_invalidos(cliente, telefono):
    respuesta = cliente.post(URL, json=estudiante_base(telefono=telefono))
    assert respuesta.status_code == 422


def test_telefono_es_opcional(cliente):
    datos = estudiante_base()
    del datos["telefono"]
    assert cliente.post(URL, json=datos).status_code == 201