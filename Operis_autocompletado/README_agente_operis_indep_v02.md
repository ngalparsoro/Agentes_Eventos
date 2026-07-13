# Documentación del Agente: `agente_operis`

> **Versión de la documentación:** 2.0.0  
> **Última actualización:** 12/07/2026  
> **Autor / Equipo responsable:** Equipo Data Science de OPERIS, The Bridge — responsable nominal por confirmar  
> **Estado:** 🟡 Beta

---

## Nota importante

OPERIS no es software completamente determinista. Aunque utiliza temperatura `0`, una misma entrada puede producir variaciones si cambia el modelo, el proveedor, el contexto o el estado de los servicios externos.

El agente puede ejecutarse localmente de forma aislada para desarrollo y pruebas. En la arquitectura del proyecto, sin embargo, su salida sigue siendo una **propuesta**: no escribe en la base de datos, no envía comunicaciones y no ejecuta acciones externas. Toda persistencia o acción real corresponde al backend y requiere validación humana.

---

## 1. Resumen ejecutivo

| Campo | Valor |
|---|---|
| **Nombre** | `agente_operis` / OPERIS |
| **Propósito (una frase)** | Extrae información de briefings de eventos y propone una actualización JSON estructurada, fusionándola de forma segura con el estado anterior. |
| **Fase(s) del proceso que cubre** | Captación, preparación y actualización documental de eventos ya creados |
| **Modelo(s) LLM utilizado(s)** | Groq, `openai/gpt-oss-120b` por defecto |
| **Tipo de agente** | Copiloto de extracción y actualización documental |
| **Entorno de ejecución** | Local o servidor Python; acceso cloud opcional a Groq y Neon Postgres |
| **Frameworks / SDK** | SDK de Groq; Streamlit para la interfaz de prueba; Flask para la propuesta REST; `psycopg` para BD opcional |
| **Nivel de criticidad** | Medio: una extracción incorrecta puede proponer datos erróneos, pero no se persiste sin revisión |
| **Estado** | 🟡 Beta |

---

## 2. Estructura interna del agente

La implementación actual es anterior a la estructura fija propuesta en la plantilla y no coincide literalmente con ella. Mantiene, no obstante, el punto de entrada y los componentes funcionales equivalentes.

```text
agente_operis_llm/
├── README.md
├── main.py                     → prueba local por CLI
├── app.py                      → interfaz Streamlit de prueba
├── servidor.py                 → propuesta de API Flask
├── requirements.txt
├── requirements_servidor.txt
├── config/
│   ├── settings.py             → configuración y variables de entorno
│   └── permisos.py             → permisos seguros
├── prompts/
│   └── prompt_sistema.md       → instrucciones del LLM
├── src/
│   ├── agente.py               → punto de entrada público
│   ├── nucleo.py               → flujo principal
│   ├── schemas.py              → estructuras y salida
│   ├── validaciones.py         → validación de entrada
│   ├── llm.py                  → integración con Groq
│   ├── lectura_archivos.py     → lectura de TXT, PDF y DOCX
│   ├── lectura_bd.py           → traducción de BD a esquema OPERIS
│   └── rag.py                  → placeholder, sin RAG activo
├── integrations/
│   └── bd_backend.py           → PostgreSQL de solo lectura
├── inputs/
│   └── payload_demo.json
├── outputs/
│   └── respuestas_json/salida_demo.json
├── data/
│   ├── ejemplos/
│   └── conocimiento/           → legado no utilizado del motor de reglas
└── docs/
    ├── Agente_OPERIS_implementacion.md
    └── ESTIMACION_TOKENS.md
```

| Archivo actual | Equivalencia funcional |
|---|---|
| `src/agente.py` | `agente.py`: expone `ejecutar_agente(payload)` |
| `config/settings.py` y `config/permisos.py` | `parametros.py` |
| `src/nucleo.py`, `src/validaciones.py`, `src/lectura_archivos.py` | `funciones.py` |
| `src/llm.py` e `integrations/bd_backend.py` | `tools.py` |
| `src/rag.py` | `rag.py`; actualmente no implementa RAG |
| `src/schemas.py` | `schemas.py` |
| `main.py` | `pruebas.py` |
| `inputs/payload_demo.json` | `ejemplos/entrada_demo.json` |
| `outputs/respuestas_json/salida_demo.json` | `ejemplos/salida_demo.json` |

