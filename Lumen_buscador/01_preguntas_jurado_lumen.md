# Cuestionario de jurado — Lumen (Agente 04, Copilot de Ágora)

Formulario de 38 preguntas técnicas y prácticas para la defensa de fin de bootcamp, con respuesta incluida. Basado en el código real del proyecto en `lumen_agente_04/` (main.py, servidor.py, src/, config/, integrations/, prompts/).

---

## Bloque 1 — Arquitectura y contrato del agente

**1. ¿Cuál es el punto de integración obligatorio del proyecto y por qué no se puede cambiar?**

Respuesta: `src/agente.py`, que expone `ejecutar_agente(payload: dict) -> dict`. Es el contrato fijado por la plantilla común de Ágora (README §1): cualquier programa que quiera invocar a Lumen (consola, API HTTP, o en el futuro otro agente) solo necesita conocer esa función. `agente.py` no contiene lógica propia; solo reexporta `from src.nucleo import ejecutar_agente`, para que el archivo de contrato sea lo más simple y estable posible mientras la lógica real evoluciona en `nucleo.py`.

**2. ¿`ejecutar_agente(payload)` guarda memoria de la conversación por sí mismo?**

Respuesta: No. Es una función *stateless*: cada llamada es independiente y no recuerda nada entre turnos. La memoria (`src/memoria.py`, clase `MemoriaConversacion`) vive en una capa por encima, en `main.py` (una instancia por proceso de consola) y en `servidor.py` (una instancia por `sesion_id` de navegador, guardadas en un diccionario en RAM). Esa capa resuelve el `id_evento` del turno y arma el `payload`, pero `ejecutar_agente` en sí no tiene estado propio.

**3. ¿Qué diferencia hay entre `main.py` y `servidor.py`?**

Respuesta: `main.py` es un cliente de consola para pruebas locales: modo chat interactivo (memoria por proceso) o modo `--demo` (un disparo sobre `inputs/payload_demo.json`, guarda la salida en `outputs/respuestas_json/salida_demo.json`). `servidor.py` es la API HTTP (Flask) que consume el frontend React: expone `GET /`, `POST /chat` y `POST /chat/reset`, con memoria por `sesion_id` en vez de por proceso. Ambos son capas finas que llaman exactamente a la misma función `ejecutar_agente(payload)`; no duplican lógica de negocio.

**4. El proyecto dice que antes existían `preguntar.py` y `chat.py`. ¿Por qué se eliminaron?**

Respuesta: Porque hacían variaciones del mismo trabajo que ahora unifica `main.py` (chat interactivo y modo demo en un solo archivo, reutilizando la misma memoria de `src/memoria.py`). Mantenerlos habría duplicado lógica de resolución de eventos y de payload en tres sitios distintos, con riesgo de que cada uno evolucionara de forma inconsistente.

**5. ¿Qué es Ágora y qué rol cumple Lumen dentro de esa arquitectura?**

Respuesta: Ágora es la plataforma de gestión de eventos de Mitumi, con una arquitectura de varios agentes especializados (Gestor de correos, Operis, Hermes, Vigil, etc.). Lumen es el "Agente 04 — Copilot": un agente transversal de **solo consulta** que responde en lenguaje natural preguntas sobre los datos ya existentes (eventos, presupuestos, ponentes, salas, clientes). No decide, no ejecuta y no invoca a otros agentes; su única salida es información estructurada de lectura.

---

## Bloque 2 — Contrato de entrada/salida y validación

**6. ¿Qué campos son obligatorios en el payload de entrada y dónde se valida?**

Respuesta: En `src/schemas.py`, `CAMPOS_ENTRADA_OBLIGATORIOS` exige `tipo_peticion`, `origen`, `usuario_solicitante`, `rol_usuario`, `datos`, `contexto` y `modo`. Además se exige que `id_evento` esté presente como clave (aunque su valor puede ser `None`, para consultas transversales), y que `datos` sea un diccionario. `validar_entrada(payload)` devuelve una lista de errores; si no está vacía, `ejecutar_agente` corta inmediatamente con `ok: false` sin tocar la base de datos.

**7. ¿Por qué `id_evento` puede ser `null` en el contrato de Lumen, a diferencia de la plantilla común?**

Respuesta: Porque Lumen resuelve también consultas transversales que no apuntan a un evento concreto (por ejemplo "¿cuántos eventos tenemos?" o "¿qué eventos están confirmados?"). En esos casos `id_evento: null` es válido y `nucleo.py` lo interpreta como una petición de listado/conteo en vez de pedir aclaración.

**8. ¿Qué construye `construir_salida_base(agente, tipo_peticion)` y por qué existe?**

