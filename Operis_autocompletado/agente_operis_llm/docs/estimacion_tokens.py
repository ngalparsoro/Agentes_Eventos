# estimacion_tokens.py
# =====================================================================
# MEDICIÓN DE USO DE TOKENS DEL AGENTE (Groq, src/llm.py)
# =====================================================================
# Mide el consumo REAL de tokens (no una estimación) haciendo una
# llamada de verdad a Groq para dos casos: un briefing simple
# (data/ejemplos/briefing_prueba.txt) y uno complejo con varios
# ponentes y servicios (data/ejemplos/briefing_complejo.txt).
#
# Ejecutar con: python docs/estimacion_tokens.py (desde la raíz del
# agente, agente_operis_llm/). Genera (o regenera) docs/ESTIMACION_TOKENS.md
# con el informe.
#
# REQUIERE GROQ_API_KEY configurada en .env: este script hace 2
# llamadas reales a la API y consume tokens de tu cuota (poco: ver
# tabla de resultados, del orden de 1000-3000 tokens en total).
#
# METODOLOGÍA:
#   - Antes de que el motor de reglas se eliminase, esta medición era
#     una ESTIMACIÓN con tiktoken sobre una salida "esperada" construida
#     a mano (el motor de reglas no soportaba consultar la API). Ahora
#     que el único motor es Groq y ya hay una clave real disponible, se
#     mide el consumo REAL de cada llamada (usage.prompt_tokens /
#     completion_tokens / total_tokens de la respuesta de la API) --
#     más preciso, y ya no hace falta aproximar nada.
#   - Precios de openai/gpt-oss-120b en Groq (verificados en julio de
#     2026): $0.15 / 1M tokens de entrada, $0.60 / 1M tokens de salida.
#   - Free tier de Groq para este modelo (verificado en julio de 2026):
#     1000 peticiones/día, 200.000 tokens/día -- Y ADEMÁS 8.000
#     tokens/minuto (TPM). Este script solo mide el consumo de UNA
#     llamada (no dice nada por sí solo del límite por minuto), pero el
#     TPM es el límite que de verdad importa vigilar en modo
#     actualización: una sola llamada con un prompt grande puede
#     saltarlo aunque quede mucho margen de tokens/día. Ver
#     src/schemas.py::extraer_ultimo_estado y
#     src/nucleo.py::_proteger_bloques_no_actualizados (12/07/2026): el
#     histórico que se manda al LLM se redujo a una única versión, y la
#     protección de bloques se movió a Python, precisamente para no
#     rozar este límite en actualizaciones con histórico.
# =====================================================================

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # agente_operis_llm/
sys.path.insert(0, str(BASE_DIR))

from src.llm import construir_prompt_sistema  # noqa: E402
from src.lectura_archivos import leer_archivo  # noqa: E402
from config import settings  # noqa: E402

PRECIO_INPUT_POR_M = 0.15
PRECIO_OUTPUT_POR_M = 0.60
LIMITE_TPD_FREE = 200_000
LIMITE_RPD_FREE = 1000
LIMITE_TPM_FREE = 8_000  # tokens/minuto -- el límite que salta con UNA llamada grande,
                          # no por acumulación de uso a lo largo del día (ver cabecera)


def medir_caso(nombre_caso, ruta_archivo):
    """Hace una llamada real a Groq y mide el consumo de tokens de verdad."""
    from groq import Groq

    texto = leer_archivo(str(ruta_archivo))
    prompt_sistema = construir_prompt_sistema()

    cliente_groq = Groq(api_key=settings.GROQ_API_KEY)
    respuesta = cliente_groq.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": texto},
        ],
    )

    uso = respuesta.usage
    tokens_input = uso.prompt_tokens
    tokens_salida = uso.completion_tokens
    tokens_totales = uso.total_tokens

    coste_input = tokens_input / 1_000_000 * PRECIO_INPUT_POR_M
    coste_output = tokens_salida / 1_000_000 * PRECIO_OUTPUT_POR_M
    coste_total = coste_input + coste_output

    llamadas_por_dia_tpd = LIMITE_TPD_FREE // tokens_totales if tokens_totales else 0
    llamadas_por_dia_free = min(llamadas_por_dia_tpd, LIMITE_RPD_FREE)

    return {
        "caso": nombre_caso,
        "archivo": str(ruta_archivo),
        "caracteres_texto": len(texto),
        "tokens_input_total": tokens_input,
        "tokens_salida_medidos": tokens_salida,
        "tokens_totales": tokens_totales,
        "coste_input_usd": coste_input,
        "coste_output_usd": coste_output,
        "coste_total_usd": coste_total,
        "llamadas_por_dia_en_free_tier": llamadas_por_dia_free,
        "cuello_de_botella_free_tier": "tokens/día" if llamadas_por_dia_tpd < LIMITE_RPD_FREE else "peticiones/día",
    }


