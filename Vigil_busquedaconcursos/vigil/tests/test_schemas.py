import pytest
from pydantic import ValidationError

from vigil.schemas import Convocatoria, VeredictoRelevancia


def test_convocatoria_acepta_campos_no_verificados_como_null():
    convocatoria = Convocatoria(
        id_expediente="EXP-1",
        diputacion="Araba",
        objeto="Organización de un congreso institucional",
        organo_convocante="Diputación Foral de Álava",
        importe=None,
        plazo_presentacion=None,
        enlace_pliego="https://example.org/exp-1",
    )
    assert convocatoria.importe is None
    assert convocatoria.plazo_presentacion is None


def test_convocatoria_rechaza_diputacion_fuera_del_alcance():
    with pytest.raises(ValidationError):
        Convocatoria(
            id_expediente="EXP-2",
            diputacion="Madrid",
            objeto="Algo",
            organo_convocante="Ayuntamiento de Madrid",
            enlace_pliego="https://example.org/exp-2",
        )


def test_veredicto_relevancia_por_defecto_sin_campos_no_verificables():
    veredicto = VeredictoRelevancia(relevante=True, motivo="Encaja porque es un congreso.")
    assert veredicto.campos_no_verificables == []
