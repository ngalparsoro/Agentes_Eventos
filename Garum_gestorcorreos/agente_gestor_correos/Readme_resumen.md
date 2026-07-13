# Gestor Inteligente de Correos

> **Versión:** 0.2  
> **Proyecto:** MITUMI  
> **Estado:** MVP Funcional

---

# Descripción

El Gestor Inteligente de Correos automatiza el tratamiento de los correos electrónicos mediante IA. Analiza los mensajes recibidos, los clasifica, genera propuestas de respuesta, consulta el historial de conversaciones (RAG), verifica disponibilidad en Google Calendar cuando es necesario y notifica mediante Telegram.

El agente actúa como asistente, manteniendo siempre la validación humana antes de realizar acciones críticas.

---

# Tecnologías

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python |
| IA | OpenAI |
| Correo | Gmail API |
| Calendario | Google Calendar API |
| Base de datos | SQLite |
| Histórico | RAG (JSONL) |
| Notificaciones | Telegram |
| Entrada | servicio.py |

---

# Funcionalidades

- Lectura automática de Gmail.
- Clasificación inteligente de correos.
- Generación de borradores.
- Consulta del histórico mediante RAG.
- Detección de reuniones.
- Consulta de Google Calendar.
- Notificaciones por Telegram.
- Registro de actividad.
- Salida estructurada en JSON.

---

# Limitaciones

El agente **no**:

- Envía correos automáticamente.
- Elimina mensajes.
- Modifica el histórico.
- Modifica directamente la base de datos.
- Crea eventos sin autorización.
- Sustituye la revisión humana.

---

# Arquitectura

```text
Gmail
   │
servicio.py
   │
agente.py
   │
├── LLM (OpenAI)
├── SQLite
├── RAG
├── Google Calendar
└── Telegram
   │
Borrador + JSON + Notificación
```

---

# Flujo de funcionamiento

```text
Nuevo correo
      │
Lectura Gmail
      │
Clasificación
      │
Consulta RAG
      │
Consulta Calendar (si aplica)
      │
Construcción del contexto
      │
LLM
      │
Generación de borrador
      │
Salida JSON
      │
Notificación Telegram
```

---

# Estructura

```text
agente_gestor_correos/

├── data/
│   ├── gestor_correos_mitumi.db
│   └── rag/
│       └── correos_historicos.jsonl
│
├── docs/
├── logs/
├── outputs/
│   ├── borradores/
│   └── respuestas_json/
│
├── prompts/
├── src/
│   ├── agente.py
│   ├── gmail.py
│   ├── calendar.py
│   ├── llm.py
│   ├── memoria.py
│   ├── rag.py
│   ├── telegram.py
│   ├── funciones.py
│   ├── parametros.py
│   ├── prompts.py
│   └── tools.py
│
├── autorizar_google.py
├── crear_rag.py
├── servicio.py
├── main.py
├── requirements.txt
└── README.md
```

---

# Componentes principales

## servicio.py

Orquesta el funcionamiento del sistema:

- Detecta nuevos correos.
- Lanza el procesamiento.
- Coordina todos los módulos.
- Registra los resultados.

## agente.py

Núcleo del agente.

- Analiza el correo.
- Construye el contexto.
- Consulta RAG y Calendar.
- Invoca el LLM.
- Genera la respuesta.

## gmail.py

Gestiona la autenticación OAuth y la lectura de Gmail.

## calendar.py

Consulta disponibilidad y eventos del calendario.

## rag.py

Recupera conversaciones anteriores para mantener el contexto.

## llm.py

Gestiona toda la comunicación con OpenAI.

## telegram.py

Envía notificaciones sobre correos procesados.

## memoria.py

Mantiene información temporal y evita reprocesar mensajes.

---

# Instalación

```bash
git clone <repositorio>

cd agente_gestor_correos

python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Linux

```bash
source .venv/bin/activate
```

Instalar dependencias

```bash
pip install -r requirements.txt
```

Autorizar Google

```bash
python autorizar_google.py
```

---

# Configuración

Crear un archivo `.env` con las credenciales:

```text
OPENAI_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
TELEGRAM_BOT_TOKEN=
DATABASE_PATH=
LOG_LEVEL=
```

---

# Ejecución

```bash
python servicio.py
```

o

```bash
python main.py
```

---

# Validaciones

El sistema verifica:

- Acceso a Gmail.
- Acceso a Calendar.
- Disponibilidad del RAG.
- Respuesta del LLM.
- Formato JSON.
- Persistencia en SQLite.

---

# Gestión de errores

Si algún servicio falla:

- Se registra el error.
- El procesamiento continúa siempre que sea posible.
- Se evita perder información.
- Se notifica cuando corresponde.

---

# Seguridad

- OAuth para Google.
- Variables de entorno.
- Separación entre configuración y código.
- Revisión manual antes del envío.
- Logs de auditoría.

---

# Salida

Cada correo genera una estructura similar a:

```json
{
  "correo": {},
  "clasificacion": "",
  "respuesta": "",
  "acciones": [],
  "requiere_revision": true
}
```

---

# Casos de uso

- Gestión diaria del correo.
- Atención a clientes.
- Gestión de proveedores.
- Organización de reuniones.
- Coordinación de eventos.
- Gestión de ponentes.

---

# Mejoras futuras

- Outlook e IMAP.
- Mejoras del sistema RAG.
- Panel web.
- Múltiples cuentas.
- Priorización inteligente.
- Estadísticas de uso.

---

# Historial

| Versión | Cambios |
|----------|---------|
| 0.1 | Primera versión |
| 0.2 | Gmail, Calendar, Telegram, SQLite, RAG y generación de borradores |

---

# Conclusión

El Gestor Inteligente de Correos es un agente modular que automatiza la gestión del correo electrónico mediante IA, integrando Gmail, Google Calendar, RAG, SQLite y Telegram. Su diseño prioriza la asistencia al usuario, manteniendo siempre el control humano sobre las decisiones finales y facilitando futuras ampliaciones del sistema.