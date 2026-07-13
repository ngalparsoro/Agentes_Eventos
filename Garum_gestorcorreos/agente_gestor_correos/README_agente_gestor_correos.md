# Gestor Inteligente de Correos

> **Versión del proyecto:** 0.2  
> **Versión del README:** 1.0  
> **Estado:** MVP Funcional  
> **Proyecto:** MITUMI  
> **Tipo de agente:** Agente inteligente de gestión de correo electrónico

---

# Índice

1. Introducción
2. Resumen ejecutivo
3. Objetivo
4. Arquitectura general
5. Funcionalidades
6. Límites del agente
7. Flujo general de funcionamiento
8. Estructura del proyecto
9. Explicación de la estructura

---

# 1. Introducción

El Gestor Inteligente de Correos es un agente desarrollado para automatizar la gestión del correo electrónico dentro de la plataforma MITUMI.

Su finalidad es reducir el tiempo dedicado a revisar la bandeja de entrada clasificando automáticamente los mensajes, generando borradores de respuesta, detectando solicitudes de reunión y notificando los correos relevantes mediante Telegram.

El sistema combina reglas de negocio, un modelo de lenguaje (LLM), un histórico de comunicaciones (RAG) y las APIs de Google para asistir al usuario sin sustituir la validación humana.

Todas las respuestas generadas por el agente son propuestas que pueden ser revisadas antes de enviarse.

---

# 2. Resumen ejecutivo

| Campo | Valor |
|--------|-------|
| Nombre | Gestor Inteligente de Correos |
| Proyecto | MITUMI |
| Lenguaje | Python |
| Estado | MVP Funcional |
| Canal principal | Gmail |
| Notificaciones | Telegram |
| Calendario | Google Calendar |
| Base de datos | SQLite |
| Modelo IA | OpenAI |
| Historial | RAG JSONL |
| Punto de entrada | `servicio.py` |

---

# 3. Objetivo

El objetivo del agente consiste en automatizar el tratamiento de los correos electrónicos recibidos.

Para ello analiza cada mensaje, identifica su finalidad y ejecuta las acciones correspondientes.

Actualmente puede:

- Leer nuevos correos electrónicos.
- Clasificarlos automáticamente.
- Generar propuestas de respuesta.
- Detectar solicitudes de reunión.
- Consultar el histórico de conversaciones.
- Notificar mediante Telegram.
- Guardar toda la información procesada.
- Registrar respuestas en formato JSON.

El agente busca minimizar las tareas repetitivas manteniendo siempre al usuario en el proceso de decisión.

---

# 4. Arquitectura general

El agente integra varios servicios externos que colaboran durante el procesamiento de cada correo.

```text
                     Gmail

                       │

             Nuevos correos

                       │

                  servicio.py

                       │

                 agente.py

      ┌──────────┼──────────┬──────────┐

      │          │          │          │

    SQLite      RAG        LLM     Google Calendar

      │          │          │

      └──────────┼──────────┘

                 │

         Respuesta generada

                 │

        JSON + Borrador + Telegram
```

El flujo completo comienza con la lectura del correo y finaliza con la generación de la propuesta de respuesta y la correspondiente notificación.

---

# 5. Funcionalidades

Actualmente el agente implementa las siguientes capacidades.

## Lectura automática de Gmail

Consulta la bandeja de entrada mediante la API de Gmail para localizar nuevos mensajes pendientes de procesar.

---

## Clasificación inteligente

Analiza el contenido del correo utilizando un modelo de lenguaje.

Puede clasificar diferentes tipos de mensajes siguiendo las reglas definidas en los prompts del proyecto.

---

## Generación de borradores

Cuando el correo requiere contestación, el agente redacta una propuesta de respuesta.

Los borradores se almacenan para su revisión antes del envío definitivo.

---

## Consulta del histórico

Antes de responder, el agente consulta el histórico almacenado en el RAG.

Esto permite mantener coherencia con conversaciones anteriores.

---

## Gestión de reuniones

Cuando detecta una solicitud relacionada con una reunión, consulta Google Calendar para ayudar en la preparación de la respuesta.

