# Fuente de datos — UNAreserva

## 1. Origen de los datos

UNAreserva no depende de un dataset externo. Todos los datos los genera el propio sistema durante su uso:

| Dato | Quién lo genera | Cómo entra al sistema |
|------|-----------------|-----------------------|
| Recursos (salas, laboratorios, equipos) | Administradores | `POST /api/recursos` |
| Reservas | Estudiantes, profesores y miembros de coworking | `POST /api/reservas` |
| Solicitudes pendientes | El propio sistema, ante una caída de red | Automático, desde `reservar()` |
| Bloqueos temporales | El propio sistema, durante una reserva | Automático, en Redis |

Para pruebas y demostraciones, los datos de ejemplo se crean con `python src/servicios.py` (recurso "Sala de estudio 1" y reservas de prueba).

## 2. Dónde vive cada dato

| Motor | Qué guarda | Duración | Justificación |
|-------|------------|----------|---------------|
| MongoDB Atlas | Colecciones `recursos` y `reservas` | Permanente | Documentos flexibles y consultas por rangos de fecha |
| Redis (Memurai) | Claves `UNAreserva:lock:<id_recurso>` | 10 segundos (TTL) | Bloqueo rápido que evita reservas simultáneas |
| SQLite | Tabla `pendientes` | Hasta sincronizar | Respaldo local sin depender de la red |

## 3. Estructura de los datos

### Colección `recursos` (MongoDB)

| Campo | Tipo | Ejemplo |
|-------|------|---------|
| `_id` | ObjectId | generado por MongoDB |
| `nombre` | string | "Sala de estudio 1" |
| `tipo` | string | "sala" |
| `capacidad` | int | 8 |
| `ubicacion` | string | "Biblioteca, piso 2" |
| `horario.apertura` | string `HH:MM` | "07:00" |
| `horario.cierre` | string `HH:MM` | "21:00" |

### Colección `reservas` (MongoDB)

| Campo | Tipo | Ejemplo |
|-------|------|---------|
| `_id` | ObjectId | generado por MongoDB |
| `id_recurso` | string | id del recurso reservado |
| `id_usuario` | string | "est-001" |
| `fecha_inicio` | datetime | 2026-10-20 09:00 |
| `fecha_fin` | datetime | 2026-10-20 11:00 |
| `estado` | string | "activa" o "cancelada" |
| `fecha_creacion` | datetime | momento de creación |

### Tabla `pendientes` (SQLite)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER, clave primaria | autoincremental |
| `id_recurso` | TEXT | recurso solicitado |
| `id_usuario` | TEXT | usuario que reservó |
| `fecha_inicio` | TEXT | fecha en formato ISO |
| `fecha_fin` | TEXT | fecha en formato ISO |
| `sincronizado` | INTEGER | 0 = pendiente, 1 = confirmada, -1 = rechazada |

## 4. Flujo de los datos

1. El usuario envía la solicitud de reserva a la API.
2. Redis crea un bloqueo temporal sobre el recurso.
3. MongoDB valida el horario del recurso y busca reservas que se solapen.
4. Si no hay choque, la reserva se guarda en `reservas` y se libera el bloqueo.
5. Si MongoDB o Redis no responden, la solicitud se guarda en `pendientes` (SQLite).
6. Al recuperar la conexión, `POST /api/sincronizar` reenvía las pendientes a MongoDB. Las que ya chocan con otra reserva se marcan como rechazadas.

## 5. Consideraciones

- No se almacenan datos personales sensibles: solo un identificador de usuario.
- Las credenciales de Atlas viven en `.env`, que no se sube al repositorio.
- No hay autenticación en el MVP; queda como mejora futura.

