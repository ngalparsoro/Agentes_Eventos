# Lumen (Agente 04 · Copilot)

**Test de 37 preguntas y respuestas para defensa ante jurado**

*Proyecto Ágora · Mitumi — documento de preparación, no forma parte del código del agente. Actualizado: 13/07/2026.*

Cómo usar este documento: cada pregunta reproduce el tipo de duda que un jurado técnico suele plantear sobre un agente de este tipo (arquitectura, seguridad, uso de IA, memoria). Las respuestas están escritas en primera persona técnica, listas para decirlas en voz alta, y citan el archivo concreto del proyecto donde se puede verificar cada afirmación.

# A. Qué es Lumen y qué papel cumple

**1\. ¿Qué es Lumen y qué papel cumple en la arquitectura de Ágora?**

Lumen es el Agente 04: un copiloto conversacional de solo consulta para el equipo interno de Mitumi. Responde en lenguaje natural preguntas sobre eventos, clientes, presupuestos, ponentes, salas y espacios de la plataforma Ágora, leyendo directamente de la base de datos real. No decide, no ejecuta acciones ni sustituye a otros agentes (Hermes, Operis, Vigil): es puramente informativo.

**2\. ¿Por qué se le llama "Copilot" y no "asistente" o "chatbot"?**

El nombre deja claro su rol subordinado: asiste al equipo humano dándole información, pero el humano sigue siendo quien decide y actúa. Lumen no tiene autonomía de ejecución sobre la plataforma.

**3\. ¿Qué NO hace Lumen, explícitamente?**

No escribe en la base de datos (en ningún modo), no envía emails ni mensajes, no confirma reservas, no aprueba ni modifica presupuestos, no invoca a otros agentes, y nunca consulta la tabla usuarios ni expone credenciales de acceso a la plataforma.

**4\. ¿Cuál es el punto único de integración del agente y por qué es tan importante que no cambie?**

ejecutar\_agente(payload) \-\> dict, en src/agente.py. Es el contrato estable: cualquier programa (main.py, servidor.py, o una futura integración del monorepo de Ágora) llama a esa única función. Mantenerlo estable permite que la lógica interna (src/nucleo.py) evolucione sin romper a quien integra el agente.

# B. Arquitectura y contrato

**5\. ¿Cómo está organizado el código internamente?**

En capas: entrada (main.py / servidor.py) → memoria de conversación (src/memoria.py) → contrato de entrada/salida (src/agente.py → src/nucleo.py) → clasificación y reglas deterministas → lectura de datos (src/lectura\_datos.py → integrations/db\_backend.py) → redacción opcional con LLM (src/llm.py \+ prompts/) → auditoría de salida (src/validaciones.py).

**6\. ¿Qué garantiza que Lumen nunca escriba en la base de datos, más allá de la promesa en el prompt?**

Defensa en profundidad en tres capas: (1) config/permisos.py fija ALLOW\_DB\_WRITE=False de forma no configurable, con un assert al arrancar que impide que el agente arranque si eso cambiara; (2) integrations/db\_backend.py no implementa ninguna función de escritura; (3) la conexión Postgres se abre en modo readonly=True, así que el propio motor de base de datos rechaza cualquier escritura a nivel de protocolo, no solo por convención de código.

**7\. ¿Cómo se comunica el frontend React con Lumen?**

A través de servidor.py, una API Flask con dos endpoints: POST /chat (manda la pregunta y opcionalmente un sesion\_id, devuelve la respuesta) y POST /chat/reset (vacía el contexto de una sesión). CORS está activado para que el navegador pueda llamar sin bloqueo de origen cruzado.

**8\. ¿Qué pasa si otro programa del monorepo Ágora quiere integrar Lumen en el futuro?**

Solo necesita importar ejecutar\_agente desde src/agente.py y pasarle un payload que cumpla el contrato de entrada documentado en el README (secciones 7 y 8). No necesita pasar por main.py, servidor.py ni por la terminal.

