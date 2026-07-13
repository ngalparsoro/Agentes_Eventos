import json
import os

import vigil.publisher as publisher
from vigil.schemas import Alerta, Convocatoria, Urgencia, VeredictoRelevancia


def _alerta(id_expediente="EXP-1", es_modificacion=False):
    # creo una alerta de prueba con todos sus datos
    conv = Convocatoria(
        id_expediente=id_expediente,
        diputacion="Araba",
        objeto="Organización de un congreso institucional",
        organo_convocante="Diputación Foral de Álava",
        importe="45.000,00",
        plazo_presentacion="30/07/2026 23:59:00",
        enlace_pliego="https://example.org/exp",
        fecha_publicacion="05/07/2026",
        fecha_ultima_publicacion="05/07/2026",
    )
    ver = VeredictoRelevancia(relevante=True, motivo="Os encaja.", etiquetas=["Institucional"])
    urg = Urgencia(nivel="alta", dias_habiles_restantes=3, etiqueta="URGENCIA ALTA · 3 días hábiles")
    return Alerta(convocatoria=conv, veredicto=ver, urgencia=urg, es_modificacion=es_modificacion)


def test_publicar_escribe_json_y_ics(tmp_path, monkeypatch):
    # apunto la carpeta de salida a una temporal
    monkeypatch.setattr(publisher, "OUTPUT_DIR", str(tmp_path))

    # publico una alerta
    ok = publisher.publicar([_alerta("EXP-1")])
    assert ok is True

    # compruebo que se creó el JSON
    ruta_json = os.path.join(str(tmp_path), "concursos.json")
    assert os.path.exists(ruta_json)

    # leo el JSON y compruebo su contenido
    with open(ruta_json, encoding="utf-8") as f:
        datos = json.load(f)
    assert datos["total"] == 1
    concurso = datos["concursos"][0]
    assert concurso["id_expediente"] == "EXP-1"
    assert concurso["titulo"] == "Organización de un congreso institucional"
    assert concurso["urgencia"]["nivel"] == "alta"
    assert concurso["etiquetas"] == ["Institucional"]
    # el plazo también se ofrece en formato ISO
    assert concurso["plazo_iso"] == "2026-07-30T23:59:00"

    # compruebo que se creó el archivo .ics referenciado
    assert concurso["archivo_ics"] is not None
    ruta_ics = os.path.join(str(tmp_path), concurso["archivo_ics"])
    assert os.path.exists(ruta_ics)


def test_publicar_lista_vacia_escribe_json_vacio(tmp_path, monkeypatch):
    # apunto la carpeta de salida a una temporal
    monkeypatch.setattr(publisher, "OUTPUT_DIR", str(tmp_path))

    # publico una lista vacía (día sin novedades)
    ok = publisher.publicar([])
    assert ok is True

    # el JSON existe pero con cero concursos
    with open(os.path.join(str(tmp_path), "concursos.json"), encoding="utf-8") as f:
        datos = json.load(f)
    assert datos["total"] == 0
    assert datos["concursos"] == []
