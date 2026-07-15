# README — Agente OPERIS

Proyecto: **Gestión Inteligente de Eventos — Mitümi**  
Tipo de componente: **Agente especializado ejecutable localmente, dependiente del orquestador/backend en la arquitectura final**  
Versión documentada: **2.3.0**  
Fecha de revisión: **12/07/2026**

---

## 0. Principio arquitectónico obligatorio

OPERIS puede ejecutarse de forma local para desarrollo y pruebas:

```bash
python main.py --demo
```

En la arquitectura final no actúa como agente autónomo. Su punto de entrada es `ejecutar_agente(payload)` y su resultado es siempre una propuesta estructurada que debe revisar una persona antes de que el backend realice cualquier escritura o acción.

```text
Backend / Orquestador
        ↓
ejecutar_agente(payload)
        ↓
OPERIS: extracción y actualización de briefings
        ↕ solo lectura opcional
Base de datos Neon Postgres
        ↓
Respuesta JSON estructurada
        ↓
Validación humana → Backend → persistencia o acción real
```

Regla principal:

```text
OPERIS analiza, extrae, fusiona y propone.
El orquestador/backend coordina y enruta.
El backend valida, guarda y ejecuta acciones reales.
Una persona aprueba las propuestas.
La base de datos es la fuente final de verdad.
```

---

## 1. Regla crítica no modificable

El punto de entrada común está implementado en:

```text
agente_operis_llm/src/agente.py
```

Y expone:

```python
def ejecutar_agente(payload: dict) -> dict:
    """Punto de entrada común del agente."""
```

OPERIS respeta estas reglas:

1. Acepta una entrada estructurada.
2. Devuelve una salida estructurada.
3. No invoca directamente a otros agentes.
4. No escribe en la base de datos final.
5. No envía comunicaciones ni ejecuta acciones externas.
6. Mantiene `requiere_validacion_humana = true` en todas las respuestas.

---

## 2. Identificación del agente

| Campo | Valor |
|---|---|
| **Nombre del agente** | `agente_operis` / OPERIS |
| **Equipo responsable** | Equipo Data de OPERIS — responsable nominal por confirmar |
| **Fase del evento que cubre** | Captación, preparación y actualización de información del evento |
| **Propósito en una frase** | Convertir briefings de eventos en una propuesta JSON estructurada y fusionarla de forma segura con la información previa del evento. |
| **Tipo de agente** | Especializado dependiente del orquestador/backend |
| **Modo por defecto** | `propuesta` |
| **Estado** | MVP funcional / experimental |
| **Versión** | `2.3.0` según la memoria técnica |
| **Última actualización** | 12/07/2026 |

---

## 3. Qué hace este agente

OPERIS lee un briefing en texto libre —procedente de texto pegado o de archivos `.txt`, `.pdf` y `.docx`— y extrae la información en cuatro bloques:

- `evento`: nombre, ciudad, lugar, fechas, aforo, tipo, estado y notas;
- `cliente`: empresa, contacto general y lista de personas de contacto;
- `ponentes`: datos profesionales, contacto, logística y ponencia;
- `nota_bene`: resumen ejecutivo, presupuesto y servicios, requisitos, riesgos y acciones pendientes.

### Capacidades principales

- Extraer datos de lenguaje natural mediante un LLM de Groq.
- Aplicar la regla de no invención: los datos ausentes quedan vacíos.
- Actualizar todos los bloques o solo los indicados en `datos.bloques_a_actualizar`.
- Fusionar información nueva con `contexto.historial_anterior`.
- Autocargar el estado actual desde Neon Postgres cuando existe `DATABASE_URL`, siempre en modo de solo lectura.
- Proteger mediante código Python los bloques que no deben actualizarse.
- Generar un resumen, porcentaje de completitud y lista de campos pendientes.
- Mantener trazabilidad de fuente, modo y fecha de ejecución.

