from bs4 import BeautifulSoup

from vigil.sources import _parse_resultado, _publicada_recientemente
from datetime import datetime

# Fragmento simplificado de un "bloqueResultado" real de KontratazioA (formato ampliado),
# tal como se vio al validar la lectura de la web antes de escribir sources.py.
_HTML_EJEMPLO = """
<div class="bloqueResultado">
  <fieldset>
    <div class="cabecera-resultado">
      <legend>Servicio de organización de un congreso institucional</legend>
      <div class="ver-detalle">
        <a href="/webkpe00-kpeperfi/es/contenidos/anuncio_contratacion/expjaso123456/es_doc/index.html">
          <img id="lupa" alt="Ver detalle">
        </a>
      </div>
    </div>
    <div>
      <dl>
        <dt>Expediente</dt><dd>ADM1-2026-0000001234</dd>
        <dt>Fecha primera publicación</dt><dd>05/07/2026</dd>
        <dt>Fecha última publicación</dt><dd>08/07/2026</dd>
        <dt>Tipo de contrato</dt><dd>Servicios</dd>
        <dt>Estado de la tramitación</dt><dd>Abierto / Plazo de presentación</dd>
        <dt>Fecha límite de presentación</dt><dd>30/07/2026 23:59:00</dd>
        <dt>Presupuesto del contrato sin IVA</dt><dd>45.000,00</dd>
        <dt>Poder adjudicador</dt><dd>Diputación Foral de Álava</dd>
        <dt>Entidad Impulsora</dt><dd>Departamento de Cultura</dd>
      </dl>
    </div>
  </fieldset>
</div>
"""


def test_parse_resultado_extrae_todos_los_campos():
    soup = BeautifulSoup(_HTML_EJEMPLO, "html.parser")
    bloque = soup.select_one("div.bloqueResultado")

    resultado = _parse_resultado(bloque, "Araba")

    assert resultado["diputacion"] == "Araba"
    assert resultado["objeto"] == "Servicio de organización de un congreso institucional"
    assert resultado["id_expediente"] == "ADM1-2026-0000001234"
    assert resultado["fecha_publicacion"] == "05/07/2026"
    assert resultado["fecha_ultima_publicacion"] == "08/07/2026"
    assert resultado["plazo_presentacion"] == "30/07/2026 23:59:00"
    assert resultado["importe"] == "45.000,00"
    assert resultado["organo_convocante"] == "Diputación Foral de Álava"
    assert resultado["enlace_pliego"].startswith("https://www.contratacion.euskadi.eus/")
    assert "expjaso123456" in resultado["enlace_pliego"]


def test_publicada_recientemente_filtra_por_fecha():
    limite = datetime(2026, 7, 1)
    assert _publicada_recientemente({"fecha_publicacion": "05/07/2026"}, limite) is True
    assert _publicada_recientemente({"fecha_publicacion": "28/12/2024"}, limite) is False
    assert _publicada_recientemente({"fecha_publicacion": None}, limite) is False
