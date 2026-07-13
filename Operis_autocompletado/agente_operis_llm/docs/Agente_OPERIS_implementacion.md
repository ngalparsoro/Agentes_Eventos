**Conexión con el orquestador y la base de datos:** cómo invoca el backend a `ejecutar_agente(payload)` (desde `src/agente.py`) **sigue sin decidirse** (sección 8.3 — no hay orquestador). Con la base de datos, la conexión **sí está resuelta**: `agente_operis` lee la BD real (Neon Postgres) en modo **solo lectura**, usando el `kit_conexion_agentes_Nora` oficial del proyecto (mismo patrón que Lumen en producción) — nunca escribe en ella. Los bloques `evento`, `cliente` y `ponentes` reutilizan los nombres de columna reales de `Datos_alimentación_bbdd_Leire_Eduardo/*.csv`; el bloque `nota_bene` (ver sección 2) es un resumen calculado por el LLM, no una copia campo a campo de esas columnas — quien lo consuma debe interpretarlo, no volcarlo directo con un `INSERT`. Fechas en `DD/MM/AAAA`.

---

# Documentación del Agente: `agente_operis` (implementación real)

> **Versión de la documentación:** 2.1.0
> **Última actualización:** 10/07/2026
> **Autor / Equipo responsable:** Ainara / David — Data Science, The Bridge
> **Estado:** 🟢 Funcional — motor único (`llm`, Groq), conectado en modo lectura a la BD real (Neon), probado de extremo a extremo con clave real: extracción simple, actualización parcial por bloques y fusión con histórico

---

## Nota importante

Este documento es el complemento de `Agente_OPERIS.md` (que describe la arquitectura **objetivo/aspiracional** del agente: backend Node, Groq/Llama, Prisma, canal Telegram). Este documento describe, con la misma honestidad, **lo que existe hoy y funciona**: una implementación en Python, con un único motor de extracción (Groq), reestructurada el 10/07/2026 de un esquema de 6 bloques a uno de 4 bloques + **Nota Bene**, con capacidad de fusionar un briefing nuevo con el histórico de un evento ya existente.

Documentación técnica completa (código, contratos, casos de prueba) en el propio código: [`README.md`](../README.md), en la raíz de esta misma carpeta del agente. Este documento es la versión "para todo el equipo", sin necesidad de leer código.

**Regla de oro (compartida con `Agente_OPERIS.md`):** el agente **nunca escribe en la base de datos** ni inventa datos que no estén explícitos en el documento. Solo propone; una persona revisa y confirma.

---

## 1. Resumen ejecutivo

| Campo | Descripción |
|---|---|
| **Nombre del agente** | `agente_operis` — Asistente de recordatorio de eventos (extracción + actualización de briefings) |
| **Propósito en una frase** | Lee un briefing de evento (.txt, .pdf o .docx) y propone un JSON estructurado en 4 bloques (Evento, Cliente, Ponentes, Nota Bene); si se le da el histórico de un evento ya existente, fusiona el briefing nuevo con lo ya sabido. |
| **Modelo(s) LLM utilizado(s)** | `openai/gpt-oss-120b` en Groq. Único motor — el motor de reglas (gratis, regex+etiquetas) se **eliminó** el 10/07/2026 por quedar incompatible con el nuevo esquema. |
| **Tipo de agente** | Automatización de extracción y actualización de datos, dependiente de orquestador/backend (human-in-the-loop, no autónomo). |
| **Entorno de ejecución** | Local / dependiente de quien lo invoque. Sin servicio propio desplegado. |
| **Frameworks / SDK** | SDK `groq` (obligatorio, mismo SDK que usa `agente_alerta_roberto`/Vigil). |
| **Nivel de criticidad** | Bajo — el peor fallo posible es un formulario mal cumplimentado que la persona corrige antes de confirmar. No hay escritura autónoma en BD. |

> **En lenguaje llano:** es como un becario que ya no solo rellena el primer formulario de un evento nuevo — también sabe leer los apuntes anteriores del mismo evento y actualizar solo lo que ha cambiado, dejando lo demás tal cual estaba. Sigue sin guardar nada por su cuenta: siempre le pasa la propuesta a una persona para que la revise.

---

## 2. Propósito y límites del agente

