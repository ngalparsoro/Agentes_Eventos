# agente_operis — Asistente de recordatorio de eventos (extracción + actualización de briefings)

**Conexión con el orquestador y la base de datos:** cómo invoca el backend a
`ejecutar_agente(payload)` (desde `src/agente.py`) **sigue sin decidirse** (ver el recuadro de
abajo y la sección 8.3 — no hay orquestador). Con la base de datos, la conexión **sí está
resuelta**: `agente_operis` lee la BD real (Neon Postgres) en modo **solo lectura**, usando el
`kit_conexion_agentes_Nora` oficial del proyecto (mismo patrón que Lumen en producción) — nunca
escribe en ella. Los bloques `evento`, `cliente` y `ponentes` reutilizan los nombres de columna
reales de `Datos_alimentación_bbdd_Leire_Eduardo/*.csv`; el bloque `nota_bene` (ver sección 3)
es un resumen calculado por el LLM, no una copia campo a campo de esas columnas — quien lo
consuma tiene que interpretarlo, no volcarlo directo con un `INSERT`. Fechas en `DD/MM/AAAA`.

> ### 🔴 Lo que sigue sin resolver (10/07/2026)
> 1. **Pedir a Nora la cadena de conexión `agente_readonly`** y ponerla en `.env` como
>    `DATABASE_URL`. Sin esto, la conexión a BD está construida y probada en el camino "sin BD
>    disponible", pero no se ha verificado todavía contra la base de datos real. Verificación:
>    `python kit_conexion_agentes_Nora/test_conexion.py .env` (ruta relativa a `DESAFIO_MITUMI/`)
>    debe dar todo `PASS`.
> 2. **Cómo invoca el backend al agente.** No hay orquestador, y no está decidido si el backend
>    llama a `ejecutar_agente(payload)` por API REST, importándolo como librería Python
>    directamente, o de otra forma. La conexión a BD resuelve qué sabe el agente sobre un
>    evento; no resuelve esta pregunta.

---

## 0. Qué es este agente, en una frase

Lee un briefing de evento (texto, `.txt`/`.pdf`/`.docx`) y devuelve una propuesta
estructurada en 4 bloques — no es solo un extractor puntual: también sabe **fusionar** un
briefing nuevo con el histórico de versiones de un evento ya existente, y actualizar
**solo** los bloques que el usuario indique, protegiendo el resto. Sigue siendo un agente
de propuesta, nunca de escritura: `requiere_validacion_humana` SIEMPRE `true`.

---

## 1. Cambio de arquitectura (10/07/2026): de 6 bloques a 3 + Nota Bene

| Antes | Ahora |
|---|---|
| Evento | Evento |
| Cliente | Cliente (+ `personas_contacto`, `cliente_existente`) |
| Espacio | **Eliminado** — resumido dentro de `nota_bene` |
| Sala | **Eliminado** — resumido dentro de `nota_bene` |
| Presupuesto | **Eliminado** — resumido dentro de `nota_bene.presupuesto_servicios` |
| Ponentes | Ponentes (+ `nota_ponente`) |
| — | **Nuevo: Nota Bene** — resumen ejecutivo + presupuesto/servicios + cajón de sastre |

**Motor:** el motor de reglas (regex + etiquetas, gratis) se **eliminó por completo**. El
único motor disponible es `llm` (Groq). Esto tiene una consecuencia práctica importante:
el agente ya **no funciona sin `GROQ_API_KEY`**, y ejecutarlo (incluido `main.py --demo`)
consume tokens reales — ver `docs/ESTIMACION_TOKENS.md` para el coste medido.

**`id_evento` ahora es opcional en la capa HTTP.** Si llega, Operis lo usa para cargar
histórico del evento y fusionar datos. Si no llega, procesa una extracción inicial sin
histórico, útil para pantallas independientes como Cliente o Espacio. El agente sigue
sin escribir en BD: siempre devuelve una propuesta para validación humana.

---

## 2. Principio arquitectónico

```bash
cd agente_operis_llm
python main.py --demo
```

```text
Backend / quien invoque el agente
        ↓
ejecutar_agente(payload)        [src/agente.py]
        ↓                              ↕ (solo lectura)
agente_operis (extracción + fusión con histórico)   ←→   BD real (Neon), vía
        ↓                                                 kit_conexion_agentes_Nora
Respuesta estructurada (propuesta, nunca escritura directa)
        ↓
[PERSONA revisa y confirma] → Backend → BD (escritura, siempre por el backend)
```

