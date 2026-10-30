# UNAreserva

Sistema de reservación de espacios y recursos compartidos para la comunidad universitaria.

## Problema

En universidades y espacios de coworking, la reserva de salas, laboratorios o equipos se realiza de forma manual (hojas de cálculo o correos), lo que genera conflictos de doble reserva y pérdida de tiempo.

## Usuarios

Estudiantes, profesores, administradores de bibliotecas y miembros de espacios de coworking.

## Alcance del MVP

- *Incluye:* Crear recursos, consultar horarios disponibles, reservar, cancelar y visualizar reservas del día.
- *No incluye:* Pasarela de pagos, autenticación con redes sociales, facturación.

## Arquitectura

- *MongoDB (principal):* catálogo de recursos y reservas.
- *Redis:* bloqueos temporales (TTL) durante el proceso de reserva.
- *SQLite:* respaldo local de solicitudes pendientes cuando hay interrupción de red.

## Tecnologías

### Lenguaje y framework

- *Lenguaje:* Python 3.11+
- *Framework Web:* Flask 3.0
- *Gestor de dependencias:* pip + requirements.txt

### Bases de datos y librerías

| Motor | Librería Python | Propósito |
|-------|-----------------|-----------|
| MongoDB | pymongo | Catálogo de recursos y reservas |
| Redis | redis-py | Bloqueos temporales (TTL) |
| SQLite | sqlite3 (nativo de Python) | Respaldo local de solicitudes |
| SSL | certifi | Certificados para conectar a MongoDB Atlas |
| Variables de entorno | python-dotenv | Cargar configuración desde .env |

## Requisitos previos

Antes de instalar el proyecto, asegúrate de tener:

- Python 3.11 o superior instalado (python.org/downloads)
- Git instalado (git-scm.com)
- Cuenta en MongoDB Atlas (gratuita) con un cluster M0 creado
- Memurai (Redis para Windows) instalado (memurai.com)

## Instalación paso a paso

### Paso 1: Clonar el repositorio

    git clone https://github.com/javierdi12/UNAreserva.git
    cd UNAreserva

### Paso 2: Crear y activar el entorno virtual

El entorno virtual aísla las dependencias del proyecto para evitar conflictos con otros proyectos de Python.

    python -m venv venv
    venv\Scripts\activate

Sabrás que el entorno está activo porque el prompt de la terminal mostrará (venv) al inicio.

### Paso 3: Instalar las dependencias

Instala todas las librerías listadas en requirements.txt:

    pip install -r requirements.txt

Esto instalará: Flask, pymongo, redis, python-dotenv y certifi.

### Paso 4: Configurar las variables de entorno

Copia la plantilla de variables de entorno y edítala con tus credenciales:

    copy .env.example .env

Abre el archivo .env y configura al menos la variable MONGO_URI con la cadena de conexión de tu cluster en MongoDB Atlas:

    MONGO_URI=mongodb+srv://usuario:password@cluster0.xxxxx.mongodb.net/unareserva_db?retryWrites=true&w=majority



### Paso 5: Inicializar las bases de datos

Este script crea las colecciones en MongoDB y la tabla en SQLite:

    python scripts/init_db.py

Para cargar datos sintéticos reproducibles en MongoDB:

    python scripts/load_data.py

La carga usa la semilla `42`, la fecha base `2030-01-07` y reemplaza el contenido
de `recursos` y `reservas`. Para variar el tamaño manteniendo la repetibilidad:

    python scripts/load_data.py --seed 7 --resources 10 --reservations 20

También se puede cambiar la fecha base con `--base-date YYYY-MM-DD`.

### Paso 6: Verificar la conexión a los motores

Ejecuta el script principal para comprobar que los 3 motores están accesibles:

    python src/main.py

Deberías ver una salida como esta:

    ==================================================
       UNAreserva - Sistema de Reservacion
    ==================================================
    [OK] Conexion a MongoDB exitosa
    [OK] Conexion a Redis exitosa
    [OK] Conexion a SQLite exitosa
    ==================================================

Si algún motor falla, revisa las variables del archivo .env y las credenciales en MongoDB Atlas.

### Redis en Windows (Memurai)