---

## Notificaciones

El agente puede enviar una notificación mediante Telegram indicando que existe un nuevo correo procesado o que requiere revisión.

---

## Registro de actividad

Todas las respuestas generadas se almacenan en formato JSON para facilitar su trazabilidad.

---

# 6. Qué NO hace

Este agente ha sido diseñado como asistente.

Por ello presenta las siguientes limitaciones.

No puede:

- Enviar respuestas automáticamente sin validación.
- Eliminar correos.
- Modificar el contenido del histórico.
- Alterar directamente la base de datos.
- Crear eventos en Google Calendar sin autorización.
- Tomar decisiones críticas sin supervisión humana.

El usuario mantiene siempre el control sobre las acciones finales.

---

# 7. Flujo general de funcionamiento

Cada correo recibido sigue el siguiente recorrido.

```text
Correo recibido

      │

      ▼

Google Gmail

      │

      ▼

servicio.py

      │

      ▼

agente.py

      │

      ├────────► Clasificación

      │

      ├────────► Consulta RAG

      │

      ├────────► Consulta Calendar

      │

      ├────────► LLM

      │

      ▼

Generación de respuesta

      │

      ├────────► JSON

      ├────────► Borrador

      └────────► Telegram
```

Este flujo se ejecuta para cada correo procesado.

---

# 8. Estructura del proyecto

```text
agente_gestor_correosV0.2/

│

├── data/

│   ├── gestor_correos_mitumi.db

│   └── rag/

│       └── correos_historicos.jsonl

│

├── deploy/

│

├── docs/

│

├── logs/

│

├── outputs/

│   ├── borradores/

│   └── respuestas_json/

│

├── prompts/

│

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

├── main.py

├── servicio.py

├── requirements.txt

└── README.md
```

---

# 9. Explicación de la estructura

## data/

Contiene toda la información persistente utilizada por el agente.

Incluye la base de datos SQLite y el histórico conversacional empleado por el sistema RAG.

---

### gestor_correos_mitumi.db

Base de datos SQLite utilizada por el proyecto para almacenar la información necesaria durante el procesamiento de los correos.

---

### rag/

Contiene el histórico de conversaciones utilizado para aportar contexto adicional al modelo de lenguaje.

Actualmente el histórico se almacena en formato JSONL.

---

## deploy/

Incluye los archivos necesarios para el despliegue del servicio.

Entre ellos se encuentra el servicio para systemd y la guía de despliegue.

---

## docs/

Documentación técnica del proyecto y guía de funcionamiento interno del agente.

---

## logs/

Directorio destinado al almacenamiento de los registros generados durante la ejecución.

---

## outputs/

Contiene todos los resultados producidos por el agente.

Se divide en:

### borradores/

Almacena las respuestas generadas pendientes de revisión.

### respuestas_json/

Guarda la salida estructurada generada durante el procesamiento de cada correo.

---

## prompts/

Contiene todos los prompts utilizados por el modelo de lenguaje.

El proyecto organiza distintos prompts especializados para clasificación, redacción, reuniones, Telegram y reglas generales del sistema.

---

## src/

Implementa toda la lógica del agente.

Aquí se encuentran los módulos encargados de la comunicación con Gmail, Calendar, Telegram, el modelo LLM, la memoria, el RAG y las funciones auxiliares.

Esta carpeta constituye el núcleo del proyecto.

---

## autorizar_google.py

Realiza el proceso de autorización OAuth necesario para acceder a las APIs de Google.

---

## crear_rag.py

Genera el histórico inicial utilizado por el sistema RAG a partir de la información disponible.

---

## servicio.py

Proceso principal del sistema.

Coordina la lectura de correos, el procesamiento mediante el agente y la generación de respuestas.

---

## main.py

Permite iniciar la aplicación desde un único punto de entrada.

---

## README.md

Documento técnico del proyecto.

---

---

# 10. Funcionamiento interno del agente

El procesamiento de cada correo se realiza mediante una secuencia de módulos especializados que colaboran para interpretar el mensaje, recuperar el contexto necesario y generar una respuesta adecuada.

