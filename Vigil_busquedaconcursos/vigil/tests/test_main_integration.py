"""Prueba de integración de main.run() con extractor/relevance/publisher simulados.

No llama a Groq ni escribe archivos reales — comprueba que la orquestación
(dedupe, modificaciones, manejo de errores, publicación) funciona.
"""

import vigil.main as main
from vigil.schemas import Alerta, Convocatoria, VeredictoRelevancia


def _convocatoria(id_expediente: str, fecha_ultima: str = "05/07/2026") -> dict:
    # creo un diccionario crudo de ejemplo como el que devuelve sources.py
    return {
        "diputacion": "Araba",
        "objeto": f"Objeto de {id_expediente}",
        "enlace_pliego": f"https://example.org/{id_expediente}",
        "id_expediente": id_expediente,
        "fecha_publicacion": "05/07/2026",
        "fecha_ultima_publicacion": fecha_ultima,
        "estado_tramitacion": "Abierto / Plazo de presentación",
        "organo_convocante": "Diputación Foral de Álava",
        "importe": "10.000,00",
        "plazo_presentacion": "30/07/2026 23:59:00",
    }


def _fake_extraer(cruda: dict) -> Convocatoria:
    # convierto el crudo en una Convocatoria sin llamar al LLM
    return Convocatoria(
        id_expediente=cruda["id_expediente"],
        diputacion=cruda["diputacion"],
        objeto=cruda["objeto"],
        organo_convocante=cruda["organo_convocante"],
        importe=cruda["importe"],
        plazo_presentacion=cruda["plazo_presentacion"],
        enlace_pliego=cruda["enlace_pliego"],
        fecha_ultima_publicacion=cruda["fecha_ultima_publicacion"],
    )


def test_convocatoria_relevante_dispara_email_y_queda_marcada(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SQLITE_PATH", str(tmp_path / "vigil.db"))
    monkeypatch.setattr(main, "obtener_convocatorias", lambda: [_convocatoria("EXP-REL")])
    monkeypatch.setattr(main, "extraer_convocatoria", _fake_extraer)
    monkeypatch.setattr(
        main,
        "evaluar_relevancia",
        lambda c: VeredictoRelevancia(relevante=True, motivo="Es un congreso.", etiquetas=["Institucional"]),
    )
    enviados = []
    monkeypatch.setattr(
        main.publisher, "publicar", lambda alertas: enviados.append(alertas) or True
    )

    main.run()

    # se envió un email con una alerta, y es la convocatoria esperada
    assert len(enviados) == 1
    assert len(enviados[0]) == 1
    assert isinstance(enviados[0][0], Alerta)
    assert enviados[0][0].convocatoria.id_expediente == "EXP-REL"


def test_convocatoria_no_relevante_no_dispara_email(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SQLITE_PATH", str(tmp_path / "vigil.db"))
    monkeypatch.setattr(main, "obtener_convocatorias", lambda: [_convocatoria("EXP-NOREL")])
    monkeypatch.setattr(main, "extraer_convocatoria", _fake_extraer)
    monkeypatch.setattr(
        main,
        "evaluar_relevancia",
        lambda c: VeredictoRelevancia(relevante=False, motivo="Es una obra pública."),
    )
    enviados = []
    monkeypatch.setattr(
        main.publisher, "publicar", lambda alertas: enviados.append(alertas) or True
    )

    main.run()

    # se publica igualmente, pero con la lista de concursos vacía
    assert enviados == [[]]


def test_segunda_ejecucion_no_reprocesa_lo_ya_visto(tmp_path, monkeypatch):
    db_path = str(tmp_path / "vigil.db")
    monkeypatch.setattr(main, "SQLITE_PATH", db_path)
    monkeypatch.setattr(main, "obtener_convocatorias", lambda: [_convocatoria("EXP-DUP")])
    monkeypatch.setattr(main, "extraer_convocatoria", _fake_extraer)
    llamadas_relevancia = []

    def evaluar(c):
        llamadas_relevancia.append(c.id_expediente)
        return VeredictoRelevancia(relevante=True, motivo="Encaja.")

    monkeypatch.setattr(main, "evaluar_relevancia", evaluar)
    monkeypatch.setattr(main.publisher, "publicar", lambda alertas: True)

    main.run()
    main.run()

    # solo se evaluó una vez (la segunda vez ya estaba vista)
    assert llamadas_relevancia == ["EXP-DUP"]


def test_modificacion_se_reprocesa_y_se_marca(tmp_path, monkeypatch):
    db_path = str(tmp_path / "vigil.db")
    monkeypatch.setattr(main, "SQLITE_PATH", db_path)
    monkeypatch.setattr(main, "extraer_convocatoria", _fake_extraer)
    monkeypatch.setattr(
        main, "evaluar_relevancia", lambda c: VeredictoRelevancia(relevante=True, motivo="Encaja.")
    )
    enviados = []
    monkeypatch.setattr(
        main.publisher, "publicar", lambda alertas: enviados.append(alertas) or True
    )

    # primera ejecución: la convocatoria es nueva
    monkeypatch.setattr(
        main, "obtener_convocatorias", lambda: [_convocatoria("EXP-MOD", "05/07/2026")]
    )
    main.run()

    # segunda ejecución: reaparece con una última publicación distinta → modificación
    monkeypatch.setattr(
        main, "obtener_convocatorias", lambda: [_convocatoria("EXP-MOD", "09/07/2026")]
    )
    main.run()

    # se enviaron dos emails y el segundo va marcado como modificación
    assert len(enviados) == 2
    assert enviados[1][0].es_modificacion is True


def test_fallo_del_llm_no_marca_como_procesada(tmp_path, monkeypatch):
    db_path = str(tmp_path / "vigil.db")
    monkeypatch.setattr(main, "SQLITE_PATH", db_path)
    monkeypatch.setattr(main, "obtener_convocatorias", lambda: [_convocatoria("EXP-FALLO")])

    intentos = []

    def extraer_que_falla(cruda):
        intentos.append(cruda["id_expediente"])
        raise RuntimeError("Groq no responde")

    monkeypatch.setattr(main, "extraer_convocatoria", extraer_que_falla)
    monkeypatch.setattr(main.publisher, "publicar", lambda alertas: True)

    main.run()
    main.run()

    # como falló extractor.py, dedupe no la marcó — se reintenta cada día
    assert intentos == ["EXP-FALLO", "EXP-FALLO"]
