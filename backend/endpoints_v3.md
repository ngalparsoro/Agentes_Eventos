# Endpoints del sistema · v3 — inventario real

**Fecha:** 9 de julio de 2026 · Acompaña a `contrato_api_eventos_3.md` (convenciones y reglas).
**Sustituye** como referencia de rutas a la sección de endpoints de `contrato_api_eventos_2.md` y a los `openapi.yaml`/`openapi_raul.yaml` de esta carpeta (borradores previos).
La especificación máquina del backend vive en su repo: `proyectoTripulacionesBackend` (rama **`develop`**) → `openapi.yaml` + colección Postman.

Leyenda: ✅ implementado y probado · 🔨 implementado, no probado por nosotros · ⚠️ pendiente de construir

---

## 1. Backend (Express) — `http://localhost:3000/api/v1`

Autenticación: `POST /auth/login` con id-token de Firebase → deja **JWT en cookie httpOnly**. Todas las rutas de recursos exigen sesión con rol `admin` (hoy, todo el que entra es admin — ver contrato §3).
Sobre de respuesta: `{ ok, msg, filters, data }`.

### Auth y utilidades
| Ruta | Qué hace | Estado |
|---|---|---|
| `GET /health` | Health check | 🔨 |
| `POST /auth/login` | Login con Firebase, JWT en cookie | 🔨 |
| `GET /auth/verify` | ¿Sesión válida? | 🔨 |
| `GET /auth/logout` | Cierra sesión | 🔨 |
| `POST /upload` | Sube archivo a Cloudinary (fotos ponentes, presentaciones) | 🔨 |

### Recursos (CRUD, todos admin-only)
| Recurso | Rutas | Filtros query | Estado |
|---|---|---|---|
| Eventos | `GET/POST /eventos` · `GET/PATCH/DELETE /eventos/{id}` | `ciudad`, `tipo_evento`, `estado` | 🔨 ⚠️¹ |
| Clientes | `GET/POST /clientes` · `GET/PATCH/DELETE /clientes/{id}` | `sector`, `ciudad` | 🔨 |
| Espacios | `GET/POST /espacios` · `GET/PATCH/DELETE /espacios/{id}` · `GET /espacios/buscar` | `ciudad`, `aforo`; buscar: `min`, `max` (capacidad) | 🔨 |
| Ponentes | `GET/POST /ponentes` · `GET/PATCH/DELETE /ponentes/{id}` (con subida de foto) | `sector` | 🔨 |
| Salas | `GET/POST /salas` · `GET/PATCH/DELETE /salas/{id}` | `idEspacio` | 🔨 |
| Ponencias | `GET/POST /ponencias` · `GET/PATCH/DELETE /ponencias/{id}` | — | 🔨 |

¹ Aviso: `GET /eventos` **con** filtros responde en `snake_case` (SQL crudo) y **sin** filtros en `camelCase` (Prisma). Ver contrato §2.3 — hasta que backend unifique, cuidado en el front.

### Pendientes pedidos al backend ⚠️
| Ruta | Para quién | Por qué |
|---|---|---|
| `GET/POST /presupuestos` (+`/{id}`) | Front (dashboard presupuesto) | Modelo existe, ruta no |
| `GET /estados` | Front (desplegables de estado) | Modelo existe, ruta no |
| `GET /ponentes/by-telegram/{telegram_user_id}` | Agente Telegram | Identificar al ponente que escribe (requiere además la columna en BD) |
| Aceptar `Authorization: Bearer` además de cookie | Todos los agentes | Hoy los agentes no pueden autenticarse (middleware solo lee cookie) |
| `POST /borradores`, `POST /bloqueos` + aprobar/rechazar | Agentes (fase 2) | Persistir propuestas de la IA con validación humana |

---

## 2. Agentes (API para el front) — HTTP directo, CORS activado

Sin autenticación (fase demo, solo lectura). Los tres pueden convivir arrancados: puertos 5000/5001/5002.

### Lumen — copiloto de consulta · `http://localhost:5001` ✅
Arrancar: `cd Agente_04_Copilot_Raul/lumen_agente_04 && python servidor.py`
Datos: **Neon real** (rol solo-lectura). Probado: responde los 40 eventos, estados sin distinguir mayúsculas.

| Ruta | Body | Devuelve |
|---|---|---|
| `GET /` | — | health + sesiones activas |
| `POST /chat` | `{"pregunta": "...", "sesion_id": "..."(opcional)}` | `{resumen, datos_detectados, sesion_id, ...}` — **guardar `sesion_id`** y reenviarlo para mantener la memoria de conversación |
| `POST /chat/reset` | `{"sesion_id": "..."}` | olvida esa conversación |

```js
const r = await fetch("http://localhost:5001/chat", {
  method: "POST", headers: {"Content-Type": "application/json"},
  body: JSON.stringify({ pregunta: "¿Cuántos eventos hay confirmados?", sesion_id })
});
```

### Operis — autocompletar briefing · `http://localhost:5002` ✅
Arrancar: `cd agente_operis_autocompletar_Ainara_Dv/agente_operis_llm && pip install -r requirements_servidor.txt && python servidor.py`
Probado con el motor de reglas (gratis, sin API key). Con `GROQ_API_KEY` en su `.env` puede usarse `"motor": "llm"`.

| Ruta | Body | Devuelve |
|---|---|---|
| `GET /` | — | health + motor por defecto |
| `POST /autocompletar` | `{"texto_briefing": "...", "motor": "reglas"\|"llm"(opcional)}` | contrato común del agente: `datos_detectados` con 6 bloques (evento, cliente, espacio, sala, presupuesto, ponentes), `bloqueos_detectados` (campos no encontrados), `requiere_validacion_humana: true` **siempre** |

**Regla para el front:** lo que devuelve Operis se pinta como **propuesta editable** en el formulario. Nunca se guarda solo — guardar es del backend tras revisión humana.

### Mock API (API_Nora) · `http://localhost:5000` ✅
`cd API_Nora/api/mock && pip install -r requirements.txt && python app.py`
Réplica del contrato v2 con datos falsos. Útil para maquetar pantallas cuya ruta real aún no existe (presupuesto, borradores IA). **No confundir sus datos con los reales.**

### Otros agentes (no exponen API al front)
- **Agente Telegram (ponentes)**: su interfaz es Telegram; el front no lo llama. Bloqueado por `telegram_user_id` (BD).
- **Vigil (alertas de concursos)**: genera HTML/ICS por su cuenta; el front puede enlazar su salida.

---

## 3. Acceso a datos de los agentes (no es HTTP, pero es parte del mapa)

Los agentes leen **Neon Postgres** directamente con el rol `agente_readonly`: solo `SELECT` sobre `clientes, espacios, estados, eventos, ponencias, ponentes, presupuestos, salas`; sin acceso a `usuarios`; escritura imposible a nivel de BD. Configuración: `DATABASE_URL` en el `.env` de cada agente (pedir la credencial a Nora — **nunca** usar la cadena del owner ni subirla a git). Patrón de código: `lumen_agente_04/integrations/bd_backend.py`.

---

## 4. Registro de cambios

| Versión | Fecha | Qué |
|---|---|---|
| v3 | 2026-07-09 | Primer inventario contra el sistema real: backend `develop`, servidores de agentes Lumen/Operis, Neon. Marca pendientes y el aviso snake/camel. |
| v2 | jul 2026 | Endpoints propuestos en `contrato_api_eventos_2.md` + mock (previos al código real). |