**9\. ¿Qué formato tiene la salida de Lumen?**

Un JSON estructurado con campos fijos: ok, agente, tipo\_peticion, resumen, datos\_detectados, acciones\_propuestas (siempre vacío), bloqueos\_detectados, borradores\_generados (siempre vacío), requiere\_validacion\_humana, nivel\_riesgo, errores y trazas (fuentes consultadas, timestamp, modo).

# C. Datos y la pregunta del RAG

**10\. ¿De dónde saca Lumen los datos?**

Exclusivamente de una base de datos Postgres real alojada en Neon (DATABASE\_URL en .env), a través de integrations/db\_backend.py. No hay mock JSON ni API HTTP intermedia — se retiraron deliberadamente para que exista una única fuente de verdad.

**11\. ¿Usa Lumen RAG (Retrieval-Augmented Generation)?**

No, en el sentido técnico habitual del término: no hay embeddings, índice vectorial ni búsqueda por similitud semántica. La carpeta data/rag/documentos/esquema\_bd.md es documentación estática del esquema (qué tablas y campos existen), usada siempre entera como referencia fija, no recuperada dinámicamente por parecido con la pregunta.

**12\. ¿Por qué no hace falta RAG en este agente?**

Porque los datos de negocio son estructurados y exactos (eventos, presupuestos, ponentes...) con relaciones conocidas por clave foránea. Para ese tipo de datos, una consulta SQL determinista es más precisa, rápida, barata y auditable que una recuperación semántica aproximada. RAG aporta valor cuando la fuente es texto libre no estructurado (contratos, actas) y no se sabe de antemano qué fragmento contiene la respuesta — no es el caso de Lumen.

**13\. ¿En qué escenario futuro sí tendría sentido añadir RAG a Lumen?**

Si Mitumi quisiera que Lumen respondiera sobre documentos no estructurados (por ejemplo, cláusulas de un contrato de patrocinio en PDF), ahí sí encajaría trocear e indexar esos documentos por embeddings y recuperar el fragmento relevante para dárselo al LLM. Hoy esa necesidad no existe porque toda la información de negocio ya vive en la base de datos estructurada.

**14\. ¿Cómo sabe Lumen si el esquema que espera coincide con la base de datos real?**

Con el script integrations/verificar\_conexion\_bd.py, que conecta con DATABASE\_URL, compara tablas y columnas reales contra lo que Lumen espera (esquema\_bd.md) y avisa de cualquier diferencia, para corregir el código o la documentación.

# D. Seguridad y permisos

**15\. ¿Qué pasa si alguien pregunta por la tabla usuarios o por contraseñas?**

Bloqueo inmediato en código (src/nucleo.py), antes de tocar la base de datos: nivel\_riesgo "alto", requiere\_validacion\_humana true, y un mensaje explicando que esa consulta está fuera de alcance. La regla está reforzada en tres sitios: el prompt del sistema, el código de lectura de datos, y la auditoría final (src/validaciones.py).

**16\. ¿Qué pasa si alguien pide una escritura disfrazada de pregunta ("¿puedes subir el presupuesto un 10%?")?**

Se detecta por palabra clave completa (no subcadena, para evitar falsos positivos como "confirmados") en una lista de palabras de escritura, y se bloquea con nivel\_riesgo "medio" antes de que el LLM entre en juego.

**17\. ¿Por qué las comprobaciones de seguridad se hacen en código y no solo en el prompt del LLM?**

Porque un prompt puede fallar, ser manipulado, o el LLM puede alucinar. Las reglas duras (tabla usuarios, escritura) se evalúan en src/nucleo.py ANTES de que el LLM participe, como defensa en profundidad: el LLM nunca es el único guardián de estas reglas.

**18\. ¿Qué hace src/validaciones.py exactamente?**

