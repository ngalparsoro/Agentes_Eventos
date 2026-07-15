# Memoria del Agente Operis — evolución y decisiones técnicas

---

## 1. Contexto y origen del agente

El agente Operis nace como parte de la arquitectura de agentes del proyecto Mitümi, una plataforma de organización de eventos desarrollada en el bootcamp de Data Science de The Bridge. Su propósito inicial era resolver un problema concreto: la fase de captación de un evento, cuando un cliente envía un briefing en texto libre (email, documento adjunto, notas) y alguien tiene que transcribir manualmente esa información a los campos del sistema.

La propuesta era diseñar un agente de propuesta — no de acción — que leyera ese briefing y devolviera un JSON estructurado con los datos del evento, para que una persona los revisara y confirmara antes de guardarlos. El agente nunca escribiría en la base de datos, nunca enviaría comunicaciones ni ejecutaría acciones externas. Su única salida sería una propuesta, y siempre con `requiere_validacion_humana = True`. Esta regla de oro se mantuvo inalterada durante toda la evolución.

El agente se desarrolló siguiendo el precedente real de `lumen_agente_04` (el agente de copilot del proyecto), con la misma estructura de "agente dependiente" definida en `Definicion_Agentes_RAUL/README_plantilla_agente_dependiente.md`. El punto de entrada único sería siempre `ejecutar_agente(payload)` desde `src/agente.py`, y el contrato de entrada/salida estaría definido en `src/schemas.py`.

---

## 2. Primera aproximación: motor de reglas

La primera implementación, documentada el 08/07/2026, optó por un enfoque determinista y gratuito: un motor de reglas basado en expresiones regulares y etiquetas explícitas del documento. El agente leía el briefing, lo convertía a texto plano (soportando `.txt`, `.pdf` y `.docx`), y extraía la información en seis bloques: Evento, Cliente, Espacio, Sala, Presupuesto y Ponentes. Las etiquetas explícitas como `"Cliente: Michelin"` tenían prioridad máxima sobre cualquier heurístico de texto libre. Si un campo no aparecía en el documento, quedaba vacío (`""`), nunca se inventaba un valor.

Este motor era 100% determinista: mismo texto de entrada, misma salida. No requería dependencias externas, ni claves de API, ni coste por uso. Se probó de extremo a extremo con `briefing_prueba.txt` y `briefing_complejo.txt`, y se verificó que el resultado fuera reproducible.

Sin embargo, durante las pruebas se detectaron varias limitaciones. La más relevante era la ambigüedad con varios ponentes: si el documento mencionaba a varios ponentes y contenía datos sueltos (email, teléfono, empresa) sin una etiqueta que los asignara a un ponente concreto, el motor de reglas no podía resolver la asignación. Un caso concreto fue un documento con "Email ponente:" y varios ponentes, donde ese email se copiaba también en el email del cliente por ser el único email del documento. Otro caso fue un briefing con bloques numerados ("Ponente 1", "Ponente 2") donde los campos `nombre_evento` y `cliente` se contaminaban con los datos del último ponente, porque los sinónimos `"nombre"` y `"empresa"` eran ambiguos. También se detectó que el bloque `espacio` era un único objeto, no una lista, lo que no modelaba bien un briefing que comparara varios espacios candidatos.

Estas limitaciones no eran bugs en el sentido estricto, sino límites de diseño de un enfoque puramente basado en reglas. Para resolverlas, el motor de reglas necesitaría una lógica de contexto mucho más compleja, lo que llevó a considerar una alternativa.

---

## 3. Segunda fase: integración del motor LLM

El 09/07/2026 se integró un segundo motor de extracción basado en un LLM de Groq (`openai/gpt-oss-120b`). El objetivo era cubrir los matices de lenguaje que el motor de reglas no podía manejar: interpretación de texto libre, comprensión de contexto, y asignación de datos a ponentes cuando el documento los describía en prosa sin etiquetas explícitas. Ambos motores compartían el mismo esquema de salida de seis bloques, lo que los hacía intercambiables desde `src/nucleo.py`. El motor de reglas seguía siendo el que se usaba por defecto, y el motor LLM se activaba explícitamente con `payload.datos.motor = "llm"`.

