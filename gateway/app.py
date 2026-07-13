"""Gateway de data (:5003) — una sola URL para el front, agentes detrás.

Sigue el patrón del backend unificado de la v4 (endpoints_v4.md): los agentes
se consumen bajo `/agentes/<nombre>/...`, pero aquí NO se cargan en el mismo
proceso (aquello obligaba a resolver colisiones de paquetes `src`/`config`
entre agentes): cada agente sigue siendo su propio servidor y el gateway
reenvía la petición por HTTP. Ventajas para la integración:

- El front integra contra UNA base (`http://localhost:5003`) y rutas
  definitivas, aunque el agente de detrás aún no exista.
- Los agentes que faltan por llegar responden con un STUB que tiene la
  forma real del contrato (marcado con `"_stub": true`); cuando llegue el
  definitivo, se registra su URL en AGENTES y el stub se retira SIN que el
  front cambie nada.

Arrancar:  pip install -r requirements.txt && python app.py   (o vía
../arrancar_todo.sh, que lo levanta junto al resto con el .env común).
"""

# traigo os para leer el puerto del entorno
import os

# traigo FastAPI para declarar la API y httpx para reenviar peticiones
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

app = FastAPI(
    title="Agentes_Eventos — gateway de data",
    description="Una sola URL para el front: agentes reales por proxy y stubs de los pendientes.",
    version="1.0.0",
)

# CORS abierto (fase demo): el front en otro puerto puede llamar sin bloqueo
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------------------------------------------------------------------
# Registro de agentes REALES: nombre → (url base, ruta de health)
# Cuando llegue un agente definitivo que hoy es stub, se añade aquí y se
# borra su entrada de STUBS_PENDIENTES. Nada más.
# ---------------------------------------------------------------------
AGENTES = {
    "operis": {"base": "http://127.0.0.1:5002", "health": "/"},
    "jano": {"base": "http://127.0.0.1:8001", "health": "/health"},
    "vigil": {"base": "http://127.0.0.1:8000", "health": "/health"},
}

# Backend de datos para agentes (no es un agente, pero es parte del mapa)
BACKEND_AGENTES = {"base": "http://127.0.0.1:5004", "health": "/"}

# Agentes PENDIENTES de recibir en versión definitiva: responden 501 con
# un mensaje claro (salvo los que tienen stub con forma real, más abajo).
STUBS_PENDIENTES = {
    "correos": "Agente gestor de correos — pendiente de recibir la versión definitiva.",
    "alertas": "Agente de alertas — pendiente de definir (ver endpoints_v4.md).",
}

# tiempo máximo de espera al reenviar (Operis con LLM puede tardar)
TIMEOUT_PROXY = 60.0


def _error(codigo: str, mensaje: str, http: int = 400) -> JSONResponse:
    # mismo formato de error común que en v3/v4
    return JSONResponse({"error": True, "codigo": codigo, "mensaje": mensaje}, status_code=http)


# ---------------------------------------------------------------------
# Stub de Lumen: contrato real del chat (endpoints_v4.md) con datos de
# ejemplo. El front puede montar su pantalla de chat contra esto HOY.
# ---------------------------------------------------------------------
@app.post("/agentes/lumen/chat")
async def stub_lumen_chat(request: Request):
    cuerpo = {}
    try:
        cuerpo = await request.json()
    except Exception:
        pass
    if not isinstance(cuerpo, dict) or not (cuerpo.get("pregunta") or "").strip():
        return _error("CAMPO_OBLIGATORIO", "El campo 'pregunta' es obligatorio.")
    return {
        "_stub": True,
        "resumen": "[STUB] Lumen aún no está conectado en este repo. Esta respuesta tiene la forma real del contrato para que el front pueda integrar la pantalla de chat.",
        "datos_detectados": {},
        "sesion_id": cuerpo.get("sesion_id") or "sesion-stub-0001",
        "id_evento_actual": None,
        "requiere_validacion_humana": True,
    }