Cada componente tiene una responsabilidad concreta, facilitando el mantenimiento y la evolución del proyecto.

El procesamiento siempre sigue un flujo definido antes de devolver el resultado final.

---

# 11. Ciclo de procesamiento de un correo

Cada correo recibido sigue el siguiente recorrido:

```text
Nuevo correo

      │

      ▼

Lectura desde Gmail

      │

      ▼

Extracción de información

      │

      ▼

Clasificación del correo

      │

      ▼

Consulta del histórico (RAG)

      │

      ▼

Consulta de Google Calendar (si aplica)

      │

      ▼

Construcción del contexto

      │

      ▼

Modelo LLM

      │

      ▼

Generación de borrador

      │

      ▼

Salida JSON

      │

      ▼

Notificación por Telegram
```

Cada etapa del proceso puede utilizar información obtenida en las fases anteriores para enriquecer la respuesta final.

---

# 12. Servicio principal

El archivo `servicio.py` constituye el núcleo operativo del proyecto.

Entre sus principales responsabilidades se encuentran:

- Inicializar el sistema.
- Comprobar periódicamente la existencia de nuevos correos.
- Invocar al agente para procesar cada mensaje.
- Coordinar las llamadas a los distintos módulos.
- Registrar el resultado del procesamiento.
- Gestionar la salida final del sistema.

Este componente actúa como orquestador interno del agente.

---

# 13. Agente principal

La lógica de negocio se concentra en `src/agente.py`.

Este módulo coordina todas las operaciones necesarias para procesar un correo electrónico.

Entre ellas:

- Analizar el mensaje recibido.
- Obtener información adicional.
- Consultar el histórico.
- Construir el contexto para el modelo.
- Solicitar la generación de la respuesta.
- Validar el resultado obtenido.
- Preparar la salida estructurada.

El resto de módulos colaboran con el agente proporcionando funcionalidades especializadas.

---

# 14. Integración con Gmail

El módulo `gmail.py` implementa la comunicación con la API de Gmail.

Entre sus funciones destacan:

- Autenticación mediante OAuth.
- Lectura de nuevos mensajes.
- Recuperación del contenido del correo.
- Obtención de remitente, destinatarios y asunto.
- Descarga de adjuntos cuando corresponda.

Toda la interacción con Gmail se realiza a través de este módulo.

---

# 15. Integración con Google Calendar

El módulo `calendar.py` permite consultar la agenda del usuario cuando un correo hace referencia a reuniones o disponibilidad.

Entre las operaciones soportadas se encuentran:

- Consulta de eventos existentes.
- Verificación de disponibilidad.
- Obtención de fechas y horas.
- Recuperación de información del calendario.

Esta información se incorpora al contexto utilizado para generar la respuesta.

---

# 16. Integración con Telegram

El módulo `telegram.py` permite enviar notificaciones relacionadas con el procesamiento de los correos.

Las notificaciones pueden utilizarse para:

- Informar de nuevos correos importantes.
- Avisar de incidencias.
- Solicitar revisión manual.
- Comunicar el resultado del procesamiento.

Telegram actúa como canal complementario de comunicación.

---

# 17. Modelo de lenguaje

El módulo `llm.py` encapsula toda la comunicación con el modelo de lenguaje utilizado por el agente.

El modelo recibe un contexto formado por:

- Contenido del correo.
- Información obtenida mediante Gmail.
- Histórico recuperado desde el RAG.
- Información del calendario.
- Reglas definidas mediante prompts.

El resultado es una respuesta adaptada al contexto del correo procesado.

---

# 18. Sistema RAG

El proyecto incorpora un sistema de recuperación de información basado en un histórico de conversaciones.

El histórico se almacena en:

```text
correos_historicos.jsonl
```

Antes de generar una respuesta, el agente consulta este histórico para recuperar conversaciones relacionadas.

Esto permite:

- Mantener coherencia entre respuestas.
- Evitar repetir información.
- Recuperar decisiones anteriores.
- Aportar contexto adicional al modelo.

---

# 19. Memoria del agente