### 2.1 Su cometido
- [x] **Extrae campos estructurados de un briefing en texto libre**, agrupados en 4 bloques: `evento`, `cliente` (con lista de `personas_contacto`), `ponentes`, y **`nota_bene`** — el bloque nuevo, un resumen ejecutivo "de un vistazo" que agrupa cabecera + presupuesto/servicios (4 sub-bloques: ubicación, catering, audiovisuales, otros) + información adicional (notas, requerimientos especiales, acciones pendientes, dependencias, histórico de actualizaciones).
- [x] **Actualización parcial por bloques** (`datos.bloques_a_actualizar`): el usuario puede pedir que solo se actualice, por ejemplo, `nota_bene` — el resto de bloques quedan protegidos, copiados literalmente del histórico. Verificado con Groq real.
- [x] **Fusión con histórico** (`contexto.historial_anterior`): si se le pasa el estado anterior de un evento, el LLM lo usa como base y solo actualiza lo que el documento nuevo module, destacando cambios de presupuesto ("3200€ (anterior: 2500€)") y añadiendo una entrada al histórico de actualizaciones. Verificado con Groq real.
- [x] **Prioriza siempre lo explícito del documento** — nunca inventa ni deduce.
- [x] **Marca qué campos obligatorios del bloque Evento faltan** (`_validacion.porcentaje_completado`).

### 2.2 Qué NO hace (límites explícitos)
- [x] **No escribe en la base de datos.** Solo devuelve un diccionario/JSON de propuesta.
- [x] **No inventa ni deduce datos.** Lo que no aparece explícito en el texto se queda vacío (`""`/`[]`).
- [x] **No propone eventos nuevos.** `id_evento` es obligatorio — el agente solo actualiza eventos que el backend ya haya creado.
- [x] **No hace OCR en PDFs escaneados** — depende de que el documento tenga capa de texto.
- [x] **No guarda ni carga el histórico por su cuenta.** Recibe `contexto.historial_anterior` ya cargado en el payload; quien lo guarda y se lo pasa es el backend, nunca el agente (`src/rag.py` sigue siendo un stub por este motivo).
- [x] **No funciona sin `GROQ_API_KEY`.** Sin motor de reglas de respaldo, una clave ausente o el free tier agotado detienen la extracción por completo (antes, el motor de reglas seguía disponible sin coste).

### 2.3 Casos de uso fuera del alcance de `agente_operis`
- Cumplimentar automáticamente y guardar sin revisión humana (viola la regla de oro).
- Crear un evento nuevo desde cero (necesita un `id_evento` ya existente).
- Cruzar o deducir datos entre varios documentos sin que se le pase el histórico explícitamente.
- Coordinar con otros agentes — eso corresponde a un futuro orquestador, no a este agente.
- Decidir qué campos actualizar automáticamente sin que el usuario lo indique (`bloques_a_actualizar` lo decide una persona, no el agente).

---

## 3. Inicio rápido (Quick Start)

### 3.1 Requisitos previos
```
- Python 3.10+
- paquete `groq` + clave de console.groq.com (OBLIGATORIA, ya no opcional)
- pypdf o PyPDF2 (lectura de .pdf)
- python-docx (lectura de .docx)
- streamlit (para la interfaz de prueba)
```

### 3.2 Instalación / configuración
```bash
cd agente_operis_llm
pip install -r requirements.txt
cp .env.example .env      # y rellena GROQ_API_KEY
```

### 3.3 Ejemplo realista de uso (extracción inicial)
```text
Input del usuario:
"Se trata del Congreso Anual de Innovación Digital, en Madrid, del 15
al 17 de octubre de 2026. Aforo de 350 personas. Presupuesto de 45.000
euros, pendiente de aprobación interna. Cliente: TechCorp S.L."

Proceso interno esperado:
1. Se construye el payload con id_evento (OBLIGATORIO) y datos.texto_briefing.
2. ejecutar_agente(payload) valida el contrato (motor único: llm).
3. src/llm.py llama a Groq con el esquema de 4 bloques.
4. Se calcula qué campos obligatorios del bloque Evento faltan.
5. Se devuelve la respuesta estructurada, con requiere_validacion_humana=true.

Output esperado (abreviado):
{
  "ok": true,
  "agente": "agente_operis",
  "resumen": "✅ Evento completo. Información en 3 bloques. Requiere validación humana.",
  "datos_detectados": {
    "evento": {"nombre_evento": "Congreso Anual de Innovación Digital", "...": "..."},
    "cliente": {"cliente": "TechCorp S.L.", "personas_contacto": [...], "...": "..."},
    "ponentes": [],
    "nota_bene": {
      "cabecera": {"presupuesto_total_estimado": "45.000€", "...": "..."},
      "presupuesto_servicios": {"ubicacion": {...}, "catering": {...}, "...": "..."},
      "informacion_adicional": {"acciones_pendientes": ["Aprobación interna del presupuesto"], "...": "..."}
    }
  },
  "bloqueos_detectados": [],
  "requiere_validacion_humana": true
}
```
Este ejemplo es real: es la salida medida de `main.py --demo` sobre este mismo texto, con Groq real (ver `outputs/respuestas_json/salida_demo.json`).

