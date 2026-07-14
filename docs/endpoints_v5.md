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

**Aviso Operis:** la v3/v4 documentaban el motor `"reglas"` y `texto_briefing` como único
campo de texto. **Actualizado 14/07/2026**: Operis usa motor único `"llm"` y body flexible.
`id_evento` es opcional: si llega, permite usar histórico del evento; si no llega, procesa
una extracción inicial sin histórico para pantallas como Cliente o Espacio.

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
| `POST /agentes/garum/ciclos` | Lanza un ciclo de Garum en segundo plano (202 + `id_ciclo`); 409 si ya hay uno en marcha | 🔨 |
| `GET /agentes/garum/ciclos/{id_ciclo}` | Estado del ciclo: `en_marcha` / `terminado` (con `resultado`) / `error` | 🔨 |
| `/agentes/alertas/...` | Alias → Vigil (la ruta que reservó la v4; confirmado 13/07 que Vigil ES el agente de alertas) | 🔨 |
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
| `POST /autocompletar` | JSON flexible (`texto`, `texto_briefing`, `contenido` o `datos.texto_briefing`) o `multipart/form-data` con archivo `archivo`/`file`/`documento`/`upload` (`.txt`, `.pdf`, `.docx`), `tipo_objetivo` y `campos_objetivo`. `id_evento` es opcional. | contrato común: `datos_detectados` (4 bloques: evento, cliente, ponentes, nota_bene), `campos_detectados`, `campos_no_detectados`, `bloqueos_detectados`, `requiere_validacion_humana: true` SIEMPRE |

Motor único `"llm"` (Groq). Si llega `id_evento` y no llega `historial_anterior`, intenta autocargar histórico de la BD; sin `id_evento`, extrae desde cero.
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

### Garum — gestor de correos · `Garum_gestorcorreos/agente_gestor_correos/` ✅ (llegó 13/07, por ciclos)

No es un servidor: cada ejecución es un **ciclo** (lee Gmail no leídos vía **Composio**, clasifica
con Groq, deja **borradores** — `ALLOW_EMAIL_SEND=False`: nunca envía). Se dispara a mano
(`python main.py` en su carpeta) o desde el gateway (`POST /agentes/garum/ciclos`, ver §1).
Necesita `LLM_API_KEY` (Groq), `COMPOSIO_API_KEY` y `COMPOSIO_USER_ID`. ⚠️ Su README describe
OAuth de Google/OpenAI: es de una versión anterior, el código real usa Composio + Groq.

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

## 4. Agentes pendientes de recibir

**Ninguno** desde el 13/07: confirmado que el "agente de alertas (Roberto)" que la v4 dejó
pendiente es **Vigil** con su nombre definitivo (su README: *"agente de alertas de licitaciones"*).
`/agentes/alertas/...` queda como alias de Vigil por continuidad. **Los 6 agentes del sistema
están recibidos e integrados**: Lumen, Operis, Jano, Vigil, Hermes y Garum.

---

## 5. Entorno y arranque

- **`.env` común en la raíz** (copiar de `.env.example`): `arrancar_todo.sh` lo exporta antes de
  lanzar cada servicio; como `load_dotenv()` no pisa el entorno ya exportado, el común manda y
  los `.env` locales de cada agente quedan de respaldo para arrancarlos sueltos.
- `./arrancar_todo.sh` levanta backend :5004 + Operis + Jano + Vigil + gateway (logs en `.logs/`);
  `--con-hermes` añade el bot; `--parar` detiene todo.
- `./comprobar_salud.sh` es el smoke test: ✓/✗ por servicio + salud agregada del gateway.

## 6. Despliegue y ejemplos de petición/respuesta

### URLs base (mismas rutas en las dos)

| Entorno | URL base | Notas |
|---|---|---|
| Local | `http://localhost:5003` | `./arrancar_todo.sh` |
| Nube (Render) | `https://backstage-agentes.onrender.com` ¹ | contenedor Docker único (`render.yaml`); plan free: **se duerme a los 15 min** — despertar con `GET /salud` (~1 min) antes de la demo |

¹ Confirmar el sufijo exacto al crear el Blueprint (Render añade uno si el nombre está cogido).
Limitaciones de la imagen en nube: Vigil sirve su **histórico** pero no el scrape en vivo (sin
navegadores Playwright); Hermes va apagado por defecto (`ARRANCAR_HERMES`).

Todos los ejemplos siguientes son **capturas reales** del sistema (13/07/2026), abreviadas con `…`.

### Lumen — `POST /agentes/lumen/chat`

Entrada:
```json
{ "pregunta": "¿Qué eventos hay en Bilbao?", "sesion_id": "demo-doc-001" }
```
(`sesion_id` opcional: si no se manda, Lumen genera uno — **guardarlo y reenviarlo** para mantener la memoria.)