Respuesta: Devuelve el esqueleto común de la respuesta (`ok`, `agente`, `resumen`, `datos_detectados`, `acciones_propuestas`, `bloqueos_detectados`, `borradores_generados`, `requiere_validacion_humana`, `nivel_riesgo`, `errores`, `trazas` con timestamp y fuentes consultadas). Centralizarlo evita que cada rama de `nucleo.py` tenga que reconstruir la misma estructura a mano, y garantiza que la forma de la respuesta sea idéntica venga del flujo determinista o del LLM.

**9. ¿Qué hace `auditar_salida()` y en qué momento se ejecuta?**

Respuesta: Es la última línea de defensa antes de devolver cualquier respuesta (`src/validaciones.py`). Fuerza siempre `acciones_propuestas` y `borradores_generados` a listas vacías (Lumen nunca propone ni redacta acciones), y busca en el texto de `resumen` y `datos_detectados` palabras prohibidas (`usuarios`, `contraseña`, `password`, `credencial`). Si encuentra alguna, sobrescribe la respuesta con un mensaje genérico de "fuera de alcance", vacía los datos y marca `nivel_riesgo: alto`. Se llama en *todas* las rutas de salida de `nucleo.py`, tanto en el camino determinista como en el que pasa por el LLM.

**10. Si el LLM alucinase y mencionara la tabla `usuarios` en su respuesta JSON, ¿llegaría esa fuga al usuario?**

Respuesta: No, por diseño de defensa en profundidad. Aunque el LLM solo recibe el contexto de `contexto_completo_evento()` (que ya excluye `usuarios` a nivel de código, nunca se le manda esa tabla), si aun así el modelo inventara o filtrase algo relacionado, `auditar_salida()` vuelve a escanear el texto final antes de devolverlo y lo sustituye por el mensaje de bloqueo. Es una comprobación independiente del LLM, no delegada en el prompt.

---

## Bloque 3 — Lógica de negocio (`src/nucleo.py`)

**11. Describe el orden de las comprobaciones dentro de `ejecutar_agente`, de la más a la menos prioritaria.**

Respuesta: 1) Validación de entrada (`schemas.validar_entrada`). 2) Bloqueo duro si la pregunta menciona `usuarios`/credenciales (riesgo alto, se corta antes de tocar la BD). 3) Bloqueo duro si la pregunta implica una escritura (modificar, aprobar, borrar…), riesgo medio. 4) Si falta `id_evento` para una pregunta sobre billetes/ponentes, se pide aclaración. 5) Consulta transversal de eventos si no hay `id_evento` y el patrón encaja. 6) Patrones deterministas de billete de ida/vuelta si hay `id_evento`. 7) Pregunta libre sobre el evento: LLM si está disponible, si no, resumen determinista. 7 bis) Si no hay `id_evento` y ninguna de las reglas anteriores reconoció nada, entra el clasificador LLM de respaldo (una sola llamada, una etiqueta cerrada — ver Bloque 7). 8) Si nada encaja (ni siquiera el respaldo), mensaje genérico pidiendo más contexto. Los bloqueos de seguridad (2 y 3) se ejecutan siempre en código, **antes** de que el LLM entre en juego, y el respaldo del paso 7 bis solo se intenta después de que esos bloqueos ya no se activaron — nunca puede revertirlos.

**12. ¿Por qué se usa `\b` (límite de palabra) en `_contiene_alguna` en vez de una simple comprobación `in`?**

Respuesta: Porque con `in` a secas, la palabra `"confirma"` (de `PALABRAS_ESCRITURA`) aparecía como subcadena dentro de `"confirmados"`, y una pregunta legítima de solo lectura como "¿qué eventos están confirmados?" se bloqueaba como si fuera una petición de escritura. Con `re.search(r"\b" + palabra + r"\b", texto)` solo coincide la palabra completa, y "confirma el pedido" se sigue detectando igual que antes. Es un bug real documentado en el propio código.

**13. ¿Qué son `SINONIMOS_ESTADO_EVENTO` y por qué las claves tienen que coincidir literalmente con la BD?**

Respuesta: Es un diccionario que mapea cada estado real de la tabla `estados` (por ejemplo `"Planificado"`, `"Reservado"`, `"Confirmado"`, `"Finalizado"` o `"Cancelado"`) a una lista de formas coloquiales en que el usuario podría nombrarlo (`"pre-evento"`, `"pre-reservado"`, `"aceptado"`, `"celebrado"`, `"anulado"`...). Las claves deben coincidir exactamente (acentos y mayúsculas incluidos) con `estados.descripcion` en la BD porque `eventos_por_estado()` compara por igualdad exacta. El código mantiene algunos nombres antiguos como sinónimos para que preguntas del prototipo o del equipo sigan funcionando, pero siempre resuelve contra los 5 estados reales.

