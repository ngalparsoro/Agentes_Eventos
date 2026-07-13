# Medición de uso de tokens — agente Operis (Groq)

Generado automáticamente por `docs/estimacion_tokens.py`. Modelo: `openai/gpt-oss-120b` en Groq. Consumo **medido de verdad** (usage de la respuesta de la API), no una estimación.

Precios: $0.15/1M tokens entrada, $0.6/1M tokens salida. Free tier: 1000 peticiones/día, 200,000 tokens/día, 8,000 tokens/minuto.

**Nota (12/07/2026):** la tabla de abajo sigue siendo la última medición real (extracción en frío, sin histórico) — no se ha vuelto a ejecutar `docs/estimacion_tokens.py` para no gastar cuota. El límite de 8.000 tokens/minuto no estaba documentado aquí originalmente porque no se había manifestado todavía; se descubrió y se corrigió el mismo día probando el modo actualización (ver la última nota de "Lectura de los resultados", más abajo, y `memoria_operis_barbara.md` sección 7 para el detalle completo).

## Resumen comparativo

| | Simple (briefing_prueba.txt) | Complejo (briefing_complejo.txt) |
|---|---|---|
| Caracteres del briefing | 1,052 | 3,642 |
| Tokens de entrada (prompt sistema + briefing) | 4,110 | 4,819 |
| Tokens de salida (JSON medido) | 1,452 | 3,072 |
| Tokens totales por llamada | 5,562 | 7,891 |
| Coste entrada (USD) | $0.000616 | $0.000723 |
| Coste salida (USD) | $0.000871 | $0.001843 |
| Coste total por llamada (USD) | $0.001488 | $0.002566 |
| Llamadas/día posibles en free tier | 35 | 25 |
| Límite que se agota primero | tokens/día | tokens/día |

## Lectura de los resultados

- Estos números son una **medición real**, de una única llamada por caso, con `temperature=0`. Pueden variar ligeramente entre ejecuciones (la tokenización de la salida depende del contenido exacto que genere el modelo), pero deberían ser estables dentro de un margen pequeño.
- El bloque Nota Bene (cabecera + 4 sub-bloques de presupuesto/servicios + información adicional) es la parte más grande del esquema de salida — normal que el caso complejo (varios ponentes, varios servicios) tenga una salida notablemente más larga que el simple.
- El bloque `espacio` de la versión anterior del esquema (objeto único, no lista) desapareció: ahora la comparación de varios espacios candidatos se resume dentro de `nota_bene` (p. ej. en `presupuesto_servicios.ubicacion.nota` o en `informacion_adicional.notas_generales`), sin necesitar un bloque de datos estructurado propio para cada opción.
- El límite que se agota primero en el free tier de Groq para este modelo, con briefings de este tamaño, es normalmente el de **tokens/día** (200.000), no el de peticiones/día (1000).
- **Nota sobre el modo actualización (actualizado 12/07/2026):** cuando se envía `contexto.historial_anterior`, el prompt de sistema crece con la última versión conocida del evento en JSON -- el consumo de tokens de entrada en ese modo sigue siendo mayor que el medido aquí (extracción inicial, sin histórico), pero ya no crece sin límite: antes se mandaba la lista COMPLETA de versiones anteriores (crecía con cada ronda de actualización y llegó a hacer saltar el límite de 8.000 tokens/minuto), ahora solo se manda la última (`src/schemas.py::extraer_ultimo_estado`). Además, el ejemplo JSON completo del prompt (~700 tokens) se omite automáticamente en modo actualización, porque la última versión ya hace de ejemplo. Estos números no incluyen esa diferencia -- para medirla de verdad haría falta una llamada real con `historial_anterior`, que este script no hace (para no complicar la comparación simple/complejo).