Salida:
```json
{
  "sesion_id": "demo-doc-001",
  "resumen": "Hay N evento(s) en Bilbao: …",
  "datos_detectados": {
    "eventos": [
      { "id_evento": "019f5b21-f482-78ef-b57a-8cfc9772fb40", "nombre_evento": "Tech Summit 2026" }
    ]
  },
  "bloqueos_detectados": [],
  "requiere_validacion_humana": false,
  "nivel_riesgo": "bajo",
  "id_evento_actual": null,
  "errores": []
}
```

### Operis — `POST /agentes/operis/autocompletar`

Entrada para evento existente (`id_evento` opcional, recomendado si se quiere histórico):
```json
{
  "id_evento": "019f5b21-f482-78ef-b57a-8cfc9772fb40",
  "texto_briefing": "Evento para 200 personas en Bilbao el 20 de octubre…",
  "bloques_a_actualizar": ["evento", "nota_bene"]
}
```

Entrada para autocompletar Cliente/Espacio sin evento:
```json
{
  "tipo_objetivo": "cliente",
  "texto": "Cliente: TechCorp S.L. Contacto: Laura Martinez, laura@techcorp.es, sector tecnologia."
}
```

Salida (200 si `ok`, 422 si el briefing no se pudo procesar — mismo cuerpo):
```json
{
  "ok": true,
  "agente": "agente_operis",
  "resumen": "…",
  "datos_detectados": {
    "evento":  { "nombre_evento": "…", "ciudad": "…", "fecha_inicio": "…", "fecha_fin": "…", "numero_personas": "…", "tipo_evento": "…", "estado": "…", "lugar_confirmado": "…", "nota": "…" },
    "cliente": { "cliente": "…", "empresa": "…", "email": "…", "…": "…" },
    "ponentes": [],
    "nota_bene": { "cabecera": { "…": "…" }, "presupuesto_servicios": { "…": "…" }, "informacion_adicional": { "…": "…" } },
    "_validacion": { "campos_pendientes": ["…"], "porcentaje_completado": 60 }
  },
  "bloqueos_detectados": [],
  "requiere_validacion_humana": true,
  "errores": [],
  "trazas": { "fuentes_consultadas": ["motor:llm"], "modo": "propuesta", "timestamp": "…" }
}
```
⚠️ `requiere_validacion_humana` es `true` **siempre**: el front pinta los campos como propuesta editable, nunca los guarda solo.

### Jano — `POST /agentes/jano/buscar`

Entrada (los campos del formulario):
```json
{
  "nombre_ponente": "Elena Vidal",
  "email_ponente": "elena.vidal@example.com",
  "nombre_evento": "Congreso Gastronómico Euskadi 2026",
  "ciudad_evento": "San Sebastián",
  "fecha_inicio": "2026-09-15",
  "fecha_fin": "2026-09-17",
  "ciudad_origen": "Madrid",
  "personas": 1,
  "preferencias": "cerca del recinto",
  "necesita_hotel": true,
  "necesita_viaje": true
}
```

Salida (los enlaces PDF se descargan contra la misma base, vía gateway: `/agentes/jano/informes/...`):
```json
{
  "propuesta": {
    "id": "e134a4d53fc0484c93c7e0bde828f0fd",
    "evento": { "nombre": "Congreso Gastronómico Euskadi 2026", "ciudad": "San Sebastián", "fecha_inicio": "2026-09-15", "fecha_fin": "2026-09-17" },
    "fecha_llegada": "2026-09-14",
    "fecha_salida": "2026-09-18",
    "hoteles": [
      { "nombre": "Gran Hotel Central San Sebastián", "estrellas": 4, "precio_noche": 215.0, "precio_total": 860.0, "noches": 4, "distancia_recinto_km": 0.8, "valoracion": 8.2, "enlace_reserva": "https://www.booking.com/…", "moneda": "EUR" }
    ],
    "trenes": [ { "…": "…" } ],
    "vuelos": [ { "…": "…" } ],
    "taxis":  [ { "…": "…" } ],
    "recomendacion": "…",
    "coste_estimado": 940.0,
    "resumen": "…"
  },
  "pdf_ponente": "/informes/e134a4d53fc0484c93c7e0bde828f0fd/ponente.pdf",
  "pdf_mitumi": "/informes/e134a4d53fc0484c93c7e0bde828f0fd/mitumi.pdf"
}
```

### Vigil — `GET /agentes/vigil/concursos?limite=1&en_plazo=true`

(Filtros query: `q`, `diputacion`, `urgencia`, `en_plazo`, `relevante`, `limite`, `offset`.)