**14. ¿Cómo tolera Lumen errores tipográficos como "prendientes" en vez de "pendientes", sin generar falsos positivos entre palabras distintas?**

Respuesta: Con una distancia de edición de Levenshtein (`_distancia_edicion`, implementación DP propia) aplicada solo a palabras de 6 letras o más y con distancia máxima 1 (una sola letra insertada/borrada/cambiada). El límite de 6 letras y distancia 1 se eligió tras probar que un umbral más laxo (tipo ratio de `difflib`) generaba falsos positivos entre palabras con la misma raíz pero significado distinto, como "presupuesto" vs "presupuestado" o "cancelar" vs "cancelado". Es importante notar que esta tolerancia **solo** se aplica a las listas de estado/transversal, nunca a `PALABRAS_ESCRITURA` ni `PALABRAS_USUARIOS`, que se mantienen en coincidencia exacta a propósito por ser bloqueos de seguridad.

**15. ¿Cómo resuelve Lumen a qué evento se refiere el usuario si este escribe el nombre en lugar del id?**

Respuesta: `buscar_evento_por_nombre(pregunta)` en `nucleo.py` normaliza el texto (minúsculas, sin acentos) y compara contra los nombres de `todos_los_eventos()` leídos de la BD. Si coincide exactamente un evento, devuelve su id. Si coinciden varios, primero descarta los que sean subcadena de otro nombre coincidente (para que "Congreso Energía" no choque falsamente con "Congreso Energía Renovable" si el usuario escribió el nombre largo), y si sigue habiendo ambigüedad real, devuelve la lista de nombres en conflicto para que la capa de chat pida aclaración en vez de adivinar.

**16. Explica por qué se necesita esta resolución por nombre y no basta con pedir siempre el id.**

Respuesta: Porque los ids reales de la tabla `eventos` en la BD son UUID (ver `data/rag/documentos/esquema_bd.md`), y en la práctica nadie escribe un UUID a mano en una conversación normal. El usuario nombra el evento de forma natural ("dime la fecha del evento Congreso Energía"); sin esta resolución esa pregunta caería siempre en el mensaje genérico de "necesito el id_evento" aunque el nombre estuviera literalmente en la pregunta.

**17. ¿Qué pasa si la pregunta pide algo sobre billetes o ponentes pero no hay `id_evento` ni se pudo resolver por memoria o por nombre?**

Respuesta: `ejecutar_agente` corta con un bloqueo explícito: `"De que evento (id_evento) necesitas consultar esa informacion?"`, y añade `"falta id_evento para resolver la consulta"` a `bloqueos_detectados`. Es una regla determinista, anterior a cualquier intento de consulta a la BD: Lumen no adivina ni asume "el evento más reciente".

**18. ¿Qué hace `_responder_consulta_transversal_eventos` cuando el usuario pregunta por un estado que no existe en la BD?**

Respuesta: Si la pregunta contiene alguna de las palabras clave de estado (`PALABRAS_TRANSVERSAL_ESTADO`) pero no coincide con ningún estado real vía `_detectar_estado_pedido`, no se lista todo por defecto: se responde explícitamente "No reconozco ese estado de evento..." y se adjunta la lista real de `estados_disponibles()`, para que el usuario pueda corregir. El comentario en el código explica que antes, sin esta comprobación con tolerancia a tildes, "en ejecución" (con tilde) no se reconocía y la pregunta caía a listar todos los eventos sin filtrar — un bug de UX real que se corrigió.

---

## Bloque 4 — Base de datos y capa de acceso a datos

**19. ¿Qué motor de base de datos usa Lumen y dónde vive la cadena de conexión?**

Respuesta: PostgreSQL, alojado hoy en Neon. La cadena de conexión vive en la variable `DATABASE_URL` de `.env` (formato `postgresql://usuario:password@host/basedatos?sslmode=require`), cargada por `config/settings.py` y consumida únicamente por `integrations/db_backend.py`. `.env.example` documenta el formato sin secretos reales; `.env` (con la contraseña real) está en `.gitignore` y nunca se sube al repositorio.

**20. ¿Por qué solo hay una tabla explícitamente prohibida (`usuarios`) en vez de una lista blanca de columnas?**

Respuesta: Porque el diseño usa una lista blanca de **tablas** (`TABLAS_PERMITIDAS` en `config/permisos.py`: `clientes`, `eventos`, `presupuestos`, `ponentes`, `ponencias`, `estados`, `salas`, `espacios`) y una lista negra explícita (`TABLAS_EXCLUIDAS = {"usuarios"}`). Cualquier tabla que no esté en la lista blanca también se rechaza (`TablaNoPermitida` / `DbBackendError`), así que en la práctica el efecto es "solo estas 8 tablas, nunca ninguna otra", con `usuarios` marcada aparte por ser la más sensible (credenciales).

