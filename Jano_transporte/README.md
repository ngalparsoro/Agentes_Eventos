# Mercurio — agente de viajes para los ponentes de Mitumi

Agente que resuelve la **logística de viaje de los ponentes**: se rellenan unos
campos en un formulario, se pulsa **Buscar** y el agente devuelve varias
sugerencias de **hotel, transporte (vuelo/tren), taxi y coche de alquiler**, con
su **enlace de compra** y **dos informes en PDF** (uno para el ponente, sin
precios, y otro para Mitumi, con precios).

## Instalación y arranque rápido

```bash
# creo el entorno virtual
python -m venv .venv
# lo activo (Windows)
.venv\Scripts\activate
# instalo las dependencias
pip install -r requirements.txt
# levanto la demo (web + API) en http://127.0.0.1:8001/
python serve_demo_mercurio.py
```

## Cómo funciona: búsqueda bajo demanda (sin base de datos)

No hay base de datos ni lectura de la plataforma: la búsqueda se dispara con el
formulario. La entrada es la petición `POST /buscar` y la salida es la respuesta
JSON + los dos PDFs. El agente es un **servicio de búsqueda puro**.

```
Formulario (campos + casillas)  →  POST /buscar  →  sugerencias + 2 PDFs
```

### Datos de la plataforma + datos extra (se conjugan en el formulario)

El agente **no lee la base de datos**: es la plataforma la que precarga en el
formulario los datos que ya tiene del ponente y del evento (nombre, email,
evento, ciudad destino, fechas), y el organizador **añade** los campos que no
están en la BD (**ciudad de origen** y **preferencias**). Todo se envía junto a
`POST /buscar`; al agente le da igual qué vino de la BD y qué se tecleó.

En la demo esto se simula con un desplegable de ponentes que precarga esos
campos (ver `PONENTES_DEMO` en `static/index.html`). En producción, ese bloque
lo rellena la plataforma con sus datos reales.

### Campos del formulario

| Campo | Obligatorio |
| --- | --- |
| Nombre del ponente | ✔ |
| Email del ponente | — (para enviarle el PDF) |
| Nombre del evento | — (sale en el informe) |
| Ciudad del evento (destino) | ✔ |
| Fecha de inicio / Fecha de fin | ✔ (de ahí se calcula llegada, salida y noches) |
| Ciudad de origen | ✔ **solo si se pide viaje** |
| Número de personas | por defecto 1 (afecta a habitaciones y a los precios) |
| Preferencias (texto libre) | — (p. ej. «sin escalas», «cerca del recinto») |

### Servicios: una casilla "Necesita Sí/No" por servicio

Cuatro servicios, cada uno con su casilla **Necesita Sí/No** (estilo tomado de
la ficha del ponente del prototipo de Mitumi BackStage):

- **Alojamiento** (hotel), **Transporte** (vuelos + trenes), **Taxi**
  (traslados en el destino) y **Coche de alquiler**.
- Se busca solo lo marcado como "Sí"; la sección de lo no pedido no aparece.
- Si **ningún** servicio está en "Sí" → el botón queda **deshabilitado**.
- Si **Transporte** está en "Sí" pero falta la **ciudad de origen**, el botón se
  deshabilita y avisa (sin origen no hay vuelos ni trenes). Taxi y coche son
  servicios en el destino, así que no necesitan origen.

El estilo visual (tema oscuro, acentos cian/rosa, tarjetas de opción) replica el
prototipo `Mituyo_App_Prototipo_Completo` para integrarse con la plataforma.

### Dos PDFs

Cada búsqueda genera dos informes descargables:

- **PDF del ponente** → **sin precios**. El porqué se explica por **comodidad**
  (directo, más rápido, cercanía, valoración): nunca se le habla de coste.
- **PDF para Mitumi** → **con precios**, coste estimado y la recomendación con
  importes; el porqué sí puede hablar de que es la opción más económica.

## Módulos

1. **schemas.py** → `SolicitudBusqueda` (formulario) y `PropuestaViaje` (resultado).
2. **servicio.py** → orquesta una búsqueda: respeta las casillas, calcula la ventana, busca, recomienda y redacta.
3. **sources.py / demo.py** → proveedores de hotel/vuelo/tren (reales o simulados deterministas). Las preferencias afinan los resultados.
4. **ranking.py** → elige la mejor combinación, **explica el porqué** (mejor valorado / más cercano / más económico / directo…) y redacta el informe (Groq en real, heurística en demo). Genera la recomendación con y sin precios.
5. **pdf_report.py** → genera las dos variantes de PDF (reportlab).
6. **api.py** → `POST /buscar` y descarga de los dos PDFs (Flask).

## Modo demo (sin APIs ni claves)

```powershell
python serve_demo_mercurio.py
```

Abre **http://127.0.0.1:8001/** → el formulario. Rellena, marca hotel/viaje y
busca: aparecen las sugerencias con precios (vista del organizador), los enlaces
de compra y los dos botones de PDF. En modo demo los resultados son simulados
pero deterministas; los enlaces de compra apuntan a búsquedas reales.

También hay un CLI de prueba que genera los PDFs de unas solicitudes de ejemplo:

```bash
python -m mercurio.main
```

## API

Arranque: `waitress-serve --port=8001 mercurio.api:app`

- `POST /buscar` — cuerpo `SolicitudBusqueda`; devuelve la propuesta y los enlaces a los dos PDFs.
- `GET /informes/{id}/ponente.pdf` — informe del ponente (sin precios).
- `GET /informes/{id}/mitumi.pdf` — informe para Mitumi (con precios).
- `GET /health` — sonda de vida.

## De demo a real

- **Proveedores reales:** implementar `buscar_hoteles/vuelos/trenes` en
  `sources.py` (hoy lanzan `NotImplementedError`) con la API que se elija
  (Amadeus, Booking, Renfe/Trainline). Las firmas ya coinciden con las de demo.
- **Informe con LLM:** poner `GROQ_API_KEY` para que `ranking.py` redacte el resumen.
- Quitar `MERCURIO_DEMO` para usar el modo real.

## Tests

```bash
pytest mercurio/tests
```