El módulo `memoria.py` gestiona la información necesaria para conservar el contexto durante la ejecución.

Su finalidad es mantener información útil entre distintas operaciones del agente.

La memoria permite:

- Evitar procesar varias veces el mismo correo.
- Conservar información temporal.
- Compartir contexto entre módulos.

---

# 20. Herramientas

El módulo `tools.py` agrupa las herramientas utilizadas por el agente durante el procesamiento.

Estas herramientas encapsulan operaciones reutilizables para evitar duplicar lógica.

Entre ellas pueden encontrarse:

- Consultas auxiliares.
- Procesamiento de datos.
- Utilidades comunes.
- Adaptadores de servicios externos.

Su utilización simplifica el mantenimiento del proyecto.

---

# 21. Funciones auxiliares

El archivo `funciones.py` contiene funciones de apoyo utilizadas por distintos módulos.

Estas funciones implementan tareas comunes que no forman parte directamente de la lógica del agente.

Su objetivo es mejorar la reutilización del código.

---

# 22. Parámetros

La configuración específica del agente se centraliza mediante `parametros.py`.

Este archivo permite modificar el comportamiento del sistema sin alterar la lógica principal.

Entre los parámetros configurables pueden encontrarse:

- Modelos utilizados.
- Límites de procesamiento.
- Configuración del agente.
- Opciones generales del sistema.

---

# 23. Prompts

El proyecto separa las instrucciones dirigidas al modelo de lenguaje mediante distintos prompts especializados.

Esta organización facilita su mantenimiento y evolución.

Los prompts permiten controlar aspectos como:

- Clasificación de correos.
- Redacción de respuestas.
- Gestión de reuniones.
- Generación de mensajes para Telegram.
- Reglas generales del asistente.

---

# 24. Configuración del proyecto

La configuración del sistema se realiza mediante variables de entorno y archivos específicos del proyecto.

Entre la información configurable se encuentran:

- Credenciales de OpenAI.
- Credenciales de Gmail.
- Credenciales de Google Calendar.
- Token de Telegram.
- Configuración de la base de datos.
- Parámetros del modelo.

---

# 25. Variables de entorno

El proyecto utiliza un archivo `.env` para almacenar información sensible.

Entre las variables más habituales se encuentran:

```text
OPENAI_API_KEY=

GOOGLE_CLIENT_ID=

GOOGLE_CLIENT_SECRET=

TELEGRAM_BOT_TOKEN=

DATABASE_PATH=

LOG_LEVEL=
```

Estas credenciales no deben almacenarse directamente en el código fuente.

---

# 26. Instalación

## Clonar el proyecto

```bash
git clone <repositorio>

cd agente_gestor_correos
```

---

## Crear entorno virtual

```bash
python -m venv .venv
```

---

## Activar entorno

Windows

```bash
.venv\Scripts\activate
```

Linux

```bash
source .venv/bin/activate
```

---

## Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## Configurar credenciales

Copiar el archivo:

```text
.env.example
```

como:

```text
.env
```

y completar todas las variables necesarias para la ejecución del sistema.

---

## Autorizar Google

Antes del primer uso es necesario ejecutar:

```bash
python autorizar_google.py
```

Este proceso genera las credenciales necesarias para acceder a Gmail y Google Calendar mediante OAuth.

---

# 27. Ejecución

Una vez configurado el proyecto puede iniciarse mediante:

```bash
python servicio.py
```

o, alternativamente:

```bash
python main.py
```

El servicio comenzará a supervisar la bandeja de entrada y procesará automáticamente los nuevos correos recibidos.

---

# 28. Flujo completo del sistema

```text
Inicio

   │

Carga configuración

   │

Autenticación Google

   │

Lectura Gmail

   │

Nuevo correo

   │

Clasificación

   │

Consulta RAG

   │

Consulta Calendar

   │

Construcción del prompt

   │

LLM

   │

Borrador

   │

JSON

   │

Telegram

   │

Fin
```

---

---

# 29. Validaciones

El agente incorpora distintos mecanismos de validación antes de ejecutar cualquier acción o generar una respuesta.

