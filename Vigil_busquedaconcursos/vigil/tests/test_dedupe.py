from vigil import dedupe


def test_nueva_luego_vista(tmp_path):
    # uso una base de datos temporal para el test
    db_path = str(tmp_path / "vigil_test.db")

    with dedupe.get_connection(db_path) as conn:
        # la primera vez que la veo, es nueva
        assert dedupe.estado_convocatoria(conn, "EXP-1", "05/07/2026") == "nueva"
        # la registro con su última publicación
        dedupe.registrar(conn, "EXP-1", "https://example.org/exp-1", "05/07/2026")
        # si vuelve con la misma última publicación, ya está vista
        assert dedupe.estado_convocatoria(conn, "EXP-1", "05/07/2026") == "vista"


def test_detecta_modificacion(tmp_path):
    # uso una base de datos temporal para el test
    db_path = str(tmp_path / "vigil_test.db")

    with dedupe.get_connection(db_path) as conn:
        # registro la convocatoria con una última publicación
        dedupe.registrar(conn, "EXP-2", "https://example.org/exp-2", "01/07/2026")
        # si reaparece con una última publicación distinta, es una modificación
        assert dedupe.estado_convocatoria(conn, "EXP-2", "08/07/2026") == "modificada"
        # tras registrar la nueva fecha, ya vuelve a estar vista
        dedupe.registrar(conn, "EXP-2", "https://example.org/exp-2", "08/07/2026")
        assert dedupe.estado_convocatoria(conn, "EXP-2", "08/07/2026") == "vista"


def test_persiste_entre_conexiones(tmp_path):
    # uso una base de datos temporal para el test
    db_path = str(tmp_path / "vigil_test.db")

    # registro en una conexión
    with dedupe.get_connection(db_path) as conn:
        dedupe.registrar(conn, "EXP-3", "https://example.org/exp-3", "05/07/2026")

    # compruebo en otra conexión distinta (simula otra ejecución del cron)
    with dedupe.get_connection(db_path) as conn:
        assert dedupe.estado_convocatoria(conn, "EXP-3", "05/07/2026") == "vista"