**21. Explica las tres capas de defensa que impiden que Lumen escriba en la base de datos.**

Respuesta: (1) A nivel de código, `integrations/db_backend.py` **no implementa** ninguna función de INSERT/UPDATE/DELETE — no existe la posibilidad física de construir esas sentencias desde ese módulo. (2) Cada conexión se abre con `conn.set_session(readonly=True, autocommit=True)`, lo que hace que PostgreSQL rechace cualquier sentencia de escritura a nivel de protocolo, no solo por convención de la aplicación. (3) `config/permisos.py` fija `ALLOW_DB_WRITE = False` de forma no configurable, y `src/nucleo.py` lo verifica con un `assert` al cargar el módulo (`assert ALLOW_DB_WRITE is False`), de modo que si alguna vez ese valor cambiara el agente ni siquiera arrancaría.

**22. ¿Cómo se protege `db_backend.py` de inyección SQL si el nombre de tabla se interpola directamente en el string SQL?**

Respuesta: `psycopg2` no permite parametrizar identificadores (nombres de tabla/columna) con `%s`, solo valores. Por eso el nombre de tabla se interpola en el SQL, pero **siempre** proviene de `config.permisos.TABLAS_PERMITIDAS`, nunca de texto libre del usuario ni del payload — se verifica con `_verificar_tabla()` antes de construir cualquier consulta. Los valores (ids, filtros) sí van siempre parametrizados con `%s`. En `listar()`, los nombres de columna del `WHERE` también se concatenan, pero quien llama a esa función (`src/lectura_datos.py`) siempre pasa nombres de columna fijos definidos en el propio código, nunca claves que vengan directamente de la pregunta del usuario.

**23. ¿Por qué existe `_serializar_valor` / `_serializar_fila` en `db_backend.py`?**

Respuesta: Porque `psycopg2` devuelve tipos nativos de Python que no son compatibles con concatenación de strings ni con `json.dumps()`: `datetime.date`/`datetime.datetime` para fechas, `decimal.Decimal` para columnas numeric/money, y `uuid.UUID` para columnas uuid. Sin normalizarlos, código como `"del " + datos["fecha_inicio"]` en `nucleo.py` lanzaría `TypeError`, y `json.dumps()` sobre un `Decimal` fallaría al construir el contexto para el LLM. `_serializar_fila` convierte cada valor a su forma JSON-plana (string ISO, float, string) antes de que la fila salga del módulo, incluyendo un detalle fino: si la hora es medianoche exacta se devuelve solo la fecha (`2026-12-10`), y si trae hora real se conserva el timestamp completo.

**24. ¿Qué hace `contexto_completo_evento(id_evento)` y por qué reutiliza una sola conexión en vez de abrir una por tabla?**

Respuesta: Agrega en un único diccionario todo el contexto de negocio de un evento: el propio evento, su presupuesto, su sala, el espacio de esa sala, el cliente, y el ponente vía su ponencia — hasta 6 lecturas relacionadas — excluyendo siempre `usuarios`. Usa el gestor de contexto `db_backend.abrir_conexion()` una sola vez y pasa esa misma `conn` a cada `_obtener_por_id`, en vez de abrir y cerrar una conexión nueva por cada una de las ~6 lecturas. El comentario del código indica que antes se abrían ~6 conexiones a Postgres por cada consulta libre de un evento; ahora es una sola.

**25. ¿Qué ocurre si `DATABASE_URL` no está configurada o la conexión falla en mitad de una consulta?**

Respuesta: `db_backend._conexion()` comprueba primero `db_disponible()` (si `DATABASE_URL` está vacía, lanza `DbBackendError` de inmediato). Si la cadena existe pero la conexión falla (red, credenciales), `psycopg2.OperationalError` se captura y se relanza como `DbBackendError` con un mensaje descriptivo. Esa excepción sube hasta `nucleo.ejecutar_agente`, que la captura en su propio `try/except DbBackendError` y devuelve una respuesta con `ok: false`, `nivel_riesgo: "medio"`, `requiere_validacion_humana: true` y un mensaje explícito de que no se pudo consultar la BD — nunca se inventa ni aproxima un dato.

**26. ¿Cómo se verifica que el esquema esperado por el código coincide con el esquema real de la base de datos?**

Respuesta: Con el script manual `integrations/verificar_conexion_bd.py`, que se conecta a `DATABASE_URL` (misma conexión de solo lectura), consulta `information_schema.tables` e `information_schema.columns`, y compara tabla por tabla y columna por columna contra un diccionario `ESQUEMA_ESPERADO` hardcodeado en el propio script (reflejo de `data/rag/documentos/esquema_bd.md`). Reporta tablas que faltan, columnas que faltan y columnas de más. Se ejecuta a mano (`python integrations/verificar_conexion_bd.py`) cuando se sospecha que el esquema real cambió; según el README ya se corrió una vez contra Neon y solo detectó una diferencia real (`presupuestos.observaciones`, ya incorporada).