### 3.4 Ejemplo de actualización parcial (verificado con Groq real)
```text
Histórico previo: evento "Congreso de Prueba", presupuesto 2500€.
Documento nuevo: "El presupuesto ha subido a 3200 euros, ya confirmado."
Payload: bloques_a_actualizar=["nota_bene"], contexto.historial_anterior=<histórico>

Resultado:
- evento y cliente: COPIA EXACTA del histórico (protegidos, ni tocados).
- nota_bene.cabecera.presupuesto_total_estimado: "3200€ (anterior: 2500€)".
- nota_bene.informacion_adicional.historico_actualizaciones: nueva entrada añadida.
```

---

## 4. Lógica de decisión

Sigue siendo un agente **de un solo paso** (sin bucle de razonamiento tipo ReAct), pero ahora tiene una decisión adicional real: qué bloques actualizar y si hay histórico que fusionar.

### 4.1 Entradas que afectan a las decisiones
| Entrada | Afecta a | Ejemplo |
|---|---|---|
| Texto del briefing | Todo el resultado | El documento pegado o subido |
| `id_evento` | Obligatorio — sin él, el agente rechaza la petición | `"evt_001"` |
| `datos.bloques_a_actualizar` | Qué bloques actualiza el LLM y cuáles copia literalmente del histórico | `["nota_bene"]` |
| `contexto.historial_anterior` | Si está presente, el LLM fusiona en vez de partir de cero | Estado previo completo del evento |
| Esquema de la BD (nombres de columna reales) | Estructura de `evento`/`cliente`/`ponentes` (no de `nota_bene`, que es un resumen calculado) | CSV de `Datos_alimentación_bbdd_Leire_Eduardo/` |

### 4.2 Priorización de acciones
```
1 · Bloques protegidos (bloques_a_actualizar): copia EXACTA del histórico, nunca se tocan
2 · Lo explícito del documento nuevo, para los bloques SÍ seleccionados
3 · Lo que ya había en el histórico, si el documento nuevo no lo contradice
4 · Campo vacío (nunca se inventa un valor)
```

### 4.3 Capa de percepción
Antes de razonar, el documento (`.pdf`/`.docx`/`.txt`) se convierte a texto plano (`src/lectura_archivos.py`). La calidad de esa conversión determina el techo de la extracción — un PDF escaneado como imagen, sin capa de texto, llega casi vacío.

### 4.4 Mecanismos de fallback
- **Campo no encontrado** → `""`/`[]`, nunca se inventa.
- **Sin `GROQ_API_KEY`** → error controlado (`ValueError`). Ya no hay motor de reglas de respaldo.
- **`id_evento` ausente o vacío** → error de validación explícito, no se procesa nada.
- **`bloques_a_actualizar` con un valor no reconocido** → error de validación (`BLOQUES_VALIDOS`: `evento`, `cliente`, `ponentes`, `nota_bene`).
- **JSON inválido del LLM** → error controlado, nunca se "adivina" un JSON mal formado.

---

## 5. Modos de fallo