> **Conexión con la BD real: ✅ resuelta el 10/07/2026** (ver sección 8). El agente ya
> lee la BD real (Neon Postgres) en modo solo lectura, usando el `kit_conexion_agentes_Nora`
> del proyecto (`DESAFIO_MITUMI/kit_conexion_agentes_Nora/`) — el mismo patrón que usa
> Lumen en producción. Con esto, `id_evento` se verifica de verdad contra la BD, y el
> modo actualización ya no depende de que un backend externo guarde y pase el histórico:
> si la BD está disponible, el agente autocarga el estado actual del evento. **Lo que
> sigue sin resolver:** cómo invoca el backend a `ejecutar_agente(payload)` en sí (¿API
> REST?, ¿librería importada directamente?) — eso no lo resuelve la conexión a BD, sigue
> siendo una decisión pendiente del equipo de backend.

---

## 3. El bloque Nota Bene

Es el bloque más importante del nuevo esquema: un resumen "de un vistazo" del evento, más
el desglose de presupuesto/servicios, más cualquier información que no encaje en los otros
tres bloques. Tiene tres partes:

### 3.1 Cabecera (resumen ejecutivo)
`nombre_evento`, `estado_evento`, `fecha_celebracion` (rango, ej. `"20-22/09/2027"`),
`cliente_principal`, `persona_contacto`, `presupuesto_total_estimado`,
`ultima_actualizacion` (ISO, la rellena el código, no el LLM).

### 3.2 Presupuesto y servicios (4 sub-bloques fijos)
`ubicacion`, `catering`, `audiovisuales`, `otros` — cada uno con `descripcion`,
`precio_estimado`, `nota`, `estado`. El LLM clasifica cada servicio mencionado en el
sub-bloque que corresponda; si el texto solo da un presupuesto total (lo habitual), los
`precio_estimado` quedan vacíos y el total va en `cabecera.presupuesto_total_estimado`.

### 3.3 Información adicional (cajón de sastre)
`notas_generales`, `requerimientos_especiales`, `riesgos_detectados`,
`acciones_pendientes` (lista), `dependencias` (lista), `historico_actualizaciones`
(lista de versiones, la rellena el código).

---

## 4. Actualización parcial por bloques (`bloques_a_actualizar`)

**El problema que resuelve:** si subes un documento que solo habla de presupuesto, y el
agente reprocesara todo desde cero, devolvería Evento y Cliente vacíos (no están en ese
texto) — un backend que guardase esa respuesta perdería información ya validada.

**La solución:** el payload acepta `datos.bloques_a_actualizar` (lista opcional).

```python
payload = {
    "id_evento": "evento_123",
    "datos": {
        "texto_briefing": "Nuevo presupuesto...",
        "bloques_a_actualizar": ["nota_bene"]   # opcional
    },
    "contexto": {
        "historial_anterior": {...}             # opcional, ver sección 5
    },
    ...
}
```

| `bloques_a_actualizar` | Bloques actualizados (por el LLM) | Bloques protegidos (por el código, no por el LLM) |
|---|---|---|
| `["nota_bene"]` | Solo Nota Bene | Evento, Cliente, Ponentes |
| `["evento", "cliente"]` | Evento y Cliente | Ponentes, Nota Bene |
| No presente / `null` | Todos | Ninguno |

Valores válidos: `evento`, `cliente`, `ponentes`, `nota_bene` (`src/validaciones.py::BLOQUES_VALIDOS`).
**Quién decide:** el usuario, normalmente a través de checkboxes en la UI (ver `app.py`,
sidebar "Bloques a actualizar").

**Cómo se protege un bloque (12/07/2026, rediseñado):** antes, la protección se le pedía
al LLM en el propio prompt ("copia este bloque tal cual") — caro en tokens (había que
mandarle el bloque completo igualmente) y frágil (un LLM no siempre copia un JSON grande
sin alterarlo). Ahora `src/nucleo.py::_proteger_bloques_no_actualizados` sobrescribe
directamente, en Python, los bloques que no estén en `bloques_a_actualizar` con el último
estado conocido — el LLM ni siquiera necesita reproducirlos bien. Verificado end-to-end
con Groq real: actualización parcial (solo `nota_bene`) y fusión con histórico en varias
rondas seguidas sobre el mismo evento.

---

## 5. Histórico y modo actualización

- **Dos formas de obtener el histórico, con esta prioridad:**
  1. **Explícito en el payload** (`contexto.historial_anterior`) — si quien invoca al
     agente ya lo tiene (p. ej. un backend con su propio almacenamiento), tiene prioridad
     absoluta y el agente no toca la BD para nada.
  2. **Autocargado desde la BD real** (`src/lectura_bd.py::construir_historial_desde_bd`)
     — si no se pasó explícito y hay `DATABASE_URL` configurada, `src/nucleo.py` lee el
     estado ACTUAL del evento en la BD (Neon, vía `integrations/bd_backend.py`) y lo usa
     como histórico de una única "versión: el presente". Si la BD no está disponible, o el
     evento no existe todavía ahí, se procesa como una extracción inicial sin histórico
     (nunca falla por esto).
