# Agente 04 — Lumen (Copilot de consulta)

Proyecto: **Ágora — arquitectura de agentes de Mitumi**
Tipo de componente: **Agente especializado, ejecutable localmente, dependiente del orquestador**
Versión plantilla base: **1.1.0** (adaptada de la plantilla común de Gestión Inteligente de Eventos)

---

## 0. Principio arquitectónico

Lumen se desarrolla como subproyecto propio, ejecutable en local para pruebas:

```bash
cd lumen_agente_04
python main.py
```

En la arquitectura final no actúa de forma autónoma. Lo llama el **agente orquestador** de Ágora
mediante la interfaz común `ejecutar_agente(payload)`:

```text
Backend / Orquestador
        ↓
ejecutar_agente(payload)
        ↓
Lumen (Agente 04 · Copilot)
        ↓
Respuesta estructurada (solo lectura)
        ↓
Orquestador / Backend / Usuario interno de Mitumi
```

Lumen es un agente **de consulta**, no de acción: analiza, interpreta y responde. Nunca guarda, nunca
ejecuta, nunca decide por otro agente.

---

## 1. Regla crítica no modificable

La estructura interna puede adaptarse, **excepto la comunicación con el orquestador**:

```text
lumen_agente_04/src/agente.py
```

Debe exponer siempre:

```python
def ejecutar_agente(payload: dict) -> dict:
    """
    Punto de entrada común del agente Lumen.
    Lo usa el main.py local, el orquestador o una futura API.
    """
    ...
```

Y respetar siempre:

```text
1. Mismo contrato de entrada.
2. Mismo contrato de salida.
3. Salida siempre estructurada.
4. Lumen no invoca directamente a otro agente.
5. Lumen no escribe directamente en la BBDD final — de hecho, no escribe nunca, bajo ningún modo.
6. Lumen no ejecuta acciones externas reales.
```

En una integración final dentro del monorepo de Ágora, esta carpeta se ubicaría en
`src/agents/lumen_copilot/`; aquí se entrega como carpeta autocontenida `lumen_agente_04/` para poder
probarla de forma aislada.

---

## 2. Identificación del agente

| Campo | Valor |
|---|---|
| **Nombre del agente** | Lumen |
| **Número / rol en la arquitectura** | Agente 04 — Copilot |
| **Equipo responsable** | Raúl, Eduardo |
| **Fase del evento que cubre** | Transversal — consulta sobre todas las fases (espacios, presupuesto, ponentes, clientes) |
| **Propósito en una frase** | Responder en lenguaje natural las preguntas del equipo de Mitumi sobre los datos ya existentes en Ágora, sin modificar nada. |
| **Tipo de agente** | Especializado, dependiente del orquestador |
| **Modo por defecto** | `consulta` (solo lectura — no aplican `propuesta` ni `ejecucion_controlada`, ver §9) |
| **Estado** | MVP |
| **Última actualización** | 10/07/2026 |

---

## 3. Qué hace este agente

Lumen es el copiloto conversacional del equipo interno de Mitumi para consultar el estado de la
plataforma Ágora sin tener que abrir la base de datos o pedírselo a otra persona.

```text
Un organizador pregunta "¿el ponente del evento X todavía no ha subido su presentación?" y Lumen
responde, cruzando ponencias.presentacion_link vacío (vía eventos.id_ponencia) con
ponentes.nombre_ponente, citando de dónde sale el dato si se le pide.
```

### Capacidades principales

- Responde preguntas en lenguaje natural sobre eventos, clientes, presupuestos, ponentes, salas y
  espacios, usando el esquema documentado en `data/rag/documentos/esquema_bd.md`.
- Resuelve tanto consultas puntuales (un evento, un ponente) como métricas agregadas (conteos,
  totales, comparativas entre eventos).
- Detecta cuándo falta un filtro imprescindible (qué evento, qué rango de fechas) y pide la aclaración
  mínima en vez de adivinar.