### Ejemplos de uso

- Convertir un correo de solicitud de evento en datos de Evento, Cliente, Ponentes y Nota Bene.
- Incorporar una revisión de presupuesto sin sobrescribir datos ya validados del cliente.
- Actualizar únicamente el bloque `nota_bene` a partir de un documento complementario.
- Recuperar el estado de un evento existente desde la base de datos y fusionar un briefing nuevo.

---

## 4. Qué NO hace este agente

El agente no debe ni puede:

- escribir directamente en la base de datos final;
- crear eventos en la base de datos;
- enviar emails, Telegram, WhatsApp u otras comunicaciones;
- confirmar espacios, hoteles, vuelos o proveedores;
- aprobar presupuestos;
- modificar fechas críticas sin revisión;
- ejecutar acciones irreversibles;
- invocar directamente a otros agentes;
- sustituir al orquestador o al backend;
- procesar peticiones distintas de `extraer_briefing`;
- funcionar en modo autónomo o de autoaprobación;
- garantizar que la extracción del LLM sea correcta sin revisión humana.

Límites específicos actuales:

- Requiere `GROQ_API_KEY`; el motor de reglas fue eliminado.
- Solo admite el modo `propuesta`.
- `id_evento` es opcional en la capa HTTP; si llega, se usa para historico, y si no llega propone una extraccion inicial sin guardar nada.
- Sin `DATABASE_URL` no comprueba la existencia real del evento ni autocarga histórico.
- La BD actual relaciona como máximo una ponencia/ponente con cada evento, aunque el esquema de OPERIS acepta una lista.
- El LLM está sujeto a límites de cuota y tokens por minuto de Groq.

---

## 5. Estructura actual del agente

```text
agente_operis_llm/
├── README.md
├── main.py                     # CLI y demo local
├── app.py                      # interfaz Streamlit de prueba
├── servidor.py                 # propuesta de API Flask
├── requirements.txt
├── requirements_servidor.txt
├── config/
│   ├── settings.py             # GROQ_API_KEY, GROQ_MODEL, DATABASE_URL
│   └── permisos.py             # permisos seguros
├── prompts/
│   └── prompt_sistema.md
├── src/
│   ├── agente.py               # interfaz pública
│   ├── nucleo.py               # flujo principal y protección de bloques
│   ├── schemas.py              # estructuras y contrato de salida
│   ├── validaciones.py         # contrato de entrada
│   ├── llm.py                  # integración con Groq
│   ├── lectura_archivos.py     # .txt, .pdf y .docx
│   ├── lectura_bd.py           # traducción BD → esquema OPERIS
│   └── rag.py                  # placeholder; RAG no utilizado
├── integrations/
│   └── bd_backend.py           # acceso PostgreSQL de solo lectura
├── inputs/
│   └── payload_demo.json
├── data/
│   ├── ejemplos/
│   └── conocimiento/           # legado del motor de reglas, sin uso actual
├── outputs/
│   └── respuestas_json/
└── docs/
    ├── Agente_OPERIS_implementacion.md
    └── ESTIMACION_TOKENS.md
```

Observación: en el estado revisado no existe `.env.example`, aunque la plantilla lo exige.

---

## 6. Estructura mínima obligatoria: estado

| Elemento | Estado | Observación |
|---|---:|---|
| `README.md` | ✅ | Existe documentación extensa en el agente. |
| `main.py` | ✅ | Admite demo y archivo por CLI. |
| `.env.example` | ❌ | No aparece en el árbol revisado. |
| `src/agente.py` | ✅ | Expone `ejecutar_agente`. |
| `src/schemas.py` | ✅ | Define estructuras y salida. |
| `inputs/payload_demo.json` | ✅ | Existe payload de demostración. |
| `outputs/respuestas_json/` | ✅ | Existe salida demo. |

---

## 7. Configuración y variables de entorno

Configuración mínima propuesta para un futuro `.env.example`:

