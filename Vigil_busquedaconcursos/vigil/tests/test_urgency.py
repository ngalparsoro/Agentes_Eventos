from datetime import date

from vigil.urgency import calcular_urgencia


def test_urgencia_alta_pocos_dias():
    # tomo un lunes como "hoy" para controlar los días hábiles
    hoy = date(2026, 7, 6)  # lunes
    # plazo el jueves de esa misma semana → pocos días hábiles → alta
    urg = calcular_urgencia("09/07/2026 23:59:00", "Abierto / Plazo de presentación", hoy=hoy)
    assert urg.nivel == "alta"
    assert urg.dias_habiles_restantes == 3


def test_urgencia_media():
    # tomo un lunes como "hoy"
    hoy = date(2026, 7, 6)
    # plazo unas dos semanas después → entre 6 y 15 días hábiles → media
    urg = calcular_urgencia("22/07/2026 23:59:00", "Abierto / Plazo de presentación", hoy=hoy)
    assert urg.nivel == "media"


def test_urgencia_baja_muchos_dias():
    # tomo un lunes como "hoy"
    hoy = date(2026, 7, 6)
    # plazo más de un mes después → más de 15 días hábiles → baja
    urg = calcular_urgencia("31/08/2026 23:59:00", "Abierto / Plazo de presentación", hoy=hoy)
    assert urg.nivel == "baja"


def test_estado_no_abierto_es_cerrado():
    # si el estado no permite presentarse, es cerrado sin importar la fecha
    urg = calcular_urgencia("31/08/2026 23:59:00", "Adjudicación", hoy=date(2026, 7, 6))
    assert urg.nivel == "cerrado"


def test_sin_plazo_es_desconocida():
    # si no hay plazo, la urgencia es desconocida
    urg = calcular_urgencia(None, "Abierto / Plazo de presentación", hoy=date(2026, 7, 6))
    assert urg.nivel == "desconocida"