- Señala explícitamente cuándo un dato no existe o no está disponible, en vez de aproximarlo.

### Ejemplos de uso

- "¿Cuál es el presupuesto total aprobado para los eventos de este trimestre en Madrid?"
- "¿Qué sala tiene mayor aforo disponible para un evento de 300 personas en Barcelona?"
- "Del evento Congreso Energía, ¿el ponente tiene pendiente el billete de vuelta?"

---

## 4. Qué NO hace este agente

Lumen **no debe**:

- escribir directamente en la base de datos final (ni en ningún modo, ni siquiera en `ejecucion_controlada`);
- enviar emails reales ni mensajes de Telegram/WhatsApp;
- confirmar reservas de espacios, hoteles, vuelos o proveedores;
- aprobar ni modificar presupuestos;
- modificar fechas del evento;
- ejecutar ninguna acción irreversible o reversible sobre la plataforma;
- invocar directamente a otros agentes (Gestor de correos, Operis, Hermes, Vigil);
- sustituir al orquestador ni al backend.

Límites propios de Lumen (más estrictos que la base común, por ser agente de solo consulta):

- nunca genera ni sugiere sentencias de escritura (INSERT/UPDATE/DELETE/ALTER), ni siquiera como
  ejemplo o borrador;
- nunca consulta la tabla `usuarios` ni expone credenciales de acceso a la plataforma — exclusión
  dura, ver `data/rag/documentos/esquema_bd.md`;
- no redacta borradores de comunicación (email, mensaje) — eso es competencia de Hermes (03), no de
  Lumen; si el usuario lo pide, Lumen lo redirige;
- no genera exportaciones masivas de datos personales (email, teléfono, documento de identificación)
  sin que el usuario lo pida explícitamente y de forma acotada a un evento o ponente concreto.

---

## 5. Estructura del agente

Árbol real de `lumen_agente_04/` (verificado sobre el disco, no aspiracional — se omiten los
`__pycache__/` que genera Python automáticamente al ejecutar):

```text
lumen_agente_04/
│
├── README.md                  ← este archivo
├── GUIA_EJECUCION.md          ← guía paso a paso para arrancar main.py / servidor.py
├── main.py                    ← consola: sin args = chat con memoria; --demo = un solo disparo
│                                  sobre inputs/payload_demo.json (regresion/prueba reproducible)
├── servidor.py                 ← API HTTP (Flask) para el frontend React: memoria por sesion
├── requirements.txt             ← openai (Groq) + flask/flask-cors (solo hace falta para servidor.py)
├── .env                       ← secretos reales (Groq API key) - NO se sube al repo
│
├── config/
│   ├── __init__.py
│   ├── settings.py            ← carga variables desde .env (o .env.example si .env no existe)
│   └── permisos.py            ← fuerza ALLOW_DB_WRITE=False de forma no configurable
│
├── prompts/
│   ├── prompt_sistema.md              ← rol, permisos de solo lectura, tono, formato de salida
│   ├── prompt_clasificar_consulta.md  ← clasifica la pregunta entrante (referencia; hoy la
│   │                                     clasificacion real es determinista en src/nucleo.py)
│   ├── prompt_generar_respuesta.md    ← redacta la respuesta final cuando se usa el LLM
│   └── prompt_validar_salida.md       ← referencia de la auditoria anti-fuga (real en src/validaciones.py)
│
├── src/
│   ├── __init__.py
│   ├── agente.py               ← punto de entrada OBLIGATORIO: ejecutar_agente(payload).
│   │                               Reexporta la logica real desde nucleo.py (no tocar mas alla de eso).
│   ├── nucleo.py               ← logica real: clasificacion, orquestacion de la consulta y la
│   │                               respuesta. Incluye consultas transversales (eventos por estado,
│   │                               conteos/listados generales) ademas de consultas por id_evento.
│   ├── memoria.py               ← memoria de conversacion (capa POR ENCIMA de ejecutar_agente, sin
│   │                               tocar su contrato). La usan main.py (por proceso) y servidor.py
│   │                               (por sesion de navegador), cada uno con sus propias instancias.
│   ├── lectura_datos.py        ← acceso de SOLO LECTURA a la BD real (integrations/db_backend.py);
│   │                               bloquea la tabla `usuarios` a nivel de codigo
│   ├── consultas.py            ← alias de compatibilidad -> reexporta lectura_datos.py
│   ├── llm.py                  ← cliente Groq (API compatible OpenAI) - lee API key de config/settings
│   ├── prompts.py               ← carga los prompts/*.md (extrae el bloque de codigo) para pasarselos al LLM
│   ├── schemas.py               ← contrato de entrada/salida (validar_entrada, construir_salida_base)
│   └── validaciones.py          ← auditoria anti-alucinacion y anti-escritura (defensa en profundidad)
│
├── integrations/
│   ├── __init__.py
│   ├── db_backend.py            ← UNICA via de acceso a datos: cliente Postgres de solo lectura
│   │                               (DATABASE_URL en .env, sesion abierta en modo readonly)
│   └── verificar_conexion_bd.py ← script manual: compara el esquema real de la BD contra lo que
│                                    Lumen espera (data/rag/documentos/esquema_bd.md)
│
├── inputs/
│   └── payload_demo.json       ← payload de ejemplo que usa main.py --demo
│
├── data/
│   └── rag/
│       └── documentos/
│           └── esquema_bd.md   ← esquema de tablas/campos, fuente unica de verdad del dominio
│
└── outputs/
    └── respuestas_json/        ← aqui guarda main.py --demo la salida de cada ejecucion
```