Estas comprobaciones tienen como objetivo garantizar la calidad de la información procesada y reducir la posibilidad de errores durante la automatización.

Entre las principales validaciones se encuentran:

- Verificación del formato del correo recibido.
- Comprobación de las credenciales de acceso a Google.
- Validación de la información obtenida desde Gmail.
- Verificación de disponibilidad del histórico RAG.
- Comprobación de acceso al calendario.
- Validación de la respuesta generada por el modelo LLM.
- Verificación del formato JSON de salida.
- Control de errores durante el almacenamiento de información.

Estas validaciones permiten que el agente continúe funcionando incluso cuando alguno de los componentes externos presenta incidencias.

---

# 30. Gestión de errores

Durante la ejecución pueden producirse diferentes tipos de errores.

El sistema intenta controlarlos para evitar interrupciones innecesarias del servicio.

| Error | Acción realizada |
|---------|-----------------|
| Error de autenticación con Google | Se registra el error y se detiene la consulta correspondiente. |
| Error al acceder a Gmail | Se informa mediante el sistema de logs y se continúa el ciclo de ejecución. |
| Error de conexión con Google Calendar | Se omite la consulta del calendario manteniendo el resto del procesamiento. |
| Error del modelo LLM | Se genera un mensaje de error controlado evitando respuestas incompletas. |
| Error de acceso al histórico RAG | El agente continúa trabajando utilizando únicamente la información disponible. |
| Error al generar el borrador | Se registra el incidente para su revisión. |
| Error en Telegram | La notificación no se envía pero el procesamiento del correo continúa. |
| Error en SQLite | Se registra la incidencia y se evita corromper la información almacenada. |

Siempre que es posible el sistema devuelve un resultado controlado y registra el incidente para facilitar su análisis.

---

# 31. Registro de actividad (Logging)

El proyecto incorpora un sistema de registro que permite conocer el comportamiento del agente durante toda su ejecución.

Los logs facilitan:

- Diagnóstico de errores.
- Seguimiento del procesamiento de correos.
- Auditoría de las respuestas generadas.
- Control de incidencias.
- Depuración del sistema.

Dependiendo del nivel configurado pueden almacenarse distintos tipos de información.

| Nivel | Descripción |
|---------|-------------|
| INFO | Información general del funcionamiento. |
| WARNING | Situaciones que requieren revisión. |
| ERROR | Errores producidos durante la ejecución. |
| DEBUG | Información detallada para depuración. |

Los registros generados se almacenan dentro del directorio:

```text
logs/
```

---

# 32. Herramientas utilizadas

El agente combina distintas tecnologías y servicios externos para realizar su trabajo.

| Herramienta | Función |
|-------------|----------|
| Gmail API | Lectura de correos electrónicos. |
| Google Calendar API | Consulta de reuniones y disponibilidad. |
| OpenAI | Comprensión y generación de respuestas. |
| Telegram Bot API | Envío de notificaciones. |
| SQLite | Persistencia de información local. |
| JSON | Almacenamiento de resultados estructurados. |
| RAG | Recuperación del histórico de conversaciones. |

La combinación de estas herramientas permite automatizar gran parte del proceso de gestión del correo electrónico.

---

# 33. Seguridad

El proyecto aplica diferentes medidas orientadas a proteger tanto la información procesada como las credenciales utilizadas.

Entre ellas destacan:

- Uso de autenticación OAuth para los servicios de Google.
- Almacenamiento de credenciales mediante variables de entorno.
- Separación entre configuración y código.
- Acceso controlado a Gmail y Google Calendar.
- Almacenamiento local del histórico.
- Registro de actividad mediante logs.
- Revisión manual de los borradores antes del envío.

Estas medidas buscan minimizar el riesgo de accesos no autorizados y evitar modificaciones accidentales sobre la información gestionada.

---

# 34. Estructura de salida

Cada correo procesado genera una salida estructurada que facilita su tratamiento por otros componentes del sistema.

La información puede almacenarse en formato JSON incluyendo, entre otros, los siguientes elementos:

