"""Pruebas de la API HTTP (api.py) con el test_client de Flask, sin lanzar el agente de verdad."""

# traigo time para esperar a que el hilo de la ejecución termine
import time

# traigo el módulo de la API, el de conexión y el histórico
from vigil import api, dedupe, history
# traigo los moldes para sembrar datos
from vigil.schemas import Convocatoria, Urgencia, VeredictoRelevancia


def _sembrar(db_path: str, id_expediente: str, objeto: str, relevante: bool) -> None:
    # meto un concurso en el histórico de la base de datos indicada
    with dedupe.get_connection(db_path) as conn:
        conv = Convocatoria(
            id_expediente=id_expediente,
            diputacion="Araba",
            objeto=objeto,
            organo_convocante="Diputación Foral de Álava",
            plazo_presentacion="30/07/2026",
            enlace_pliego=f"https://example.org/{id_expediente}",
        )
        ver = VeredictoRelevancia(relevante=relevante, motivo="Motivo.", etiquetas=[])
        urg = Urgencia(nivel="media", dias_habiles_restantes=7, etiqueta="URGENCIA MEDIA · 7 días hábiles")
        history.guardar_concurso(conn, conv, ver, urg, relevante)


def test_listar_concursos_con_filtros(tmp_path, monkeypatch):
    db_path = str(tmp_path / "vigil.db")
    # apunto la API a la base de datos temporal
    monkeypatch.setattr(api, "SQLITE_PATH", db_path)
    _sembrar(db_path, "EXP-CULT", "Festival de cultura", relevante=True)
    _sembrar(db_path, "EXP-OBRA", "Obras de carretera", relevante=False)

    client = api.app.test_client()

    # sin filtros salen los dos
    r = client.get("/concursos")
    assert r.status_code == 200
    assert r.get_json()["total"] == 2

    # con relevante=true solo sale el cultural
    r = client.get("/concursos", query_string={"relevante": True})
    assert [c["id_expediente"] for c in r.get_json()["concursos"]] == ["EXP-CULT"]

    # con q=obras solo sale la obra pública
    r = client.get("/concursos", query_string={"q": "obras"})
    assert [c["id_expediente"] for c in r.get_json()["concursos"]] == ["EXP-OBRA"]


class _FakeProc:
    # proceso falso que simula que el agente terminó bien
    def wait(self) -> int:
        return 0


def test_lanzar_ejecucion(tmp_path, monkeypatch):
    db_path = str(tmp_path / "vigil.db")
    monkeypatch.setattr(api, "SQLITE_PATH", db_path)
    # en vez de lanzar "python -m vigil.main", devuelvo un proceso falso...
    def _fake_lanzar():
        # ...y de paso simulo que el agente añadió un concurso al histórico
        _sembrar(db_path, "EXP-NUEVO", "Concurso recién encontrado", relevante=True)
        return _FakeProc()

    monkeypatch.setattr(api, "_lanzar_proceso", _fake_lanzar)

    client = api.app.test_client()

    # lanzo la ejecución: responde 202 y en curso
    r = client.post("/ejecuciones")
    assert r.status_code == 202
    run_id = r.get_json()["id"]
    assert r.get_json()["estado"] == "en_curso"

    # espero (con tope) a que el hilo de vigilancia marque la ejecución terminada
    for _ in range(50):
        estado = client.get(f"/ejecuciones/{run_id}").get_json()
        if estado["estado"] != "en_curso":
            break
        time.sleep(0.05)

    assert estado["estado"] == "terminada"
    # detectó que hay un concurso nuevo respecto al conteo previo
    assert estado["nuevos"] == 1


def test_calendario_ics(tmp_path, monkeypatch):
    db_path = str(tmp_path / "vigil.db")
    monkeypatch.setattr(api, "SQLITE_PATH", db_path)
    _sembrar(db_path, "EXP-CAL", "Congreso institucional", relevante=True)

    client = api.app.test_client()

    # el .ics se sirve como descarga de calendario
    r = client.get("/concursos/EXP-CAL/calendario.ics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert "attachment" in r.headers["content-disposition"]
    assert "BEGIN:VCALENDAR" in r.get_data(as_text=True)
    assert "EXP-CAL@vigil" in r.get_data(as_text=True)

    # un concurso inexistente da 404
    assert client.get("/concursos/NO-EXISTE/calendario.ics").status_code == 404


def test_ejecucion_desconocida_da_404(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "SQLITE_PATH", str(tmp_path / "vigil.db"))
    client = api.app.test_client()
    r = client.get("/ejecuciones/no-existe")
    assert r.status_code == 404