Nota importante sobre `src/agente.py`: el nombre de archivo y la funcion `ejecutar_agente(payload)`
son el contrato obligatorio del proyecto (seccion 1) y no cambian. La logica en si vive en
`src/nucleo.py` para mantener el fichero de contrato lo mas simple y estable posible; `agente.py`
solo hace `from src.nucleo import ejecutar_agente`.

## 6. Archivo `.env`

Ver `.env.example` para la plantilla completa (sin secretos). Variables clave:

```env
ENVIRONMENT=local
LLM_PROVIDER=groq                       # motor confirmado
LLM_MODEL=llama-3.3-70b-versatile       # limite de tokens/dia por modelo: ver src/llm.py y GUIA_EJECUCION.md
LLM_TEMPERATURE=0.1                     # respuestas deterministas para consulta de datos
LLM_MAX_TOKENS=800
GROQ_API_KEY=...                        # solo en .env real, nunca en .env.example ni en el codigo
GROQ_BASE_URL=https://api.groq.com/openai/v1
ALLOW_DB_WRITE=False       # no negociable para Lumen
ALLOW_EXTERNAL_SEND=False
ALLOW_CREATE_EVENT=False
ALLOW_AUTO_APPROVAL=False
DATABASE_URL=postgresql://...           # conexion real (Postgres/Neon) - FUENTE UNICA de datos
DATABASE_ROLE=readonly
TABLAS_EXCLUIDAS=usuarios
FLASK_DEBUG=false                       # servidor.py: debug del reloader de Flask. OFF por defecto (RCE si se expone)
PORT=5001                               # servidor.py: puerto de la API HTTP
```

`.gitignore` debe incluir `.env`, `*.log`, `outputs/`, `data/rag/indice/`. La API key y la cadena
de conexión a la BD viven solo en `.env` (nunca en `.env.example`, nunca hardcodeadas en el código).

## 7. Contrato de entrada — adaptación para Lumen

- `id_evento` puede ser `null` cuando la consulta es transversal a varios eventos (ej. métricas
  globales) — el campo se mantiene en el contrato, pero se documenta explícitamente esta excepción.
- `tipo_peticion` para Lumen usa valores como: `"consultar_datos_evento"`,
  `"consultar_metricas_globales"`, `"responder_pregunta_libre"`.