@app.post("/agentes/lumen/chat/reset")
async def stub_lumen_reset(request: Request):
    cuerpo = {}
    try:
        cuerpo = await request.json()
    except Exception:
        pass
    return {"_stub": True, "ok": True, "sesion_id": (cuerpo or {}).get("sesion_id")}


# ---------------------------------------------------------------------
# Alias de compatibilidad v4 (mismas rutas en la raíz): el front actual
# puede migrar al gateway cambiando solo la URL base.
# ---------------------------------------------------------------------
@app.post("/chat")
async def alias_chat(request: Request):
    return await stub_lumen_chat(request)


@app.post("/chat/reset")
async def alias_chat_reset(request: Request):
    return await stub_lumen_reset(request)


@app.post("/autocompletar")
async def alias_autocompletar(request: Request):
    return await proxy_agente("operis", "autocompletar", request)


# ---------------------------------------------------------------------
# Salud agregada: el smoke test y el front pueden ver todo de un vistazo
# ---------------------------------------------------------------------
@app.get("/salud")
async def salud():
    estado = {}
    async with httpx.AsyncClient(timeout=3.0) as cliente:
        # pregunto a cada agente real y al backend de agentes
        piezas = dict(AGENTES)
        piezas["backend_agentes"] = BACKEND_AGENTES
        for nombre, datos in piezas.items():
            try:
                r = await cliente.get(datos["base"] + datos["health"])
                estado[nombre] = "ok" if r.status_code == 200 else f"http {r.status_code}"
            except httpx.HTTPError:
                estado[nombre] = "no responde"
    # los stubs siempre están "disponibles" (viven en este proceso)
    estado["lumen"] = "stub"
    for nombre in STUBS_PENDIENTES:
        estado[nombre] = "pendiente"
    return {"servicio": "gateway de data", "puerto": os.getenv("PUERTO_GATEWAY", "5003"), "agentes": estado}


@app.get("/")
def raiz():
    return {
        "servicio": "Agentes_Eventos — gateway de data",
        "documentacion": "/docs",
        "salud": "/salud",
        "agentes_reales": sorted(AGENTES),
        "stubs": ["lumen"] + sorted(STUBS_PENDIENTES),
    }


# ---------------------------------------------------------------------
# Proxy genérico: /agentes/<nombre>/<lo que sea> → servidor del agente
# (declarado el último para no tapar las rutas de stub de arriba)
# ---------------------------------------------------------------------
@app.api_route("/agentes/{agente}/{ruta:path}", methods=["GET", "POST"])
async def proxy_agente(agente: str, ruta: str, request: Request):
    # si es un pendiente sin stub, lo digo claro (el front sabe a qué atenerse)
    if agente in STUBS_PENDIENTES:
        return _error("AGENTE_PENDIENTE", STUBS_PENDIENTES[agente], http=501)
    if agente not in AGENTES:
        return _error("RUTA_NO_ENCONTRADA", f"No conozco el agente '{agente}'. Reales: {sorted(AGENTES)}; stub: lumen.", http=404)

    destino = AGENTES[agente]["base"] + "/" + ruta
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_PROXY) as cliente:
            respuesta = await cliente.request(
                request.method,
                destino,
                params=dict(request.query_params),
                content=await request.body(),
                headers={"Content-Type": request.headers.get("Content-Type", "application/json")},
            )
    except httpx.HTTPError:
        return _error("AGENTE_CAIDO", f"El agente '{agente}' no responde en {AGENTES[agente]['base']}. ¿Está arrancado?", http=502)

    # devuelvo el cuerpo tal cual (JSON, PDF, ICS…) con su tipo y su código
    return Response(
        content=respuesta.content,
        status_code=respuesta.status_code,
        media_type=respuesta.headers.get("Content-Type", "application/json"),
    )


if __name__ == "__main__":
    import uvicorn

    puerto = int(os.getenv("PUERTO_GATEWAY", "5003"))
    print(f"gateway de data — escuchando en http://127.0.0.1:{puerto}  (docs en /docs)")
    uvicorn.run(app, host="127.0.0.1", port=puerto)