- **Estructura del histórico** (`src/schemas.py::crear_estructura_vacia_historico`), igual
  venga de donde venga:
  ```json
  {
      "evento_id": "evt_001",
      "versiones": [
          {
              "fecha": "2026-07-09T10:00:00",
              "archivo": "briefing_v1.txt",
              "resumen": "Propuesta inicial",
              "datos": { "...": "JSON completo de datos_detectados de esa versión..." }
          }
      ],
      "ultima_actualizacion": "2026-07-10T10:00:00"
  }
  ```
- **Solo se manda al LLM la ÚLTIMA versión (12/07/2026, rediseñado):**
  `src/schemas.py::extraer_ultimo_estado` se queda solo con `versiones[-1]["datos"]` antes
  de construir el prompt — nunca la lista completa. Antes, `app.py` (histórico local de
  sesión) iba **acumulando** una versión más en `versiones` en cada ronda de prueba sobre
  el mismo `id_evento`, y el prompt mandaba esa lista entera al LLM: tras varias rondas,
  esto hacía saltar el límite de **tokens por minuto** del free tier de Groq (8.000 TPM,
  distinto del límite de 200.000 tokens/día — ver `docs/ESTIMACION_TOKENS.md`), con un
  error `413 rate_limit_exceeded`. Con el histórico autocargado de la BD real
  (`construir_historial_desde_bd`) esto no pasaba, porque esa función ya construye una
  única "versión: el presente" cada vez — pero limitarse a la última versión también en el
  histórico local de sesión evita el problema por completo y hace que ambos caminos se
  comporten igual.
- **Cómo fusiona el LLM:** recibe la última versión conocida dentro del prompt de sistema
  (ver `src/llm.py::construir_prompt_sistema`) con instrucciones de mantener lo que ya
  existía y solo actualizar lo que el nuevo texto modifique. Los cambios de presupuesto se
  destacan así: `"3200€ (anterior: 2500€)"`. El ejemplo JSON completo del prompt de sistema
  (`prompts/prompt_sistema.md`, marcado con `<!-- EJEMPLO_SOLO_SIN_HISTORIAL -->`) se omite
  automáticamente cuando hay histórico, porque en ese caso la última versión ya hace de
  ejemplo (y es un ejemplo mejor: es del mismo evento) — otro ahorro de tokens para el
  mismo límite TPM.
- **Histórico de cambios gestionado por código, no por el LLM (12/07/2026):**
  `nota_bene.informacion_adicional.historico_actualizaciones` ya no depende de que el LLM
  reproduzca fielmente las entradas anteriores en su respuesta — `src/nucleo.py` lee la
  lista vieja directamente de la última versión conocida y le añade la entrada nueva. Esto
  también corrigió un bug: el número de `version` de cada entrada se contaba antes por
  `len(historial_anterior["versiones"])`, que con el histórico autocargado de la BD real
  siempre vale 1 (una única "versión: el presente"), así que se quedaba clavado en
  `version: 2` para siempre; ahora se cuenta `len(historico_actualizaciones)`.
- **`contexto.modo_actualizacion`:** `"fusionar"` (por defecto) o `"sobrescribir"`.
- `app.py` sigue incluyendo un histórico **local, solo de sesión** (por `id_evento`), útil
  para probar el flujo sin conexión a la BD real; si la BD SÍ está conectada, tiene
  prioridad el histórico local si lo activas explícitamente, si no, se usa el de la BD
  automáticamente.
- **Traza de transparencia:** cuando el histórico se autocarga de la BD (no viene explícito
  en el payload), `trazas.fuentes_consultadas` incluye `"bd:eventos(historial_anterior)"`.

**Esquema mostrado al LLM vs. esquema interno (12/07/2026, bug corregido):**
`src/llm.py::ESQUEMA_SALIDA` guarda listas planas de nombres de campo (p. ej.
`"evento": ["nombre_evento", "ciudad", ...]`), porque `_fusionar_sobre_plantilla` las usa
para saber qué claves son válidas en cada bloque. Mandarle esa misma forma al LLM como "así
debe verse tu respuesta" es ambigua: en una prueba real, el modelo interpretó que el valor
de `"evento"` debía ser ese array, y devolvió `evento`/`cliente` como listas de valores
posicionales en vez de objetos — JSON inválido, error `400 json_validate_failed`. Se separó
en dos: `ESQUEMA_SALIDA` sigue igual para la fusión interna, y una función nueva,
`src/llm.py::_esquema_para_prompt`, construye la forma real (objetos anidados, listas con
un elemento de ejemplo para `ponentes`/`personas_contacto`) que es lo único que ahora se le
enseña al LLM.

---

## 6. Contrato de entrada