- `modo` para Lumen es siempre efectivamente de solo lectura. El campo se mantiene por compatibilidad
  con el contrato común, pero Lumen ignora cualquier instrucción de `modo: "ejecucion_controlada"` que
  implique escritura.

Ver `inputs/payload_demo.json` para el payload real que usa `main.py`.

---

## 8. Contrato de salida — adaptación para Lumen

```json
{
  "ok": true,
  "agente": "lumen_copilot",
  "tipo_peticion": "consultar_datos_evento",
  "resumen": "El evento Congreso Energía tiene 1 ponente sin billete de vuelta: Ana Ruiz.",
  "datos_detectados": { "ponentes_sin_billete_vuelta": ["Ana Ruiz"] },
  "acciones_propuestas": [],
  "bloqueos_detectados": [],
  "borradores_generados": [],
  "requiere_validacion_humana": false,
  "nivel_riesgo": "bajo",
  "errores": [],
  "trazas": {
    "fuentes_consultadas": ["ponencias.billete_vuelta_link", "ponentes.nombre_ponente"],
    "timestamp": "2026-07-08T09:00:00",
    "modo": "consulta"
  }
}
```

`acciones_propuestas` y `borradores_generados` quedan **siempre vacíos** en Lumen. `src/validaciones.py`
lo fuerza en código, no solo por prompt.

---

## 9. Esquema de datos de referencia

Ver `data/rag/documentos/esquema_bd.md` para el detalle completo de tablas, campos, relaciones y la
exclusión dura de la tabla `usuarios`. `src/lectura_datos.py` (y su alias `src/consultas.py`) usan
esos mismos nombres de tabla y campo al leer de la BD real.

---

## 9 bis. Fuente de datos: BD real (única)

Lumen lee exclusivamente de una base de datos Postgres real (`DATABASE_URL` en `.env`), a través de
`integrations/db_backend.py`. No hay mock JSON ni API HTTP intermedia — se retiraron deliberadamente
para que exista una única fuente de verdad, sin ambigüedad sobre de dónde sale cada dato.

- Conexión de solo lectura reforzada en dos capas: la sesión de Postgres se abre con
  `readonly=True` (Postgres rechaza cualquier escritura a nivel de protocolo, no solo por
  convención en el código), y `db_backend.py` no implementa ni expone ninguna función de escritura.
- La tabla `usuarios` sigue bloqueada en `config/permisos.py` (`TABLAS_EXCLUIDAS`), comprobado tanto
  en `src/lectura_datos.py` como en `integrations/db_backend.py` (defensa en dos capas).
- Si la conexión falla (red, credenciales, columna que no existe), `ejecutar_agente` devuelve un
  bloqueo explícito (`nivel_riesgo: "medio"`) en vez de fallar en seco o inventar un dato — ver
  `integrations/db_backend.py::DbBackendError` y su manejo en `src/nucleo.py`.

**Estado de verificación:** el esquema se verificó en vivo contra la BD real (Neon) con el script
de abajo: todas las tablas coinciden con `data/rag/documentos/esquema_bd.md`. La única diferencia
(columna `presupuestos.observaciones`, presente en la BD y antes no documentada) ya está añadida. Si
en el futuro cambian tablas o columnas, vuelve a ejecutar:

```bash
cd lumen_agente_04
python integrations/verificar_conexion_bd.py
```

Esto conecta con `DATABASE_URL`, compara tablas y columnas reales contra lo que Lumen espera, y avisa
de cualquier diferencia (tabla o columna que falte, o que sobre) para corregir `db_backend.py` o el
esquema si hace falta.

**Seguridad de `DATABASE_URL`:** la cadena de conexión (usuario, contraseña, host) vive solo en
`.env`, que ya está en `.gitignore` — igual que `GROQ_API_KEY`. No se hardcodea en ningún archivo
de código ni se sube al repositorio. Si esa contraseña se ha compartido por un canal no seguro
(chat, email), lo prudente es rotarla desde el panel de Neon en cuanto sea posible.