def formatear_informe(casos):
    lineas = []
    lineas.append("# Medición de uso de tokens — agente Operis (Groq)")
    lineas.append("")
    lineas.append(
        "Generado automáticamente por `docs/estimacion_tokens.py`. Modelo: "
        f"`{settings.GROQ_MODEL}` en Groq. Consumo **medido de verdad** "
        "(usage de la respuesta de la API), no una estimación."
    )
    lineas.append("")
    lineas.append(
        f"Precios: ${PRECIO_INPUT_POR_M}/1M tokens entrada, "
        f"${PRECIO_OUTPUT_POR_M}/1M tokens salida. "
        f"Free tier: {LIMITE_RPD_FREE} peticiones/día, {LIMITE_TPD_FREE:,} tokens/día, "
        f"{LIMITE_TPM_FREE:,} tokens/minuto."
    )
    lineas.append("")
    lineas.append("## Resumen comparativo")
    lineas.append("")
    lineas.append("| | " + " | ".join(c["caso"] for c in casos) + " |")
    lineas.append("|---|" + "---|" * len(casos))

    filas = [
        ("Caracteres del briefing", "caracteres_texto", "{:,}"),
        ("Tokens de entrada (prompt sistema + briefing)", "tokens_input_total", "{:,}"),
        ("Tokens de salida (JSON medido)", "tokens_salida_medidos", "{:,}"),
        ("Tokens totales por llamada", "tokens_totales", "{:,}"),
        ("Coste entrada (USD)", "coste_input_usd", "${:.6f}"),
        ("Coste salida (USD)", "coste_output_usd", "${:.6f}"),
        ("Coste total por llamada (USD)", "coste_total_usd", "${:.6f}"),
        ("Llamadas/día posibles en free tier", "llamadas_por_dia_en_free_tier", "{:,}"),
        ("Límite que se agota primero", "cuello_de_botella_free_tier", "{}"),
    ]

    for etiqueta, clave, formato in filas:
        valores = [formato.format(c[clave]) for c in casos]
        lineas.append(f"| {etiqueta} | " + " | ".join(valores) + " |")

    lineas.append("")
    lineas.append("## Lectura de los resultados")
    lineas.append("")
    lineas.append(
        "- Estos números son una **medición real**, de una única llamada por "
        "caso, con `temperature=0`. Pueden variar ligeramente entre "
        "ejecuciones (la tokenización de la salida depende del contenido "
        "exacto que genere el modelo), pero deberían ser estables dentro de "
        "un margen pequeño."
    )
    lineas.append(
        "- El bloque Nota Bene (cabecera + 4 sub-bloques de presupuesto/"
        "servicios + información adicional) es la parte más grande del "
        "esquema de salida — normal que el caso complejo (varios ponentes, "
        "varios servicios) tenga una salida notablemente más larga que el "
        "simple."
    )
    lineas.append(
        "- El bloque `espacio` de la versión anterior del esquema (objeto "
        "único, no lista) desapareció: ahora la comparación de varios "
        "espacios candidatos se resume dentro de `nota_bene` (p. ej. en "
        "`presupuesto_servicios.ubicacion.nota` o en "
        "`informacion_adicional.notas_generales`), sin necesitar un bloque "
        "de datos estructurado propio para cada opción."
    )
    lineas.append(
        "- El límite que se agota primero en el free tier de Groq para este "
        "modelo, con briefings de este tamaño, es normalmente el de "
        "**tokens/día** (200.000), no el de peticiones/día (1000)."
    )
    lineas.append(
        "- **Nota sobre el modo actualización (actualizado 12/07/2026):** cuando se "
        "envía `contexto.historial_anterior`, el prompt de sistema crece con la "
        "última versión conocida del evento en JSON -- el consumo de tokens de "
        "entrada en ese modo sigue siendo mayor que el medido aquí (extracción "
        "inicial, sin histórico), pero ya no crece sin límite: antes se mandaba la "
        "lista COMPLETA de versiones anteriores (crecía con cada ronda de "
        "actualización y llegó a hacer saltar el límite de 8.000 tokens/minuto), "
        "ahora solo se manda la última (`src/schemas.py::extraer_ultimo_estado`). "
        "Además, el ejemplo JSON completo del prompt (~700 tokens) se omite "
        "automáticamente en modo actualización, porque la última versión ya hace de "
        "ejemplo. Estos números no incluyen esa diferencia -- para medirla de verdad "
        "haría falta una llamada real con `historial_anterior`, que este script no "
        "hace (para no complicar la comparación simple/complejo)."
    )
    lineas.append("")

    return "\n".join(lineas)


def main():
    es_valida, mensaje_error = settings.validar_configuracion()
    if not es_valida:
        print(f"ERROR: {mensaje_error}")
        print("Este script necesita GROQ_API_KEY real en .env -- hace llamadas de verdad a la API.")
        return

    ejemplos_dir = BASE_DIR / "data" / "ejemplos"

    caso_simple = medir_caso("Simple (briefing_prueba.txt)", ejemplos_dir / "briefing_prueba.txt")
    caso_complejo = medir_caso("Complejo (briefing_complejo.txt)", ejemplos_dir / "briefing_complejo.txt")

    casos = [caso_simple, caso_complejo]

    informe = formatear_informe(casos)

    ruta_informe = Path(__file__).resolve().parent / "ESTIMACION_TOKENS.md"
    with open(ruta_informe, "w", encoding="utf-8") as f:
        f.write(informe)

    print(informe)
    print(f"\n(Informe guardado también en {ruta_informe})")


if __name__ == "__main__":
    main()
