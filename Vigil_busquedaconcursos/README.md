# Vigil (versión plataforma) — agente de alertas de licitaciones para Mitumi

Vigil es un agente que, cada mañana, consulta la Plataforma de Contratación
Pública de Euskadi (KontratazioA) para las tres diputaciones forales
(Araba, Gipuzkoa y Bizkaia), filtra las licitaciones relevantes para Mitumi
(agencia de eventos) usando un modelo de lenguaje, y **publica el resultado
hacia la plataforma Mitumi BackStage** (sección "Concursos Públicos").

Esta versión **no envía email**: en su lugar genera un fichero JSON (más un
`.ics` por concurso) que la plataforma lee. Es la variante "solo plataforma".

## Funcionalidades

- **⏱️ Semáforo de urgencia**: cada concurso incluye los días hábiles que
  quedan y su nivel (alta/media/baja) (`urgency.py`).
- **🔄 Detector de modificaciones**: si un concurso ya avisado cambia (p. ej.
  amplían el plazo), se marca como modificación (`dedupe.py`).
- **🏷️ Etiquetado temático**: el LLM añade etiquetas (Institucional, Cultura,
  Gastronomía…) para repartir la revisión por áreas (`relevance.py`).
- **📅 Calendario `.ics`**: cada concurso lleva un archivo de calendario para
  que la plataforma ofrezca añadir el plazo a la agenda (`calendar_ics.py`).

## Registro histórico y API (integración con la plataforma)

Además del JSON diario, Vigil **acumula un histórico** de todos los concursos
encontrados —relevantes o no— en la tabla `concursos` del mismo `vigil.db`
(`history.py`). Cada concurso guarda sus datos, si fue relevante para Mitumi, su
urgencia y el plazo en formato ISO para poder ordenar y filtrar.

Para que la plataforma (que construye el equipo full-stack) lo consuma, hay una
pequeña **API HTTP** (`api.py`, Flask). Se arranca así:

```bash
waitress-serve --port=8000 vigil.api:app
```

Endpoints:

- `GET /concursos` — consulta el histórico con filtros de query string:
  `q` (texto en objeto/órgano), `diputacion`, `urgencia`, `en_plazo` (bool,
  "solo los que siguen en plazo"), `relevante` (bool), `limite`, `offset`.
- `GET /concursos/{id}/pliego.pdf` — **resumen del concurso en PDF** (lo que
  abre el botón "Ver pliego"): objeto, poder adjudicador, importe, plazo,
  urgencia, encaje con Mitumi y áreas temáticas, más el enlace al pliego oficial
  en KontratazioA (el documento vinculante, campo `enlace_pliego`). Se genera al
  vuelo desde el histórico (`pliego_pdf.py`); devuelve 404 si el expediente no
  existe.
- `GET /concursos/{id}/calendario.ics` — el plazo del concurso como evento de
  calendario, para añadirlo a la agenda.
- `POST /ejecuciones` — **lanza el agente en vivo** (scrape + LLM) en segundo
  plano; es el "botón de búsqueda al instante". Devuelve un `id` y `estado`.
- `GET /ejecuciones/{id}` — estado de esa ejecución (`en_curso` / `terminada` /
  `error`) y cuántos concursos nuevos añadió, para hacer *polling* desde la UI.
- `GET /health` — sonda de vida.

El seguimiento de ejecuciones se guarda en memoria (se reinicia con el servidor);
suficiente para un disparo puntual desde un botón.

## Integración técnica (para full-stack)

Esta sección describe, en detalle, **de dónde salen los datos, cómo se procesan
y cómo se entregan**, para que la plataforma los integre sin sorpresas.

### 1. De dónde se obtienen los datos (origen)

- **Fuente**: Plataforma de Contratación Pública de Euskadi (**KontratazioA**),
  vista de resultados en *formato ampliado* (HTML renderizado en servidor).
- **Cómo**: `sources.py` usa **Playwright (Chromium headless)** para navegar,
  seleccionar cada diputación en el autocompletado y paginar; el HTML resultante
  se parsea con **BeautifulSoup**. No hay API pública del portal: se lee la web.
- **Alcance**: las 3 diputaciones forales (Araba, Gipuzkoa, Bizkaia). Se miran
  las convocatorias publicadas en los últimos **7 días** (`LOOKBACK_DAYS`), con
  un filtro extra en cliente por "fecha de primera publicación".
- **Estructurado + criba**: cada convocatoria cruda pasa por `extractor.py`
  (**Groq LLM** + Pydantic) para limpiarla, y por `relevance.py` (**Groq LLM**)
  que decide si encaja con Mitumi, redacta el motivo y pone etiquetas.