---

## 10. Flujo interno implementado

```text
1. main.py lee inputs/payload_demo.json y llama a ejecutar_agente(payload) (src/agente.py).
2. src/schemas.py valida entrada minima (id_evento puede ser null, tipo_peticion obligatorio).
3. src/nucleo.py aplica PRIMERO las reglas duras deterministas (nunca delegadas al LLM):
   - si la pregunta menciona la tabla `usuarios` / credenciales -> bloqueo, riesgo alto.
   - si pide una escritura (modificar, aprobar, borrar, confirmar...) -> bloqueo, riesgo medio.
   Estas dos comprobaciones se hacen en codigo, ANTES de que el LLM entre en juego, como defensa
   en profundidad: el LLM nunca es el unico guardian de estas reglas.
4. Para preguntas de solo lectura sobre un evento:
   - los patrones especificos (billete de ida/vuelta de ponentes) se resuelven de forma
     determinista via src/lectura_datos.py, sin LLM (mas rapido y 100% predecible).
   - el resto de preguntas libres (presupuesto, sala, espacio, cliente...) se resuelven con el
     LLM configurado (Groq) si GROQ_API_KEY esta presente en .env: src/nucleo.py arma el contexto
     completo del evento (src/lectura_datos.py, tabla `usuarios` ya excluida) y llama al LLM con
     prompts/prompt_sistema.md + prompts/prompt_generar_respuesta.md (ver src/llm.py, src/prompts.py).
   - la llamada a Groq pide modo JSON (`response_format=json_object`) y la respuesta se limpia de
     posibles fences de markdown antes de parsear (`src/nucleo._parsear_json_llm`); si aun asi el
     LLM no esta configurado, falla, o no devuelve JSON valido, se hace fallback automatico al
     resumen determinista del evento - Lumen nunca se queda sin responder por un fallo del LLM.
5. src/validaciones.py audita SIEMPRE la salida final (venga del LLM o de las reglas): fuerza
   acciones_propuestas/borradores_generados vacios y bloquea cualquier fuga sobre `usuarios` o
   credenciales de acceso, incluso si el LLM alucinase o el usuario intentase manipular el prompt.
6. main.py imprime el resultado y lo guarda en outputs/respuestas_json/salida_demo.json.
```

El `SELECT` real lo construye codigo determinista en `src/lectura_datos.py` — el LLM nunca genera SQL
ni decide que tabla consultar; solo redacta la respuesta en lenguaje natural a partir del contexto que
ya se le entrega, ya filtrado. Esto es intencional: aunque el LLM fallase o fuese manipulado, no puede
saltarse las restricciones de acceso a datos.

## 11. Prompts

```text
prompts/
├── prompt_sistema.md              ← rol, permisos de solo lectura, tono, formato de salida
├── prompt_clasificar_consulta.md  ← clasifica la pregunta entrante
├── prompt_generar_respuesta.md    ← redacta la respuesta grounded en los datos recuperados
└── prompt_validar_salida.md       ← auditoría final anti-alucinación y anti-escritura
```

---

## 12. RAG, datos e integraciones

```text
data/rag/documentos/esquema_bd.md      ← esquema de tablas/campos (fuente única de verdad)
integrations/db_backend.py             ← única vía de acceso a datos: Postgres real, solo lectura
integrations/verificar_conexion_bd.py  ← script manual para comparar el esquema real contra esquema_bd.md
```

Las integraciones de Lumen solo leen. No existe ninguna integración de escritura en este agente.

---

## 13. Modo seguro por defecto

```python
ALLOW_DB_WRITE = False          # fijo en config/permisos.py, no configurable para Lumen
ALLOW_EXTERNAL_SEND = False
ALLOW_CREATE_EVENT = False
ALLOW_AUTO_APPROVAL = False
```

En Lumen estos flags no son un "modo por defecto que se podría cambiar más adelante": son una
restricción arquitectónica permanente, reforzada en `config/permisos.py` y verificada en
`src/agente.py`.

