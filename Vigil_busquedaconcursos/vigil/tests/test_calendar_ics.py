from vigil.calendar_ics import generar_ics, nombre_fichero_ics
from vigil.schemas import Convocatoria


def _convocatoria(plazo):
    # creo una convocatoria de prueba con el plazo que me pasen
    return Convocatoria(
        id_expediente="EXP 2026 / 123",
        diputacion="Araba",
        objeto="Organización de un congreso",
        organo_convocante="Diputación Foral de Álava",
        enlace_pliego="https://example.org/exp",
        plazo_presentacion=plazo,
    )


def test_genera_ics_con_fecha_valida():
    # genero el .ics de una convocatoria con plazo válido
    ics = generar_ics(_convocatoria("30/07/2026 23:59:00"))
    # compruebo que tiene la estructura básica de un calendario
    assert ics is not None
    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    # compruebo que la fecha se ha convertido al formato del calendario
    assert "DTSTART:20260730T235900" in ics


def test_sin_plazo_no_genera_ics():
    # si no hay plazo, no se genera ningún .ics
    assert generar_ics(_convocatoria(None)) is None


def test_nombre_fichero_es_seguro():
    # el nombre del archivo no debe tener espacios ni barras
    nombre = nombre_fichero_ics(_convocatoria("30/07/2026"))
    assert nombre.endswith(".ics")
    assert " " not in nombre
    assert "/" not in nombre