Antes de integrarlo en una estructura común deberá acordarse si se migra físicamente a `src/agents/agente_operis/` o se mantiene la organización actual.

---

## 3. Propósito y límites del agente

### 3.1 Su cometido

- [x] **Extraer briefings:** transforma texto libre procedente de emails, notas o documentos en cuatro bloques: Evento, Cliente, Ponentes y Nota Bene.
- [x] **Actualizar información existente:** fusiona un briefing nuevo con el último estado conocido del evento sin borrar datos anteriores que no hayan cambiado.
- [x] **Actualizar por bloques:** permite modificar solo `evento`, `cliente`, `ponentes` o `nota_bene`, restaurando mediante código los bloques protegidos.
- [x] **Construir un resumen ejecutivo:** Nota Bene reúne cabecera, presupuesto, servicios, requisitos, riesgos y tareas explícitamente mencionadas.
- [x] **Consultar contexto previo:** acepta histórico en el payload o intenta autocargarlo desde Neon Postgres en modo de solo lectura.
- [x] **Detectar información pendiente:** calcula completitud sobre los campos obligatorios del evento y devuelve campos vacíos o bloqueos sin inventar datos.

### 3.2 Qué NO hace

- [x] No escribe directamente en la base de datos.
- [x] No crea eventos; `id_evento` debe existir previamente.
- [x] No envía emails, mensajes ni notificaciones.
- [x] No confirma espacios, reservas, viajes, proveedores o ponentes.
- [x] No aprueba presupuestos ni cambios de fecha o estado.
- [x] No invoca a otros agentes.
- [x] No funciona sin acceso a Groq: el motor de reglas fue eliminado.
- [x] No garantiza la exactitud del LLM; siempre exige validación humana.
- [x] No realiza búsqueda semántica: RAG no está activo.

### 3.3 Casos de uso fuera de alcance

- La creación inicial y persistencia de eventos corresponde al backend.
- La negociación con espacios, catering o proveedores corresponde a los equipos o agentes de esas áreas.
- La gestión y el envío de comunicaciones corresponde a un agente de comunicación o a la capa común.
- La aprobación financiera corresponde a una persona responsable y al backend.
- La coordinación entre OPERIS y otros agentes corresponde al orquestador o servicio global.
- La comparación automática de múltiples espacios candidatos no está modelada como una función propia.

---

## 4. Inicio rápido (Quick Start)

### 4.1 Requisitos previos

```text
- Python 3 compatible con las dependencias del proyecto.
- GROQ_API_KEY válida y cuota disponible.
- Dependencias de requirements.txt.
- DATABASE_URL opcional con rol agente_readonly para consultar Neon Postgres.
- Archivos admitidos por la CLI/UI: .txt, .pdf y .docx.
```

### 4.2 Instalación y configuración

```bash
cd agente_operis_autoV2.0/agente_operis_llm
python -m venv .venv
# Activar .venv según el sistema operativo
pip install -r requirements.txt
```

Crear manualmente `.env`:

```env
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
DATABASE_URL=
```

El repositorio revisado no contiene todavía `.env.example`; debe crearse sin secretos antes de publicar el agente.

### 4.3 Ejecución y prueba local

```bash
# Payload incluido
python main.py --demo

# Archivo propio
python main.py ruta/al/briefing.pdf --id-evento evt_001

# Interfaz visual
streamlit run app.py
```

La demo llama al LLM real y consume cuota de Groq.

### 4.4 Ejemplo realista de uso

