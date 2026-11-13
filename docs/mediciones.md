# Mediciones para la demostración

Ejecución: 13 de noviembre de 2026, Windows 11, Python 3.14.0 y SQLite 3.50.4. Código: commit `f0bb4cf`. Desde la raíz:

```powershell
python -m scripts.benchmark_s3 --repeticiones 10
```

| Operación | Ejecuciones | Mediana (ms) | Mínimo (ms) | Máximo (ms) |
|---|---:|---:|---:|---:|
| Validar rango de fechas | 10 | 0,000 | 0,000 | 0,004 |
| Guardar una solicitud pendiente en SQLite | 10 | 6,143 | 4,453 | 9,843 |
| Preparar y sincronizar pendientes con adaptador simulado | 10 | 18,491 | 13,630 | 59,184 |

La validación se redondeó a 0,000 ms; no significa que no consuma tiempo. Son muestras pequeñas y dependen del equipo.

Se usa SQLite temporal y la inserción en MongoDB se simula: no se midieron red, MongoDB ni Redis. La sincronización incluye crear una solicitud y procesar las pendientes acumuladas; la primera ejecución también procesa las diez solicitudes de la medición anterior. No demuestra integración de punta a punta ni mejora respecto de una alternativa.

## Evidencia pendiente

- Medir disponibilidad con MongoDB real: `python -m scripts.benchmark_disponibilidad <id-recurso> --repeticiones 10`. Registrar fecha, datos y configuración, sin credenciales.
- Comparar Redis con y sin caché; documentar invalidación y caída.
- En SQLite, comparar consulta con y sin índice mediante `EXPLAIN QUERY PLAN` y demostrar WAL o respaldo con `.backup`.
- En MongoDB, registrar `explain()`, un pipeline o `$lookup` y tiempos de consulta.
- Comprobar concurrencia y recuperación con los motores reales en una base aislada.

No ejecutar `scripts/load_data.py` sobre una base que contenga datos que se quieran conservar: reemplaza recursos y reservas.
