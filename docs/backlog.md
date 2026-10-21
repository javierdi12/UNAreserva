# Backlog del proyecto

## Configuración en GitHub

Crear el hito **S1 - Problema, arquitectura y repositorio** con fecha límite del
Seguimiento 1. Crear los Issues siguientes y asignar el responsable indicado.
Las cuentas deben ajustarse si los nombres de usuario reales son distintos.

| Issue | Título propuesto | Responsable | Criterio de cierre |
|---|---|---|---|
| S1-01 | `docs: documentar arquitectura v1` | Daniel Briones | Diagrama, roles de los tres motores, flujo de reserva y comportamiento ante fallos documentados en `docs/arquitectura.md`. |
| S1-02 | `docs: definir modelo de datos v1` | Javier Díaz | Colecciones MongoDB, tabla SQLite, llaves Redis, TTL e índices documentados en `docs/modelo_datos.md`. |
| S1-03 | `feat: validar conexión a los tres motores` | Dixon Gómez | `src/main.py` conecta a MongoDB, Redis y SQLite; se adjunta salida de prueba sin secretos. |
| S1-04 | `chore: definir datos sintéticos de prueba` | Javier Díaz | Se especifican recursos, usuarios y reservas sintéticas, su origen y cómo se generarán. Nunca se usan datos personales reales. |
| S1-05 | `docs: registrar bitácora del seguimiento 1` | Daniel Briones | `docs/seguimientos/S1.md` enlaza commits/issues, pendientes, bloqueos, decisiones y responsables de la siguiente semana. |
| S1-06 | `chore: preparar entrega v0.1.0` | Dixon Gómez | Todos los cambios S1 están integrados, cada integrante tiene al menos un commit, y el tag `v0.1.0` apunta a esa versión. |

Etiquetas recomendadas: `S1`, `documentación`, `backend`, `datos`, `redis`,
`mongodb`, `sqlite` y `bloqueado`.

## Backlog priorizado para el MVP

| Prioridad | Entregable | Dependencia | Hito sugerido |
|---|---|---|---|
| Alta | Crear recursos y persistirlos en MongoDB. | S1-02 | S2 |
| Alta | Consultar horarios disponibles por recurso y fecha. | Datos de prueba e índice de reservas. | S2 |
| Alta | Crear reservas, validar intervalos y responder conflictos con HTTP 409. | Bloqueo Redis y consulta MongoDB. | S2 |
| Alta | Cancelar reservas sin borrar su historial. | Crear reservas. | S2 |
| Alta | Registrar solicitudes en SQLite cuando MongoDB falle y sincronizarlas de forma idempotente. | Esquema SQLite ampliado. | S3 |
| Media | Invalidar la caché de disponibilidad al crear o cancelar una reserva. | Consulta de disponibilidad. | S3 |
| Media | Medir disponibilidad con/sin caché y reservas bajo concurrencia. | Flujo principal completo. | S3 |
| Media | Documentar pruebas: caso normal, error de conexión y datos inválidos. | Flujo principal completo. | S3 |
| Baja | Optimizar horarios, predecir demanda y asignar espacios automáticamente. | MVP estable y datos históricos. | Roadmap |

## Definición de terminado para una tarea

Una tarea se cierra solo cuando tiene código o documentación versionada, prueba o
evidencia reproducible, Issue actualizado y pull request revisado por otro
integrante. Los secretos nunca se incluyen en el Issue, commit ni captura.
