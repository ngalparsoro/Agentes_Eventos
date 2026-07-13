# Contrato de la API — "idioma común" · v3

**Proyecto:** Gestión de eventos y ponentes (Mitümi)
**Versión:** 3 — 9 de julio de 2026. **Sustituye a `contrato_api_eventos_2.md`.**
**Qué cambia:** la v2 era una propuesta previa al código; la v3 refleja lo que **ya existe de verdad** (BBDD en Neon migrada y cargada, backend en la rama `develop`, agentes conectados) y marca lo que queda por decidir. Donde v2 y la realidad chocaban, gana la realidad.

> Inventario detallado de rutas: ver `endpoints_v3.md` (mismo directorio).
> Especificación máquina del backend: `openapi.yaml` del repo `proyectoTripulacionesBackend` (rama `develop`) — esa es la fuente canónica de su API; este contrato no la duplica, la enmarca.

---

## 1. La foto real del sistema (julio 2026)

```
Front (React)
   │  fetch directo (CORS activado)
   ├────────────▶ Backend Express :3000/api/v1  ── Prisma ──▶ Neon Postgres (lee y ESCRIBE)
   ├────────────▶ Lumen :5001  POST /chat            ─┐
   └────────────▶ Operis :5002 POST /autocompletar   ─┤ agentes: SOLO LECTURA
                                                      ▼
                                          Neon Postgres (rol agente_readonly)
```

Decisión vigente (acordada 9-jul):
- **Los agentes LEEN directo de Neon** con el rol `agente_readonly` (solo `SELECT` sobre las 8 tablas de negocio; sin acceso a `usuarios`; Postgres rechaza cualquier escritura). Motivo: el backend aún no expone todas las tablas ni autenticación para agentes.
- **Toda ESCRITURA pasa por el backend**, sin excepción. La IA propone; el humano valida; el backend ejecuta. Esto ya no es solo una norma: el rol de BD de los agentes físicamente no puede escribir.
- **Migración prevista**: cuando el backend cubra las tablas que faltan y la autenticación de agentes, los agentes pasarán a leer por su API cambiando solo el `.env` (el código ya contempla ambos modos).

---

## 2. Convenciones generales (las reales)

### 2.1 Identificadores
- Todos los `id` son **UUID** (texto, ej. `44818427-4876-4b88-b71f-72449ce866b1`). La v2 decía enteros: **obsoleto**.
- Los genera la base de datos. Ni la app ni la IA inventan ids.

### 2.2 Formato de datos
- JSON en UTF-8 siempre.
- Fechas: `AAAA-MM-DD`. Fecha con hora: ISO `AAAA-MM-DDTHH:MM:SS`.
- Dinero: número (ej. `48000.0`), en euros, sin símbolo.
- Booleanos: `true`/`false`.

### 2.3 ⚠️ Nombres de campos — DECISIÓN PENDIENTE (la más urgente del contrato)
Hoy conviven **tres estilos** y esto va a doler en la integración:
- La **BD** usa `snake_case` (`nombre_evento`, `id_cliente`).
- El **cliente Prisma** del backend usa `camelCase` (`nombreEvento`, `idCliente`) — y sus respuestas JSON salen así… excepto las rutas con SQL crudo (p.ej. `GET /eventos?ciudad=`), que devuelven `snake_case`. **Una misma ruta puede responder con dos formatos según si filtras o no.**
- El **openapi.yaml del backend** mezcla ambos (`nombre_evento` + `clienteId`) y no coincide con lo que el controlador acepta (`nombreEvento` + `idCliente`).

**Propuesta a cerrar en la próxima reunión:** las respuestas y cuerpos de la API van en `camelCase` (es lo que Prisma produce solo); la BD sigue en `snake_case` (ya está migrada). El backend unifica sus rutas de filtro para no devolver crudo, y actualiza su openapi. Hasta que se cierre, **el front debe tolerar ambos estilos o no usar los filtros por query**.

### 2.4 Sobre de respuesta (el real del backend)
```json
{ "ok": true, "msg": "…", "filters": {}, "data": [ … ] }
```
Error: `{ "ok": false, "msg": "…" }` · Validación: `{ "ok": false, "msg": "…", "errors": [{ "msg", "path", "type" }] }`
La v2 proponía `{error, codigo, mensaje, detalles}`: **obsoleto** para el backend. Los servidores de los agentes usan `{"error": true, "codigo", "mensaje"}` — pendiente de unificar, de momento el front distingue por origen.

### 2.5 Paginación
No implementada en el backend (las listas vienen enteras: 40 eventos, 120 salas — asumible en esta fase). Si el volumen crece, se retoma el esquema de la v2 (`?pagina=&por_pagina=`).

---

## 3. Autenticación y roles (lo real)

| Ruta | Qué hace |
|---|---|
| `POST /auth/login` | Entra con un id-token de **Firebase** (cabecera `Authorization: Bearer <firebase_token>`). Devuelve el usuario y deja un **JWT en cookie httpOnly** (7 días) |
| `GET /auth/verify` | Comprueba la sesión de la cookie |
| `GET /auth/logout` | Borra la cookie |

