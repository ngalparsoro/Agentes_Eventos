# 🚀 Backend de APIs para Agentes — Backstage

Servicio intermedio desarrollado en **FastAPI** que sirve como puente entre la base de datos de producción (Neon PostgreSQL) y los agentes autónomos (bot de Telegram, gestor de correos, etc.). 

---

## 🛠️ Aspectos Clave

- **📍 Puerto:** `5004` (Convivencia: Express `3000`, Data Nora `5003`).
- **🛡️ Seguridad (Solo Lectura):** Utiliza un rol de solo lectura (`agente_readonly`) en Neon. Las peticiones de escritura (POST) se guardan solo en la **memoria local** del servidor y generan logs.
- **🛡️ Resiliencia de Esquema:** Si falta la columna `telegram_user_id` en la tabla `ponentes` (pendiente de migración), el backend aplica un fallback hacia un diccionario local (`MAPEO_TELEGRAM_DEMO`) para que los agentes no se rompan y sigan funcionando al 100%.
- **🔗 Formato Híbrido:** Devuelve respuestas nativas pero añade la estructura `{ ok: true, data: {...} }` compatible con el backend de Express.
- **📚 Base de Datos:** Las consultas leen uniendo directamente las tablas `eventos`, `ponentes` y `ponencias` adaptándose al esquema relacional actual.
- **📅 Parseo Seguro de Fechas:** Se aplica programación defensiva mediante tipado dinámico (`hasattr()`) sobre los campos de fecha. Esto evita caídas críticas (`AttributeError`) en caso de que la BBDD retorne strings planos o datos mal formateados.

---

## 💻 Pila Tecnológica

- **Python:** 3.10+
- **Framework REST:** FastAPI + Uvicorn
- **Base de Datos:** psycopg (PostgreSQL)
- **Variables de Entorno:** python-dotenv

---

## ⚙️ Instalación y Puesta en Marcha

1. **Entra al directorio:**
   ```bash
   cd traspaso_backend_agentes_RaulRojo/backend_agentes
   ```
2. **Instala dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Variables de entorno (`.env`):**
   Duplica `.env.example` como `.env` e incluye el acceso a tu base de datos:
   ```ini
   DATABASE_URL="postgresql://rol_readonly:password@host/neondb?sslmode=require"
   PORT=5004
   HOST=127.0.0.1
   ```
4. **Arranca el servicio:**
   ```bash
   python app.py
   ```
   > 📄 Documentación interactiva (Swagger) disponible en: `http://127.0.0.1:5004/docs`

---

## 📡 Endpoints (Mapa de la API)

### 🏥 Healthcheck
- `GET /` → Verifica que el backend está "activo" y lista todas sus rutas disponibles.

### 👤 Ponentes y Búsqueda
- `GET /api/ponentes/by-telegram/{telegram_user_id}`
  > Busca un ponente por su ID de Telegram. Si no existe la columna en BBDD, hace fallback automático a la demo.
- `GET /api/ponentes/{id_ponente}/eventos-activos`
  > Retorna la lista de eventos (`id`, `nombre_evento`, `fecha`) en los que participa el ponente.

### 📅 Eventos y Logística
- `GET /api/eventos/{id_evento}/ponentes/{id_ponente}`
  > Devuelve el **detalle logístico completo** para un ponente específico en un evento: hotel, horas de vuelos/tren, taxis, hora de la presentación, lugar físico y lista de documentos pendientes.
- `GET /api/eventos/{id_evento}/ponentes`
  > Lista un array masivo de **todos los ponentes** de un evento, cada uno con toda su información personal y logística de ponencia. (Idéntico a la propuesta del patch de backend de Express).

### ✍️ Acciones de Escritura (Mocks Locales)
*(Simulan escrituras reales pero se almacenan en RAM y lanzan logs para mantener a los agentes a salvo de corromper la BBDD).*
- `POST /api/comunicaciones`
  > Registra mensajes entrantes/salientes (emails, chats) del agente con el ponente. 
- `POST /api/incidencias`
  > Registra incidencias o imprevistos de un ponente en su viaje, lanzando alertas (warnings) en consola.
