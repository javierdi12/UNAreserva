# Reglas de conciliación de reservas

La sincronización de una solicitud pendiente siempre vuelve a validar el
recurso, el horario y el traslape en MongoDB. Una fila local no es una reserva
confirmada.

## Estados

| Estado | Significado | Acción |
|---|---|---|
| `pendiente` | La solicitud está guardada localmente y aún no se procesó. | Se reintenta cuando MongoDB y Redis estén disponibles. |
| `aceptada` | La solicitud fue insertada como reserva activa en MongoDB. | Se conserva el id de la reserva creada. |
| `rechazada` | Los datos no son válidos o el recurso ya no existe. | No se reintenta automáticamente; se informa el motivo. |
| `conflicto` | El intervalo se traslapa con una reserva activa existente. | No se inserta una segunda reserva y se informa el conflicto. |

## Prioridad de decisión

1. Se validan formato, rango horario y existencia del recurso.
2. Se adquiere el bloqueo Redis del recurso. Si está ocupado, la solicitud
   permanece `pendiente` para un nuevo intento.
3. Se consulta MongoDB usando el criterio de traslape
   `inicio_existente < fin_nuevo` y `fin_existente > inicio_nuevo`.
4. Sin traslape se crea una reserva activa y la solicitud pasa a `aceptada`.
5. Con traslape se pasa a `conflicto`; nunca se sobrescribe la reserva existente.

Los límites son semiabiertos: una reserva que termina a las 10:00 no entra en
conflicto con otra que empieza a las 10:00.

## Reintentos y trazabilidad

Los errores de conectividad no se convierten en rechazo: la fila continúa como
`pendiente`. Los errores de negocio sí son terminales (`rechazada` o
`conflicto`). Cada intento debe dejar disponible el estado final y el motivo
para que la interfaz pueda distinguir una espera de sincronización de un
conflicto real.