```text
Input:
"TechCorp organizará el Congreso Anual de Innovación Digital en Madrid,
del 15 al 17 de octubre de 2026, para 350 personas. Presupuesto aproximado:
45.000 euros. Contacto: Laura Martínez, laura.martinez@techcorp.es."

Proceso interno esperado:
1. Validar id_evento, tipo_peticion, modo y texto.
2. Recuperar el último estado si existe.
3. Construir el prompt con el esquema de cuatro bloques.
4. Solicitar una respuesta JSON a Groq.
5. Completar la plantilla y proteger bloques no actualizados.
6. Calcular campos pendientes y devolver una propuesta.

Output esperado:
Evento, Cliente y Nota Bene rellenos; Ponentes vacío; validación humana obligatoria.
```

---

## 5. Lógica de decisión

### 5.1 Entradas que afectan las decisiones

| Entrada | Afecta a | Ejemplo |
|---|---|---|
| `datos.texto_briefing` | Información extraída en los cuatro bloques | Fechas, cliente, presupuesto y servicios |
| `datos.bloques_a_actualizar` | Bloques que pueden cambiar | `['nota_bene']` protege Evento, Cliente y Ponentes |
| `contexto.historial_anterior` | Base de la fusión | Última versión validada del evento |
| `contexto.modo_actualizacion` | Estrategia de actualización | `fusionar` o `sobrescribir` |
| `id_evento` | Validación y consulta opcional a BD | Si la BD está activa, debe existir |
| `GROQ_MODEL` | Calidad, latencia y variabilidad | `openai/gpt-oss-120b` |
| Disponibilidad de BD | Autocarga y validación del evento | Sin BD se procesa como ejecución standalone |
| Prompt de sistema | Esquema, regla de no invención y formato | Respuesta exclusivamente JSON |

### 5.2 Priorización de acciones

OPERIS aplica reglas jerárquicas, no una puntuación:

```text
Recibir payload
  ↓
¿Cumple el contrato mínimo?
  ├─ No → devolver error estructurado
  └─ Sí
      ↓
¿Hay histórico explícito?
  ├─ Sí → usarlo; no consultar BD
  └─ No → intentar autocargar estado desde BD
      ↓
Conservar solo el último estado disponible
      ↓
¿Se indicaron bloques a actualizar?
  ├─ No → procesar los cuatro bloques
  └─ Sí → procesar la propuesta y proteger el resto en Python
      ↓
¿Modo fusionar o sobrescribir?
  ├─ fusionar → mantener datos no contradichos
  └─ sobrescribir → sustituir el contenido actualizable
      ↓
Normalizar esquema → validar → devolver propuesta
```

La prioridad de las fuentes es:

1. Nuevo briefing, para cambios explícitos.
2. Histórico explícito del payload.
3. Estado autocargado desde la BD.
4. Vacío cuando el dato no está disponible; nunca una suposición.

### 5.3 Capa de percepción

La capa de percepción convierte documentos en texto plano mediante `src/lectura_archivos.py`. Después, el LLM transforma ese texto en una representación JSON normalizada:

- Evento;
- Cliente y personas de contacto;
- lista de Ponentes;
- Nota Bene con cabecera, presupuesto/servicios e información adicional.

Los documentos subidos se tratan como datos, no como instrucciones de sistema. Aun así, el código actual no implementa una defensa específica y completa contra prompt injection documental; se considera una mejora pendiente.

### 5.4 Mecanismos de fallback

- Sin histórico explícito → intentar cargarlo desde la BD.
- Sin `DATABASE_URL`, sin `psycopg` o sin evento en BD → continuar sin histórico; no bloquear la extracción por esa causa.
- Dato ausente → cadena o lista vacía y campo pendiente; nunca inventarlo.
- Bloque excluido de la actualización → restaurarlo directamente desde el último estado mediante Python.
- JSON parcial del LLM → fusionarlo sobre la plantilla completa, conservando solo claves válidas.
- Falta de clave Groq, cuota excedida o JSON inválido → devolver error estructurado; no existe fallback por reglas.

---

## 6. Modos de fallo

