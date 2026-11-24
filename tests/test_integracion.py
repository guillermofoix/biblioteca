"""Tests con una base de datos PostgreSQL de verdad.

Solo se ejecutan si existe la variable TEST_DATABASE_URL (en el CI, el job «integracion»).
En tu PC se saltan. No usan DATABASE_URL a propósito: la de tu .env apunta a una base de
datos con datos que no hay que tocar.
"""
import os
import uuid

import pytest

import app as modulo_app

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Sin TEST_DATABASE_URL: solo se ejecutan en el CI")


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(modulo_app, "DATABASE_URL", URL)
    monkeypatch.setattr(modulo_app, "tabla_creada", False)   # que vuelva a pasar por las migraciones
    modulo_app.app.config["TESTING"] = True
    return modulo_app.app.test_client()


def test_health_con_base_de_datos_real(cliente):
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"status": "ok", "db": "ok"}


def test_anadir_y_listar_un_libro(cliente):
    titulo = f"Libro de prueba {uuid.uuid4().hex[:8]}"   # único: no choca con otras ejecuciones
    respuesta = cliente.post("/nuevo", data={"titulo": titulo, "autor": "Autora de prueba",
                                             "anio": "2020", "genero": "Ensayo"})
    assert respuesta.status_code == 302                    # redirige a la lista: se ha guardado
    assert titulo in cliente.get("/").get_data(as_text=True)


def test_las_migraciones_se_pueden_repetir(cliente, monkeypatch):
    cliente.get("/health")                                 # primera vez: crea o migra la tabla
    monkeypatch.setattr(modulo_app, "tabla_creada", False)
    assert cliente.get("/health").status_code == 200       # segunda vez: no debe fallar