```json
{
  "correo": {},
  "clasificacion": "",
  "respuesta": "",
  "acciones": [],
  "requiere_revision": true
}
```

Este formato facilita la trazabilidad y la integración con futuras aplicaciones.

---

# 35. Borradores generados

Cuando el agente determina que un correo requiere respuesta, genera automáticamente un borrador.

Estos borradores:

- No se envían automáticamente.
- Permanecen disponibles para revisión.
- Pueden modificarse antes de su envío.
- Mantienen el contexto de la conversación.
- Incorporan la información recuperada desde el histórico cuando resulta relevante.

Este comportamiento garantiza que el usuario conserve el control sobre las comunicaciones enviadas.

---

# 36. Casos de uso

El agente resulta especialmente útil en situaciones como:

- Gestión diaria del correo corporativo.
- Clasificación automática de mensajes.
- Preparación de respuestas.
- Organización de reuniones.
- Seguimiento de conversaciones anteriores.
- Atención a clientes.
- Gestión de proveedores.
- Coordinación con ponentes y asistentes.

---

# 37. Pruebas

El proyecto incluye distintos recursos destinados a verificar el correcto funcionamiento del sistema.

Entre ellos se encuentran:

- Casos de prueba.
- Correos de ejemplo.
- Histórico para pruebas del RAG.
- Documentación técnica.
- Guía de despliegue.

Se recomienda ejecutar las pruebas tras cualquier modificación significativa del código.

---

# 38. Recomendaciones de despliegue

Para un funcionamiento estable se recomienda:

- Utilizar un entorno virtual independiente.
- Mantener actualizado el archivo `requirements.txt`.
- Renovar periódicamente las credenciales OAuth.
- Supervisar regularmente los registros del sistema.
- Proteger el archivo `.env`.
- Realizar copias de seguridad de la base de datos SQLite.
- Actualizar el histórico RAG cuando se incorporen nuevas conversaciones relevantes.

---

# 39. Limitaciones actuales

La versión 0.2 presenta las siguientes limitaciones conocidas:

- Depende de la disponibilidad de las APIs de Google.
- Depende del modelo LLM para la generación de respuestas.
- No envía respuestas automáticamente.
- No elimina correos electrónicos.
- No modifica directamente la información almacenada en Gmail.
- El histórico RAG requiere actualización cuando se incorporan nuevas conversaciones.

Estas limitaciones forman parte del diseño del sistema y permiten mantener un mayor control sobre las acciones realizadas.

---

# 40. Evolución prevista

Entre las mejoras previstas para futuras versiones destacan:

- Integración con IMAP y Microsoft Outlook.
- Clasificación mediante aprendizaje continuo.
- Mejoras en el sistema RAG.
- Búsqueda semántica del histórico.
- Panel web de administración.
- Gestión de múltiples cuentas de correo.
- Estadísticas de uso.
- Priorización automática de correos.
- Integración con nuevos canales de mensajería.

---

# 41. Historial de versiones

| Versión | Descripción |
|----------|-------------|
| 0.1 | Primera versión funcional del gestor inteligente de correos. |
| 0.2 | Integración con Gmail, Google Calendar, Telegram, SQLite, RAG, generación de borradores y mejora del procesamiento mediante LLM. |

---

# 42. Autor

Proyecto desarrollado para la plataforma **MITUMI**.

Este agente forma parte del ecosistema de automatización inteligente orientado a optimizar la gestión del correo electrónico mediante Inteligencia Artificial, integrando modelos de lenguaje, servicios de Google y un histórico de conversaciones para asistir al usuario durante el tratamiento diario de los mensajes.

---

# 43. Conclusión

El Gestor Inteligente de Correos constituye una solución modular diseñada para automatizar una gran parte del trabajo asociado al correo electrónico sin perder el control humano sobre las decisiones importantes.

Su arquitectura basada en componentes independientes facilita el mantenimiento, la incorporación de nuevas funcionalidades y la integración con servicios externos.

La versión 0.2 proporciona una base sólida para evolucionar hacia un asistente inteligente capaz de gestionar de forma cada vez más eficiente las comunicaciones de la plataforma MITUMI.

---