| Patrón de fallo | Síntoma observable | Causa probable | Estrategia de recuperación |
|---|---|---|---|
| Configuración incompleta | `ok=false` indicando que falta `GROQ_API_KEY` | `.env` ausente o incompleto | Configurar la clave sin incluirla en Git |
| Límite TPM/cuota | Error Groq `413 rate_limit_exceeded` | Prompt grande o cuota agotada | Esperar ventana de cuota, reducir contexto y conservar solo la última versión |
| JSON inválido | Error `400 json_validate_failed` o error controlado | El modelo no respeta la estructura | Revisar esquema mostrado al LLM, prompt y respuesta original |
| Completación parcial | Campos o bloques vacíos | Briefing incompleto o respuesta parcial | Fusionar sobre plantilla y solicitar revisión humana |
| Alucinación | Fecha, precio o relación no presentes en el documento | Inferencia indebida del modelo | Comparar con fuente y BD; reforzar prompt y validaciones deterministas |
| Contaminación cliente/ponente | Datos personales asignados al bloque equivocado | Texto ambiguo con varias personas | Exigir asociaciones explícitas; dejar el dato vacío si no es inequívoco |
| Pérdida de datos en actualización | Bloque anterior aparece vacío | Reprocesamiento sin histórico o protección incorrecta | Pasar histórico y verificar `bloques_a_actualizar`; protección en Python |
| Evento inexistente | Petición rechazada cuando hay BD | `id_evento` no está registrado | Crear el evento mediante backend y repetir la extracción |
| BD no disponible | No se autocarga histórico | Falta `DATABASE_URL`, dependencia o conectividad | Continuar standalone o restaurar la conexión de solo lectura |
| Render incorrecto en Streamlit | Nota Bene aparece como código/texto plano | Indentación interpretada por CommonMark | Mantener el desindentado previo a `st.markdown()` |
| Variación entre ejecuciones | Diferencias menores con el mismo texto | Naturaleza no determinista del LLM | Fijar modelo/temperatura, guardar entradas y revisar diferencias |

---

## 7. Observabilidad

### 7.1 Estado actual

La respuesta contiene trazabilidad mínima:

```json
{
  "trazas": {
    "fuentes_consultadas": ["motor:llm"],
    "timestamp": "...",
    "modo": "propuesta"
  }
}
```

Cuando el histórico se autocarga desde la BD se añade una fuente equivalente a `bd:eventos(historial_anterior)`.

No se ha identificado en el estado revisado un sistema completo de logging con niveles `INFO`, `DEBUG` y `TRACE`, ni un panel centralizado de observabilidad.

### 7.2 Logging recomendado

| Nivel | Qué debería capturar | Precauciones |
|---|---|---|
| `INFO` | Inicio/fin, id de evento, resultado, latencia y fuente utilizada | No registrar PII completa |
| `DEBUG` | Esquema, tamaño de prompt, bloques seleccionados y respuesta técnica | Enmascarar emails, teléfonos y credenciales |
| `TRACE` | Decisiones de fusión y restauración por bloque | Solo desarrollo; no usar con datos reales sin protección |

Variable recomendada, aún no verificada como implementada:

```env
AGENT_LOG_LEVEL=INFO
```

### 7.3 Reproducción y replay

Para reproducir una sesión deben conservarse de forma segura:

- payload original;
- archivo o texto del briefing;
- último estado usado como histórico;
- modelo y temperatura;
- respuesta y error originales;
- timestamp y disponibilidad de BD;
- versión del código y del prompt.

```bash
# Sustituir temporalmente inputs/payload_demo.json por una copia anonimizada
python main.py --demo
```

Los datos personales deben anonimizarse antes de convertir una sesión real en fixture de prueba.

---

## 8. Comportamiento determinista vs. no determinista

