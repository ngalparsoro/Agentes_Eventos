# Endpoints del sistema · v5 — repo Agentes_Eventos

**Fecha:** 13 de julio de 2026 · Acompaña a `contrato_api_eventos_3.md` (convenciones y reglas, sigue vigente).
**Sustituye** a `endpoints_v4.md` en lo relativo a agentes. La sección 1 (backend Express :3000)
de `endpoints_v3.md` **sigue siendo la referencia** del backend full stack — aquí no se repite.

**Qué cambia respecto a v4:** los agentes de data viven ahora en el repo `Agentes_Eventos`
(github.com/ngalparsoro/Agentes_Eventos) con nombres nuevos, hay dos agentes que la v3/v4 no
recogían (Jano y Vigil con API propia), un backend de datos para agentes (:5004) y un
**gateway por proxy HTTP** (:5003) que sustituye al backend unificado en-proceso de la v4:
misma URL y mismas rutas `/agentes/...` para el front, pero cada agente sigue siendo su
propio servidor (se acabaron las colisiones de paquetes `src`/`config`).

⚠️ **Aviso Operis:** la v3/v4 documentaban el motor `"reglas"` y el `texto_briefing` como único
obligatorio. **Obsoleto**: el Operis de este repo es el contrato V2 — `id_evento` OBLIGATORIO
y motor único `"llm"` (sin `GROQ_API_KEY` devuelve error controlado).

Leyenda: ✅ implementado y probado · 🔨 implementado, no probado · ⚠️ pendiente · 🧩 stub (forma real, datos de ejemplo)

---

## 0. Mapa de puertos (canónico)

| Puerto | Servicio | Quién lo consume |
|---|---|---|
| 3000 | Backend Express (full stack) | Front (datos + escrituras) |
| 5000 | Mock API_Nora (Desafio_Mit-mi) | Front (pantallas sin ruta real) |
| 5001 | Lumen | Gateway (o front directo, plan B) |
| 5002 | Operis | Gateway (o front directo, plan B) |
| **5003** | **Gateway de data (este repo)** | **Front — LA base de integración** |
| 5004 | Backend de datos para agentes | Hermes, gestor de correos |
| 8000 | Vigil | Gateway (o front directo, plan B) |
| 8001 | Jano | Gateway (o front directo, plan B) |

**Regla de integración:** el front habla con `http://localhost:5003` y rutas `/agentes/<nombre>/...`.
Los servidores sueltos siguen operativos como plan B (igual que en v4).

---

## 1. Gateway de data — `http://localhost:5003` · carpeta `gateway/` 🔨

Arrancar: `./arrancar_todo.sh` en la raíz del repo (levanta todo con el `.env` común), o
`cd gateway && pip install -r requirements.txt && python app.py` para él solo.
Swagger: `GET /docs` · Sin autenticación, CORS abierto (fase demo).

| Ruta | Qué hace | Estado |
|---|---|---|
| `GET /` | Info: agentes reales registrados y stubs activos | 🔨 |
| `GET /salud` | Salud agregada de TODAS las piezas (agentes, backend :5004, stubs) | 🔨 |
| `POST /agentes/lumen/chat` · `/chat/reset` | Proxy → Lumen :5001 | 🔨 |
| `POST /agentes/operis/autocompletar` | Proxy → Operis :5002 | 🔨 |
| `GET/POST /agentes/jano/...` | Proxy → Jano :8001 (buscar, informes PDF, health) | 🔨 |
| `GET/POST /agentes/vigil/...` | Proxy → Vigil :8000 (concursos, ejecuciones, ICS, pliegos) | 🔨 |
| `/agentes/correos/...` · `/agentes/alertas/...` | 501 `AGENTE_PENDIENTE` hasta que lleguen los definitivos | ⚠️ |
| `POST /autocompletar` · `/chat` · `/chat/reset` | Alias de compatibilidad v4 en la raíz | 🔨 |

**Enchufar un agente definitivo cuando llegue:** registrar su URL en `AGENTES` de
`gateway/app.py`, quitar su stub y correr `./comprobar_salud.sh`. El front no cambia nada.

**Errores** (formato común de v3/v4): `{"error": true, "codigo": "...", "mensaje": "..."}` —
códigos propios del gateway: `AGENTE_PENDIENTE` (501), `AGENTE_CAIDO` (502), `RUTA_NO_ENCONTRADA` (404).

---

## 2. Agentes reales de este repo

### Lumen — chat copiloto de consulta · `:5001` · `Lumen_buscador/lumen_agente_04/` ✅ (llegó 13/07)

| Ruta | Body | Devuelve |
|---|---|---|
| `GET /` | — | health + sesiones activas |
| `POST /chat` | `{"pregunta": "...", "sesion_id": "..."(opcional)}` | `{resumen, datos_detectados, sesion_id, ...}` — **guardar `sesion_id`** y reenviarlo para mantener la memoria de conversación |
| `POST /chat/reset` | `{"sesion_id": "..."}` | olvida esa conversación |

Lee Neon real (readonly). Necesita `DATABASE_URL` y `GROQ_API_KEY`/`LLM_PROVIDER=groq` (del `.env` común o de su `.env` local en `lumen_agente_04/`).

### Operis — autocompletar briefing · `:5002` · `Operis_autocompletado/agente_operis_llm/` ✅ (contrato V2)

