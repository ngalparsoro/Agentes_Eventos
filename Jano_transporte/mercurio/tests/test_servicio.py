"""Tests del servicio de búsqueda: casillas hotel/viaje y validación."""

# traigo pytest para comprobar errores de validación
import pytest
# traigo pydantic para el tipo de error de validación
from pydantic import ValidationError

# traigo el servicio y el molde de la solicitud
from mercurio import servicio
from mercurio.schemas import SolicitudBusqueda


# fuerzo el modo demo en todos los tests de este módulo
@pytest.fixture(autouse=True)
def _demo(monkeypatch):
    monkeypatch.setenv("MERCURIO_DEMO", "1")


# construyo una solicitud base a la que sobreescribir campos
def _solicitud(**extra) -> SolicitudBusqueda:
    datos = {
        "nombre_ponente": "Ana Prueba",
        "ciudad_evento": "San Sebastián",
        "fecha_inicio": "2026-09-15",
        "fecha_fin": "2026-09-17",
        "ciudad_origen": "Madrid",
    }
    datos.update(extra)
    return SolicitudBusqueda(**datos)


# si se piden hotel y viaje, se buscan las dos cosas
def test_hotel_y_viaje():
    p = servicio.buscar(_solicitud(necesita_hotel=True, necesita_viaje=True))
    assert len(p.hoteles) == 3
    assert len(p.vuelos) > 0
    assert len(p.trenes) > 0  # Madrid → San Sebastián tiene tren
    assert p.coste_estimado is not None


# si solo se pide hotel, no se buscan vuelos ni trenes
def test_solo_hotel():
    p = servicio.buscar(_solicitud(necesita_hotel=True, necesita_viaje=False, ciudad_origen=None))
    assert len(p.hoteles) == 3
    assert p.vuelos == []
    assert p.trenes == []


# si solo se pide viaje, no se buscan hoteles
def test_solo_viaje():
    p = servicio.buscar(_solicitud(necesita_hotel=False, necesita_viaje=True))
    assert p.hoteles == []
    assert len(p.vuelos) > 0


# se pueden pedir los cuatro servicios a la vez
def test_todos_los_servicios():
    p = servicio.buscar(_solicitud(necesita_hotel=True, necesita_viaje=True, necesita_taxi=True, necesita_coche=True))
    assert len(p.hoteles) == 3 and len(p.taxis) == 3 and len(p.coches) == 3
    # el coste estimado suma también taxi y coche
    assert p.coste_estimado is not None


# solo taxi: no hace falta origen y no se buscan hotel/viaje/coche
def test_solo_taxi():
    p = servicio.buscar(_solicitud(necesita_hotel=False, necesita_viaje=False, necesita_taxi=True, ciudad_origen=None))
    assert p.hoteles == [] and p.vuelos == [] and p.coches == []
    assert len(p.taxis) == 3


# solo coche: los días de alquiler son las noches del viaje
def test_solo_coche():
    p = servicio.buscar(_solicitud(necesita_hotel=False, necesita_viaje=False, necesita_coche=True, ciudad_origen=None))
    assert p.hoteles == [] and p.taxis == []
    assert len(p.coches) == 3
    assert all(c.dias == p.noches for c in p.coches)
    # la recomendación (con precio) menciona el coche de alquiler
    assert "coche de alquiler" in p.recomendacion.lower()


# no marcar nada es un error de validación
def test_ni_hotel_ni_viaje_falla():
    with pytest.raises(ValidationError):
        _solicitud(necesita_hotel=False, necesita_viaje=False)


# pedir viaje sin ciudad de origen es un error de validación
def test_viaje_sin_origen_falla():
    with pytest.raises(ValidationError):
        _solicitud(necesita_viaje=True, ciudad_origen=None)


# la recomendación con precio lleva importe y la del ponente no
def test_recomendaciones():
    p = servicio.buscar(_solicitud())
    assert "EUR" in p.recomendacion
    assert "EUR" not in p.recomendacion_sin_precio
    assert "€" not in p.recomendacion_sin_precio


# hay dos justificaciones: la del organizador y la del ponente
def test_justificacion():
    p = servicio.buscar(_solicitud())
    # ambas existen y mencionan el hotel recomendado
    assert p.justificacion and p.justificacion_ponente
    assert p.hoteles[0].nombre in p.justificacion_ponente
    # ninguna revela importes en euros
    for j in (p.justificacion, p.justificacion_ponente):
        assert "EUR" not in j and "€" not in j


# la justificación del PONENTE no usa lenguaje de precio (económico/barato/coste)
def test_justificacion_ponente_sin_precio():
    p = servicio.buscar(_solicitud())
    texto = p.justificacion_ponente.lower()
    for palabra in ("económic", "econonic", "barat", "precio", "coste", "caro"):
        assert palabra not in texto
    # la del organizador sí puede hablar de que es lo más económico
    assert "económic" in p.justificacion.lower()


# la preferencia de cercanía se refleja en el porqué del hotel
def test_justificacion_cercania():
    p = servicio.buscar(_solicitud(preferencias="cerca del recinto"))
    assert "más cercano al recinto" in p.justificacion