| Patrón de fallo | Síntoma observable | Causa probable | Posible corrección |
|---|---|---|---|
| Sin `GROQ_API_KEY` | El agente no procesa nada, en ningún caso | Ya no hay motor de reglas de respaldo | Definir la clave en `.env` |
| PDF vacío | Formulario en blanco pese a documento con contenido | PDF escaneado (imagen), sin capa de texto | Pedir documento editable o alta manual |
| Cargo/empresa del ponente mal repartidos | P. ej. cargo="premio Nobel", empresa="Química 2024" (edge case real observado) | Prosa libre con una estructura poco habitual ("premio X de Y AAAA" en vez de "cargo de Empresa") | Revisión manual — el dato entero sigue disponible, solo mal repartido entre dos campos |
| Free tier de Groq agotado (200.000 tokens/día) | Se detiene la extracción por completo | Sin motor de reglas de respaldo | Esperar al día siguiente o usar otra clave |
| Un dato suelto (teléfono, email) sin ponente asociado claro | No se asigna automáticamente | Ambigüedad real en el texto | Revisión manual |
| `bloques_a_actualizar=["nota_bene"]` sin `historial_anterior` | El bloque protegido (p. ej. evento) queda vacío, no "protegido de verdad" | No hay nada que copiar si no se manda histórico — la protección solo tiene sentido en modo actualización | Enviar siempre `historial_anterior` junto con `bloques_a_actualizar` |

---

## 6. Observabilidad

No hay logging estructurado ni trazas persistidas todavía — el agente es lo bastante simple como para depurar leyendo la respuesta completa, que siempre incluye el detalle del error si algo falla. `trazas.fuentes_consultadas` sí indica cuándo el histórico se autocargó de la BD real (`"bd:eventos(historial_anterior)"`). Logging persistente pendiente para cuando se integre con un backend real (ver sección 8.3, punto crítico sin resolver).

---

## 7. Comportamiento determinista vs. no determinista

| Componente | Determinista | No determinista | Notas |
|---|---|---|---|
| Lectura de archivo | ✅ | | |
| Extracción (motor LLM, único) | | ✅ | `temperature=0` acota la variabilidad, no la elimina del todo |
| Fusión con histórico | | ✅ | Depende de la interpretación del LLM sobre qué cambió |
| Validación y cálculo de campos pendientes | ✅ | | Solo sobre el bloque Evento |

**Cambio respecto a la versión anterior:** hasta el 10/07/2026 existía un motor de reglas 100% determinista como alternativa gratuita. Se eliminó por quedar incompatible con el nuevo esquema de 4 bloques + Nota Bene. Consecuencia práctica: `main.py --demo` (antes gratis y determinista) ahora hace una llamada real a Groq cada vez que se ejecuta, y la salida puede variar ligeramente entre ejecuciones.

---

## 8. Patrones de integración

### 8.1 Arquitectura general
```
Documento (.txt/.pdf/.docx) → texto plano
        → motor llm (Groq), con histórico (explícito o autocargado de la BD real) y/o
          bloques parciales
        → JSON estructurado (4 bloques) + % completado (solo Evento)
        → [PERSONA revisa y confirma] → backend → BD
```

### 8.2 ✅ Conexión a la BD real — resuelta el 10/07/2026

Existe un kit de conexión oficial del proyecto (`DESAFIO_MITUMI/kit_conexion_agentes_Nora/`), el mismo que usa Lumen en producción. `agente_operis` ya lo usa: `integrations/bd_backend.py` (solo lectura, lista blanca de tablas, `usuarios` excluida) y `src/lectura_bd.py` (traduce el esquema real al esquema de salida del agente). Con esto:

- `id_evento` se verifica de verdad contra la BD real, no solo como cadena no vacía.
- El histórico se **autocarga** del estado actual del evento en la BD si no llega explícito en el payload — el modo actualización ya no depende de que un backend externo lo guarde y lo pase.
- Todo con import perezoso: sin `DATABASE_URL` (hay que pedírsela a Nora) o sin el paquete `psycopg`, el agente sigue funcionando exactamente igual que antes.

**Limitación real de la BD, no del agente:** el esquema real solo permite una ponencia/ponente por evento (relación 1:1, no la tabla `evento_ponente` N:N que se asumía antes) — al fusionar con la BD, la lista `ponentes` tendrá como mucho un elemento.

### 8.3 🔴 Sigue sin resolver: cómo invoca el backend al agente

No hay orquestador ("no va a haber orquestador") y **tampoco está definido** cómo el backend invoca a `ejecutar_agente(payload)` en sí: ¿API REST?, ¿librería Python importada directamente?, ¿otro mecanismo? La conexión a BD (8.2) resuelve "qué sabe el agente sobre el evento", no esta pregunta — sigue siendo una decisión pendiente del equipo de backend, y sigue siendo un bloqueo real para pasar de "funciona en local, probado con Groq y con BD real" a "funciona integrado en producción".

