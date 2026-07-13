# Agente Ponentes

> **Versión:** 1.0.0  
> **Proyecto:** MITUMI  
> **Estado:** Producción

---

# Descripción

El **Agente Ponentes** es un asistente inteligente encargado de gestionar las consultas y la documentación de los ponentes de un evento. Utiliza un modelo de lenguaje (LLM), un sistema RAG y herramientas de consulta para proporcionar respuestas contextualizadas y generar propuestas de comunicación.

El agente no ejecuta acciones directamente sobre la base de datos ni envía mensajes automáticamente. Todas las acciones requieren validación por parte del orquestador o del usuario.

---

# Resumen

| Campo | Valor |
|--------|-------|
| Nombre | agente_ponentes |
| Proyecto | MITUMI |
| Tipo | Conversacional + RAG |
| Modelo IA | OpenAI GPT-5.5 (configurable) |
| Framework | OpenAI SDK |
| Entorno | Cloud |
| Estado | Producción |

---

# Funcionalidades

El agente puede:

- Resolver consultas de ponentes.
- Consultar información sobre hoteles.
- Consultar vuelos y transportes.
- Mostrar agenda del evento.
- Consultar documentación disponible.
- Recuperar información histórica mediante RAG.
- Generar borradores para Telegram.
- Devolver respuestas estructuradas.

---

# Limitaciones

El agente **no**:

- Modifica la base de datos.
- Envía mensajes automáticamente.
- Reserva hoteles o transportes.
- Ejecuta acciones sin validación.

---

# Arquitectura

```text
Usuario
    │
Orquestador
    │
agente.py
    │
├── LLM (OpenAI)
├── RAG
├── Base de datos (consulta)
└── Herramientas
    │
Respuesta estructurada
```

---

# Flujo de funcionamiento

```text
Solicitud del usuario
        │
Identificación de intención
        │
Consulta BD y/o RAG
        │
Construcción del contexto
        │
LLM
        │
Validación
        │
Respuesta estructurada
```

---

# Estructura del proyecto

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

---

# Componentes

## agente.py

Núcleo del agente.

- Analiza la petición.
- Consulta las herramientas necesarias.
- Construye el contexto.
- Genera la respuesta mediante IA.
- Devuelve la propuesta estructurada.

---

## rag.py

Consulta el histórico documental para proporcionar contexto adicional y mantener coherencia en las respuestas.

---

## tools.py

Agrupa las herramientas utilizadas por el agente, como consultas a la base de datos, recuperación documental y generación de borradores.

---

## funciones.py

Contiene funciones auxiliares reutilizadas por distintos módulos del proyecto.

---

## parametros.py

Centraliza la configuración del agente y permite modificar su comportamiento sin alterar la lógica principal.

---

## schemas.py

Define la estructura de entrada y salida utilizada durante la comunicación con el orquestador.

---

# Inicio rápido

Ejecutar las pruebas:

```bash
python -m src.agents.agente_ponentes.pruebas
```

---

# Entrada del agente

```json
{
  "id_evento": 1,
  "tipo_peticion": "consulta",
  "datos": {},
  "modo": "propuesta"
}
```

---

# Salida del agente

```json
{
  "ok": true,
  "agente": "agente_ponentes",
  "resumen": "Consulta resuelta",
  "acciones_propuestas": [],
  "requiere_validacion_humana": true
}
```

---

# Herramientas

| Herramienta | Función |
|-------------|---------|
| consultar_bd | Obtener información del ponente |
| consultar_rag | Recuperar contexto histórico |
| generar_borrador | Crear propuestas de respuesta |

---

# Seguridad

El agente incorpora:

- Gestión de credenciales mediante `.env`.
- Cumplimiento del RGPD.
- Validación de entradas.
- Protección frente a *prompt injection*.
- Validación humana antes de ejecutar acciones.

---

# Gestión de errores

El sistema contempla distintos escenarios:

| Error | Acción |
|--------|--------|
| Información incompleta | Solicitar más datos |
| Documento inexistente | Informar y registrar la incidencia |
| Error de herramienta | Reintentar y registrar el fallo |

---

# Observabilidad

Se registran trazas mediante distintos niveles de logging:

- INFO
- DEBUG
- TRACE

Los registros se almacenan en:

```text
logs/
```

---

# Métricas

El agente puede monitorizar:

- Tasa de éxito.
- Latencia.
- Coste por interacción.
- Derivaciones a revisión humana.

---

# Casos de uso

- Consultar información de hoteles.
- Resolver dudas sobre vuelos.
- Consultar horarios del evento.
- Localizar documentación.
- Generar respuestas para Telegram.
- Recuperar información histórica.

---

# Versiones

| Versión | Fecha | Cambios |
|----------|------------|---------|
| 1.0.0 | 13/07/2026 | Primera versión estable |

---

# Conclusión

El Agente Ponentes es un componente especializado del ecosistema MITUMI que facilita la gestión de consultas de los ponentes mediante inteligencia artificial. Gracias a su integración con RAG, herramientas de consulta y modelos LLM, proporciona respuestas contextualizadas y propuestas estructuradas, manteniendo siempre la supervisión humana antes de ejecutar cualquier acción.