"""Pruebas de la API HTTP (api.py) con el test_client de Flask, en modo demo."""

# traigo pytest para las fixtures
import pytest

# traigo el módulo de la API
from mercurio import api


# un cuerpo de búsqueda válido (hotel + viaje con ciudad de origen)
_SOLICITUD_OK = {
    "nombre_ponente": "Elena Vidal",
    "ciudad_evento": "Bilbao",
    "ciudad_origen": "Madrid",
    "fecha_inicio": "2026-09-10",
    "fecha_fin": "2026-09-11",
    "necesita_hotel": True,
    "necesita_viaje": True,
}


@pytest.fixture
def client(monkeypatch, tmp_path):
    # activo el modo demo (resultados simulados, sin claves)
    monkeypatch.setenv("MERCURIO_DEMO", "1")
    # dirijo los PDFs a una carpeta temporal para no ensuciar la salida real
    monkeypatch.setattr(api, "_CARPETA_PDF", str(tmp_path))
    return api.app.test_client()


def test_health(client):
    # la sonda de vida responde ok
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["estado"] == "ok"


def test_buscar_valido_devuelve_propuesta_y_pdfs(client):
    # una búsqueda válida devuelve la propuesta y los enlaces a los dos PDFs
    r = client.post("/buscar", json=_SOLICITUD_OK)
    assert r.status_code == 200
    datos = r.get_json()
    assert datos["propuesta"]["ponente"]["nombre"] == "Elena Vidal"
    assert datos["pdf_ponente"].endswith("/ponente.pdf")
    assert datos["pdf_mitumi"].endswith("/mitumi.pdf")


def test_buscar_valido_permite_descargar_el_pdf(client):
    # tras buscar, el PDF del ponente se puede descargar
    id_busqueda = client.post("/buscar", json=_SOLICITUD_OK).get_json()["propuesta"]["id"]
    r = client.get(f"/informes/{id_busqueda}/ponente.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_buscar_invalido_da_422_json(client):
    # viaje sin ciudad de origen: el molde lo rechaza y responde 422 en JSON limpio
    r = client.post("/buscar", json={
        "nombre_ponente": "Test",
        "ciudad_evento": "Bilbao",
        "fecha_inicio": "2026-09-10",
        "fecha_fin": "2026-09-11",
        "necesita_viaje": True,
    })
    assert r.status_code == 422
    assert "detail" in r.get_json()


def test_pdf_inexistente_da_404_json(client):
    # pedir un informe que no existe da 404 en JSON (no HTML)
    r = client.get("/informes/no-existe/ponente.pdf")
    assert r.status_code == 404
    assert "detail" in r.get_json()