```env
# Motor LLM obligatorio
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b

# Base de datos opcional y de solo lectura
DATABASE_URL=

# Modo seguro
MODO_DEMO=True
ALLOW_DB_WRITE=False
ALLOW_EXTERNAL_SEND=False
ALLOW_CREATE_EVENT=False
ALLOW_AUTO_APPROVAL=False
```

No se deben versionar claves reales. La cadena de PostgreSQL debe corresponder al rol `agente_readonly`, nunca a un usuario propietario.

Permisos implementados en `config/permisos.py`:

```python
ALLOW_DB_WRITE = False
ALLOW_EXTERNAL_SEND = False
ALLOW_CREATE_EVENT = False
ALLOW_AUTO_APPROVAL = False
```

---

## 8. Comunicación con el orquestador/backend

### 8.1 Punto de entrada

```python
from src.agente import ejecutar_agente

respuesta = ejecutar_agente(payload)
```

`servidor.py` ofrece una propuesta de integración HTTP con Flask, pero la decisión final —API REST, import Python u otro mecanismo— sigue pendiente del equipo de backend.

### 8.2 Contrato de entrada

```json
{
  "id_evento": "evt_001",
  "id_registro": null,
  "tipo_peticion": "extraer_briefing",
  "origen": "orquestador",
  "usuario_solicitante": "admin",
  "rol_usuario": "organizador",
  "datos": {
    "texto_briefing": "Texto del briefing...",
    "groq_api_key": null,
    "bloques_a_actualizar": ["evento", "cliente", "ponentes", "nota_bene"]
  },
  "contexto": {
    "historial_anterior": null,
    "modo_actualizacion": "fusionar"
  },
  "modo": "propuesta"
}
```

Reglas específicas:

| Campo | Regla |
|---|---|
| `id_evento` | Opcional. Si llega y la BD esta disponible, debe existir; si no llega, se procesa como extraccion inicial sin historico. |
| `tipo_peticion` | Único valor admitido: `extraer_briefing`. |
| `datos.texto_briefing` | Obligatorio y no vacío. |
| `datos.groq_api_key` | Opcional; prevalece sobre la variable de entorno. |
| `datos.bloques_a_actualizar` | Opcional; valores: `evento`, `cliente`, `ponentes`, `nota_bene`. |
| `contexto.historial_anterior` | Opcional; prevalece sobre la autocarga desde BD. |
| `contexto.modo_actualizacion` | `fusionar` por defecto o `sobrescribir`. |
| `modo` | Único valor admitido: `propuesta`. |

### 8.3 Contrato de salida

```json
{
  "ok": true,
  "agente": "agente_operis",
  "tipo_peticion": "extraer_briefing",
  "resumen": "Resumen del resultado.",
  "datos_detectados": {
    "evento": {},
    "cliente": {},
    "ponentes": [],
    "nota_bene": {
      "cabecera": {},
      "presupuesto_servicios": {},
      "informacion_adicional": {}
    }
  },
  "acciones_propuestas": [],
  "bloqueos_detectados": [],
  "borradores_generados": [],
  "requiere_validacion_humana": true,
  "nivel_riesgo": "bajo",
  "errores": [],
  "trazas": {
    "fuentes_consultadas": ["motor:llm"],
    "timestamp": "2026-07-12T00:00:00",
    "modo": "propuesta"
  },
  "_validacion": {
    "porcentaje_completado": 100,
    "campos_pendientes": []
  },
  "_aviso_agente": {
    "mensaje": "Revisar la propuesta antes de guardarla."
  }
}
```

`requiere_validacion_humana` siempre es `true` y `nivel_riesgo` siempre es `bajo`, porque OPERIS no ejecuta acciones externas. El porcentaje de completitud se calcula sobre seis campos del bloque Evento: nombre, ciudad, fechas de inicio y fin, número de personas y tipo de evento.

---

