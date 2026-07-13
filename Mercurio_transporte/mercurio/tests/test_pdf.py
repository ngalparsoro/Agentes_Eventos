"""Tests de los dos informes en PDF: el del ponente (sin precios) y el de Mitumi."""

# traigo os para componer rutas
import os

# traigo pytest para saltar si falta pypdf y para el modo demo
import pytest

# traigo el servicio, el generador de PDF y el molde de la solicitud
from mercurio import pdf_report, servicio
from mercurio.schemas import SolicitudBusqueda


# fuerzo el modo demo
@pytest.fixture(autouse=True)
def _demo(monkeypatch):
    monkeypatch.setenv("MERCURIO_DEMO", "1")


# genero una propuesta completa (los cuatro servicios) para los tests
def _propuesta():
    return servicio.buscar(SolicitudBusqueda(
        nombre_ponente="Ana Prueba",
        nombre_evento="Evento PDF",
        ciudad_evento="San Sebastián",
        fecha_inicio="2026-09-15",
        fecha_fin="2026-09-17",
        ciudad_origen="Madrid",
        necesita_taxi=True,
        necesita_coche=True,
    ))


# extraigo el texto de un PDF (o salto si no está pypdf)
def _texto(ruta):
    pdf = pytest.importorskip("pypdf")
    lector = pdf.PdfReader(ruta)
    return "\n".join(p.extract_text() or "" for p in lector.pages)


# se generan los dos PDFs (ponente y mitumi)
def test_genera_ambos(tmp_path):
    rutas = pdf_report.generar_ambos(_propuesta(), str(tmp_path))
    assert rutas["ponente"] and os.path.exists(rutas["ponente"])
    assert rutas["mitumi"] and os.path.exists(rutas["mitumi"])


# el PDF del ponente NO contiene precios
def test_pdf_ponente_sin_precios(tmp_path):
    rutas = pdf_report.generar_ambos(_propuesta(), str(tmp_path))
    texto = _texto(rutas["ponente"])
    assert "EUR" not in texto
    assert "€" not in texto
    # comprobación de cordura: el PDF sí tiene contenido
    assert "Ana Prueba" in texto


# el PDF de Mitumi SÍ contiene precios (y el coste estimado)
def test_pdf_mitumi_con_precios(tmp_path):
    rutas = pdf_report.generar_ambos(_propuesta(), str(tmp_path))
    texto = _texto(rutas["mitumi"])
    assert "EUR" in texto
    assert "Coste estimado" in texto


# ambos PDFs incluyen las secciones de taxi y coche cuando se piden
def test_pdf_incluye_taxi_y_coche(tmp_path):
    rutas = pdf_report.generar_ambos(_propuesta(), str(tmp_path))
    for variante in ("ponente", "mitumi"):
        texto = _texto(rutas[variante])
        assert "Taxi" in texto
        assert "Coche de alquiler" in texto
    # el de ponente sigue sin precios pese a las nuevas secciones
    assert "EUR" not in _texto(rutas["ponente"])