### 8.4 Handoff a supervisión humana
- **Condición de handoff:** siempre. Toda propuesta pasa por revisión humana antes de guardarse (`requiere_validacion_humana: true`).
- **Interfaz de prueba:** `streamlit_app.py`, dentro de esta misma carpeta — permite subir/pegar un briefing, indicar `id_evento` (con indicador de si existe en la BD real), elegir bloques a actualizar y probar el modo actualización con el histórico real o con uno local de sesión (para pruebas sin BD).

### 8.5 Gestión de estado entre ejecuciones
El agente en sí sigue sin estado propio — pero, a diferencia de la versión de 6 bloques, **sí puede recibir y fusionar estado externo** (`contexto.historial_anterior`), ya sea explícito en el payload o autocargado de la BD real (ver 8.2). Escribir sigue siendo responsabilidad exclusiva del backend/una persona — el agente nunca escribe.

---

## 9. Herramientas y permisos (Tools / Function calling)

| Herramienta | Descripción | Permisos requeridos | Riesgo si falla |
|---|---|---|---|
| Lectura de archivo | Convierte .txt/.pdf/.docx a texto plano (`src/lectura_archivos.py`) | Lectura de archivo local | Bajo — texto vacío o parcial, detectable en revisión |
| Motor LLM (Groq, único) | Llamada a la API de Groq, `temperature=0`, salida JSON forzada, con o sin histórico/bloques parciales incrustados en el prompt | Ejecución (llamada externa) | Bajo — propuesta errónea, corregible por la persona; si falla la llamada, error controlado y ninguna extracción |
| Lectura de BD real (Neon) | `integrations/bd_backend.py` + `src/lectura_bd.py` — SOLO lectura, lista blanca de 8 tablas, `usuarios` excluida, conexión marcada `read_only` a nivel de Postgres | Cadena `agente_readonly` en `DATABASE_URL` (opcional) | Bajo — sin BD disponible, el agente funciona igual (import perezoso); nunca puede escribir (ver `config/permisos.py::ALLOW_DB_WRITE`) |

---

## 10. Seguridad y cumplimiento

- **Datos sensibles procesados:** PII de contacto (nombres, emails, teléfonos de clientes/contactos y ponentes; documento de identidad de ponentes si el briefing lo incluye).
- **Prompt injection / mitigaciones:** el texto del documento se separa del prompt de sistema (que fija las reglas y el esquema); el modelo se instruye para devolver solo JSON con claves fijas.
- **Límites de acción destructiva:** ninguna — el agente no escribe en BD ni envía nada externamente.
- **Gestión de credenciales:** `GROQ_API_KEY` vía variable de entorno / `.env` (no versionado), nunca hardcodeada. `streamlit_app.py` permite pegar una clave alternativa solo para la sesión de Streamlit (nunca se guarda en disco).
- **Histórico:** puede contener el mismo tipo de PII que el resto de bloques — quien lo almacene (el backend) hereda las mismas obligaciones de protección de datos.
- **Cumplimiento normativo aplicable:** RGPD (datos de contacto de clientes y ponentes).

---

## 11. Evaluación y monitoreo

### 11.1 Métricas clave
| Métrica | Valor medido (no estimado) | Frecuencia de revisión |
|---|---|---|
| Tasa de éxito de extracción (campos obligatorios) | *[por fijar tras uso real]* | — |
| Coste por llamada (extracción inicial, sin histórico) | Caso simple: ~$0.0015/llamada (~35 llamadas/día en free tier). Caso complejo: ~$0.0026/llamada (~25 llamadas/día en free tier). | — |

**Detalle de coste (referencia julio 2026):** `openai/gpt-oss-120b` en Groq, $0.15/1M tokens de entrada, $0.60/1M de salida. A diferencia de la ficha anterior, estos números ya **no son una estimación con `tiktoken`**: son una **medición real** (`docs/estimacion_tokens.py` hace 2 llamadas de verdad a Groq y lee `usage` de la respuesta). En ambos casos, el límite que se agota primero en el free tier sigue siendo el de tokens/día (200.000), no el de peticiones/día. Los modos de actualización (con histórico o bloques parciales) consumen más tokens de entrada que una extracción inicial, porque el prompt crece con las instrucciones adicionales y el histórico completo — no medido todavía de forma sistemática. Detalle completo en `docs/ESTIMACION_TOKENS.md`.