El motor LLM se construyó con las siguientes características: temperatura cero para minimizar la variabilidad, formato de salida JSON forzado, y un prompt de sistema que vivía en `prompts/prompt_sistema.md` (cargado en runtime con el esquema de salida insertado). La regla de oro de "nunca inventar" se reforzaba en el prompt con instrucciones explícitas: si un campo no aparece en el texto, su valor debe ser cadena vacía o lista vacía.

Se realizó una estimación de coste y tokens con `docs/estimacion_tokens.py`, usando la codificación `o200k_base` (aproximación). Un briefing simple de 1.052 caracteres costaba unos 0.000355 USD por llamada y permitía 147 llamadas/día en el free tier de Groq. Un briefing complejo de 3.642 caracteres costaba 0.001024 USD por llamada y permitía 66 llamadas/día. En ambos casos, el límite que se agotaba primero en el free tier era el de tokens/día (200.000), no el de peticiones/día (1.000).

El motor LLM se probó hasta el punto de construir correctamente la petición (prompt de sistema + esquema + texto), pero no se verificó con una clave real de Groq en ese momento.

---

## 4. Tercera fase: reestructuración a 4 bloques y Nota Bene

El 10/07/2026 se produjo una reestructuración profunda del agente. La decisión más importante fue eliminar el motor de reglas. El motivo era doble: primero, mantener dos motores duplicaba el esfuerzo de mantenimiento y testing, especialmente con un esquema de salida que iba a cambiar. Segundo, la primera prueba real con Groq (realizada ese mismo día) demostró que el motor LLM era suficientemente fiable como para ser el único motor. Como consecuencia, el agente dejó de funcionar sin `GROQ_API_KEY`.

El segundo gran cambio fue la reducción del esquema de salida: de seis bloques a cuatro. Los bloques Espacio, Sala y Presupuesto se eliminaron como bloques independientes. Su contenido no desapareció, sino que se reubicó dentro de un nuevo bloque llamado **Nota Bene**, que actuaba como un cajón de sastre para toda la información que no encajaba en Evento, Cliente o Ponentes. El objetivo era que la salida fuera más clara y que el agente funcionara como un "asistente de recordatorio": un resumen ejecutivo del evento, visible de un vistazo.

El bloque Nota Bene se estructuró en tres partes. La cabecera contenía el resumen ejecutivo: nombre del evento, estado, fecha de celebración, cliente principal, persona de contacto, presupuesto total estimado (con historial de cambios si existía) y fecha de última actualización. Los presupuestos y servicios se organizaban en cuatro sub-bloques fijos: ubicación, catering, audiovisuales y otros, cada uno con descripción, precio estimado, nota y estado. La información adicional era un cajón de sastre propiamente dicho: notas generales, requerimientos especiales, riesgos detectados, acciones pendientes, dependencias e histórico de actualizaciones.

También se eliminó la posibilidad de que `id_evento` fuera `null`. El agente ya no proponía eventos nuevos desde cero: solo actualizaba eventos que el backend ya hubiera creado. Esta decisión simplificaba el flujo y permitía el modo actualización.

Durante la implementación de esta reestructuración se encontraron y corrigieron tres bugs. El prompt de sistema se cortaba a mitad del bloque Cliente, por lo que el ejemplo de JSON quedaba incompleto y no había instrucciones para los bloques Ponentes ni Nota Bene. También se había omitido la instrucción de "responde solo JSON", lo que podía provocar respuestas con texto adicional. Por último, `construir_prompt_sistema()` usaba `.format()` para insertar el esquema, pero el prompt contenía llaves literales del ejemplo JSON, lo que provocaba un `KeyError`. Se cambió a `replace()`.

---

## 5. Cuarta fase: histórico y actualización parcial

El mismo 10/07/2026 se identificó un problema crítico: si un usuario subía un documento que solo hablaba de presupuesto, y el agente reprocesaba todo desde cero, devolvería Evento y Cliente vacíos (porque no estaban en el nuevo texto). Un backend que guardara esa respuesta perdería información ya validada. Para resolverlo, se añadió el modo actualización parcial por bloques.

El payload ahora acepta `datos.bloques_a_actualizar`, una lista opcional con los bloques que el usuario quiere actualizar. Si solo se pasa `["nota_bene"]`, el agente actualiza Nota Bene y copia literalmente Evento, Cliente y Ponentes del histórico anterior. Si no se pasa, se actualizan todos los bloques. Los valores válidos son `evento`, `cliente`, `ponentes`, `nota_bene`, y se validan en `src/validaciones.py`.