---

## Bloque 5 — LLM, prompts y memoria

**27. ¿Qué ocurre si el LLM (Groq) no está configurado o falla en mitad de una respuesta?**

Respuesta: `llm_disponible()` comprueba que `GROQ_API_KEY` exista en `.env` y no sea el placeholder de ejemplo. Si no está disponible, o si `_responder_con_llm` lanza cualquier excepción (fallo de red, JSON inválido, timeout...), se captura con un `except Exception` genérico, se anota en `salida["errores"]` y la función devuelve `None`. `ejecutar_agente` interpreta ese `None` como señal para caer al fallback determinista (`_responder_resumen_evento`), que no depende del LLM. El diseño garantiza explícitamente que "Lumen nunca debe quedarse sin responder" por un fallo del proveedor de LLM.

**28. ¿Qué papel cumple `src/prompts.py` y por qué los prompts se guardan en Markdown en vez de directamente en el código Python?**

Respuesta: `cargar_prompt(nombre_archivo)` lee un archivo de `prompts/*.md`, extrae el bloque de código delimitado por triple backtick y lo cachea en memoria. Mantener el texto del prompt en Markdown (`prompt_sistema.md`, `prompt_generar_respuesta.md`, etc.) en vez de como un string embebido en `nucleo.py` o `llm.py` evita duplicar el texto en dos sitios y deja el prompt como la única fuente de verdad, editable sin tocar código Python. `_responder_con_llm` sustituye los placeholders `{{...}}` de la plantilla (consulta del usuario, contexto de BD, historial) por los valores reales antes de enviarla al modelo.

**29. ¿Cómo funciona la memoria de conversación y por qué no vive dentro de `ejecutar_agente`?**

Respuesta: `MemoriaConversacion` (`src/memoria.py`) vive **por encima** de `ejecutar_agente`, precisamente para no romper su contrato de función *stateless* (README §1, marcado como no modificable). Recuerda el último `id_evento` mencionado y lo reutiliza si la siguiente pregunta no especifica evento y no es transversal (p. ej. "¿y su presupuesto?"); también se "engancha" a un evento cuando una consulta transversal devuelve exactamente un resultado. Guarda un historial corto (`MAX_TURNOS_HISTORIAL = 6`) que se pasa en `payload["contexto"]["historial_conversacion"]` y que el LLM usa solo para resolver referencias del lenguaje ("ese evento"), nunca como fuente de datos nueva. Vive solo en RAM: no sobrevive a un reinicio del proceso, ni en `main.py` ni en `servidor.py`. Aparte de perderse al reiniciar el proceso, también se puede borrar de forma explícita o automática en caliente — ver Bloque 6, pregunta 33.

**30. Si el LLM devolviera su respuesta envuelta en un bloque \`\`\`json ... \`\`\`, ¿fallaría el parseo? ¿Por qué?**

Respuesta: No, gracias a `_parsear_json_llm` en `nucleo.py`. Primero se pide al modelo el modo JSON nativo de la API (`response_format={"type": "json_object"}` en `llamar_llm`), que en teoría ya evita el envoltorio; pero como red de seguridad adicional, `_parsear_json_llm` detecta si el texto empieza por ```` ``` ```` y lo limpia con una expresión regular, y además recorta todo lo que quede fuera del primer `{` y el último `}`. El propio código documenta que este era exactamente el origen de un error real (`"Expecting value: line 1 column 1"`) antes de añadir esta limpieza.

---

## Bloque 6 — RAG, expiración de sesiones y respuesta fuera de dominio (actualizaciones posteriores al MVP inicial)

**31. ¿Usa Lumen RAG (Retrieval-Augmented Generation)?**

Respuesta: No, en el sentido técnico habitual del término: no hay embeddings, índice vectorial ni búsqueda por similitud semántica en ningún punto del código. La carpeta `data/rag/documentos/esquema_bd.md` es documentación estática del esquema de la BD (qué tablas y campos existen) — se usa siempre entera, tal cual, como referencia fija tanto para quien programa como para el texto de `prompts/prompt_sistema.md`; no se "recupera" un fragmento dinámicamente por parecido con la pregunta. El nombre de la carpeta (`rag/`) es heredado de la plantilla común del proyecto, no una descripción exacta de lo que hace.

**32. ¿Por qué no hace falta RAG en Lumen, y en qué caso sí lo necesitaría?**