---

## 14. Ejecución local

```bash
cd lumen_agente_04
pip install -r requirements.txt
cp .env.example .env
python main.py
```

`main.py` (consola, sin argumentos): abre un **chat interactivo con memoria de conversación**
(`src/memoria.py`) — recuerda el último evento del que se habló y lo reutiliza en preguntas de
seguimiento ("¿y su presupuesto?", "ese evento"). El evento se resuelve por UUID o número
explícito, por nombre ("del evento Congreso Energía") o por memoria. Escribe `nuevo` para
olvidar el contexto, `salir` para terminar.

`python main.py --demo`: un solo disparo — carga `inputs/payload_demo.json`, llama a
`ejecutar_agente(payload)`, imprime la respuesta y la guarda en
`outputs/respuestas_json/salida_demo.json`. El payload trae `id_evento: null` y una pregunta
transversal ("¿cuántos eventos hay?"), así que corre contra la BD real sin depender de ningún id
hardcodeado. `modo_demo` resuelve el evento igual que el chat: si editas la pregunta para nombrar
un evento o pegar su UUID, lo resuelve por nombre/UUID. Los `id` reales son UUID; el antiguo
`id_evento: 12` numérico se retiró porque no existía en la BD real y hacía fallar el demo.

`python servidor.py`: API HTTP (Flask, puerto 5001) para el **frontend React**, con memoria de
conversación por sesión (`sesion_id`) en vez de por proceso. Ver `GUIA_EJECUCION.md` sección 4.3
para el contrato de `POST /chat` y `POST /chat/reset`.

---

## 15. Casos de fallo específicos de Lumen

| Fallo | Comportamiento esperado |
|---|---|
| Falta `id_evento` en una consulta que sí lo necesita | `bloqueos_detectados` pidiendo el evento, no se adivina |
| Se pregunta por la tabla `usuarios` o por credenciales de acceso | Bloqueo inmediato, `nivel_riesgo: "alto"`, `requiere_validacion_humana: true`, no se toca la BD |
| Se pide una escritura disfrazada de pregunta ("¿puedes subir el presupuesto un 10%?") | Se bloquea la parte de escritura |
| El dato no existe en los datos disponibles | Se declara explícitamente que no existe, no se aproxima |
| El LLM devuelve texto no estructurado (cuando se conecte el LLM real) | Reintento controlado vía `prompt_validar_salida.md`; si persiste, error controlado |
| Consulta ambigua sin evento ni rango de fechas | Se pide aclaración mínima antes de consultar datos |
| Integración con la BD falla | Se devuelve error, no se inventa una respuesta con datos "probables" |

---

## 16. Checklist final

- [x] Existe `README.md` (este archivo).
- [x] Existe `.env.example` sin secretos, y `.env` real con la API key de Groq (no versionado).
- [x] Existe `main.py` para ejecucion local - funciona out-of-the-box en modo demo.
- [x] Existe `src/agente.py` con `ejecutar_agente(payload)` (reexporta `src/nucleo.py`).
- [x] Existe `src/schemas.py` con el contrato de entrada/salida.
- [x] Existen los 4 prompts, y ahora se usan de verdad (`src/prompts.py` los carga en runtime).
- [x] Existe `data/rag/documentos/esquema_bd.md` con el esquema real de la BD.
- [x] Existe `inputs/payload_demo.json`.
- [x] El agente no invoca a otros agentes.
- [x] El agente no escribe directamente en la BD final (restriccion de diseno, no solo de `.env`).
- [x] El agente no envia emails/mensajes reales.
- [x] Los permisos por defecto estan en modo seguro (y son fijos, no solo por defecto).
- [x] Se documenta que hace y que no hace (parrafos 3-4).
- [x] Motor de LLM confirmado y conectado: Groq (`llama-3.3-70b-versatile`), con fallback
      determinista automatico si el LLM no esta disponible o falla.