### 11.2 Checklist de monitoreo continuo
- [ ] **Nota de advertencia:** no hay monitoreo continuo implementado. Toda la garantía de calidad recae en la revisión humana obligatoria.

---

## 12. Casos de prueba

```text
Caso 1 (heredado de la versión de 6 bloques, sigue vigente):
Un dato suelto (email/teléfono) sin ponente asociado claro no se asigna
automáticamente al cliente ni a nadie — se deja para revisión manual.
Estado: Mitigado por diseño (mismo principio en el nuevo esquema).

Caso 2 (verificado con Groq real, 10/07/2026): Actualización parcial.
Documento: solo menciona un cambio de presupuesto.
bloques_a_actualizar=["nota_bene"], con historial_anterior de un evento
"Congreso de Prueba" con presupuesto 2500€.
Resultado obtenido: evento y cliente quedaron COPIA EXACTA del
        histórico (protegidos correctamente); nota_bene.cabecera.
        presupuesto_total_estimado pasó a "3200€ (anterior: 2500€)";
        se añadió una entrada nueva en historico_actualizaciones.
Estado: Verificado, funciona como se diseñó.

Caso 3 (bug real encontrado y corregido, 10/07/2026): prompt de sistema
incompleto.
Resultado obtenido: prompts/prompt_sistema.md se cortaba a mitad del
        bloque Cliente (sin cerrar el bloque de código del ejemplo de
        personas_contacto), sin instrucciones para Ponentes ni Nota
        Bene, y sin la instrucción de "responde solo JSON".
Resultado esperado: instrucciones completas para los 4 bloques.
Estado: Resuelto — prompt completado con las 4 secciones, instrucciones
        de formato y un ejemplo end-to-end.

Caso 4 (bug real encontrado y corregido, 10/07/2026): construir_prompt_
sistema() rompía con KeyError.
Resultado obtenido: el prompt (tanto antes como después de completarlo)
        incluye ejemplos JSON con llaves "{"/"}" literales; el código
        usaba plantilla.format(esquema=...), que interpreta CUALQUIER
        llave como marcador de sustitución -- KeyError en cuanto
        encontraba la primera llave que no fuera "{esquema}".
Resultado esperado: el prompt se construye sin error, con el esquema
        insertado correctamente.
Estado: Resuelto — se cambió a plantilla.replace("{esquema}", ...), que
        solo toca esa subcadena literal.

Caso 5 (bug real encontrado y corregido, 10/07/2026): UnicodeEncodeError
en consola de Windows.
Resultado obtenido: main.py fallaba con UnicodeEncodeError al imprimir
        el resumen del LLM (contiene emoji "✅"/"⚠️"), porque la consola
        de Windows por defecto usa cp1252, no UTF-8.
Estado: Resuelto — sys.stdout.reconfigure(encoding="utf-8") al inicio
        de main.py.
```

---

## 13. Historial de versiones del agente

| Versión | Fecha | Cambios principales | Modelo LLM usado |
|---|---|---|---|
| 1.0.0 – 1.2.0 | 09/07/2026 | Primera implementación real, esquema de 6 bloques, dos motores intercambiables (reglas + llm), fechas en `DD/MM/AAAA`, corrección de bugs de contaminación cruzada en el motor de reglas. *(Ver historial completo en versiones anteriores de este documento, en el control de versiones del repositorio.)* | `openai/gpt-oss-120b` |
| **2.0.0** | 10/07/2026 | **Reestructuración profunda:** esquema de 6 → 4 bloques (Evento, Cliente, Ponentes, **Nota Bene** nuevo); **motor de reglas eliminado** (solo `llm`); **`id_evento` ahora obligatorio** (el agente ya no crea eventos nuevos); **nuevo: actualización parcial por bloques** (`bloques_a_actualizar`) y **fusión con histórico** (`contexto.historial_anterior`, `modo_actualizacion`). Corregidos 3 bugs reales encontrados al revisar el código nuevo: prompt de sistema incompleto (se cortaba a mitad del bloque Cliente), `construir_prompt_sistema()` rompía con `KeyError` por usar `.format()` sobre un prompt con JSON de ejemplo (llaves literales), y `UnicodeEncodeError` en consola de Windows. `streamlit_app.py` reescrito completo para el nuevo esquema. `docs/estimacion_tokens.py` pasó de estimar con `tiktoken` a medir tokens reales llamando a Groq. Todo verificado de extremo a extremo con una clave real de Groq (extracción simple, actualización parcial y fusión con histórico, las tres probadas con llamadas reales). | `openai/gpt-oss-120b` |
| **2.1.0** | 10/07/2026 | **Conexión a la BD real (Neon Postgres), resuelta usando el `kit_conexion_agentes_Nora` oficial del proyecto** (el mismo patrón que usa Lumen en producción): `integrations/bd_backend.py` (solo lectura, lista blanca de 8 tablas, `usuarios` excluida) y `src/lectura_bd.py` (traduce el esquema real de la BD al esquema de salida de Operis). `id_evento` ahora se verifica de verdad contra la BD (antes solo se comprobaba que no estuviera vacío); el histórico se **autocarga** del estado actual del evento en la BD si no llega explícito en el payload — el modo actualización deja de depender de que un backend externo lo guarde y lo pase. Todo con import perezoso: sin `DATABASE_URL`/`psycopg`, el agente sigue funcionando exactamente igual que antes (probado). Encontrada y documentada una limitación real de la BD (no del agente): cada evento enlaza como mucho con una ponencia/ponente, no varios. **Pendiente:** conseguir la cadena `agente_readonly` real (hay que pedírsela a Nora) para probar contra la BD de verdad — de momento solo verificado el camino "sin BD disponible". | `openai/gpt-oss-120b` |

