# Decisiones técnicas

Este documento registra las decisiones que sostienen el MVP y las alternativas
consideradas.

## 1. MongoDB como fuente de verdad

- **Decisión:** guardar recursos y reservas confirmadas en MongoDB.
- **Alternativas:** SQLite como base principal o Redis como almacén de reservas.
- **Motivo:** MongoDB permite consultar el catálogo y las reservas con una
  estructura flexible; Redis se reserva para coordinación temporal y SQLite para
  persistencia local durante una interrupción.

## 2. Redis únicamente para bloqueo temporal

- **Decisión:** adquirir un lock `SET NX EX` por recurso y liberarlo con token.
- **Alternativas:** confiar solo en la validación previa en MongoDB o usar un
  lock permanente.
- **Motivo:** la validación sola permite carreras concurrentes; un TTL evita que
  un proceso detenido bloquee el recurso indefinidamente. Redis no confirma
  reservas y por eso su caída no rompe la fuente de verdad.

## 3. SQLite como cola offline

- **Decisión:** conservar en SQLite las solicitudes que fallan por conectividad.
- **Alternativas:** devolver un error sin conservar la solicitud o mantenerla
  únicamente en memoria.
- **Motivo:** SQLite está disponible localmente, es durable y permite reintentos
  después de reiniciar la aplicación. La fila queda `pendiente` y no se muestra
  como reserva confirmada.

## 4. Conciliación antes de confirmar

- **Decisión:** al sincronizar se repiten la validación del recurso, el horario,
  el lock Redis y la comprobación de traslape en MongoDB.
- **Alternativas:** aceptar automáticamente toda solicitud offline o aplicar
  solo la validación que se hizo antes de la caída.
- **Motivo:** el estado del recurso puede cambiar mientras la solicitud está
  offline. Por eso un dato inválido se rechaza y un traslape se marca como
  conflicto sin sobrescribir la reserva existente.

## 5. Intervalos semiabiertos

- **Decisión:** dos reservas se traslapan cuando
  `inicio_existente < fin_nuevo` y `fin_existente > inicio_nuevo`.
- **Alternativa:** considerar conflicto cuando una reserva termina exactamente
  cuando empieza la siguiente.
- **Motivo:** permite encadenar franjas contiguas, por ejemplo 09:00–10:00 y
  10:00–11:00, y mantiene una regla simple para MongoDB.

## 6. Respuestas HTTP diferenciadas

- **Decisión:** `201` para reserva confirmada, `202` para solicitud pendiente,
  `409` para conflicto, `423` para lock ocupado y `400` para datos inválidos.
- **Alternativa:** devolver siempre `200` o `500` ante cualquier fallo.
- **Motivo:** el cliente necesita distinguir éxito confirmado, éxito diferido y
  errores recuperables o de negocio para mostrar el estado correcto.