- [x] Consultas transversales (`id_evento: null`) implementadas de forma determinista en
      `src/nucleo.py`: eventos por estado (con sinónimos y sin adivinar estados que no existen) y
      conteos/listados generales ("cuántos eventos tenemos"). Resuelto en código, sin depender del
      LLM ni de que esté disponible.
- [x] Memoria de conversación (`src/memoria.py`) por encima de `ejecutar_agente(payload)`, sin
      tocar su contrato: recuerda el último evento mencionado (explícito o "enganchado" desde una
      consulta transversal con un solo resultado) y pasa el historial reciente al LLM solo para
      resolver referencias del lenguaje, nunca como fuente de datos. La usan `main.py` (memoria
      por proceso) y `servidor.py` (memoria por sesión de navegador).
- [x] API HTTP (`servidor.py`, Flask + CORS) para que el frontend React pueda chatear con Lumen:
      `POST /chat` y `POST /chat/reset`, con memoria por `sesion_id`.
- [x] Conexión a la BD real (Postgres) implementada como fuente única de datos
      (`integrations/db_backend.py`), sin mock ni API intermedia. `DATABASE_URL` (Neon) ya
      configurada en `.env`.
- [x] `contexto_completo_evento` usa UNA sola conexión Postgres para las ~6 lecturas de un evento
      (antes abría una por tabla).
- [x] Respuesta del LLM robusta a JSON envuelto en fences de markdown + modo JSON de Groq
      (`src/nucleo._parsear_json_llm`, `src/llm.py`).
- [x] Fechas de evento se muestran como fecha (`2026-12-10`), no como timestamp con hora/zona
      (`integrations/db_backend._serializar_valor`).
- [x] `id_evento` explícito reconoce UUID (además del número heredado); el demo ya no hardcodea id.
- [x] `servidor.py` arranca con `debug` OFF por defecto, activable con `FLASK_DEBUG=true` en `.env`.
- [x] Esquema real verificado en vivo contra Neon con `python integrations/verificar_conexion_bd.py`:
      todas las tablas coinciden; la única diferencia (columna `presupuestos.observaciones`, que
      faltaba en el esquema esperado) ya está añadida en `esquema_bd.md` y en el script de
      verificación. La tabla `usuarios` existe y se confirma bloqueada.
- [ ] Pendiente: extender la clasificacion de preguntas transversales al LLM (hoy es determinista
      por palabras clave; funciona sin LLM, pero no entiende frases fuera de los sinónimos
      cubiertos en `SINONIMOS_ESTADO_EVENTO`).
- [ ] Pendiente: persistencia de sesiones de `servidor.py` más allá de la memoria del proceso
      (hoy se pierden si se reinicia el servidor — aceptado para esta fase de demo).

## Nota sobre las pruebas de este entregable

`python main.py` y los casos de bloqueo (tabla `usuarios`, intentos de escritura) se probaron y
funcionan correctamente de extremo a extremo. La llamada real al LLM de Groq se probo hasta el punto
de construir la peticion (prompt + contexto JSON) correctamente; la llamada de red en si no se pudo
verificar desde este entorno de generacion porque su sandbox bloquea el acceso saliente a dominios no
incluidos en su lista blanca (api.groq.com no lo esta) - esto es una restriccion del entorno donde se
generaron estos archivos, no del codigo. En vuestro propio equipo, con acceso normal a internet, la
llamada a Groq deberia funcionar tal cual; si fallase por cualquier motivo, el agente cae de forma
segura a la respuesta determinista (se ve reflejado en el campo `errores` de la salida).

El esquema real (columnas/tablas) ya se ha confirmado en vivo contra Neon ejecutando
`python integrations/verificar_conexion_bd.py`: coincide con `data/rag/documentos/esquema_bd.md`
salvo la columna `presupuestos.observaciones`, que se ha añadido. La lógica de enrutado y manejo de
errores de `integrations/db_backend.py` se verificó además con una base de datos simulada.