| Componente | Determinista | No determinista | Notas |
|---|:---:|:---:|---|
| Carga de configuración | ✅ | | Mismo entorno, mismos valores |
| Validación del payload | ✅ | | Reglas explícitas en `validaciones.py` |
| Lectura de archivos | ✅ | | Depende de que el archivo sea legible |
| Consulta de BD | ✅ | | El resultado cambia si cambia la BD |
| Selección del último histórico | ✅ | | Usa la última versión disponible |
| Protección de bloques | ✅ | | Se ejecuta en Python |
| Cálculo de completitud | ✅ | | Seis campos obligatorios de Evento |
| Extracción del LLM | | ✅ | Temperatura `0` reduce, pero no elimina, la variabilidad |
| Latencia y disponibilidad de Groq/Neon | | ✅ | Servicios externos |

### 8.1 Puntos de control recomendados

- Retry limitado con backoff para fallos temporales `429`, `5xx` y conectividad.
- No reintentar automáticamente errores de contrato o falta de credenciales.
- Validar estructura y tipos tras cada respuesta del LLM.
- Comparar datos críticos —fechas, presupuesto, identidad— con el briefing o la BD.
- Exigir revisión humana antes de guardar cualquier propuesta.
- Registrar la versión del prompt y del modelo en las trazas.

---

## 9. Contrato de integración

### 9.1 Punto de entrada

```python
from src.agente import ejecutar_agente

respuesta = ejecutar_agente(payload)
```

La forma definitiva de integración con el backend —import Python, REST u otra— sigue pendiente. `servidor.py` es una propuesta Flask, no una decisión arquitectónica confirmada.

### 9.2 Contrato de entrada actual