## 9. Flujo interno

```text
1. main.py, app.py, servidor.py o el backend construye el payload.
2. src/agente.py delega en src/nucleo.py.
3. validaciones.py valida campos, modo, petición y bloques.
4. Si no llega histórico explícito, se intenta cargar desde la BD.
5. schemas.py reduce el histórico a su último estado.
6. llm.py construye el prompt y llama a Groq con salida JSON.
7. El resultado se fusiona sobre una plantilla de cuatro bloques.
8. nucleo.py restaura desde el histórico los bloques no actualizados.
9. El código añade fecha e histórico de actualización.
10. schemas.py genera resumen, bloqueos, completitud y trazas.
11. Se devuelve la respuesta al consumidor para revisión humana.
```

---

## 10. Prompts y LLM

El prompt principal está en `prompts/prompt_sistema.md`. Define:

- el esquema exacto de Evento, Cliente, Ponentes y Nota Bene;
- la prohibición de inventar datos;
- formatos de fechas y listas;
- salida exclusiva en JSON;
- reglas de fusión con histórico;
- clasificación de servicios en ubicación, catering, audiovisuales y otros.

El motor actual es Groq con el modelo predeterminado `openai/gpt-oss-120b`, temperatura `0` y respuesta JSON forzada. No existe fallback por reglas.

---

## 11. RAG y datos

OPERIS no utiliza RAG actualmente. El histórico por evento es pequeño y se pasa directamente al prompt, limitado al último estado para evitar crecimiento acumulativo de tokens.

La carpeta `data/conocimiento/` contiene catálogos heredados del motor de reglas eliminado. En el estado actual ningún módulo los importa; debe decidirse si se reutilizan para validación o se eliminan.

---

## 12. Integraciones

### Base de datos

`integrations/bd_backend.py` permite leer ocho tablas autorizadas:

```text
clientes, eventos, presupuestos, ponentes,
ponencias, salas, espacios
```

La tabla `usuarios` queda fuera de alcance. El estado del evento se lee desde `eventos.estado`; no existe tabla `estados`. Las conexiones PostgreSQL se marcan como `read_only`. La integración es opcional y usa importación perezosa: sin `DATABASE_URL` o sin `psycopg`, la extracción sigue funcionando, pero sin histórico ni validación real del identificador.

### Archivos

`src/lectura_archivos.py` admite `.txt`, `.pdf` y `.docx`. El payload común, sin embargo, recibe el texto ya extraído en `datos.texto_briefing`.

---

## 13. Modo seguro por defecto

OPERIS:

- puede leer archivos y, opcionalmente, datos de la BD;
- puede analizar y estructurar información;
- puede fusionar histórico y proponer actualizaciones;
- no puede escribir en la BD;
- no puede crear eventos;
- no puede enviar comunicaciones;
- no puede aprobar automáticamente;
- siempre exige validación humana.

---

## 14. Instalación y ejecución local

Desde la carpeta del agente:

```bash
python -m venv .venv
# Activar el entorno según el sistema operativo
pip install -r requirements.txt
```

Crear localmente un archivo `.env` con `GROQ_API_KEY` y, opcionalmente, `DATABASE_URL` de solo lectura.

Demo incluida:

```bash
python main.py --demo
```

Archivo propio:

```bash
python main.py ruta/al/briefing.pdf --id-evento evt_001
```

Interfaz de prueba:

```bash
streamlit run app.py
```

Servidor Flask propuesto:

```bash
pip install -r requirements_servidor.txt
python servidor.py
```

Advertencia: la demo usa el LLM real y consume cuota de Groq.

---

## 15. Casos de fallo controlados