El histórico se pasa en el payload como `contexto.historial_anterior`. Si existe, el LLM lo recibe en el prompt y fusiona la información nueva sobre la existente: mantiene lo que no se contradice, actualiza lo que cambia, y destaca los cambios de presupuesto con el formato `"3200€ (anterior: 2500€)"`. También añade una entrada en `nota_bene.informacion_adicional.historico_actualizaciones`.

Se añadió un parámetro de modo de actualización: `contexto.modo_actualizacion` con valores `"fusionar"` (por defecto) o `"sobrescribir"`. En el modo fusión, el LLM mantiene la información anterior y solo añade lo nuevo. En el modo sobrescritura, reemplaza todo.

---

## 6. Conexión a la base de datos real

El 10/07/2026 se resolvió la conexión a la base de datos real (Neon Postgres). Se usó el `kit_conexion_agentes_Nora` oficial del proyecto, el mismo que usa Lumen en producción. El agente se conecta en modo solo lectura, con una lista blanca de siete tablas de negocio (clientes, eventos, presupuestos, ponentes, ponencias, salas, espacios) y la tabla `usuarios` excluida. El estado del evento se lee desde `eventos.estado`; no existe tabla `estados`. La conexión se marca como `read_only` a nivel de Postgres, no solo por convención en el código.

El histórico ahora se autocarga desde la base de datos si no viene explícito en el payload. `src/lectura_bd.py` traduce el esquema real de la BD al esquema de salida de Operis, y expone `evento_existe(id_evento)` y `construir_historial_desde_bd(id_evento)`. `id_evento` se verifica de verdad contra la BD, no solo como cadena no vacía.

Todo está diseñado con import perezoso: si no hay `DATABASE_URL` configurada o el paquete `psycopg` no está instalado, el agente funciona exactamente igual que antes, sin conexión a BD. Esto permite usarlo tanto con BD real como en modo standalone.

Se documentó una limitación real de la BD, no del agente: el esquema real solo permite una ponencia/ponente por evento (relación 1:1 a través de `eventos.id_ponencia`, no la tabla N:N que se asumía inicialmente). Al leer o fusionar con la BD real, la lista `ponentes` tendrá como mucho un elemento.

---

## 7. Quinta fase: pruebas end-to-end con `app.py`, límite de tokens por minuto y esquema ambiguo

El 12/07/2026 empezaron las pruebas de extremo a extremo con la interfaz de Streamlit,
ahora reescrita como `app.py` (sustituye a `streamlit_app.py`). La primera prueba
identificó correctamente Evento, Cliente y Ponentes al 83%, pero Nota Bene aparecía en
blanco. Un primer intento de arreglarlo a mano (ampliar mucho el prompt de sistema con un
ejemplo más elaborado, sin tocar la causa real) empeoró el resultado hasta el 63% y luego
un 0% que resultó ser un error silencioso, no una extracción vacía real. Se investigó y se
optó por revertir ambos archivos modificados (`prompts/prompt_sistema.md`, `src/llm.py`) a
la última versión probada y funcional, en vez de intentar arreglar un problema que no se
podía identificar con certeza sin gastar más cuota de la API.

Una vez restaurado, un segundo bug de Nota Bene resultó ser puramente de renderizado, no de
datos: `mostrar_nota_bene()` en `app.py` construye el HTML con f-strings multilínea que
conservan la indentación del propio código Python (4-16 espacios). Streamlit renderiza ese
HTML pasándolo primero por un parser Markdown (CommonMark), que trata cualquier línea con
4+ espacios de indentación al inicio como un bloque de código, no como HTML -- el panel se
mostraba como texto plano en vez de con estilo. Arreglado quitando la indentación línea a
línea justo antes de pasarlo a `st.markdown()`. Se confirmó explícitamente que este bug era
exclusivo de la capa de presentación de Streamlit: la salida real del agente
(`ejecutar_agente`) es JSON puro sin HTML, así que un futuro frontend en React (que no pasa
por un parser Markdown) no puede heredar este problema.