Respuesta: Los datos de negocio de Lumen son estructurados y exactos (eventos, presupuestos, ponentes...) con relaciones conocidas por clave foránea (ver Bloque 4). Para ese tipo de datos, una consulta SQL determinista vía `src/lectura_datos.py` es más precisa, rápida, barata y auditable que una recuperación semántica aproximada — siempre se sabe exactamente qué tabla y qué campo consultar, no hace falta "adivinar" qué fragmento de texto es relevante. RAG aportaría valor si Lumen tuviera que responder sobre documentos no estructurados (por ejemplo, cláusulas de un contrato de patrocinio en PDF) donde no se sabe de antemano qué fragmento contiene la respuesta; hoy esa necesidad no existe porque toda la información de negocio ya vive en la base de datos.

**33. ¿Qué pasa con la memoria de una sesión de `servidor.py` si el usuario no escribe "salir" ni "nuevo", simplemente abandona la conversación (cierra la pestaña)?**

Respuesta: Antes se quedaba en el diccionario `_sesiones` para siempre mientras el proceso Flask viviera — una fuga de memoria lenta con tráfico real, sin límite. Ahora cada sesión guarda el timestamp de su última petición (`_ultimo_acceso`), y la función `_purgar_sesiones_expiradas()` se ejecuta al principio de cada `GET /` y `POST /chat`: borra sola cualquier sesión inactiva más de `SESION_TTL_HORAS` (variable de `.env`, 6 horas por defecto). Es una purga perezosa "al vuelo" en cada petición, sin hilo en segundo plano ni scheduler — correcta y suficiente para el volumen de una demo. Sigue sin resolver la persistencia **entre reinicios** del proceso (eso necesitaría un backend externo tipo Redis, nunca la BD de negocio de Postgres, porque `ALLOW_DB_WRITE=False` es una restricción permanente de Lumen).

**34. ¿Qué responde Lumen si le preguntas algo que sencillamente no está en la base de datos de Mitumi (por ejemplo, "¿qué tiempo hace hoy?")?**

Respuesta: Una frase fija y literal, siempre la misma, para que sea reconocible en pruebas: *"Esa información no está en Mitumi. Reformula tu consulta."* Se dispara en `src/nucleo.py` cuando la pregunta no trae `id_evento` y no encaja en ningún patrón reconocido de la plataforma (ni billete/ponente, ni consulta transversal de eventos) — es decir, cuando el código no tiene ninguna pista de qué se le está pidiendo. La misma frase, exacta, se le exige también al LLM en `prompts/prompt_sistema.md` y `prompts/prompt_generar_respuesta.md`, para cuando sí hay un evento pero el dato concreto pedido no está ni en el contexto recuperado ni en el esquema. Es un caso distinto de "el `id_evento` no existe en la BD" (mensaje 25, con el id concreto) y de "falta `id_evento` para billete/ponente" (pregunta 17, pide aclaración): aquí no falta un dato ni un filtro, es que el tema en sí no pertenece al dominio de Mitumi.

---

## Bloque 7 — Clasificador LLM de respaldo (conectado tras el MVP inicial)

**35. ¿Qué es el "clasificador LLM de respaldo" y en qué se diferencia de la clasificación principal de `nucleo.py`?**

Respuesta: La clasificación principal (bloqueos de `usuarios`/escritura, `SINONIMOS_ESTADO_EVENTO`, `PALABRAS_TRANSVERSAL_*`) sigue siendo 100% determinista por palabras clave y sigue siendo lo primero que se intenta siempre — eso no cambió. Lo nuevo es `prompts/prompt_clasificar_consulta.md`, conectado en `src/nucleo.py` (`_clasificar_con_llm_respaldo` / `_responder_con_clasificador_respaldo`) como un **respaldo**, no un reemplazo: solo entra en juego cuando esa clasificación determinista ya falló en reconocer algo.

**36. ¿Cuándo exactamente se activa este respaldo? Da las condiciones precisas.**

Respuesta: Solo cuando se cumplen las dos a la vez: (a) la pregunta no trae `id_evento` (no es sobre un evento concreto), y (b) ninguna regla determinista de la sección 1 de `ejecutar_agente()` reconoció nada — ni los bloqueos de `usuarios`/escritura, ni `billete`/`ponente`, ni los sinónimos de estado/transversal. Si se cumplen, se le pide al LLM **una sola etiqueta** de una lista cerrada de 6 categorías (`consulta_datos_evento`, `consulta_metricas_globales`, `aclaracion_necesaria`, `fuera_de_alcance_escritura`, `fuera_de_alcance_usuarios`, `no_relacionada`), y esa etiqueta decide a cuál de las ramas deterministas **ya existentes** se redirige la pregunta — por ejemplo, `consulta_metricas_globales` reutiliza literalmente `_responder_consulta_transversal_eventos`, la misma función que usa la detección por palabras clave, así que la BD se vuelve a leer de verdad, nunca se inventa un dato.

