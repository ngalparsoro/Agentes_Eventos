
# Documentación del Agente: agente_ponentes

> **Versión:** 1.0.0  
> **Última actualización:** 13/07/2026  
> **Autor:** Data Science – The Bridge  
> **Estado:** 🟢 Producción

## Nota importante

Este agente depende del orquestador del sistema y nunca ejecuta acciones directamente sobre la base de datos ni envía comunicaciones. Analiza la información, propone acciones y devuelve una respuesta estructurada para su validación.

# 1. Resumen ejecutivo

| Campo | Valor |
|---|---|
| Nombre | agente_ponentes |
| Propósito | Gestionar las consultas y documentación de los ponentes de un evento. |
| Fase | Preparación, seguimiento y soporte durante el evento. |
| Modelo LLM | OpenAI GPT-5.5 (configurable) |
| Tipo | Conversacional + RAG |
| Entorno | Cloud |
| Framework | SDK OpenAI |
| Criticidad | Media |
| Estado | Producción |

# 2. Estructura interna

```text
src/agents/agente_ponentes/
├── README.md
├── agente.py
├── parametros.py
├── funciones.py
├── tools.py
├── rag.py
├── schemas.py
├── pruebas.py
└── ejemplos/
```

# 3. Propósito y límites

## Capacidades
- Resolver consultas de ponentes sobre hoteles, vuelos, agenda, documentación y ponencias.
- Consultar documentación histórica mediante RAG.
- Generar borradores de respuestas para Telegram.

## Limitaciones
- No modifica la base de datos.
- No envía mensajes automáticamente.
- No reserva hoteles ni transportes.

# 4. Inicio rápido

```bash
python -m src.agents.agente_ponentes.pruebas
```

# 5. Lógica de decisión

1. Recibe el payload.
2. Identifica la intención del usuario.
3. Consulta BD y/o RAG cuando sea necesario.
4. Construye el contexto.
5. Genera una respuesta mediante el LLM.
6. Valida el formato.
7. Devuelve una propuesta estructurada.

# 6. Modos de fallo

| Fallo | Recuperación |
|---|---|
| Información incompleta | Solicitar datos al usuario |
| Documento inexistente | Informar y registrar incidencia |
| Error de herramienta | Reintentar y registrar el error |

# 7. Observabilidad

- Logging INFO, DEBUG y TRACE.
- Trazas almacenadas en `logs/`.

# 8. Determinismo

Las consultas a herramientas son deterministas. Las respuestas del LLM pueden variar según el modelo y la temperatura.

# 9. Contrato con el orquestador

## Entrada

```json
{
  "id_evento":1,
  "tipo_peticion":"consulta",
  "datos":{},
  "modo":"propuesta"
}
```

## Salida

```json
{
  "ok":true,
  "agente":"agente_ponentes",
  "resumen":"Consulta resuelta",
  "acciones_propuestas":[],
  "requiere_validacion_humana":true
}
```

# 10. Reglas comunes

- No escribir directamente en BD.
- No enviar comunicaciones sin validación.
- Salida siempre estructurada.

# 11. Herramientas

| Herramienta | Función |
|---|---|
| consultar_bd | Obtener datos del ponente |
| consultar_rag | Consultar histórico |
| generar_borrador | Crear respuesta |

# 12. Seguridad

Cumplimiento RGPD, gestión de credenciales mediante `.env` y validación de entradas frente a prompt injection.

# 13. Métricas

- Tasa de éxito.
- Latencia.
- Coste por interacción.
- Tasa de derivación a humano.

# 14. Casos de prueba

- Consulta sobre hotel → devuelve información.
- Falta documentación → genera bloqueo y solicita el documento.

# 15. Versiones

| Versión | Fecha | Cambios |
|---|---|---|
|1.0.0|13/07/2026|Versión inicial|

# 16. Referencias

- Repositorio del proyecto.
- Documentación interna.