| Fallo | Comportamiento esperado |
|---|---|
| Falta `id_evento` | Permitido en el endpoint HTTP; Operis procesa el texto como extraccion inicial sin historico. |
| El evento no existe y hay BD disponible | Rechazar la petición. |
| Falta `texto_briefing` | `ok=false`; no llamar al LLM. |
| Petición distinta de `extraer_briefing` | Error controlado. |
| Modo distinto de `propuesta` | Error controlado. |
| Bloque desconocido | Error con la lista de bloques válidos. |
| Falta `GROQ_API_KEY` | Error controlado de configuración. |
| Groq supera cuota o TPM | Error controlado; no ejecutar ninguna acción. |
| El LLM devuelve JSON inválido | Error controlado. |
| La BD no está configurada | Continuar sin autocarga de histórico. |
| Faltan datos en el briefing | No inventar; dejar campos vacíos e informar pendientes. |
| Actualización parcial | Restaurar en Python los bloques protegidos desde el último estado. |

---

## 16. Decisiones y evolución relevantes

- El primer prototipo utilizó reglas deterministas y seis bloques.
- El motor de reglas se eliminó tras validar el enfoque LLM.
- El esquema se redujo a cuatro bloques y se añadió Nota Bene.
- `id_evento` puede enviarse cuando OPERIS actualiza eventos creados previamente, pero ya no es obligatorio para extracciones iniciales.
- Se añadió actualización parcial e histórico con modos `fusionar` y `sobrescribir`.
- La protección de bloques se movió del prompt a Python para reducir tokens y evitar alteraciones.
- Solo se envía al LLM la última versión del histórico.
- Se separó el esquema interno del esquema mostrado al LLM para evitar arrays posicionales inválidos.
- La conexión de lectura a Neon se implementó mediante el kit oficial del proyecto.

Fuente principal de estas decisiones: `memoria_operis_barbara.md`, contrastada con los módulos actuales.

---

## 17. Pendientes conocidos

1. Crear y versionar `.env.example` sin secretos.
2. Confirmar el equipo/persona responsable para completar la identificación.
3. Obtener y probar la cadena `DATABASE_URL` del rol `agente_readonly`.
4. Definir cómo invocará el backend a `ejecutar_agente`: REST, import Python u otro mecanismo.
5. Decidir el destino de `data/conocimiento/`, actualmente huérfano.
6. Revisar la discrepancia documental entre "conexión resuelta" y "pendiente de probar contra la BD real".
7. Confirmar que `.env`, logs y salidas están correctamente excluidos por `.gitignore`.

---

## 18. Checklist final

- [x] Existe `README.md`.
- [ ] Existe `.env.example` sin secretos.
- [ ] Se verificó que `.env` esté en `.gitignore`.
- [x] Existe `main.py` para ejecución local.
- [x] Existe `src/agente.py`.
- [x] `src/agente.py` expone `ejecutar_agente(payload: dict) -> dict`.
- [x] La entrada está validada y documentada.
- [x] La salida respeta el contrato común y añade metadatos propios.
- [x] El agente no invoca a otros agentes.
- [x] El agente no escribe directamente en la BD final.
- [x] El agente no envía comunicaciones reales.
- [x] Los permisos están en modo seguro.
- [x] Existe payload demo y salida de ejemplo.
- [x] Se documenta qué hace y qué no hace.
- [x] Se documentan actualización parcial, histórico y Nota Bene.
- [ ] Ejecución real pendiente de una `GROQ_API_KEY` válida y cuota disponible.
- [ ] Lectura contra BD real pendiente de credenciales `agente_readonly` y verificación end-to-end.

---

## 19. Fuentes revisadas

- `Definicion_Agentes_RAUL/README_plantilla_agente_dependiente.md`
- `agente_operis_autoV2.0/memoria_operis_barbara.md`
- `agente_operis_llm/README.md`
- `agente_operis_llm/docs/Agente_OPERIS_implementacion.md`
- Código de `src/`, `config/`, `integrations/`, `main.py`, `app.py` y `servidor.py`
- `inputs/payload_demo.json`, `prompts/prompt_sistema.md` y archivos de requisitos