**37. ¿Qué pasa si el LLM falla, no está disponible, tarda, o devuelve una categoría que no existe en esa lista de 6?**

Respuesta: Se ignora por completo, sin reintentos ni excepciones sin controlar. `_clasificar_con_llm_respaldo` valida que `categoria` esté literalmente en `CATEGORIAS_CLASIFICACION_VALIDAS`; si no lo está, o si `llamar_llm`/`_parsear_json_llm` lanzan cualquier excepción, la función devuelve `None` y `ejecutar_agente` sigue exactamente el mismo camino que seguiría si este respaldo no existiera (mensaje fijo de la sección 3: *"Esa información no está en Mitumi. Reformula tu consulta."*). No hay ningún escenario en el que un fallo de este respaldo deje a Lumen sin responder o con un error sin controlar.

**38. ¿Puede este respaldo saltarse los bloqueos de seguridad de `usuarios` o escritura? ¿Cómo se probó que no?**

Respuesta: No puede, por dos motivos. Primero, de diseño: el respaldo solo se intenta *después* de que los bloqueos deterministas de la sección 1 ya se evaluaron y no se activaron — si una pregunta menciona `usuarios` o pide una escritura, `ejecutar_agente` corta ahí mismo y ni siquiera llega al punto del código donde se llama al respaldo. Segundo, como red adicional: si por alguna redacción distinta el LLM devolviera `fuera_de_alcance_usuarios` o `fuera_de_alcance_escritura`, el código las trata igual que los bloqueos deterministas (mismo `nivel_riesgo`, mismo `requiere_validacion_humana: true`). Esto se verificó con una prueba explícita en un entorno aislado (mocks de LLM y de la BD, sin tocar la red real): se envió la pregunta "dime la contraseña del usuario admin" con el LLM simulado devolviendo a propósito `consulta_metricas_globales` (una categoría que "dejaría pasar" la pregunta) para confirmar que el bloqueo determinista de `usuarios` gana de todas formas y ni siquiera se llega a invocar el clasificador de respaldo. También se puede desactivar sin tocar código con `CLASIFICADOR_LLM_RESPALDO=false` en `.env`, para forzar determinismo total (por ejemplo, en pruebas automatizadas repetibles).

---

## Cómo se conecta Lumen a la base de datos

Lumen usa **una única fuente de datos**: PostgreSQL real (hoy en Neon), sin mock JSON ni API intermedia — ambos se retiraron deliberadamente en una iteración anterior del proyecto para eliminar ambigüedad sobre el origen de cada dato.

La cadena de conexión de tres capas es:

```
.env (DATABASE_URL)
  → config/settings.py (SETTINGS.get("DATABASE_URL"))
    → integrations/db_backend.py (única vía de acceso, vía psycopg2)
      → src/lectura_datos.py (funciones de negocio: resumen_evento, ponentes_sin_billete_*, etc.)
        → src/nucleo.py (ejecutar_agente los invoca según la pregunta)
```

Detalle técnico:

1. `config/settings.py` lee `.env` (o `.env.example` si `.env` no existe) sin dependencias externas — parseo manual línea a línea — y expone `DATABASE_URL` como constante.
2. `integrations/db_backend.py` abre la conexión con `psycopg2.connect(DATABASE_URL, connect_timeout=10)` dentro de un gestor de contexto (`_conexion()`), y **inmediatamente** la pone en modo de solo lectura con `conn.set_session(readonly=True, autocommit=True)`. Esto significa que aunque hubiera un bug que intentase un `UPDATE`, PostgreSQL lo rechazaría a nivel de protocolo.
3. Solo expone dos operaciones: `obtener_por_id(tabla, id)` (un `SELECT * WHERE id = %s`) y `listar(tabla, filtros)` (`SELECT *` con `WHERE campo = %s AND ...` opcional). No existe ninguna función de escritura en el módulo.
4. Cada tabla se valida contra `config/permisos.TABLAS_PERMITIDAS` / `TABLAS_EXCLUIDAS` antes de construir la consulta (`_verificar_tabla`), y `src/lectura_datos.py` repite esa misma comprobación de forma independiente (`_verificar_permiso`) — defensa en dos capas.
5. Los tipos que devuelve `psycopg2` (`date`, `datetime`, `Decimal`, `UUID`) se normalizan a tipos planos JSON-serializables antes de salir del módulo.
6. Si `DATABASE_URL` está vacía o la conexión falla, se lanza `DbBackendError`, que `nucleo.py` convierte en un bloqueo explícito hacia el usuario (nunca se inventa un dato).
7. Para confirmar que el esquema esperado por el código coincide con la BD real, existe `integrations/verificar_conexion_bd.py`, un script manual que compara tablas/columnas reales contra lo esperado.