### 2. Cómo se procesan (pipeline)

```
KontratazioA (web)
  → sources.py     (scrape Playwright + BeautifulSoup)   → dict crudo
  → dedupe.py      (nueva / modificación / ya vista, SQLite)
  → extractor.py   (Groq + Pydantic)                      → Convocatoria
  → relevance.py   (Groq: relevante?, motivo, etiquetas)  → VeredictoRelevancia
  → urgency.py     (nivel + días hábiles restantes)       → Urgencia
  → history.py     (guarda TODO el histórico en SQLite)
  → publisher.py   (escribe salida/concursos.json + .ics)
```

Todo lo encontrado (relevante o no) va al **histórico SQLite**; solo lo
**relevante** se vuelca al **`concursos.json`** del día.

### 3. Cómo se entregan (dos superficies)

Hay **dos formas** de consumir los datos, con **nombres de campo distintos**
(ojo, importante):

| Superficie | Qué es | Cuándo usarla | Campos |
| --- | --- | --- | --- |
| **API HTTP** (`api.py`) | Consulta en vivo del histórico + disparador | Si la plataforma pide datos bajo demanda | nombres "planos" de BD (`objeto`, `organo_convocante`, `urgencia_nivel`…) |
| **Fichero `concursos.json`** (`publisher.py`) | Vuelco batch diario de los relevantes | Si la plataforma ingiere un fichero cada mañana | nombres "amigables" (`titulo`, `organismo`, `urgencia.nivel`…) |

Ambas comparten `id_expediente` como clave. Elegid una y fijadla; recomendado
para una web reactiva: **la API**.

### 4. Referencia de la API HTTP

- **Base URL** (producción): la del despliegue (p. ej. `https://vigil.midominio/`).
- **CORS**: configurable con `VIGIL_CORS_ORIGINS` (coma-separado). Por defecto
  `*`; en producción poned el dominio de la plataforma.
- **Content-Type**: `application/json` salvo el `.pdf` (`application/pdf`) y el
  `.ics` (`text/calendar`).
- **Errores**: siempre en JSON, forma `{ "detail": "<mensaje>" }` (incluido el 404).

#### `GET /concursos`

Consulta el histórico. **Query params** (todos opcionales):

| Param | Tipo | Defecto | Efecto |
| --- | --- | --- | --- |
| `q` | string | — | busca el texto en `objeto` y `organo_convocante` (LIKE) |
| `diputacion` | `Araba`\|`Gipuzkoa`\|`Bizkaia` | — | filtra por territorio |
| `urgencia` | `alta`\|`media`\|`baja`\|`cerrado`\|`desconocida` | — | filtra por nivel |
| `en_plazo` | bool | `false` | solo los que tienen plazo y aún no ha vencido |
| `relevante` | bool | `false` | solo los marcados relevantes para Mitumi |
| `limite` | int (1–200) | `50` | tamaño de página |
| `offset` | int (≥0) | `0` | desplazamiento (paginación) |

Los bool aceptan `1/true/yes/on/si/sí`. Orden: por `plazo_iso` ascendente (los
más próximos primero; los sin plazo, al final).

**Respuesta `200`** — `{ "total": <int>, "concursos": [<Concurso>] }`, donde
`total` es el nº de esta página (no el total global). Cada `<Concurso>`:

| Campo | Tipo | Notas |
| --- | --- | --- |
| `id_expediente` | string | clave única |
| `objeto` | string | título/objeto del contrato |
| `organo_convocante` | string | organismo que convoca |
| `diputacion` | string | `Araba`/`Gipuzkoa`/`Bizkaia` |
| `importe` | string\|null | presupuesto sin IVA, tal cual (ej. `"45.000,00"`) |
| `plazo_presentacion` | string\|null | fecha texto `dd/mm/aaaa hh:mm:ss` |
| `plazo_iso` | string\|null | mismo plazo en ISO 8601 (ordenar/filtrar) |
| `fecha_publicacion` | string\|null | `dd/mm/aaaa` |
| `fecha_ultima_publicacion` | string\|null | `dd/mm/aaaa` (para modificaciones) |
| `relevante` | bool\|null | encaje con Mitumi |
| `motivo` | string\|null | explicación del encaje (texto del LLM) |
| `etiquetas` | string[] | áreas temáticas |
| `campos_no_verificables` | string[] | requisitos que el LLM no pudo confirmar |
| `urgencia_nivel` | string\|null | `alta`/`media`/`baja`/`cerrado`/`desconocida` |
| `urgencia_dias` | int\|null | días hábiles restantes |
| `enlace_pliego` | string | URL del anuncio oficial en KontratazioA |
| `visto_por_primera_vez` | string | timestamp SQLite |
| `ultima_actualizacion` | string | timestamp SQLite |