```json
{
  "id_evento": "evt_001",
  "id_registro": null,
  "tipo_peticion": "extraer_briefing",
  "origen": "manual",
  "usuario_solicitante": "cli",
  "rol_usuario": "organizador",
  "datos": {
    "texto_briefing": "...",
    "groq_api_key": null,
    "bloques_a_actualizar": null
  },
  "contexto": {
    "historial_anterior": null,
    "modo_actualizacion": "fusionar"
  },
  "modo": "propuesta"
}
```

| Campo | Antes | Ahora |
|---|---|---|
| `id_evento` | Opcional (podía ser `null`) | **Obligatorio**, no vacío |
| `datos.motor` | `"reglas"` o `"llm"` | **Eliminado** — solo existe `llm` |
| `datos.groq_api_key` | No existía | Opcional; si no se indica, usa `GROQ_API_KEY` de `.env` |
| `datos.bloques_a_actualizar` | No existía | Opcional, ver sección 4 |
| `contexto.historial_anterior` | No existía | Opcional, ver sección 5 |
| `contexto.modo_actualizacion` | No existía | Opcional: `"fusionar"` o `"sobrescribir"` |

Validado por `src/validaciones.py::validar_entrada`. Ver `inputs/payload_demo.json` para
el payload real que usa `main.py --demo`.

---

## 7. Contrato de salida

```json
{
  "ok": true,
  "agente": "agente_operis",
  "tipo_peticion": "extraer_briefing",
  "resumen": "✅ Evento completo. Información en 3 bloques. Requiere validación humana.",
  "datos_detectados": {
    "evento": { "...": "..." },
    "cliente": { "...": "...", "personas_contacto": [ "..." ] },
    "ponentes": [ "..." ],
    "nota_bene": { "cabecera": {}, "presupuesto_servicios": {}, "informacion_adicional": {} }
  },
  "acciones_propuestas": [],
  "bloqueos_detectados": [],
  "borradores_generados": [],
  "requiere_validacion_humana": true,
  "nivel_riesgo": "bajo",
  "errores": [],
  "trazas": { "fuentes_consultadas": ["motor:llm"], "timestamp": "...", "modo": "propuesta" },
  "_validacion": { "porcentaje_completado": 100, "campos_pendientes": [] },
  "_aviso_agente": { "mensaje": "..." }
}
```

`requiere_validacion_humana` es **siempre `true`** y `nivel_riesgo` es **siempre `"bajo"`**
— el agente nunca escribe ni envía nada. `_validacion`/`_aviso_agente` aparecen tanto
dentro de `datos_detectados` (donde los calcula `src/schemas.py::generar_aviso_y_validacion`)
como replicados en el nivel superior de la respuesta, por conveniencia para quien consuma
el contrato — ver `src/schemas.py::construir_salida_base`.

`_validacion.porcentaje_completado` se calcula **solo** sobre el bloque Evento
(`CAMPOS_OBLIGATORIOS_EVENTO`): `nombre_evento`, `ciudad`, `fecha_inicio`, `fecha_fin`,
`numero_personas`, `tipo_evento`. Nota Bene no cuenta para este porcentaje.

---

## 8. Integración con el backend y la BD real

### 8.1 Conexión a la BD real (Neon Postgres) — ✅ resuelta el 10/07/2026

Existe un kit de conexión oficial del proyecto, `kit_conexion_agentes_Nora`
(`DESAFIO_MITUMI/kit_conexion_agentes_Nora/`), ya usado en producción por Lumen
(`Agente_04_Copilot_Raul/integrations/db_backend.py`). `agente_operis` ahora lo usa
también:

- `integrations/bd_backend.py` — copia adaptada de la plantilla del kit: acceso de
  **solo lectura**, lista blanca de 8 tablas (`clientes`, `eventos`, `presupuestos`,
  `ponentes`, `ponencias`, `estados`, `salas`, `espacios`), `usuarios` fuera de alcance,
  conexión marcada `read_only` a nivel de Postgres (no solo por convención en el código).
- `src/lectura_bd.py` — traduce el esquema real de la BD al esquema de salida de
  `agente_operis` (evento/cliente/ponentes/nota_bene). Expone `evento_existe(id_evento)`
  y `construir_historial_desde_bd(id_evento)`.
- **`id_evento` se verifica de verdad** (`src/validaciones.py`): si hay BD conectada y el
  id no existe, la petición se rechaza — ya no basta con que la cadena no esté vacía.
- **El histórico se autocarga** (`src/nucleo.py`): si no llega `contexto.historial_anterior`
  explícito en el payload, y hay BD conectada, se usa el estado actual del evento en la BD
  como base de la fusión — sin depender de que un backend externo lo guarde y lo pase.
