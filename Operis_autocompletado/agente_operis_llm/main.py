"""
main.py — punto de entrada único de agente_operis para uso local.

Uso:
    python main.py --demo                       -> un solo disparo sobre
                                                     inputs/payload_demo.json
                                                     (llama a Groq de verdad;
                                                     ya NO es gratis ni
                                                     determinista, ver nota
                                                     abajo), guarda la salida
                                                     en outputs/respuestas_json/
                                                     salida_demo.json
    python main.py ruta/al/briefing.txt          -> procesa un archivo cualquiera
                                                     (.txt/.pdf/.docx) con el
                                                     motor llm (Groq)
    python main.py ruta/al/briefing.txt --id-evento evt_123
                                                  -> igual, con un id_evento
                                                     concreto (por defecto:
                                                     "evt_manual_001")

Nota: esto es solo para pruebas/uso local en consola. ejecutar_agente(payload)
en src/agente.py sigue siendo el único contrato de integración real
(README.md, sección 9) — mismo principio que
Agente_04_Copilot_Raul/lumen_agente_04/main.py.

Nota sobre --demo: el motor de reglas (gratis, determinista) se eliminó --
ahora solo existe el motor llm (Groq). Esto significa que --demo ya NO es
gratis ni 100% determinista: hace una llamada real a la API de Groq y
consume tokens de tu cuota. La comparación con salida_demo.json sigue
sirviendo para detectar cambios inesperados, pero no esperes una salida
carácter por carácter idéntica entre ejecuciones (temperature=0 acota la
variabilidad, no la elimina del todo).
"""

import json
import sys
import argparse
from pathlib import Path

# La consola de Windows por defecto usa cp1252, que no sabe codificar
# los emoji que el LLM devuelve dentro de "resumen" (p. ej. "✅"/"⚠️").
# Sin esto, print() revienta con UnicodeEncodeError en vez de mostrar
# la respuesta. reconfigure() existe desde Python 3.7.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))  # permite "from src.agente import ..." y "from config import ..."

from src.agente import ejecutar_agente  # noqa: E402
from src.lectura_archivos import leer_archivo  # noqa: E402
from config import settings  # noqa: E402


def construir_payload(texto_briefing: str, id_evento: str) -> dict:
    """Construye un payload mínimo válido (ver src/validaciones.py) para pruebas manuales."""
    return {
        "id_evento": id_evento,
        "id_registro": None,
        "tipo_peticion": "extraer_briefing",
        "origen": "manual",
        "usuario_solicitante": "cli",
        "rol_usuario": "organizador",
        "datos": {
            "texto_briefing": texto_briefing
        },
        "contexto": {},
        "modo": "propuesta"
    }


def modo_demo():
    """Un solo disparo sobre inputs/payload_demo.json (llama a Groq de verdad)."""
    es_valida, mensaje_error = settings.validar_configuracion()
    if not es_valida:
        print(f"ERROR: {mensaje_error}")
        print("Define GROQ_API_KEY en .env antes de ejecutar --demo (motor único: llm).")
        return

    payload_path = BASE_DIR / "inputs" / "payload_demo.json"
    output_dir = BASE_DIR / "outputs" / "respuestas_json"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    print("--- Payload de entrada ---")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    respuesta = ejecutar_agente(payload)

    print("\n--- Respuesta de agente_operis ---")
    print(json.dumps(respuesta, ensure_ascii=False, indent=2))

    ruta_salida = output_dir / "salida_demo.json"

    if ruta_salida.exists():
        with open(ruta_salida, "r", encoding="utf-8") as f:
            referencia = json.load(f)
        # Ignoramos "trazas.timestamp" (cambia siempre) y "datos_detectados.
        # nota_bene.cabecera.ultima_actualizacion" (solo se rellena en modo
        # actualización, no aplica a este payload de demo sin histórico).
        comparable_actual = {k: v for k, v in respuesta.items() if k != "trazas"}
        comparable_ref = {k: v for k, v in referencia.items() if k != "trazas"}
        if comparable_actual == comparable_ref:
            print("\n[OK] Coincide con outputs/respuestas_json/salida_demo.json.")
        else:
            print("\n[DIFERENCIA] No coincide con salida_demo.json — motor llm, "
                  "puede variar entre ejecuciones aunque el briefing sea el mismo.")

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(respuesta, f, ensure_ascii=False, indent=2)

    print(f"\nRespuesta guardada en: {ruta_salida}")


def modo_archivo(ruta_archivo: str, id_evento: str):
    """Procesa un archivo cualquiera pasado por línea de comandos."""
    es_valida, mensaje_error = settings.validar_configuracion()
    if not es_valida:
        print(f"ERROR: {mensaje_error}")
        return

    print("=" * 70)
    print("AGENTE OPERIS - EXTRACCIÓN DE BRIEFING")
    print("=" * 70)
    print(f"Archivo: {ruta_archivo}")
    print(f"id_evento: {id_evento}")
    print("-" * 70)

    try:
        texto = leer_archivo(ruta_archivo)
    except Exception as e:
        print(f"ERROR al leer el archivo: {e}")
        return

    payload = construir_payload(texto, id_evento)
    respuesta = ejecutar_agente(payload)

    if not respuesta["ok"]:
        print(f"ERROR: {'; '.join(respuesta['errores'])}")
        return

    print("\nRESPUESTA DEL AGENTE (contrato con el orquestador):")
    print("-" * 70)
    print(json.dumps(respuesta, ensure_ascii=False, indent=2))

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Resumen: {respuesta['resumen']}")
    cabecera = respuesta["datos_detectados"].get("nota_bene", {}).get("cabecera", {})
    if cabecera.get("fecha_celebracion"):
        print(f"Fechas del evento: {cabecera['fecha_celebracion']}")
    if cabecera.get("presupuesto_total_estimado"):
        print(f"Presupuesto estimado: {cabecera['presupuesto_total_estimado']}")
    if respuesta["bloqueos_detectados"]:
        print(f"Campos pendientes: {', '.join(respuesta['bloqueos_detectados'])}")
    else:
        print("Todos los campos obligatorios han sido detectados.")
    print(f"requiere_validacion_humana: {respuesta['requiere_validacion_humana']}")
    print(f"nivel_riesgo: {respuesta['nivel_riesgo']}")


def main():
    parser = argparse.ArgumentParser(
        description="agente_operis — extracción de briefings de eventos (uso local). "
                     "Motor único: llm (Groq)."
    )
    parser.add_argument("archivo", nargs="?", default=None, help="Ruta al briefing (.txt/.pdf/.docx)")
    parser.add_argument("--id-evento", default="evt_manual_001",
                         help="id_evento del payload (obligatorio en el contrato; "
                              "por defecto 'evt_manual_001' para pruebas locales).")
    parser.add_argument("--demo", action="store_true", help="Ejecuta inputs/payload_demo.json")
    args = parser.parse_args()

    if args.demo or not args.archivo:
        modo_demo()
    else:
        modo_archivo(args.archivo, args.id_evento)


if __name__ == "__main__":
    main()
