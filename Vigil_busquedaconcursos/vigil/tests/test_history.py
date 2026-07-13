"""Pruebas del registro histórico de concursos (history.py)."""

# traigo utilidades de fecha para construir plazos futuros y pasados
from datetime import date, timedelta

# traigo el módulo de conexión (compartido con el dedupe) y el histórico
from vigil import dedupe, history
# traigo los moldes que necesito para guardar un concurso
from vigil.schemas import Convocatoria, Urgencia, VeredictoRelevancia


def _convocatoria(id_expediente: str, plazo: str | None, objeto: str = "Un congreso") -> Convocatoria:
    # creo una convocatoria mínima para las pruebas
    return Convocatoria(
        id_expediente=id_expediente,
        diputacion="Araba",
        objeto=objeto,
        organo_convocante="Diputación Foral de Álava",
        importe="10.000,00",
        plazo_presentacion=plazo,
        enlace_pliego=f"https://example.org/{id_expediente}",
    )


def _guardar(conn, conv: Convocatoria, relevante: bool = True) -> None:
    # guardo con un veredicto y una urgencia de relleno
    veredicto = VeredictoRelevancia(
        relevante=relevante, motivo="Encaja.", etiquetas=["Institucional"]
    )
    urgencia = Urgencia(nivel="media", dias_habiles_restantes=7, etiqueta="URGENCIA MEDIA · 7 días hábiles")
    history.guardar_concurso(conn, conv, veredicto, urgencia, relevante)


def test_guardar_y_consultar(tmp_path):
    db_path = str(tmp_path / "vigil.db")
    with dedupe.get_connection(db_path) as conn:
        _guardar(conn, _convocatoria("EXP-1", "30/07/2026"))
        # lo recupero del histórico
        filas = history.consultar(conn)
        assert len(filas) == 1
        assert filas[0]["id_expediente"] == "EXP-1"
        # las etiquetas vuelven como lista, no como JSON
        assert filas[0]["etiquetas"] == ["Institucional"]
        # relevante vuelve como booleano
        assert filas[0]["relevante"] is True


def test_upsert_conserva_primera_vez(tmp_path):
    db_path = str(tmp_path / "vigil.db")
    with dedupe.get_connection(db_path) as conn:
        _guardar(conn, _convocatoria("EXP-1", "30/07/2026", objeto="Título viejo"))
        primera = history.consultar(conn)[0]["visto_por_primera_vez"]
        # vuelvo a guardar el mismo expediente con otro objeto (una modificación)
        _guardar(conn, _convocatoria("EXP-1", "30/07/2026", objeto="Título nuevo"))
        filas = history.consultar(conn)
        # sigue habiendo una sola fila (UPSERT, no duplicado)
        assert len(filas) == 1
        # se actualizó el objeto
        assert filas[0]["objeto"] == "Título nuevo"
        # se conserva la fecha de la primera vez que se vio
        assert filas[0]["visto_por_primera_vez"] == primera


def test_filtro_en_plazo(tmp_path):
    db_path = str(tmp_path / "vigil.db")
    # construyo un plazo futuro y otro ya vencido, relativos a hoy
    futuro = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
    pasado = (date.today() - timedelta(days=30)).strftime("%d/%m/%Y")
    with dedupe.get_connection(db_path) as conn:
        _guardar(conn, _convocatoria("EXP-VIGENTE", futuro))
        _guardar(conn, _convocatoria("EXP-VENCIDO", pasado))
        # sin filtro salen los dos
        assert len(history.consultar(conn)) == 2
        # con solo_en_plazo solo sale el vigente
        vigentes = history.consultar(conn, solo_en_plazo=True)
        assert [f["id_expediente"] for f in vigentes] == ["EXP-VIGENTE"]


def test_filtros_texto_y_relevancia(tmp_path):
    db_path = str(tmp_path / "vigil.db")
    with dedupe.get_connection(db_path) as conn:
        _guardar(conn, _convocatoria("EXP-CULT", "30/07/2026", objeto="Festival de cultura"), relevante=True)
        _guardar(conn, _convocatoria("EXP-OBRA", "30/07/2026", objeto="Obras de carretera"), relevante=False)
        # el filtro de texto encuentra por el objeto
        assert [f["id_expediente"] for f in history.consultar(conn, q="cultura")] == ["EXP-CULT"]
        # el filtro de relevancia deja fuera la obra pública
        assert [f["id_expediente"] for f in history.consultar(conn, solo_relevantes=True)] == ["EXP-CULT"]