Superado esto, activar el histórico para probar el flujo completo de actualización hizo
saltar un `error 413 rate_limit_exceeded` de Groq: "Request too large ... tokens per minute
(TPM): Limit 8000, Requested 11211". A diferencia del límite de 200.000 tokens/día (que se
agota por acumulación de uso a lo largo del día), el límite TPM puede saltar con una sola
llamada si el prompt de esa llamada concreta es demasiado grande. Se investigaron tres
causas, todas corregidas el mismo día:

1. **El histórico local de sesión de `app.py` mandaba la lista completa de versiones
   acumuladas al LLM**, no solo la actual. Cada ronda de prueba sobre el mismo `id_evento`
   añadía una versión más a `historicos_por_evento[id_evento]["versiones"]`, y
   `construir_prompt_sistema()` volcaba ese diccionario entero (con `json.dumps`) en el
   prompt -- el tamaño crecía con cada ronda de prueba. Arreglado con una función nueva,
   `src/schemas.py::extraer_ultimo_estado`, que se queda solo con la última versión antes
   de construir el prompt. Con el histórico autocargado desde la BD real
   (`construir_historial_desde_bd`) esto no pasaba, porque esa función ya síntetiza una
   única "versión: el presente" cada vez -- pero limitar también el camino local a una
   versión evita el problema por completo y hace que ambos caminos se comporten igual.
