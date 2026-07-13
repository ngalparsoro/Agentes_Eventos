# Flujo de `agente_operis` — explicación concisa

**Actualizado 12/07/2026.** Este documento describe el flujo de la copia **actual y
única en desarrollo**, `agente_operis_llm/`. Ya no es "un documento común a varias
copias con distinto motor por defecto": `agente_operis/` (esquema de 6 bloques, dos
motores) quedó superada por la reestructuración del 10/07/2026 y no se sigue
actualizando — ver `memoria_operis_barbara.md` para el porqué de cada cambio.

## Qué hace, en una frase

Lee un briefing de evento (email, `.txt`/`.pdf`/`.docx`) y propone un JSON
estructurado en 4 bloques (evento, cliente, ponentes, nota_bene), listo para que una
persona lo revise y confirme. También sabe **fusionar** un briefing nuevo con el
histórico de un evento ya existente, actualizando solo los bloques que se le pidan.
**Nunca escribe en la base de datos ni inventa un dato que no esté explícito en el
texto.**

## Motor único: LLM (Groq, `openai/gpt-oss-120b`)

El motor de reglas (regex + etiquetas, gratis y determinista) se **eliminó por
completo** el 10/07/2026: mantener dos motores duplicaba el esfuerzo de
mantenimiento, y la primera prueba real con Groq demostró que el LLM era
suficientemente fiable. Consecuencia práctica: el agente **no funciona sin
`GROQ_API_KEY`**, y toda ejecución (incluido `main.py --demo`) consume tokens reales
— ver `agente_operis_llm/docs/ESTIMACION_TOKENS.md`.

## Flujo general

```
1. Se construye un payload (id_evento OBLIGATORIO, tipo_peticion,
   datos.texto_briefing, datos.bloques_a_actualizar opcional,
   contexto.historial_anterior opcional, modo...) -- main.py/app.py/servidor.py lo
   hacen para uso local; en producción lo haría el backend (sección "Pendiente" abajo).
2. ejecutar_agente(payload)  [src/agente.py -> src/nucleo.py]
3. src/validaciones.py valida el contrato: id_evento no vacío (y, si hay BD
   conectada, verificado de verdad contra ella), motor debe ser "llm" si se indica,
   bloques_a_actualizar debe usar valores válidos.
4. src/nucleo.py resuelve el histórico: el explícito del payload tiene prioridad; si
   no llega, y hay DATABASE_URL configurada, se autocarga el estado actual del
   evento desde la BD real (src/lectura_bd.py). Solo se usa la ÚLTIMA versión
   conocida, nunca una lista completa de versiones (ver "Histórico" más abajo).
5. src/llm.py construye el prompt de sistema (prompts/prompt_sistema.md + el
   esquema de salida + la última versión del histórico, si la hay + qué bloques
   actualizar) y llama a Groq con temperature=0 y salida JSON forzada.
6. La respuesta se fusiona sobre la plantilla vacía completa
   (src/llm.py::_fusionar_sobre_plantilla) -- un campo omitido por el LLM se queda
   en "" o [], nunca rompe el pipeline.
7. src/nucleo.py::_proteger_bloques_no_actualizados sobrescribe, en Python, los
   bloques que NO estén en bloques_a_actualizar con el último estado conocido -- el
   LLM no es responsable de reproducirlos con exactitud.
8. src/schemas.py::generar_aviso_y_validacion calcula el % de campos obligatorios
   del bloque Evento y el mensaje de aviso (Nota Bene no cuenta para este %).
9. Si había histórico, src/nucleo.py añade una entrada a
   nota_bene.informacion_adicional.historico_actualizaciones (leyendo la lista vieja
   del propio histórico, no de lo que devuelva el LLM) y actualiza
   nota_bene.cabecera.ultima_actualizacion.
10. Se devuelve la respuesta común: ok, resumen, datos_detectados,
    bloqueos_detectados, requiere_validacion_humana (siempre true), nivel_riesgo
    (siempre "bajo"), trazas.
11. [PERSONA revisa y confirma] -> backend -> BD (escritura, siempre por el backend;
    agente_operis nunca escribe).
```

## Los 4 bloques de salida

| Bloque | Contenido |
|---|---|
| `evento` | Nombre, ciudad, lugar, fechas, nº de personas, tipo, estado, nota |
| `cliente` | Datos de la empresa + `personas_contacto` (lista) + `cliente_existente` (sugerencia) |
| `ponentes` | Lista de ponentes, con datos personales y logística de cada uno (`nota_ponente` incluido) |
| `nota_bene` | Resumen ejecutivo (cabecera) + presupuesto/servicios (4 sub-bloques fijos) + información adicional (cajón de sastre, incluido el histórico de cambios) |

`nota_bene` sustituyó a los antiguos bloques Espacio, Sala y Presupuesto (eliminados
como bloques independientes el 10/07/2026): su contenido no desapareció, se
reubicó dentro de `nota_bene.presupuesto_servicios` y `nota_bene.informacion_adicional`.

## Histórico y actualización parcial (rediseñado 12/07/2026)

- El histórico completo de un evento puede tener varias "versiones" guardadas
  (`src/schemas.py::crear_estructura_vacia_historico`), pero al LLM **solo se le
  manda la última** (`extraer_ultimo_estado`) -- mandarle la lista completa es lo
  que hacía saltar el límite de tokens por minuto (TPM) del free tier de Groq tras
  varias rondas de actualización sobre el mismo evento.
- La protección de los bloques que no se piden actualizar (`bloques_a_actualizar`)
  ya no depende de que el LLM "copie bien" un JSON grande: se hace directamente en
  Python (`src/nucleo.py::_proteger_bloques_no_actualizados`), sobrescribiendo el
  resultado con el último estado conocido.
- El esquema que se le enseña al LLM en el prompt (`src/llm.py::_esquema_para_prompt`)
  es distinto del que usa el código para la fusión interna (`ESQUEMA_SALIDA`):
  mandarle al modelo la misma representación interna (listas planas de nombres de
  campo) era ambigua y en una prueba real provocó que devolviera `evento`/`cliente`
  como arrays en vez de objetos, JSON inválido.

## Requisitos y límites conocidos

- **Requiere `GROQ_API_KEY`** en `.env` (gratis en console.groq.com). Sin clave,
  falla de forma controlada -- ya no hay motor de reglas de respaldo.
- **Free tier de Groq, dos límites distintos:**
  - **Tokens/día** (200.000): se agota con el uso acumulado a lo largo del día.
  - **Tokens/minuto (TPM, 8.000)**: puede saltar con una sola llamada si el prompt
    de esa llamada es demasiado grande (mucho histórico, un briefing muy largo) --
    ver `agente_operis_llm/docs/ESTIMACION_TOKENS.md` para el detalle medido y las
    mitigaciones aplicadas.
- `temperature=0` y `response_format=json_object`: minimizan variabilidad y fuerzan
  una respuesta JSON válida (no eliminan del todo la posibilidad de un JSON inválido
  si el prompt es ambiguo -- ver el bug del esquema, arriba).

## Pendiente, sigue sin definir

Cómo invoca el backend a `ejecutar_agente(payload)` en producción (API REST vía
`servidor.py`, librería Python importada directamente, u otro mecanismo) -- no hay
orquestador en el proyecto Mitümi, y no está decidido. `servidor.py` es una
propuesta de capa HTTP, no una decisión tomada por el equipo de backend. Ver
`agente_operis_llm/README.md`, sección 8.2.