```json
{
  "id_evento": "evt_001",
  "id_registro": null,
  "tipo_peticion": "extraer_briefing",
  "origen": "backend",
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

Restricciones actuales:

| Campo | Regla |
|---|---|
| `id_evento` | Obligatorio y no vacío; se valida contra BD cuando está disponible |
| `tipo_peticion` | Solo `extraer_briefing` |
| `datos.texto_briefing` | Obligatorio y no vacío |
| `datos.bloques_a_actualizar` | Opcional; solo los cuatro bloques conocidos |
| `contexto.historial_anterior` | Opcional; tiene prioridad sobre la BD |
| `contexto.modo_actualizacion` | `fusionar` o `sobrescribir` |
| `modo` | Solo `propuesta` |

### 9.3 Contrato de salida actual

```json
{
  "ok": true,
  "agente": "agente_operis",
  "tipo_peticion": "extraer_briefing",
  "resumen": "Resumen del resultado",
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
    "timestamp": "...",
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

La salida es siempre estructurada. `requiere_validacion_humana` permanece en `true` y `nivel_riesgo` en `bajo`, incluso cuando la extracción termina correctamente.

### 9.4 Flujo básico

```text
1. Recibir payload.
2. Validar contrato.
3. Obtener histórico explícito o intentar leer la BD.
4. Reducir el contexto al último estado.
5. Construir prompt y llamar al LLM.
6. Fusionar la respuesta sobre el esquema.
7. Restaurar los bloques protegidos.
8. Añadir histórico, completitud y trazabilidad.
9. Devolver propuesta estructurada.
```

---

## 10. Reglas obligatorias de modo seguro

- OPERIS no modifica la BD directamente.
- OPERIS no invoca a otro agente.
- Toda actualización propuesta requiere validación humana.
- La BD es la fuente de verdad del estado persistido.
- El histórico incluido en el prompt solo aporta contexto; no sustituye la BD.
- Los documentos subidos son datos, no instrucciones con autoridad.
- La salida siempre es JSON estructurado.

Permisos implementados:

```python
ALLOW_DB_WRITE = False
ALLOW_EXTERNAL_SEND = False
ALLOW_CREATE_EVENT = False
ALLOW_AUTO_APPROVAL = False
```

---

## 11. Herramientas y permisos

| Herramienta / módulo | Descripción | Permisos | Confirmación humana | Idempotente | Riesgo si falla |
|---|---|---|---|---|---|
| `leer_archivo` | Convierte TXT, PDF o DOCX en texto | Lectura local | No | Sí | Bajo |
| `extraer_briefing_llm` | Envía texto y contexto a Groq y obtiene JSON | Lectura/propuesta | Sí antes de persistir | No completamente | Medio |
| `evento_existe` | Comprueba si existe el evento | Lectura BD | No | Sí | Bajo |
| `construir_historial_desde_bd` | Traduce el estado actual de BD al esquema OPERIS | Lectura BD | No | Sí respecto al mismo estado | Medio |
| `_proteger_bloques_no_actualizados` | Restaura bloques que no deben cambiar | Transformación local | No | Sí | Medio |
| `generar_aviso_y_validacion` | Calcula completitud y campos pendientes | Transformación local | No | Sí | Bajo |

No existe ninguna herramienta con permisos de escritura en la BD o ejecución externa.

---

## 12. Seguridad y cumplimiento

- **Datos sensibles:** nombres, emails, teléfonos, documento identificativo, empresa, cargo, alojamiento, itinerarios y enlaces de ponentes o clientes. Deben tratarse como PII.
- **Credenciales:** `GROQ_API_KEY` y `DATABASE_URL` deben almacenarse en `.env` o en un gestor de secretos, nunca en código, prompts, logs o fixtures.
- **Mínimo privilegio:** la BD debe utilizar el rol `agente_readonly`, nunca `neondb_owner`.
- **Prompt injection:** separar instrucciones del sistema y contenido documental; no obedecer órdenes incluidas dentro de briefings; validar el JSON y limitar claves al esquema conocido.
- **Exfiltración:** no devolver credenciales, cadenas de conexión ni contenido ajeno al evento solicitado.
- **Acciones destructivas:** OPERIS no dispone de ellas. Guardar o aplicar la propuesta requiere confirmación humana y backend.
- **RGPD:** limitar retención, anonimizar fixtures, restringir acceso a documentos y permitir borrado según la política del proyecto.
- **Logs:** evitar almacenar prompts completos con PII en producción salvo necesidad justificada y acceso restringido.

Mejoras recomendadas: validación explícita frente a prompt injection, enmascarado de PII en logs y registro de versión de prompt/modelo.

---

## 13. Evaluación y monitoreo

### 13.1 Métricas clave propuestas

| Métrica | Objetivo inicial | Frecuencia |
|---|---:|---|
| Respuestas con JSON válido | ≥ 99 % | Semanal |
| Extracciones aceptadas sin correcciones críticas | ≥ 90 % | Semanal |
| Datos críticos inventados | 0 % | Cada ejecución / auditoría semanal |
| Bloques protegidos alterados | 0 % | Test de regresión |
| Errores de Groq por cuota/TPM | < 2 % | Diario |
| Latencia p95 | Definir tras obtener línea base | Semanal |
| Coste medio por briefing | Medir y mantener dentro del presupuesto del proyecto | Mensual |
| Casos derivados a revisión humana | 100 % antes de persistir | Continuo |

### 13.2 Estado del monitoreo

- [x] Existe trazabilidad mínima dentro de la respuesta.
- [x] Existe una estimación de tokens en `docs/ESTIMACION_TOKENS.md`.
- [ ] No consta un panel de monitoreo activo.
- [ ] No consta una suite automatizada de evaluación continua.
- [ ] No consta alertado por cuota, latencia o errores del proveedor.
- [ ] Debe definirse una colección anonimizada de briefings de evaluación.

---

## 14. Casos de prueba

```text
Caso 1 — extracción inicial:
Entrada: briefing de TechCorp con nombre, fechas, ciudad, aforo, servicios,
presupuesto y persona de contacto.
Obtenido: Evento, Cliente y Nota Bene estructurados; Ponentes vacío.
Esperado: no inventar ponentes; requiere_validacion_humana=true.
Estado: Resuelto / incluido como payload demo.
```

```text
Caso 2 — actualización parcial:
Entrada: documento que solo cambia el presupuesto, con
bloques_a_actualizar=["nota_bene"] e histórico anterior.
Obtenido: Nota Bene actualizada; Evento, Cliente y Ponentes copiados del último estado.
Esperado: ningún bloque protegido debe cambiar.
Estado: Resuelto y verificado end-to-end según memoria técnica.
```

```text
Caso 3 — fallo conocido corregido:
Entrada: histórico acumulado de varias versiones y briefing adicional.
Obtenido originalmente: error 413 de Groq por superar 8.000 TPM.
Esperado: enviar únicamente el último estado y omitir contenido redundante del prompt.
Estado: Resuelto el 12/07/2026.
```

```text
Caso 4 — esquema ambiguo corregido:
Entrada: briefing_prueba_3.txt.
Obtenido originalmente: evento y cliente como arrays posicionales; error 400.
Esperado: objetos JSON con claves nominales.
Estado: Resuelto mediante _esquema_para_prompt().
```

```text
Caso 5 — datos incompletos:
Entrada: briefing sin fecha ni aforo.
Obtenido esperado: campos vacíos y campos_pendientes; no inferir valores.
Esperado: propuesta incompleta, validación humana obligatoria.
Estado: Comportamiento previsto; debe incluirse en regresión automatizada.
```

---

## 15. Historial de versiones del agente

| Versión | Fecha | Cambios principales | Modelo LLM usado |
|---|---|---|---|
| 1.0.0–1.2.0 | 09/07/2026 | Seis bloques, motor de reglas y motor LLM; correcciones de contaminación entre campos | Groq `openai/gpt-oss-120b` y reglas |
| 2.0.0 | 10/07/2026 | Cuatro bloques, Nota Bene, eliminación de reglas, `id_evento` obligatorio, actualización parcial e histórico | Groq `openai/gpt-oss-120b` |
| 2.1.0 | 10/07/2026 | Conexión opcional de solo lectura a Neon y autocarga del estado | Groq `openai/gpt-oss-120b` |
| 2.2.0 | 12/07/2026 | Pruebas Streamlit, corrección visual de Nota Bene, reducción del histórico enviado al modelo | Groq `openai/gpt-oss-120b` |
| 2.3.0 | 12/07/2026 | Protección de bloques en Python, esquema no ambiguo para el LLM y corrección del versionado del histórico | Groq `openai/gpt-oss-120b` |

---

## 16. Referencias y recursos adicionales

- Plantilla utilizada: `Definicion_Agentes_RAUL/README_plantilla_agente_independiente.md`
- Memoria técnica principal: `agente_operis_autoV2.0/memoria_operis_barbara.md`
- Código: `agente_operis_autoV2.0/agente_operis_llm/`
- Documentación existente: `agente_operis_llm/README.md`
- Implementación: `agente_operis_llm/docs/Agente_OPERIS_implementacion.md`
- Estimación de tokens: `agente_operis_llm/docs/ESTIMACION_TOKENS.md`
- Prompt: `agente_operis_llm/prompts/prompt_sistema.md`
- Contrato demo: `agente_operis_llm/inputs/payload_demo.json`
- Panel de observabilidad: no disponible actualmente.
- Canal de soporte y responsable nominal: por confirmar.

---

## Apéndice: pendientes antes de publicar

- [x] El propósito y los límites están documentados.
- [x] La lógica de decisión y sus prioridades están documentadas.
- [x] Hay ejemplos de éxito, actualización parcial y fallos conocidos.
- [x] Los componentes no deterministas están identificados.
- [x] Se documenta el punto de entrada `ejecutar_agente(payload)`.
- [x] Se documentan seguridad, permisos y validación humana.
- [ ] Crear `.env.example` sin secretos.
- [ ] Confirmar el responsable nominal del agente.
- [ ] Decidir la integración definitiva con el backend.
- [ ] Verificar end-to-end la BD con credenciales `agente_readonly`.
- [ ] Confirmar o migrar la estructura interna fija solicitada por la plantilla.
- [ ] Implantar logging estructurado y monitoreo continuo.
- [ ] Añadir tests automatizados con fixtures anonimizados.
- [ ] Decidir si `data/conocimiento/` se reutiliza o elimina.