- **Import perezoso en todo el módulo:** sin `DATABASE_URL` configurada, o sin el paquete
  `psycopg` instalado, el agente funciona exactamente igual que antes (extracción sin
  histórico, `id_evento` solo se valida como no-vacío) — nunca rompe por falta de BD.
- **Paso manual pendiente, no técnico:** hace falta pedirle a Nora la cadena de conexión
  del rol `agente_readonly` (nunca la de `neondb_owner`) y ponerla en `.env` como
  `DATABASE_URL`. Verificación: `python kit_conexion_agentes_Nora/test_conexion.py .env`
  (ruta relativa a `DESAFIO_MITUMI/`) debe dar todo `PASS`.

**⚠️ Limitación real de la BD, no de este código:** según el esquema documentado
(`Agente_04_Copilot_Raul/data/rag/documentos/esquema_bd.md`), cada evento enlaza como
mucho con **una** ponencia/ponente (`eventos.id_ponencia`, relación 1:1, no la tabla
`evento_ponente` N:N que asumían versiones anteriores de este documento). El bloque
`ponentes` de `agente_operis` sigue siendo una lista en su esquema de salida (para no
perder información si un briefing menciona varios), pero al leer o fusionar con la BD
real, esa lista tendrá como mucho un elemento — es una limitación de la BD, reportada por
el equipo de Lumen, no algo que este agente pueda resolver por su cuenta.

### 8.2 Cómo invoca el backend a `ejecutar_agente(payload)` — sigue sin definir

No hay orquestador ("no va a haber orquestador"), y **no está decidido** si el backend
llama al agente por API REST, importándolo como librería Python directamente, o de otra
forma. La conexión a la BD real (sección 8.1) resuelve la parte de "cómo se entera el
agente de lo que ya existe", pero no esta otra pregunta — sigue siendo una decisión
pendiente del equipo de backend, no algo que se pueda inferir del kit de conexión.

### 8.3 Otros pendientes

| Aspecto | Estado |
|---|---|
| `data/conocimiento/*.py` | 🟡 **Huérfano**: ciudades/tipos de evento/estados que usaba el motor de reglas, ahora eliminado. No los borré (son datos verificados contra la BD real, podrían reutilizarse para validar la salida del LLM), pero hoy no los importa nada. |
| Vistas SQL (`vistas_agentes.sql` del kit) | 🟡 No aplicadas todavía en la BD real (las aplica el equipo de BBDD cuando decida) — `src/lectura_bd.py` usa las tablas base con sus propios `JOIN` en Python, no depende de que existan. |

---

## 9. Estructura del agente

```text
agente_operis_llm/
│
├── README.md                  ← este archivo
├── app.py                     ← interfaz de prueba en Streamlit (subida de archivo/texto,
│                                  id_evento, bloques a actualizar, histórico local por
│                                  evento, panel de Nota Bene con estilo propio)
├── servidor.py                 ← API HTTP fina (Flask) para el frontend React: POST
│                                  /autocompletar sobre ejecutar_agente(payload); requiere
│                                  requirements_servidor.txt aparte (flask, flask-cors)
├── main.py                    ← consola: --demo o ruta a un archivo (motor único: llm)
├── requirements.txt            ← groq, streamlit, pypdf, python-docx (obligatorias) +
│                                  psycopg[binary] (opcional, conexión a BD real)
├── requirements_servidor.txt   ← solo para servidor.py: flask, flask-cors
├── .env.example / .env         ← GROQ_API_KEY (obligatoria), GROQ_MODEL, DATABASE_URL (opcional)
├── .gitignore                  ← .env, __pycache__/, *.pyc
│
├── config/
│   ├── settings.py             ← carga .env; validar_configuracion() comprueba GROQ_API_KEY
│   └── permisos.py             ← ALLOW_DB_WRITE=False (y el resto, no configurable al alza);
│                                  TABLAS_PERMITIDAS/TABLAS_EXCLUIDAS para la BD real
│
├── prompts/
│   └── prompt_sistema.md       ← rol, regla de "no inventar", esquema de 4 bloques,
│                                  instrucciones de actualización (histórico + bloques
│                                  parciales, insertadas en runtime), ejemplo completo
│                                  marcado con <!-- EJEMPLO_SOLO_SIN_HISTORIAL --> (solo
│                                  se envía en extracciones en frío, ver sección 5)
│
├── integrations/
│   └── bd_backend.py            ← acceso de SOLO LECTURA a la BD real (Neon), copiado y
│                                    adaptado de kit_conexion_agentes_Nora (DESAFIO_MITUMI/)
│
├── src/
│   ├── agente.py                ← punto de entrada OBLIGATORIO: ejecutar_agente(payload)
│   ├── nucleo.py                ← valida entrada, llama a src/llm.py, protege en Python los
│   │                                bloques no incluidos en bloques_a_actualizar y gestiona
│   │                                el histórico de cambios (explícito o autocargado de la
│   │                                BD, ver sección 5 y 8)
│   ├── schemas.py               ← esquema de 4 bloques + historial + validación/avisos +
│   │                                extraer_ultimo_estado (última versión del histórico)
│   ├── validaciones.py          ← contrato de entrada (id_evento opcional; se verifica si llega
│   │                                contra la BD real si está disponible, bloques válidos,
│   │                                motor único "llm"...)
│   ├── llm.py                   ← único motor: Groq, prompt + histórico (solo última
│   │                                versión) + esquema mostrado al LLM (_esquema_para_prompt,
│   │                                ver sección 5) -- la protección de bloques ya no vive
│   │                                aquí, se hace en nucleo.py
│   ├── lectura_bd.py             ← traduce el esquema real de la BD al esquema de salida
│   │                                de Operis; evento_existe(), construir_historial_desde_bd()
│   ├── lectura_archivos.py      ← leer_archivo() -- lectura .txt/.pdf/.docx (antes vivía
│   │                                en src/funciones.py, junto al motor de reglas eliminado)
│   └── rag.py                   ← stub, no aplica (documentación/BD externas -- el
│                                    histórico si acaso lo lee src/lectura_bd.py, no esto)
│
├── inputs/
│   └── payload_demo.json       ← payload de ejemplo (con id_evento) que usa main.py --demo
│
├── data/
│   ├── conocimiento/            ← HUÉRFANO desde que se eliminó el motor de reglas (ver
│   │                                sección 8) -- no lo importa ningún módulo activo
│   └── ejemplos/
│       ├── briefing_prueba.txt     ← caso simple
│       └── briefing_complejo.txt   ← caso complejo (varios ponentes y servicios)
│
├── docs/
│   ├── Agente_OPERIS_implementacion.md  ← ficha de documentación
│   ├── estimacion_tokens.py             ← MIDE tokens reales llamando a Groq (ya no estima)
│   └── ESTIMACION_TOKENS.md             ← informe de coste/tokens medido
│
└── outputs/
    └── respuestas_json/
        └── salida_demo.json    ← guarda main.py --demo (llamada real a Groq cada vez)
```