| Ruta | Body | Devuelve |
|---|---|---|
| `GET /` | — | health + motor por defecto |
| `POST /autocompletar` | `{"id_evento": "..."` **(OBLIGATORIO)**`, "texto_briefing": "..."` **(obligatorio)**`, "bloques_a_actualizar": [...](opc), "historial_anterior": {...}(opc)}` | contrato común: `datos_detectados` (4 bloques: evento, cliente, ponentes, nota_bene), `bloqueos_detectados`, `requiere_validacion_humana: true` SIEMPRE |

Motor único `"llm"` (Groq). Sin `historial_anterior`, lo autocarga de la BD por `id_evento`.
El front pinta la salida como **propuesta editable**, nunca la guarda solo.

### Jano — transporte y hotel para ponentes · `:8001` · `Jano_transporte/` ✅

| Ruta | Body/Query | Devuelve |
|---|---|---|
| `GET /health` | — | `{estado, hora}` |
| `POST /buscar` | formulario de búsqueda (ver `mercurio/schemas.py: SolicitudBusqueda`) | sugerencias de hotel y/o viaje + enlaces a los dos PDFs |
| `GET /informes/{id_busqueda}/ponente.pdf` | — | informe PDF sin precios (para el ponente) |
| `GET /informes/{id_busqueda}/mitumi.pdf` | — | informe PDF con precios (interno) |

Sin BD: la entrada es la petición, la salida el JSON + PDFs en disco. Validación 422 estilo FastAPI (`{"detail": [...]}`).

### Vigil — búsqueda de concursos públicos · `:8000` · `Vigil_busquedaconcursos/` ✅

| Ruta | Body/Query | Devuelve |
|---|---|---|
| `GET /health` | — | `{estado, hora}` |
| `GET /concursos` | filtros: texto, diputación, urgencia, solo en plazo, solo relevantes | histórico de convocatorias |
| `GET /concursos/{id_expediente}/calendario.ics` | — | evento de calendario del plazo |
| `GET /concursos/{id_expediente}/pliego.pdf` | — | resumen PDF del pliego |
| `POST /ejecuciones` | — | lanza scrape+LLM en segundo plano; devuelve `id` (tarda minutos) |
| `GET /ejecuciones/{run_id}` | — | progreso de esa ejecución (estado en memoria: se pierde al reiniciar) |

### Hermes — bot de Telegram para ponentes · `Hermes_telegram/` ✅ (sin API HTTP)

Su interfaz es Telegram (long polling): **el front no lo llama**. Necesita `TELEGRAM_BOT_TOKEN`,
`LLM_API_KEY` (Groq) y `DATABASE_URL` (readonly). Hoy lee Neon directo; el backend :5004 queda
listo para cuando se le conecte por API. Arranque: `./arrancar_todo.sh --con-hermes`.
Sigue bloqueado por la columna `telegram_user_id` en `ponentes` (pendiente de BD desde v3).

---

## 3. Backend de datos para agentes — `http://localhost:5004` · carpeta `backend/` 🔨

FastAPI · lee Neon con rol `agente_readonly` · **los POST guardan solo en memoria local** (los
agentes no pueden escribir; la escritura real seguirá siendo del backend Express cuando existan
`POST /borradores`/`/bloqueos` — contrato §6). Swagger en `/docs`.

| Ruta | Qué hace |
|---|---|
| `GET /` | health + lista de rutas |
| `GET /api/ponentes/by-telegram/{telegram_user_id}` | ponente por id de Telegram (fallback a mapeo demo si falta la columna) |
| `GET /api/ponentes/{id_ponente}/eventos-activos` | eventos activos de un ponente |
| `GET /api/eventos/{id_evento}/ponentes` | todos los ponentes de un evento con su logística |
| `GET /api/eventos/{id_evento}/ponentes/{id_ponente}` | detalle logístico completo (hotel, vuelos, taxis, documentos) |
| `POST /api/comunicaciones` · `POST /api/incidencias` | registro en memoria local + log (mock de escritura) |

---

## 4. Agentes pendientes de recibir ⚠️

| Agente | Ruta reservada en el gateway | Estado |
|---|---|---|
| Gestor de correos | `/agentes/correos/...` | ⚠️ 501; contrato por definir al recibirlo |
| Alertas (Roberto) | `/agentes/alertas/...` | ⚠️ 501; pendiente de definir desde v4 |

---

## 5. Entorno y arranque

- **`.env` común en la raíz** (copiar de `.env.example`): `arrancar_todo.sh` lo exporta antes de
  lanzar cada servicio; como `load_dotenv()` no pisa el entorno ya exportado, el común manda y
  los `.env` locales de cada agente quedan de respaldo para arrancarlos sueltos.
- `./arrancar_todo.sh` levanta backend :5004 + Operis + Jano + Vigil + gateway (logs en `.logs/`);
  `--con-hermes` añade el bot; `--parar` detiene todo.
- `./comprobar_salud.sh` es el smoke test: ✓/✗ por servicio + salud agregada del gateway.

## 6. Registro de cambios

| Versión | Fecha | Qué |
|---|---|---|
| v5 | 2026-07-13 | Inventario del repo Agentes_Eventos: gateway por proxy :5003 con stubs, Jano y Vigil documentados, backend :5004, Operis V2, mapa de puertos y .env común. Misma tarde: llegó Lumen definitivo y quedó conectado al gateway (su stub se retiró). |
| v4 | 2026-07-10 | Backend unificado de data :5003 en-proceso (Lumen+Operis). |
| v3 | 2026-07-09 | Primer inventario real (backend Express, Lumen :5001, Operis :5002 V1). |