2. **La protección de bloques no actualizados se le pedía al LLM en el prompt** ("copia
   este bloque tal cual del histórico"), lo que exigía mandarle el bloque completo de todas
   formas y no garantizaba que lo reprodujera bien. Se movió a Python:
   `src/nucleo.py::_proteger_bloques_no_actualizados` sobrescribe directamente los bloques
   protegidos con el último estado conocido, sin pedirle nada al LLM sobre ellos.
3. **El ejemplo JSON completo del prompt de sistema se enviaba en todas las llamadas**,
   incluidas las de actualización -- donde ya hay un ejemplo mejor disponible (la última
   versión real del propio evento). Se marcó la sección en `prompts/prompt_sistema.md` con
   `<!-- EJEMPLO_SOLO_SIN_HISTORIAL -->` y `construir_prompt_sistema()` la omite
   automáticamente cuando hay histórico.

Tras estos tres arreglos, dos briefings de prueba (`briefing_prueba.txt`,
`briefing_prueba_2.txt`) funcionaron de extremo a extremo con histórico activado. Un
tercero (`briefing_prueba_3.txt`) siguió fallando, primero por el mismo 413 (por muy poco
margen), y tras un intento adicional de recortar tokens (omitir el ejemplo JSON también en
frío cuando no hace falta), apareció un error distinto: `400 json_validate_failed`, con el
LLM devolviendo `evento` y `cliente` como arrays de valores posicionales en vez de objetos.
La causa: `src/llm.py::ESQUEMA_SALIDA` guarda listas planas de nombres de campo (uso
interno de `_fusionar_sobre_plantilla`), y esa misma estructura se le enviaba al LLM tal
cual como "la forma de tu respuesta" -- ambigua, y el modelo la interpretó como si el valor
de `"evento"` debiera ser ese array. Se separaron las dos responsabilidades: `ESQUEMA_SALIDA`
se mantuvo intacto para la fusión interna, y una función nueva,
`src/llm.py::_esquema_para_prompt`, construye la forma real (objetos anidados, listas con
un elemento de ejemplo) que es lo único que ahora ve el LLM. Con este arreglo,
`briefing_prueba_3.txt` se procesó correctamente.

De paso, al depurar la continuidad del histórico de cambios, se encontró y corrigió un
cuarto bug menor: el número de `version` de cada entrada de
`nota_bene.informacion_adicional.historico_actualizaciones` se calculaba como
`len(historial_anterior["versiones"])`, que con el histórico autocargado de la BD real
siempre vale 1 (una única "versión: el presente") -- en producción se habría quedado
clavado en `version: 2` para siempre. Se cambió a contar las entradas del propio histórico
de cambios (`len(historico_actualizaciones)`).

Sobre `servidor.py` (la capa HTTP Flask para el futuro frontend React, añadida por un
compañero de equipo vía un merge de git, no por este trabajo): llegó desalineada del
contrato de 4 bloques -- mandaba `id_evento: None` siempre (habría fallado toda petición,
porque `id_evento` es obligatorio) y validaba un motor `"reglas"` que ya no existe. Se
actualizó para exigir `id_evento` en el body, aceptar solo el motor `"llm"`, y pasar
`bloques_a_actualizar`/`historial_anterior` opcionales al payload.

---

## 8. Sugerencias técnicas descartadas

Durante el desarrollo se consideraron varias alternativas que finalmente no se implementaron por excesiva complejidad, por ser inoperantes en el contexto actual, o por quedar fuera del alcance de la fase actual.

| Sugerencia | Motivo de descarte |
|---|---|
| Conectar el agente a una bandeja de correo (IMAP o Gmail/Graph API) | Cambia el disparo de manual a automático; requiere infraestructura nueva (buzón dedicado, sondeo o webhook, deduplicación de correos ya procesados). Se decidió no incluirlo en esta iteración; queda como posible fase futura. |
| Usar RAG para el histórico | El histórico es un único documento por evento, no una base de conocimiento masiva con miles de documentos. No hay necesidad de búsqueda semántica; pasar el histórico completo en el prompt es más simple y suficiente. |
| Modelar `espacio` como lista (varios espacios candidatos) | El caso de uso de comparar varios espacios en un mismo briefing no se ha confirmado como habitual. Mantenerlo como objeto único simplifica el esquema. Si el caso se vuelve frecuente, es una ampliación posible. |
| Guardar el histórico en la BD en lugar de JSON local en el backend | Más complejo (requiere modificar el esquema de la BD real). JSON local en el backend es suficiente para la fase actual y no requiere cambios en la BD. |
| Asignación automática de datos sueltos a ponentes múltiples | Imposible resolver sin ambigüedad cuando el documento no etiqueta explícitamente a qué ponente pertenece cada dato. Se mantiene la decisión de dejar esos campos vacíos para revisión manual. |
| Mantener el motor de reglas como fallback del LLM | Se descartó porque el LLM es el motor principal y la primera prueba real demostró que es suficientemente fiable. Mantener reglas como fallback duplicaría el esfuerzo de mantenimiento para un caso de uso que ya no es necesario. |

---

## 9. Resumen de versiones y estado actual

La evolución del agente ha pasado por cinco fases principales:

| Versión | Fecha | Cambios principales |
|---|---|---|
| 1.0.0 – 1.2.0 | 09/07/2026 | Esquema de 6 bloques, dos motores (reglas + llm), corrección de bugs de contaminación cruzada y detección de ponentes. |
| 2.0.0 | 10/07/2026 | Reestructuración a 4 bloques, eliminación del motor de reglas, creación de Nota Bene, `id_evento` obligatorio, modo actualización por bloques e histórico (vía payload). |
| 2.1.0 | 10/07/2026 | Conexión a la BD real (Neon) en modo solo lectura, autocarga del histórico desde BD. |
| 2.2.0 | 12/07/2026 | Interfaz reescrita (`app.py`), corregido el bug de renderizado de Nota Bene en Streamlit, `servidor.py` alineado al contrato de 4 bloques, y resuelto el límite de tokens por minuto (TPM) del free tier de Groq: histórico reducido a la última versión, protección de bloques movida a Python, ejemplo del prompt condicionado al modo, y esquema mostrado al LLM separado del esquema interno (corrige un JSON inválido). |

El estado actual del agente es funcional y probado de extremo a extremo con Groq real en varios modos: extracción simple, actualización parcial por bloques, fusión con histórico en varias rondas seguidas sobre el mismo evento, y los tres briefings de prueba disponibles (`briefing_prueba.txt`, `briefing_prueba_2.txt`, `briefing_prueba_3.txt`). La conexión a la BD real está construida y funciona en el camino "sin BD disponible" (import perezoso); está pendiente de probar con la cadena de conexión real `agente_readonly` que debe proporcionar Nora.

Los pendientes críticos siguen siendo dos. Primero, la definición de cómo invoca el backend a `ejecutar_agente(payload)` (API REST -- hay una propuesta en `servidor.py` --, librería Python importada directamente, u otro mecanismo) sigue sin decidirse, como se documenta en la sección 8.2 de `Agente_OPERIS_implementacion.md` y en `agente_operis_llm/README.md`. Segundo, `data/conocimiento/` (ciudades, tipos de evento, estados que usaba el motor de reglas) está huérfano desde la eliminación del motor de reglas; podría reutilizarse para validar la salida del LLM o eliminarse definitivamente.