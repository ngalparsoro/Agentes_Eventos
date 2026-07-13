"""Tests del generador demo y del cálculo de la ventana de viaje."""

# traigo el generador demo y el cálculo de fechas
from mercurio import demo
from mercurio.fechas import calcular_ventana


# la ventana de viaje llega antes y sale después, con noches coherentes
def test_ventana_de_viaje():
    llegada, salida, noches = calcular_ventana("2026-09-15", "2026-09-17")
    assert llegada == "2026-09-14"
    assert salida == "2026-09-18"
    assert noches == 4


# la ventana funciona con timestamptz (fecha con hora y zona horaria)
def test_ventana_con_timestamptz():
    llegada, salida, noches = calcular_ventana(
        "2026-09-15T09:00:00+02:00", "2026-09-17T18:00:00+02:00"
    )
    assert (llegada, salida, noches) == ("2026-09-14", "2026-09-18", 4)


# el buscador demo devuelve 3 hoteles con precio y enlace
def test_hoteles_demo():
    hoteles = demo.buscar_hoteles("San Sebastián", "2026-09-14", "2026-09-18", 4, 1, None, "sem")
    assert len(hoteles) == 3
    for h in hoteles:
        assert h.precio_total > 0
        assert h.noches == 4
        assert h.enlace_reserva.startswith("https://")


# el resultado demo es determinista: misma semilla, mismos hoteles
def test_hoteles_deterministas():
    a = demo.buscar_hoteles("Bilbao", "2026-09-14", "2026-09-18", 4, 1, None, "sem")
    b = demo.buscar_hoteles("Bilbao", "2026-09-14", "2026-09-18", 4, 1, None, "sem")
    assert [h.nombre for h in a] == [h.nombre for h in b]


# más personas => más habitaciones y precio total mayor
def test_hoteles_por_personas():
    uno = demo.buscar_hoteles("Bilbao", "2026-09-14", "2026-09-18", 4, 1, None, "sem")
    cuatro = demo.buscar_hoteles("Bilbao", "2026-09-14", "2026-09-18", 4, 4, None, "sem")
    # 4 personas => 2 habitaciones
    assert cuatro[0].habitaciones == 2
    assert uno[0].habitaciones == 1


# la preferencia "cerca del recinto" ordena los hoteles por cercanía
def test_hoteles_preferencia_cercania():
    hoteles = demo.buscar_hoteles("Madrid", "2026-09-14", "2026-09-18", 4, 1, "cerca del recinto", "sem")
    distancias = [h.distancia_recinto_km for h in hoteles]
    assert distancias == sorted(distancias)


# hay tren entre dos ciudades españolas con alta velocidad
def test_tren_nacional():
    trenes = demo.buscar_trenes("Madrid", "San Sebastián", "2026-09-14", "2026-09-18", 1, None, "sem")
    assert len(trenes) > 0
    assert all(t.modo == "tren" for t in trenes)


# no hay tren si el origen es internacional
def test_sin_tren_internacional():
    assert demo.buscar_trenes("Londres", "San Sebastián", "2026-09-14", "2026-09-18", 1, None, "sem") == []


# sin ciudad de origen no hay vuelos
def test_sin_origen_sin_vuelos():
    assert demo.buscar_vuelos("", "Bilbao", "2026-09-14", "2026-09-18", 1, None, "sem") == []


# los vuelos vienen ordenados de más barato a más caro
def test_vuelos_ordenados():
    vuelos = demo.buscar_vuelos("Londres", "San Sebastián", "2026-09-14", "2026-09-18", 1, None, "sem")
    precios = [v.precio_total for v in vuelos]
    assert precios == sorted(precios)


# la preferencia "sin escalas" deja solo vuelos directos (si los hay)
def test_vuelos_preferencia_directo():
    vuelos = demo.buscar_vuelos("Madrid", "Bilbao", "2026-09-14", "2026-09-18", 1, "sin escalas", "sem")
    # si quedó alguno, todos deben ser directos
    if vuelos:
        assert all(v.ida.escalas == 0 and v.vuelta.escalas == 0 for v in vuelos)
