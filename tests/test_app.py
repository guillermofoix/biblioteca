"""Tests de la Biblioteca. No necesitan una base de datos real."""
import pytest

import app as modulo_app
from app import validar

# ---------- validar(): las reglas del formulario ----------


def test_validar_datos_correctos():
    errores, anio = validar("El Quijote", "Cervantes", "1605")
    assert errores == []
    assert anio == 1605


def test_validar_anio_vacio_es_valido():
    errores, anio = validar("El Quijote", "Cervantes", "")
    assert errores == []
    assert anio is None


def test_validar_titulo_y_autor_obligatorios():
    errores, _ = validar("", "", "")
    assert "El título es obligatorio." in errores
    assert "El autor es obligatorio." in errores


def test_validar_anio_no_numerico():
    errores, _ = validar("Título", "Autor", "mil")
    assert errores == ["El año debe ser un número entero."]


# ---------- Las páginas ----------


@pytest.fixture
def cliente():
    """Navegador de pruebas de Flask: pide páginas sin arrancar ningún servidor."""
    modulo_app.app.config["TESTING"] = True
    return modulo_app.app.test_client()


def test_formulario_nuevo(cliente):
    respuesta = cliente.get("/nuevo")
    assert respuesta.status_code == 200
    assert 'name="titulo"' in respuesta.get_data(as_text=True)


def test_lista_sin_base_de_datos_devuelve_503(cliente, monkeypatch):
    # Una base de datos en un puerto cerrado: la conexión falla al momento
    monkeypatch.setattr(modulo_app, "DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")
    respuesta = cliente.get("/")
    assert respuesta.status_code == 503


# ---------- La lista, con una base de datos falsa ----------


class ResultadoFalso:
    """Lo que devuelve execute(): unas filas que se leen con fetchall() o fetchone()."""

    def __init__(self, filas):
        self.filas = filas

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return self.filas[0] if self.filas else None


class ConexionFalsa:
    """Se hace pasar por la conexión a PostgreSQL: cualquier consulta devuelve las filas que le des."""

    def __init__(self, filas):
        self.filas = filas

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, consulta, parametros=None):
        return ResultadoFalso(self.filas)


QUIJOTE = {"id": 1, "titulo": "El Quijote", "autor": "Cervantes", "anio": 1605, "prestado": False, "genero": None}


def test_lista_muestra_los_libros(cliente, monkeypatch):
    # Durante este test, conectar() devuelve la conexión falsa con un libro
    monkeypatch.setattr(modulo_app, "conectar", lambda: ConexionFalsa([QUIJOTE]))
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "El Quijote" in respuesta.get_data(as_text=True)


# ---------- /health ----------


def test_health_con_base_de_datos_devuelve_200(cliente, monkeypatch):
    monkeypatch.setattr(modulo_app, "conectar", lambda: ConexionFalsa([]))
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"status": "ok", "db": "ok"}


def test_health_sin_base_de_datos_devuelve_503(cliente, monkeypatch, caplog):
    monkeypatch.setattr(modulo_app, "DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 503
    # Responde JSON (no la página de error) y el motivo queda en el log
    assert respuesta.get_json() == {"status": "error", "db": "unreachable"}
    assert "Healthcheck fallido" in caplog.text


def test_health_sin_database_url_devuelve_503(cliente, monkeypatch):
    monkeypatch.setattr(modulo_app, "DATABASE_URL", None)
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 503
    
    
def test_pie_muestra_la_version(cliente, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setattr(modulo_app, "conectar", lambda: ConexionFalsa([]))
    assert "9.9.9" in cliente.get("/").get_data(as_text=True)
