"""Pruebas del modo demo (demo.py + main.run con VIGIL_DEMO)."""

# traigo el módulo demo y el histórico para comprobar el resultado
from vigil import demo, dedupe, history
import vigil.main as main
from vigil.schemas import Convocatoria


def test_evaluar_relevancia_distingue_eventos_de_obras():
    # un congreso encaja con Mitumi
    congreso = Convocatoria(
        id_expediente="X", diputacion="Araba", objeto="Organización de un congreso",
        organo_convocante="DFA", enlace_pliego="http://x",
    )
    assert demo.evaluar_relevancia(congreso).relevante is True
    # una obra de carretera no encaja
    obra = Convocatoria(
        id_expediente="Y", diputacion="Gipuzkoa", objeto="Obras de renovación del firme",
        organo_convocante="DFG", enlace_pliego="http://y",
    )
    assert demo.evaluar_relevancia(obra).relevante is False


def test_run_en_modo_demo_puebla_el_historico(tmp_path, monkeypatch):
    # apunto la base de datos a una temporal
    db_path = str(tmp_path / "vigil.db")
    monkeypatch.setattr(main, "SQLITE_PATH", db_path)
    # activo el modo demo por variable de entorno
    monkeypatch.setenv("VIGIL_DEMO", "1")
    # evito escribir la salida real de la plataforma
    monkeypatch.setattr(main.publisher, "publicar", lambda alertas: True)

    # ejecuto el agente completo en modo demo
    main.run()

    # el histórico contiene las 6 convocatorias de ejemplo (relevantes y no)
    with dedupe.get_connection(db_path) as conn:
        todos = history.consultar(conn, limite=200)
        relevantes = history.consultar(conn, solo_relevantes=True, limite=200)
    assert len(todos) == 6
    assert len(relevantes) == 4
