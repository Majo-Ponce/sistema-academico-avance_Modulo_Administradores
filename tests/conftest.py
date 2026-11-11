import pytest
from fastapi.testclient import TestClient

import app.database as database
from app.main import app


@pytest.fixture()
def cliente_sin_login(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "sin_login.db")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    """Cliente autenticado como ADMIN (los módulos globales lo exigen)."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "pruebas.db")
    with TestClient(app) as test_client:
        login = test_client.post(
            "/api/v1/auth/login",
            json={"usuario": "admin", "clave": database.CLAVE_ADMIN_INICIAL},
        )
        test_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
        cambio = test_client.post(
            "/api/v1/auth/cambiar-password",
            json={
                "clave_actual": database.CLAVE_ADMIN_INICIAL,
                "clave_nueva": "admin-test-1234",
            },
        )
        assert cambio.status_code == 200
        yield test_client