---

## 10. Archivo `.env`

```env
GROQ_API_KEY=       # obligatoria -- sin ella, el agente no funciona en ningún modo
GROQ_MODEL=openai/gpt-oss-120b

# Opcional -- sin esto, el agente funciona igual, solo que no autocarga
# histórico de la BD ni verifica id_evento contra ella (ver sección 8.1):
DATABASE_URL=       # cadena del rol agente_readonly -- pídesela a Nora, NUNCA neondb_owner
```

Ya no existe `OPERIS_MOTOR` (no hay nada que elegir: el motor siempre es `llm`).
`config/settings.py::validar_configuracion()` comprueba que `GROQ_API_KEY` esté presente
antes de intentar nada. `.gitignore` incluye `.env`, `__pycache__/`, `*.pyc`.

Permisos, fijados en código en `config/permisos.py` (no configurables al alza desde `.env`):

```python
ALLOW_DB_WRITE = False
ALLOW_EXTERNAL_SEND = False
ALLOW_CREATE_EVENT = False
ALLOW_AUTO_APPROVAL = False
```

---

## 11. Flujo interno implementado

```text
1. Quien llame (main.py, app.py, servidor.py, o el futuro backend) construye el payload y
   llama a ejecutar_agente(payload) (src/agente.py).
2. src/validaciones.py valida el contrato: id_evento opcional, motor debe ser "llm" si
   se indica, bloques_a_actualizar debe usar valores de BLOQUES_VALIDOS, etc.
3. src/nucleo.py extrae texto_briefing, bloques_a_actualizar, historial_anterior y
   modo_actualizacion del payload, y llama a src/llm.py::extraer_briefing_llm.
4. src/llm.py construye el prompt de sistema (prompts/prompt_sistema.md + esquema real
   para el LLM +, si hay histórico, solo su última versión + instrucciones de fusión) y
   llama a Groq con temperature=0 y salida JSON forzada.
5. La respuesta del LLM se fusiona sobre la plantilla vacía completa
   (src/llm.py::_fusionar_sobre_plantilla) -- un campo omitido por el LLM se queda en
   "" o [], nunca rompe el pipeline.
6. src/nucleo.py::_proteger_bloques_no_actualizados sobrescribe, en Python, los bloques
   que NO estén en bloques_a_actualizar con el último estado conocido -- el LLM no es
   responsable de reproducirlos.
7. src/schemas.py::generar_aviso_y_validacion calcula el % de campos obligatorios del
   bloque Evento y el mensaje de aviso.
8. Si había historial_anterior, src/nucleo.py construye
   nota_bene.informacion_adicional.historico_actualizaciones a partir del histórico viejo
   (no de lo que devuelva el LLM) y le añade la entrada nueva; actualiza también
   nota_bene.cabecera.ultima_actualizacion.
9. src/schemas.py::construir_salida_base arma la respuesta final (contrato común).
```

