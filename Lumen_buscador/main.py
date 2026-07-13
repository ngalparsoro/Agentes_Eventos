"""
main.py — Punto de entrada unico de Lumen (Agente 04 - Copilot) para uso local en consola.

Uso:
    cd lumen_agente_04
    python main.py            -> chat interactivo con memoria de sesion (uso normal)
    python main.py --demo     -> un solo disparo sobre inputs/payload_demo.json (regresion /
                                  prueba reproducible), guarda la salida en
                                  outputs/respuestas_json/salida_demo.json

Antes existian tres scripts sueltos (main.py, preguntar.py, chat.py) que hacian variaciones de
lo mismo. Se han unificado aqui: preguntar.py y chat.py ya no existen. La memoria de
conversacion vive en src/memoria.py, compartida con servidor.py (la API HTTP que usa el
frontend React) para no duplicar logica.

Nota: esto sigue siendo solo para pruebas/uso local en consola. El frontend React NO llama a
este script -- llama a servidor.py (API HTTP). ejecutar_agente(payload) en src/agente.py sigue
siendo el unico contrato de integracion real (README.md, seccion 1).
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))  # permite "from src.agente import ..." y "from config import ..."

from src.agente import ejecutar_agente  # noqa: E402
from src.memoria import MemoriaConversacion, construir_payload  # noqa: E402


def modo_demo():
    """Un solo disparo sobre inputs/payload_demo.json.

    El id_evento se resuelve igual que en el chat (MemoriaConversacion.resolver_id_evento): por
    UUID/numero explicito, por nombre de evento, o transversal si la pregunta no apunta a un
    evento concreto. Antes el payload traia un id_evento numerico hardcodeado (12) que no existe
    en la BD real -- los id reales son UUID -- y hacia que el demo fallase siempre. Ahora el
    payload puede dejar id_evento en null y nombrar el evento en la pregunta, o hacer una consulta
    transversal, y el demo funciona contra la BD real sin hardcodear ningun UUID."""
    payload_path = BASE_DIR / "inputs" / "payload_demo.json"
    output_dir = BASE_DIR / "outputs" / "respuestas_json"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    pregunta = (payload.get("datos") or {}).get("pregunta", "").strip()
    if payload.get("id_evento") is None and pregunta:
        id_evento, _usando_memoria, nombres_ambiguos = MemoriaConversacion().resolver_id_evento(pregunta)
        if nombres_ambiguos:
            print(
                "Aviso: el nombre de evento es ambiguo (" + ", ".join(nombres_ambiguos) +
                "). Se consulta sin fijar un id_evento concreto.\n"
            )
        payload["id_evento"] = id_evento

    print("--- Payload de entrada ---")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    respuesta = ejecutar_agente(payload)

    print("\n--- Respuesta de Lumen ---")
    print(json.dumps(respuesta, ensure_ascii=False, indent=2))

    with open(output_dir / "salida_demo.json", "w", encoding="utf-8") as f:
        json.dump(respuesta, f, ensure_ascii=False, indent=2)

    print(f"\nRespuesta guardada en: {output_dir / 'salida_demo.json'}")


def modo_chat():
    """Chat interactivo de consola, con memoria de conversacion (src/memoria.py)."""
    memoria = MemoriaConversacion()

    print("Lumen - Copilot de consulta de Mitumi (solo lectura, con memoria de sesion).")
    print("Escribe tu pregunta. 'nuevo' olvida el contexto actual. 'salir' termina.\n")

    while True:
        try:
            pregunta = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not pregunta:
            continue
        if pregunta.lower() in {"salir", "exit", "quit"}:
            break
        if pregunta.lower() in {"nuevo", "reset", "olvida", "olvidalo"}:
            memoria.reiniciar()
            print("(memoria de la conversacion reiniciada)\n")
            continue

        id_evento, _usando_memoria, nombres_ambiguos = memoria.resolver_id_evento(pregunta)
        if nombres_ambiguos:
            print(
                "Lumen: Hay mas de un evento que coincide con lo que preguntas: " +
                ", ".join(nombres_ambiguos) + ". ¿A cual te refieres?"
            )
            print()
            continue
        payload = construir_payload(id_evento, memoria.historial_para_payload(), pregunta)

        respuesta = ejecutar_agente(payload)

        print("Lumen:", respuesta.get("resumen", ""))
        if respuesta.get("bloqueos_detectados"):
            print("  (bloqueos:", ", ".join(respuesta["bloqueos_detectados"]), ")")
        if respuesta.get("errores"):
            print("  (errores:", ", ".join(respuesta["errores"]), ")")
        print()

        memoria.registrar_turno(pregunta, respuesta, id_evento)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        modo_demo()
    else:
        modo_chat()