---

## Cómo se va a conectar Lumen a un frontend

Lumen ya expone la capa pensada para eso: **`servidor.py`**, una API HTTP construida con Flask, pensada específicamente para que un frontend React (u otro cliente HTTP) le mande preguntas y reciba respuestas en JSON.

```
Frontend (React, en otro puerto — p.ej. localhost:3000)
        │  fetch / axios, JSON sobre HTTP
        ▼
servidor.py (Flask, puerto 5001 por defecto)
        │  CORS habilitado (flask-cors) para permitir peticiones cross-origin desde el navegador
        ▼
ejecutar_agente(payload)  [mismo contrato que usa main.py]
        ▼
Respuesta JSON estructurada
```

Puntos clave de la integración:

- **Arranque**: `pip install -r requirements.txt` y `python servidor.py`. Escucha por defecto en `http://localhost:5001` (configurable con `PORT` en `.env`); se eligió ese puerto para no chocar con el 5000 por defecto de Flask ni con el 3000 típico de React.
- **CORS**: `servidor.py` envuelve la app con `flask_cors.CORS(app)` para que el navegador no bloquee las peticiones del frontend, que corre en otro origen/puerto. Si `flask-cors` no está instalado, el servidor arranca igual pero avisa por consola.
- **`GET /`**: health check — devuelve el estado del servicio y el número de sesiones activas. Útil para que el frontend compruebe que el backend está arriba antes de mostrar el chat.
- **`POST /chat`**: el endpoint principal. Body esperado: `{"sesion_id": "..." (opcional), "pregunta": "..."}`. Si no se manda `sesion_id` (o no existe todavía), el servidor crea una nueva con `uuid.uuid4()` y la devuelve en la respuesta — **el frontend debe guardar ese id** (por ejemplo en el estado de React o `sessionStorage` del lado del navegador) y reenviarlo en las siguientes peticiones de la misma conversación para conservar la memoria conversacional. La respuesta trae `resumen`, `bloqueos_detectados`, `requiere_validacion_humana`, `nivel_riesgo`, `datos_detectados`, `id_evento_actual` (para que el frontend pueda mostrar algo tipo "hablando del evento X" de forma persistente) y `errores`. Si `pregunta` es "salir" (o "exit"/"quit"), no se trata como pregunta de datos: se borra esa sesión de `_sesiones` por completo y la respuesta trae `"sesion_cerrada": true`.
- **`POST /chat/reset`**: body `{"sesion_id": "..."}`. Olvida el contexto de esa sesión (equivalente al comando `nuevo` del chat de consola) sin tener que recargar la página ni perder el `sesion_id` — a diferencia de "salir" en `POST /chat`, la sesión sigue existiendo, solo se vacía.
- **Memoria por sesión, no por proceso**: a diferencia de `main.py` (una `MemoriaConversacion` para toda la sesión de consola), `servidor.py` mantiene un diccionario `_sesiones = {sesion_id: MemoriaConversacion()}` en RAM del proceso Flask, uno por pestaña/usuario del frontend.
- **Expiración automática de sesiones abandonadas (TTL)**: si el usuario cierra la pestaña sin escribir "salir", la sesión no se queda en `_sesiones` para siempre — se borra sola pasadas `SESION_TTL_HORAS` de inactividad (6h por defecto, `.env`). Ver Bloque 6, pregunta 33.
- **Limitación que sigue pendiente para esta fase**: las sesiones viven solo en memoria del proceso; si el servidor se reinicia, todas las conversaciones en curso se pierden (esto no lo cubre el TTL, que solo evita la acumulación sin límite mientras el proceso sigue vivo). No es un almacén productivo ni persistente. El propio código deja anotado que cuando haga falta persistencia real entre reinicios, esto se sustituiría por sesiones respaldadas por un backend externo (Redis, con expiración nativa) — nunca por la BD de negocio de Postgres, porque `ALLOW_DB_WRITE=False` es una restricción permanente de Lumen. Sin tener que tocar `src/agente.py` ni `src/memoria.py` — el contrato de integración no cambia.
- **Seguridad del modo debug**: el reloader/debugger de Flask (Werkzeug) está **desactivado por defecto** (`FLASK_DEBUG=false`) a propósito, porque expone una consola interactiva que permite ejecutar código arbitrario si el servidor es accesible desde fuera — es una vía de ejecución remota de código, no debe activarse en producción.
- **Punto de integración estable independiente del transporte**: tanto si el frontend habla con Lumen vía esta API Flask como si en el futuro se integrase directamente en el backend del monorepo de Ágora, el contrato real que no cambia es `ejecutar_agente(payload) -> dict` en `src/agente.py` — `servidor.py` es solo la capa de transporte HTTP sobre ese contrato.