⚠️ **Tres avisos acordados como pendientes del backend:**
1. **El middleware solo lee la cookie**, no la cabecera `Authorization`. Los agentes (y cualquier script) no pueden autenticarse. Pedido: aceptar también `Bearer` en la cabecera.
2. **Todo el que se loguea recibe `role: 'admin'`** (hardcodeado) y **todas las rutas exigen admin**. El rol `ponente` (solo ve lo suyo) está sin implementar. Existe tabla `usuarios` con roles que el login aún no consulta.
3. La cookie va con `secure:false` y `sameSite:'lax'`: **romperá el login cuando el front esté en otro dominio** (Vercel). Pedido: `secure:true` + `sameSite:'none'` en producción.

---

## 4. Estados de evento (los reales, tabla `estados`)

`Borrador` · `Presupuestado` · `Pendiente de aprobación` · `Confirmado` · `En ejecución` · `Celebrado` · `Facturado` · `Cancelado`

La lista de la v2 (`pre-evento`, `en-curso`…) queda **obsoleta**. Los estados se referencian por su `id` (UUID) en `eventos.id_estado`; la descripción es para mostrar. Comparaciones de texto: **sin distinguir mayúsculas** (los agentes ya lo hacen así).

---

## 5. Modelo de datos real (9 tablas en Neon)

- **eventos** — nombre, ciudad, lugar_confirmado, fechas, nº personas, tipo, nota + FKs: `id_cliente`, `id_estado`, `id_presupuesto`, `id_sala`, `id_ponencia`.
- **clientes** — cliente (nombre persona), email, teléfono, empresa, sector, ciudad.
- **espacios** — nombre, ciudad, dirección, aforo, contacto. / **salas** — nombre, tipo, capacidad, `id_espacio`.
- **ponentes** — nombre, identificación, email, sector, teléfono, foto/cv (links), empresa, cargo.
- **ponencias** — hotel, transporte (notas y horarios), horario ponencia, check-in, estado del ponente, links (presentación, billetes), tipo, `id_ponente`.
- **presupuestos** — estado, total, partidas (ubicación/catering/audiovisuales/otros con precio y nota), observaciones.
- **estados** — catálogo de la sección 4. / **usuarios** — login y rol (vetada para agentes).

⚠️ **Dos problemas de modelo/datos reconocidos (bloquean funcionalidades de agentes y front):**
1. **La relación evento↔ponente quedó invertida**: `eventos.id_ponencia` apunta a UNA ponencia → un evento solo puede tener **un** ponente. El acuerdo original (y `evento_ponente.csv`, con los 40 vínculos) es **muchos-a-muchos**. Pedido a backend/BD: mover la FK a `ponencias.id_evento` (o tabla puente) y recargar.
2. **`eventos.id_sala` e `id_ponencia` están a NULL en los 40 eventos** (la carga no los enlazó). Hasta que se pueblen, nadie puede responder "¿qué ponentes/sala tiene este evento?".
3. (Para el bot de Telegram) **falta `telegram_user_id`** en `ponentes` — sin ese campo no se puede saber qué ponente escribe.

---

## 6. Reglas para la IA (sin cambios de fondo, con más garantías)

1. Los agentes **leen** (hoy de Neon con rol readonly; mañana por la API del backend).
2. Lo que **proponen** (borradores de comunicación, campos extraídos de un briefing, bloqueos detectados) **siempre requiere validación humana** — los agentes lo marcan con `requiere_validacion_humana`.
3. Ninguna acción con efecto real (enviar, confirmar, pagar, guardar) la ejecuta un agente. Los endpoints para persistir propuestas (`POST /borradores`, `POST /bloqueos` de la v2) **siguen pendientes de construir en el backend** — mientras tanto las propuestas viven en la respuesta al front y en los `outputs/` locales de cada agente.
4. El contrato interno agente↔orquestador (`ejecutar_agente(payload) → dict`, payload común) **no cambia** — ver `Definicion_Agentes_RAUL/`.

---

## 7. Quién construye qué (reparto vigente)

| Pieza | Equipo | Estado |
|---|---|---|
| CRUD eventos/clientes/espacios/ponentes/salas/ponencias | Backend | ✅ en `develop` |
| Rutas de presupuestos y estados | Backend | ⚠️ modelos hechos, rutas faltan |
| Auth Bearer para agentes + roles reales + cookie prod | Backend | ⚠️ pendiente (sección 3) |
| `GET /ponentes/by-telegram/{telegram_user_id}` | Backend | ⚠️ pendiente |
| `POST /borradores`, `POST /bloqueos` + aprobación | Backend | ⚠️ pendiente (post-MVP) |
| Relación evento↔ponentes + poblar `id_sala`/`id_ponencia` + `telegram_user_id` | BD/Datos | ⚠️ pendiente, **bloquea a agentes** |
| Chat Lumen (`:5001/chat`) y Operis (`:5002/autocompletar`) | Data/Agentes | ✅ probados contra Neon |
| Consumir todo lo anterior | Front | según `endpoints_v3.md` |

---

## 8. Cómo se cambia este contrato

Igual que siempre: cualquier cambio se avisa al grupo y sube la versión (**la próxima es v4 en archivo nuevo** — no se edita este). Si el código y este documento discrepan, se corrige el que esté equivocado *el mismo día*, y mientras tanto manda el código que está desplegado.