Salida:
```json
{
  "total": 1,
  "concursos": [
    {
      "id_expediente": "EJEMPLO-2026-0000001",
      "diputacion": "Araba",
      "organo_convocante": "Diputación Foral de Álava",
      "objeto": "Servicio de organización integral y secretaría técnica del Congreso…",
      "importe": "45.000,00",
      "plazo_presentacion": "14/07/2026 23:59:00",
      "plazo_iso": "2026-07-14T23:59:00",
      "etiquetas": ["Institucional", "Sostenibilidad"],
      "motivo": "Es un servicio de organización de eventos que encaja con vuestro perfil…",
      "enlace_pliego": "https://…",
      "campos_no_verificables": []
    }
  ]
}
```
Extras por expediente: `GET …/concursos/{id}/calendario.ics` y `GET …/concursos/{id}/pliego.pdf`.
`POST /agentes/vigil/ejecuciones` → `202 {"id", "estado": "en_curso", …}` (409 si ya hay una en curso) y `GET /agentes/vigil/ejecuciones/{id}` para el progreso. **Solo en local** (la imagen de nube no lleva navegadores).

### Garum — `POST /agentes/garum/ciclos` (sin body)

Salida inmediata (202):
```json
{ "id_ciclo": "858586c7cf95", "estado": "en_marcha", "consultar": "/agentes/garum/ciclos/858586c7cf95" }
```

`GET /agentes/garum/ciclos/{id_ciclo}` cuando termina:
```json
{
  "id_ciclo": "858586c7cf95",
  "estado": "terminado",
  "lanzado_en": "2026-07-13T13:14:38",
  "terminado_en": "2026-07-13T13:14:39",
  "resultado": { "ok": true, "estado": "…", "resultados": ["…"] }
}
```
(409 `CICLO_EN_MARCHA` si se lanza otro sin terminar el anterior.)

### Backend de agentes — `GET :5004/api/eventos/{id_evento}/ponentes`

(Consumo interno de agentes — el front usa el backend Express :3000; se documenta por completitud.)
```json
{
  "ok": true,
  "data": [
    {
      "id": "019f5b21-f2e7-7ff6-9ffb-0fcdd4bd6e60",
      "nombre_ponente": "Carlos Barrabés",
      "email": "c.barrabes@innovacion.es",
      "empresa": "Barrabés",
      "cargo": "CEO",
      "ponencia": {
        "tipo_ponencia": "Keynote",
        "ponente_estado": "Activo",
        "nombre_hotel": "Hotel NH Europa",
        "horario_ida_transporte": "2026-09-09T06:30:00+00:00",
        "horario_ponencia": "2026-09-10T07:00:00+00:00"
      }
    }
  ]
}
```

### Errores (todos los servicios del gateway)

```json
{ "error": true, "codigo": "AGENTE_CAIDO", "mensaje": "El agente 'jano' no responde en …. ¿Está arrancado?" }
```
Códigos del gateway: `AGENTE_CAIDO` (502) · `RUTA_NO_ENCONTRADA` (404) · `CICLO_EN_MARCHA` (409).
Los agentes usan el mismo sobre; Jano/Vigil añaden `"detail"` por compatibilidad con sus webs de demo.
El backend :5004 responde `{"ok": false, "message": "Base de datos no disponible", …}` con **503** si Neon no está accesible.

## 7. Registro de cambios

| Versión | Fecha | Qué |
|---|---|---|
| v5 | 2026-07-13 | Inventario del repo Agentes_Eventos: gateway por proxy :5003 con stubs, Jano y Vigil documentados, backend :5004, Operis V2, mapa de puertos y .env común. Misma tarde: llegaron Lumen definitivo (conectado al gateway, stub retirado) y Garum gestor de correos (integrado por ciclos: `POST /agentes/garum/ciclos`). Confirmado que Vigil es el agente de alertas de la v4 → sin pendientes: mapa completo. Homogeneización posterior: `GET /health` uniforme en TODOS los servicios, errores siempre en JSON `{"error":true,codigo,mensaje}` (Jano/Vigil añaden `detail` por compatibilidad), Operis pasa a 127.0.0.1, Vigil devuelve 409 si ya hay ejecución en curso, backend responde 503 (no listas vacías) con la BBDD caída y usa pool de conexiones. Añadida §6: URLs de despliegue (local + Render) y ejemplos reales de entrada/salida por endpoint. |
| v4 | 2026-07-10 | Backend unificado de data :5003 en-proceso (Lumen+Operis). |
| v3 | 2026-07-09 | Primer inventario real (backend Express, Lumen :5001, Operis :5002 V1). |
# Nota actualizada 14/07/2026 - Operis

`POST /agentes/operis/autocompletar` acepta body flexible. `id_evento` ya no es obligatorio:
si llega, Operis intenta usar historico del evento; si no llega, procesa una extraccion
inicial sin historico, util para pantallas como Cliente o Espacio. El texto puede llegar en
`texto`, `texto_briefing`, `contenido`, `datos.texto_briefing` o `multipart/form-data` con un archivo llamado `archivo`, `file`, `documento` o `upload`. Formatos soportados: `.txt`, `.pdf` y `.docx`; los PDF escaneados sin capa de texto no se extraen porque no hay OCR.