#### `GET /concursos/{id}/pliego.pdf`

Devuelve el **resumen del concurso en PDF** (`application/pdf`, `inline`). `200`
con el binario, o `404` si el `id` no existe. Es lo que abre "Ver pliego". Para
enlazar al pliego **oficial**, usad el campo `enlace_pliego`.

#### `GET /concursos/{id}/calendario.ics`

Devuelve el plazo como evento iCalendar (`text/calendar`, `attachment`). `200`, o
`404` si el expediente no existe o no tiene un plazo con fecha válida.

#### `POST /ejecuciones`

Lanza el agente en vivo (scrape + LLM) en segundo plano; **sin body**. Responde
`202` con el objeto de ejecución:

```json
{ "id": "hex", "estado": "en_curso", "iniciado_en": "ISO",
  "terminado_en": null, "nuevos": null, "error": null }
```

En producción tarda **minutos** (Playwright + Groq); en demo ~1 s. Guardad el
`id` y haced *polling*.

#### `GET /ejecuciones/{id}`

Estado de una ejecución. `200` con el mismo objeto de arriba (cuando termina,
`estado` = `terminada` y `nuevos` = nº de concursos añadidos; o `estado` =
`error` con `error`), o `404` si el `id` no existe. El registro vive **en
memoria**: se pierde al reiniciar el servidor.

#### `GET /health`

`200` → `{ "estado": "ok", "hora": "ISO" }`.

### 5. Esquema del fichero `concursos.json`

Lo escribe `publisher.py` en `salida/` en cada ejecución (siempre, aunque el día
no haya novedades → lista vacía). Estructura:

```json
{
  "generado_en": "2026-07-13T10:09:33.359628",
  "fuente": "KontratazioA — Diputaciones Forales (Araba, Gipuzkoa, Bizkaia)",
  "total": 4,
  "concursos": [ { /* … */ } ]
}
```

Cada concurso usa nombres **distintos a los de la API**:

| Campo (JSON) | Equivale en la API a | Tipo |
| --- | --- | --- |
| `id_expediente` | `id_expediente` | string |
| `titulo` | `objeto` | string |
| `organismo` | `organo_convocante` | string |
| `diputacion` | `diputacion` | string |
| `fecha_publicacion` | `fecha_publicacion` | string\|null |
| `fecha_ultima_publicacion` | `fecha_ultima_publicacion` | string\|null |
| `plazo_presentacion` | `plazo_presentacion` | string\|null |
| `plazo_iso` | `plazo_iso` | string\|null |
| `importe` | `importe` | string\|null |
| `enlace_pliego` | `enlace_pliego` | string |
| `urgencia` | `{urgencia_nivel, urgencia_dias}` | objeto `{nivel, dias_habiles_restantes, etiqueta}` |
| `etiquetas` | `etiquetas` | string[] |
| `es_modificacion` | (no está en la API) | bool |
| `motivo` | `motivo` | string |
| `campos_no_verificables` | `campos_no_verificables` | string[] |
| `archivo_ics` | (no está en la API) | string\|null, ruta relativa (`ics/<archivo>.ics`) |

Además, `salida/ics/*.ics` contiene un calendario por concurso.

### 6. Variables de entorno

| Variable | Para qué | Defecto |
| --- | --- | --- |
| `GROQ_API_KEY` | clave del LLM (Groq). **Obligatoria en real** | `""` |
| `GROQ_MODEL` | modelo de Groq | `llama-3.3-70b-versatile` |
| `VIGIL_OUTPUT_DIR` | carpeta de salida del JSON/`.ics` | `./salida` |
| `VIGIL_DB_PATH` | ruta del SQLite (histórico + dedupe) | `vigil/vigil.db` |
| `VIGIL_CORS_ORIGINS` | orígenes CORS permitidos (coma-separado) | `*` |
| `VIGIL_DEMO` | si `=1`, modo demo (sin web ni LLM) | (sin poner) |
| `CRON_HORA` / `CRON_TIMEZONE` | hora/zona de la ejecución diaria | `07:00` / `Europe/Madrid` |

### 7. Formatos de fecha (importante)