---

## 12. Ejecución local

```bash
cd agente_operis_llm
pip install -r requirements.txt   # groq, streamlit, pypdf, python-docx -- todas obligatorias
cp .env.example .env              # y rellena GROQ_API_KEY (obligatoria)
python main.py --demo
```

`python main.py --demo`: llama a Groq de verdad sobre `inputs/payload_demo.json`. **Ya no
es gratis ni determinista** (motor de reglas eliminado) — compara con
`outputs/respuestas_json/salida_demo.json` para detectar cambios groseros, no espera una
igualdad carácter por carácter entre ejecuciones.

```bash
python main.py ruta/al/briefing.txt                     # id_evento por defecto: evt_manual_001
python main.py ruta/al/briefing.txt --id-evento evt_42   # id_evento concreto
```

```bash
streamlit run app.py
```
Interfaz completa: subida de archivo o texto pegado, `id_evento`, clave de Groq pegable
(sin tocar `.env`), selector de bloques a actualizar, histórico local de sesión por
`id_evento` para probar el modo actualización, y un panel de Nota Bene con estilo propio
además de las pestañas Evento/Cliente/Ponentes/JSON completo.

```bash
pip install -r requirements_servidor.txt   # flask, flask-cors -- solo para esto
python servidor.py
```
Servidor HTTP fino para el frontend React: `GET /` (estado) y `POST /autocompletar` con body flexible:
`{"texto": "...", "tipo_objetivo": "cliente"}` o
`{"id_evento": "...", "texto_briefing": "...", "bloques_a_actualizar": [...], "historial_anterior": {...}}`.
`id_evento`, `bloques_a_actualizar` e `historial_anterior` son opcionales. Escucha en `http://localhost:5002` por defecto. No sustituye
el contrato real (`ejecutar_agente(payload)`), es solo una capa HTTP encima.

```bash
python docs/estimacion_tokens.py   # hace 2 llamadas reales a Groq y mide el coste
```

---

## 13. Casos de fallo específicos de `agente_operis`

| Fallo | Comportamiento esperado |
|---|---|
| Falta `GROQ_API_KEY` | Error controlado (`ValueError`) — ya no hay motor de reglas de respaldo |
| Falta `id_evento`, o va vacío/`null` | Permitido: extracción inicial sin histórico del evento |
| `bloques_a_actualizar` con un valor fuera de `BLOQUES_VALIDOS` | Error de validación explícito |
| PDF escaneado sin capa de texto | Formulario en blanco — límite conocido, no hay OCR |
| El LLM devuelve un JSON inválido | Error controlado (`ValueError`), nunca se "adivina" |
| Free tier de Groq agotado (200.000 tokens/día) | Se detiene la extracción; sin motor de reglas de respaldo, hay que esperar al día siguiente |
| Límite de tokens **por minuto** de Groq superado (8.000 TPM, `error 413 rate_limit_exceeded`) | Distinto del límite diario -- salta con prompts puntuales grandes (mucho histórico o un briefing muy largo), no por acumular llamadas. Mitigado (12/07/2026): solo se manda la última versión del histórico (no la lista completa), el ejemplo JSON del prompt se omite en llamadas de actualización, y el esquema mostrado al LLM ya no es ambiguo (ver sección 5). Con un briefing puntual muy largo aún puede saltar; no hay reintento automático. |
| Un dato suelto (teléfono, email) sin ponente asociado claro | No se asigna automáticamente; revisión manual |

---

## 14. Checklist final