**Próximos pasos previstos:**
1. Pedirle a Nora la cadena de conexión `agente_readonly` y probar la integración de BD contra la base de datos real (hoy solo verificado el camino sin BD).
2. **Sigue crítico:** definir cómo invoca el backend a `ejecutar_agente(payload)` en sí (API REST, librería, u otro) — la conexión a BD resuelve la lectura de estado, no esta decisión.
3. Decidir el destino de `data/conocimiento/` (huérfano desde que se eliminó el motor de reglas: ciudades/tipos de evento/estados verificados contra la BD real, hoy sin ningún módulo que los importe).
4. Medir el consumo de tokens de los modos de actualización (con histórico / bloques parciales), no solo el de extracción inicial.
5. Si backend decide guardar su propio histórico (en vez de depender del autocargado de BD), coordinarlo con lo construido en `src/lectura_bd.py` para no duplicar lógica.

---

## 14. Referencias y recursos adicionales

- Documentación técnica completa (código, contratos, casos de prueba): [`README.md`](../README.md), en la raíz de esta misma carpeta del agente.
- Arquitectura objetivo / aspiracional: `Agente_OPERIS.md`
- Precedente real de estructura seguido: `Agente_04_Copilot_Raul/lumen_agente_04/`
- Contrato de API del proyecto: `API_Nora/api/contrato_api_eventos_2.md`
- CSV de referencia de la base de datos: `Datos_alimentación_bbdd_Leire_Eduardo/`
- Canal de soporte / contacto: Ainara / David

**Nota sobre la bandeja de correo (descartado, sigue igual):** se valoró que el agente leyera directamente una bandeja de entrada en vez de recibir el texto ya extraído de un documento. Se decidió no incluirlo; queda como posible fase futura. Sin cambios respecto a la decisión anterior.

---

## Apéndice: Checklist final antes de publicar la documentación

- [x] ¿Puede entenderla alguien que no conoce el diseño interno? — Sí; usa la misma analogía del "becario" que la ficha anterior, actualizada.
- [x] ¿Está documentado el razonamiento, no solo la API? — Sí; sección 4.
- [x] ¿Hay al menos un ejemplo real de entrada + salida? — Sí; secciones 3.3 y 3.4, ambas con datos reales medidos (no inventados), incluyendo el caso de actualización parcial.
- [x] ¿Están los modos de fallo con síntoma, causa y recuperación? — Sí; sección 5.
- [x] ¿Se puede reproducir una sesión fallida? — El motor único (`llm`) no es 100% determinista (`temperature=0` acota, no elimina la variabilidad) — ya no hay motor de reglas determinista como red de seguridad.
- [x] ¿Están marcados los componentes no deterministas y sus salvaguardas? — Sí; sección 7.
- [x] ¿Son honestos y explícitos los límites del agente? — Sí; sección 2, incluyendo el punto crítico sin resolver de cómo invoca el backend al agente (sección 8.3) y la limitación real de 1 ponente/evento en la BD (sección 8.2).