Los campos `*_presentacion` y `fecha_*` vienen **tal cual del portal** en texto
español (`dd/mm/aaaa` o `dd/mm/aaaa hh:mm:ss`). Para ordenar o comparar en la
plataforma, usad **`plazo_iso`** (ISO 8601). Los timestamps `generado_en`,
`visto_por_primera_vez` y `ultima_actualizacion` ya son ISO.

## Modo demo (enseñar el agente sin web ni Groq)

Para mostrar el agente funcionando —p. ej. al equipo full-stack— sin depender de
`GROQ_API_KEY`, de Playwright ni de que la web tenga novedades ese día, se activa
el **modo demo** con la variable `VIGIL_DEMO=1`. Usa las convocatorias de ejemplo
de `vigil/examples/` y salta el LLM (`demo.py`), pero recorre **el mismo pipeline**
(dedupe → estructurar → relevancia → urgencia → histórico → JSON + API).

La forma más simple de enseñarlo es con un único comando, que carga los datos de
ejemplo (si hacen falta) y levanta la web + la API:

```powershell
python serve_demo.py
```

Luego abre **`http://127.0.0.1:8000/`** → una web con los concursos en tarjetas,
buscador, filtros (diputación, urgencia, "solo en plazo", "solo relevantes") y el
botón **"Actualizar ahora"**, que lanza el agente en vivo (en demo, ~1 s). Esta web
sirve de referencia visual para el equipo full-stack; la propia API queda en la
misma dirección (ver los endpoints en "Integración técnica").

Usa una base de datos y una salida de demo aparte (`vigil_demo.db`, `salida_demo/`),
así que **no toca los datos reales**. Para el agente **real**, quita `VIGIL_DEMO` y
pon `GROQ_API_KEY`.

## El contrato de salida (lo que lee la plataforma)

Al ejecutarse, el agente escribe en la carpeta `salida/`:

- `salida/concursos.json` → lista de concursos relevantes del día, cada uno
  con título, organismo, fechas, importe, urgencia, etiquetas, si es una
  modificación, el motivo de encaje y la ruta a su `.ics`.
- `salida/ics/*.ics` → un archivo de calendario por concurso.

La carpeta se puede cambiar con la variable de entorno `VIGIL_OUTPUT_DIR`.
Cuando la plataforma defina su mecanismo (API REST o base de datos), solo hay
que adaptar `publisher.py` para enviar ese mismo JSON por el nuevo canal.

## Cómo funciona (flujo)

1. **sources.py** → lee la web de KontratazioA con Playwright y saca las convocatorias de las 3 diputaciones.
2. **dedupe.py** → detecta si cada convocatoria es nueva, una modificación o ya vista (SQLite).
3. **extractor.py** → convierte cada convocatoria en datos limpios (Groq + Pydantic).
4. **relevance.py** → decide si encaja con el perfil de Mitumi, explica por qué y pone etiquetas.
5. **urgency.py** → calcula el semáforo de urgencia según el plazo.
6. **calendar_ics.py** → genera el archivo de calendario de cada concurso.
7. **history.py** → guarda cada concurso encontrado (relevante o no) en el histórico SQLite.
8. **publisher.py** → escribe el JSON y los `.ics` en `salida/` para la plataforma.
9. **main.py** → orquesta todo el proceso de principio a fin.
10. **api.py** → expone el histórico y el disparador de ejecución a la plataforma (Flask).
11. **pliego_pdf.py** → arma, bajo demanda, el resumen del concurso en PDF que sirve la API en "Ver pliego".

## Instalación

```bash
# creo un entorno virtual de Python
python -m venv .venv
# lo activo (Windows)
.venv\Scripts\activate
# instalo las librerías
pip install -r requirements.txt
# descargo el navegador que usa Playwright
playwright install chromium
```

## Cómo ejecutarlo a mano

Necesita esta variable de entorno:

- `GROQ_API_KEY` — clave de la API de Groq

Y de forma opcional:

- `VIGIL_OUTPUT_DIR` — carpeta donde escribir la salida (por defecto `salida/`)

Con eso puesto:

```bash
python -m vigil.main
```

Al terminar, revisa `salida/concursos.json` y `salida/ics/`.

## Tests

```bash
pytest vigil/tests
```

## Nota sobre la automatización diaria

El fichero `.github/workflows/vigil.yml` define la ejecución automática cada
mañana con GitHub Actions. **Solo funciona si este proyecto está en la raíz
de su propio repositorio** (GitHub ignora los workflows que están dentro de
subcarpetas). En el repositorio definitivo del proyecto habrá que colocarlo
en la raíz y configurar las credenciales como *secrets* del repo.