- [x] `README.md` actualizado a la arquitectura de 4 bloques + Nota Bene.
- [x] `src/agente.py` con `ejecutar_agente(payload)` (reexporta `src/nucleo.py`), docstring al día.
- [x] `src/schemas.py`, `src/validaciones.py`, `src/llm.py`, `src/nucleo.py` — motor único `llm`, `id_evento` opcional en HTTP, histórico si existe y bloques parciales.
- [x] `prompts/prompt_sistema.md` completo (antes se cortaba a mitad del bloque Cliente — bug corregido) con instrucciones de los 4 bloques + ejemplo.
- [x] `construir_prompt_sistema()` usa `.replace()`, no `.format()` (el prompt tiene JSON de ejemplo con llaves literales que rompían `.format()`).
- [x] `inputs/payload_demo.json` con `id_evento` válido.
- [x] `main.py` sin motor de reglas, `--id-evento`, salida UTF-8 correcta en consola de Windows.
- [x] `streamlit_app.py` reescrito: `id_evento`, selector de bloques a actualizar, histórico local de sesión, pestañas del nuevo esquema (incluida Nota Bene con sus 3 sub-partes).
- [x] Probado de extremo a extremo con Groq real: extracción simple, actualización parcial (`bloques_a_actualizar`) y fusión con histórico (`historial_anterior`) — los tres verificados con una llamada real a la API.
- [x] `docs/estimacion_tokens.py` mide tokens reales (ya no estima con `tiktoken` sobre una salida inventada) — `docs/ESTIMACION_TOKENS.md` regenerado.
- [x] **Conexión a la BD real (Neon)**: `integrations/bd_backend.py` + `src/lectura_bd.py`, usando el `kit_conexion_agentes_Nora` oficial del proyecto (mismo patrón que Lumen en producción). `id_evento` se verifica contra la BD real; el histórico se autocarga si no viene explícito en el payload. Import perezoso: sin `DATABASE_URL`/`psycopg`, el agente funciona exactamente igual que antes.
- [x] **Interfaz de prueba reescrita (`app.py`, 12/07/2026)**: sustituye a `streamlit_app.py`; panel de Nota Bene con estilo propio (`mostrar_nota_bene`). Corregido un bug de renderizado: el HTML se construía con f-strings indentadas igual que el código Python, y Streamlit/CommonMark trata 4+ espacios al inicio de línea como bloque de código -- el panel se mostraba como texto plano en vez de renderizarse. Arreglado quitando la indentación línea a línea justo antes de `st.markdown()`.
- [x] **`servidor.py` alineado al contrato de 4 bloques (actualizado 14/07/2026)**: acepta body flexible para el front. `id_evento` es opcional; el único motor es `"llm"`; acepta `texto`, `texto_briefing`, `contenido` o `datos.texto_briefing`, además de `bloques_a_actualizar`/`historial_anterior` opcionales.
- [x] **Límite de tokens por minuto (TPM) del free tier de Groq, resuelto (12/07/2026)**: un `error 413 rate_limit_exceeded` (8.000 TPM) apareció al probar el modo actualización con histórico tras varias rondas sobre el mismo evento. Tres causas encontradas y corregidas: (1) el histórico local de sesión de `app.py` mandaba la lista completa de versiones acumuladas al LLM, ahora solo la última (`src/schemas.py::extraer_ultimo_estado`); (2) el ejemplo JSON completo del prompt de sistema se enviaba siempre, ahora se omite en llamadas de actualización (ya hay un ejemplo mejor: la última versión real); (3) la protección de bloques no actualizados se le pedía al LLM en el prompt ("cópialo tal cual"), ahora se hace en Python (`src/nucleo.py::_proteger_bloques_no_actualizados`), sin necesidad de mandarle esos bloques al LLM con la misma insistencia. Verificado end-to-end con Groq real, varias rondas de actualización sobre el mismo evento sin volver a saltar el límite.
- [x] **Esquema ambiguo mostrado al LLM, corregido (12/07/2026)**: `ESQUEMA_SALIDA` (listas planas de nombres de campo, uso interno de `_fusionar_sobre_plantilla`) se enviaba tal cual al LLM como "la forma de tu respuesta" -- ambiguo, provocó que el modelo devolviera `evento`/`cliente` como arrays de valores posicionales en vez de objetos (JSON inválido, error 400). Nueva función `src/llm.py::_esquema_para_prompt` construye la forma real (objetos anidados) solo para lo que ve el LLM; `ESQUEMA_SALIDA` sigue igual para la fusión interna.
- [ ] Pendiente, no técnico: pedirle a Nora la cadena `agente_readonly` y ponerla en `.env` — sin eso, lo de arriba está construido pero sin probar contra la BD real (sí probado el camino "sin BD disponible", que degrada con elegancia).
- [ ] **Pendiente, sigue sin definir:** cómo invoca el backend a `ejecutar_agente(payload)` en sí (API REST / librería / otro) — la conexión a BD resuelve la lectura de estado, no esta decisión (ver sección 8.2). `servidor.py` es una propuesta de capa REST, no una decisión tomada por el equipo de backend.
- [ ] Pendiente: decidir si `data/conocimiento/` se recupera (p. ej. para validar la salida del LLM contra listas conocidas) o se elimina definitivamente.
# Nota actualizada 14/07/2026 - contrato HTTP

`POST /autocompletar` ya no exige `id_evento` en el body. Si llega `id_evento`, Operis lo usa
para intentar cargar historico del evento desde BD y fusionar datos; si no llega, procesa una
extraccion inicial sin historico, pensada para pantallas independientes como Cliente o Espacio.
El texto de entrada puede llegar como `texto`, `texto_briefing`, `contenido` o
`datos.texto_briefing`. Si no llega ningun texto, devuelve `TEXTO_NO_RECIBIDO`.