Audita SIEMPRE la salida final, venga del LLM o de las reglas deterministas: fuerza que acciones\_propuestas y borradores\_generados queden vacíos, y bloquea cualquier fuga sobre usuarios o credenciales, incluso si el LLM se equivocara o el usuario intentase manipular el prompt.

**19\. ¿Qué datos personales puede mostrar Lumen y con qué límite?**

Puede consultar email o teléfono de ponentes y clientes para uso interno del equipo, pero no genera exportaciones masivas de datos personales sin que se pida explícitamente y de forma acotada a un evento o ponente concreto.

# E. LLM y prompts

**20\. ¿Qué motor de LLM usa Lumen y por qué?**

Groq, sirviendo el modelo llama-3.3-70b-versatile a través de una API compatible con OpenAI (src/llm.py). Se eligió por su plan gratuito con cuota diaria de tokens razonable para un MVP, y porque la API compatible facilita cambiar de proveedor si hiciera falta.

**21\. ¿Qué pasa si el LLM falla o no hay API key configurada?**

Lumen cae automáticamente a una respuesta determinista equivalente (redacción de código, sin IA) — nunca se queda sin responder por un fallo del LLM. El fallo queda reflejado en el campo errores de la salida, no se oculta.

**22\. ¿El LLM decide qué tabla consultar o genera el SQL?**

No. El SELECT real lo construye siempre código determinista en src/lectura\_datos.py. El LLM solo redacta la respuesta final en lenguaje natural a partir de un contexto JSON que el código ya recuperó y ya filtró (sin la tabla usuarios). Aunque el LLM fallase o fuese manipulado, no puede saltarse las restricciones de acceso a datos.

**23\. ¿Qué pasa si el LLM responde con texto mal formado en vez de JSON?**