Instala Memurai desde [memurai.com](https://www.memurai.com/) y deja iniciado
el servicio `Memurai`. La configuración local usa `REDIS_HOST=localhost` y
`REDIS_PORT=6379`; también puedes configurar una URL completa con
`REDIS_URL=redis://localhost:6379/0`.

Para comprobarlo desde PowerShell:

    redis-cli ping

La respuesta esperada es `PONG`. Como alternativa, con Docker ejecuta:

    docker run --name unareserva-redis -p 6379:6379 -d redis:7-alpine

No uses `FLUSHALL` ni `FLUSHDB` en un entorno compartido; la aplicación limita
sus llaves al prefijo configurado en `REDIS_PREFIX`.

## Autenticación

La aplicación usa sesiones Flask y contraseñas almacenadas como hashes. El registro
público crea únicamente estudiantes. Para preparar la base de datos y crear el
primer administrador:

    python scripts/init_db.py
    python scripts/init_admin.py

Antes de ejecutar el segundo comando, configura `ADMIN_EMAIL`, `ADMIN_PASSWORD` y
opcionalmente `ADMIN_NAME` en el entorno. Nunca guardes esas variables en Git ni
las imprimas en logs.

La recuperación de contraseña usa MailerLite. Configura `MAILERLITE_API_TOKEN`,
`MAILERLITE_RESET_GROUP_ID`, `MAILERLITE_RESET_FIELD_KEY` y `APP_BASE_URL`.
En MailerLite crea el campo personalizado indicado por
`MAILERLITE_RESET_FIELD_KEY` y una automatización cuyo disparador sea la entrada
al grupo indicado por `MAILERLITE_RESET_GROUP_ID`. El correo de esa automatización
debe incluir el campo personalizado como enlace de recuperación.

El token de API se genera desde Integrations > MailerLite API. No lo guardes en
Git ni lo imprimas en logs. La API de MailerLite usa el endpoint base
`https://connect.mailerlite.com/api` y autenticación Bearer.

## Equipo y estructura

El proyecto se organiza por responsabilidad:

    src/app.py                 API Flask y vistas web
    src/servicios.py           Reglas de reserva y sincronización offline
    src/crud/                  Operaciones MongoDB de recursos y reservas
    src/db/                    Persistencia SQLite y cliente Redis
    src/templates/             Plantillas HTML
    tests/                     Pruebas automatizadas
    scripts/                   Inicialización, carga y mediciones
    docs/                      Arquitectura, modelo y reglas de conciliación

Comandos equivalentes en Linux/macOS:

| Windows | Linux/macOS |
|---|---|
| `venv\Scripts\activate` | `source venv/bin/activate` |
| `copy .env.example .env` | `cp .env.example .env` |
| `python src/main.py` | `python3 src/main.py` |
| `python scripts/init_db.py` | `python3 scripts/init_db.py` |


## Licencia

MIT

## Resultados, arquitectura y limitaciones

La evidencia de integración, pruebas, mediciones y decisiones de la Semana 15
está en [`docs/seguimientos/S3.md`](docs/seguimientos/S3.md) y
[`docs/decisiones.md`](docs/decisiones.md).

Las mediciones reproducibles se ejecutan sobre una base de prueba:

    python scripts/benchmark_s3.py --repeticiones 5
    python scripts/benchmark_disponibilidad.py <id-recurso> --repeticiones 10
    python scripts/load_test_slot.py <id-recurso> --solicitudes 50
    python scripts/sync_pending.py

El benchmark reporta mediana, mínimo y máximo de disponibilidad en milisegundos.
La prueba de carga informa cuántas solicitudes fueron confirmadas, quedaron
pendientes o entraron en conflicto; `doble_reserva_detectada` debe permanecer en
`False`. La sincronización informa aceptación, rechazo, conflicto, pendientes y
duración total.

La arquitectura mantiene MongoDB como fuente de verdad, Redis como coordinación
de corta duración y SQLite como cola local durable. Sus principales limitaciones
son que Redis y MongoDB siguen siendo dependencias operativas, la cola SQLite es
local a una instancia y las métricas no sustituyen una prueba de carga de
producción con datos representativos. Las cifras deben guardarse junto con la
fecha, cantidad de datos, número de repeticiones y configuración usada.
