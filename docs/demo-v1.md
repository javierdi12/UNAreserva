# Guion de demo v1.0

## Preparación

1. Activar el entorno virtual y copiar `.env.example` a `.env`.
2. Confirmar que MongoDB y Redis estén disponibles.
3. Ejecutar `python scripts/init_db.py`.
4. Cargar datos reproducibles con `python scripts/load_data.py`.
5. Iniciar la aplicación con `python -m src.app`.

## Recorrido

1. Iniciar sesión como administrador y mostrar los recursos disponibles.
2. Consultar la disponibilidad de un recurso por fecha.
3. Crear una reserva y verificarla en “Mis reservas”.
4. Intentar reservar el mismo intervalo desde otra sesión y mostrar el conflicto.
5. Simular una caída de MongoDB/Redis, crear una solicitud y mostrar el aviso de
   pendiente de sincronización.
6. Recuperar los servicios, ejecutar `python scripts/sync_pending.py` y mostrar
   el resumen de aceptadas, rechazadas y conflictos.
7. Ejecutar la carga concurrente y confirmar que
   `doble_reserva_detectada` sea `False`.

## Evidencia

Guardar la salida de los scripts y anotar fecha, cantidad de solicitudes y
configuración utilizada. No incluir credenciales, tokens ni datos personales en
la captura o en el artefacto de entrega.