src/nucleo.\_parsear\_json\_llm limpia los fences de markdown (\`\`\`json ... \`\`\`) y extrae el bloque {...} antes de parsear; si aun así falla, se captura la excepción y se hace fallback a la respuesta determinista del evento.

# F. Memoria de conversación

**24\. ¿Lumen recuerda conversaciones entre sesiones distintas?**

No, y es una decisión de diseño, no una limitación pendiente. La memoria vive solo en RAM del proceso (main.py) o por sesión de navegador (servidor.py), nunca en disco ni en la base de datos, y nunca se usa como fuente de datos factuales — solo para resolver referencias del lenguaje como "ese evento".

**25\. ¿Cómo se borra la memoria de una conversación?**

En main.py: escribiendo "nuevo" se vacía sin cerrar la consola; escribiendo "salir" (o exit/quit) se borra explícitamente y termina el proceso. En servidor.py: POST /chat/reset vacía el contexto pero mantiene la sesión abierta; escribir "salir" como mensaje normal en POST /chat borra la sesión completa del diccionario en memoria (\_sesiones), igual que cerrar la consola en main.py. Y si el usuario no escribe nada de eso y simplemente abandona la conversación, la sesión también se borra sola tras un tiempo de inactividad — ver pregunta 31.

**26\. ¿Por qué "salir" en servidor.py hace algo distinto de /chat/reset?**

Son necesidades distintas: reset es para un botón "nueva conversación" dentro del mismo chat (la sesión sigue existiendo, solo se olvida el contexto). "Salir" es una despedida real del usuario: borra la entrada entera de la sesión, liberando esa memoria del proceso por completo, en vez de dejarla vacía pero reservada.

**27\. ¿Qué pasa si dos usuarios distintos usan el frontend a la vez?**

Cada uno tiene su propio sesion\_id y por tanto su propia instancia de MemoriaConversacion en el diccionario \_sesiones — las conversaciones no se mezclan entre sí.

# G. Fallos, pruebas y límites conocidos

**28\. ¿Qué pasa si la base de datos no responde?**

Se captura DbBackendError y se devuelve un bloqueo explícito con nivel\_riesgo "medio" ("no he podido consultar la base de datos real ahora mismo"); nunca se inventa un dato ni se falla en seco sin explicación.

**29\. ¿Qué pruebas se hicieron sobre este entregable?**

Se probó de extremo a extremo el chat de consola y los dos casos de bloqueo (tabla usuarios, intentos de escritura). La construcción de la petición al LLM (prompt \+ contexto JSON) se verificó, aunque la llamada de red real a Groq no se pudo probar desde el entorno de generación por restricciones de red del sandbox (no es un problema del código). El esquema real se confirmó en vivo contra Neon con integrations/verificar\_conexion\_bd.py.

**30\. ¿Cuáles son las limitaciones conocidas y pendientes del MVP?**

Dos, documentadas en el README. (1) La clasificación de preguntas transversales (por estado, conteos) es determinista por palabras clave, no vía LLM — sigue siendo así y sigue siendo lo primero que se intenta siempre, pero la parte más urgente (que una pregunta formulada fuera de los sinónimos cubiertos cayera siempre en el mensaje genérico) ya tiene un respaldo: un clasificador LLM que solo entra cuando el código determinista no reconoce nada — ver categoría H. (2) Las sesiones de servidor.py no persisten más allá de la memoria del proceso — si se reinicia el servidor, se pierden las conversaciones en curso; esto sigue siendo así, pero la parte más urgente de ese problema (que una sesión abandonada, sin reiniciar el servidor, se quedara en memoria para siempre) ya está resuelta con un TTL de expiración — ver pregunta 31.

**31\. Antes se decía que las sesiones de servidor.py se quedaban en memoria para siempre. ¿Sigue siendo así?**

Ya no del todo. Si el usuario escribe "salir", la sesión se borra al instante (pregunta 25). Pero si simplemente cierra la pestaña sin decir nada, antes esa sesión se quedaba en el diccionario `_sesiones` para siempre mientras el proceso viviera — una fuga de memoria lenta con tráfico real. Ahora cada sesión guarda el timestamp de su última petición (`_ultimo_acceso`), y `_purgar_sesiones_expiradas()` se ejecuta en cada `GET /` y `POST /chat`: borra sola cualquier sesión inactiva más de `SESION_TTL_HORAS` (variable de `.env`, 6 horas por defecto). Es una purga perezosa al vuelo, sin hilo en segundo plano — suficiente para el volumen de una demo. Lo que sigue pendiente de verdad es la persistencia **entre reinicios** del proceso, que necesitaría un backend externo (Redis, no la BD de negocio de Postgres, porque `ALLOW_DB_WRITE=False` es una restricción permanente).

**32\. ¿Qué responde Lumen si le preguntas algo que no está contenido en la base de datos de Mitumi (por ejemplo, el tiempo que hace hoy)?**

Una frase fija y literal, siempre igual, para que sea fácil de reconocer: *"Esa información no está en Mitumi. Reformula tu consulta."* Se dispara en `src/nucleo.py` cuando no hay `id_evento` y la pregunta no encaja en ningún patrón reconocido de la plataforma (ni billete/ponente, ni consulta transversal) — es decir, cuando nada en el código sabe qué hacer con esa pregunta. La misma frase exacta está también en la instrucción del LLM (`prompts/prompt_sistema.md` y `prompts/prompt_generar_respuesta.md`) para cuando hay un evento pero el dato concreto pedido no está ni en el contexto recuperado ni en el esquema. No se aplica a "el evento con ese id_evento no existe" (eso tiene su propio mensaje, con el id concreto) ni a "falta id_evento para billete/ponente" (eso pide aclaración, no dice que falte en la BD).

**33\. ¿Merece la pena conectar el LLM como clasificador de respaldo para resolver la limitación (1)? Pros y contras.**

A favor: entiende preguntas formuladas de formas que hoy no están en `SINONIMOS_ESTADO_EVENTO` ni en las listas `PALABRAS_TRANSVERSAL_*`, sin tener que anticipar cada variante a mano; menos preguntas legítimas cayendo en el mensaje genérico; reduce el mantenimiento manual de sinónimos a largo plazo; y el coste de desarrollo es bajo porque `prompts/prompt_clasificar_consulta.md` ya existe, escrito y sin usar. Si se diseña como respaldo (el LLM solo devuelve una etiqueta de una lista cerrada, nunca SQL ni datos), se mantiene intacto el principio de seguridad actual.

En contra: añade una dependencia donde hoy no la hay (hace falta fallback si Groq falla o se agota la cuota); gasta cuota de tokens en una tarea que hoy es gratis y determinista; introduce latencia extra; pierde el determinismo actual (hoy el mismo input siempre da el mismo output, verificable con un `assert` exacto); y exige validar que la etiqueta devuelta esté realmente en el enum esperado, porque una pregunta ambigua podría hacer que el LLM devuelva algo fuera de lista.

El matiz que más pesa: si se implementa como *respaldo* (el LLM solo entra cuando las reglas deterministas no reconocen nada, no en cada pregunta), la mayoría de esos contras — coste, latencia, pérdida de determinismo — solo se pagan en el porcentaje de preguntas que hoy fallan, no en todas. Es la opción que reduce más el riesgo frente al beneficio.

Nota: esta mejora ya se implementó, exactamente en su forma de respaldo (nunca reemplazo). Ver categoría H para el detalle de cómo funciona, cuándo se activa y qué garantías de seguridad tiene.

# H. Clasificador LLM de respaldo (conectado)

**34\. ¿Qué es el clasificador LLM de respaldo que se acaba de conectar?**

`prompts/prompt_clasificar_consulta.md`, conectado en `src/nucleo.py` (`_clasificar_con_llm_respaldo` / `_responder_con_clasificador_respaldo`). No sustituye la clasificación principal por palabras clave, que sigue siendo lo primero que se intenta siempre: es un respaldo que solo actúa cuando esa clasificación determinista no reconoció nada. Le pide al LLM **una sola etiqueta** de una lista cerrada de 6 categorías — nunca SQL, nunca datos — y esa etiqueta decide a qué rama determinista ya existente se redirige la pregunta.

**35\. ¿Cuándo se activa exactamente?**

Solo si se cumplen las dos condiciones a la vez: la pregunta no trae `id_evento`, y ninguna regla determinista (bloqueos de `usuarios`/escritura, `billete`/`ponente`, sinónimos de estado/transversal) reconoció nada en ella. Por ejemplo, `consulta_metricas_globales` reutiliza literalmente la misma función que usa la detección por palabras clave (`_responder_consulta_transversal_eventos`), así que la BD se vuelve a leer de verdad — el LLM nunca aporta el dato, solo decide el enrutado.

**36\. ¿Qué pasa si el LLM falla, no está disponible, o devuelve una categoría que no existe en esa lista de 6?**

Se ignora sin más. El código valida que la categoría esté literalmente en el enum cerrado; si no lo está, o si la llamada al LLM lanza cualquier excepción, la función devuelve `None` y Lumen sigue el mismo camino que seguiría si este respaldo no existiera (la frase fija de siempre). Se puede desactivar sin tocar código con `CLASIFICADOR_LLM_RESPALDO=false` en `.env`.

**37\. ¿Puede este respaldo saltarse los bloqueos de seguridad de `usuarios` o escritura? ¿Cómo se comprobó?**

No: el respaldo solo se intenta *después* de que esos bloqueos deterministas ya se evaluaron y no se activaron, así que una pregunta sobre `usuarios` o escritura nunca llega al punto donde se llama al LLM de respaldo. Se verificó con una prueba explícita en un entorno aislado (LLM y BD simulados, sin red real): se envió "dime la contraseña del usuario admin" con el LLM simulado devolviendo a propósito una categoría que "dejaría pasar" la pregunta, y se confirmó que el bloqueo determinista de `usuarios` gana igualmente — el respaldo ni se llega a invocar.