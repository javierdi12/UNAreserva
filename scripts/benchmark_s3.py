"""Mide tres operaciones locales representativas del MVP.

No requiere MongoDB ni Redis: mide validación, persistencia de una solicitud
offline y conciliación de una solicitud pendiente con el adaptador simulado.
Para una medición de disponibilidad contra MongoDB se mantiene además
``benchmark_disponibilidad.py``.
"""

import argparse
import statistics
import time
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import servicios


def medir(funcion, repeticiones):
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion()
        tiempos.append((time.perf_counter() - inicio) * 1000)
    return {
        "ejecuciones": repeticiones,
        "mediana_ms": round(statistics.median(tiempos), 3),
        "min_ms": round(min(tiempos), 3),
        "max_ms": round(max(tiempos), 3),
    }


def ejecutar(repeticiones):
    fecha_inicio = datetime(2030, 1, 7, 9)
    fecha_fin = datetime(2030, 1, 7, 10)
    resultados = {}

    resultados["validar_rango"] = medir(
        lambda: servicios._validar_rango(fecha_inicio, fecha_fin), repeticiones
    )

    with TemporaryDirectory() as directorio:
        ruta = str(Path(directorio) / "s3.db")
        with patch.object(servicios.Config, "SQLITE_PATH", ruta):
            resultados["guardar_pendiente_sqlite"] = medir(
                lambda: servicios._guardar_pendiente(
                    "recurso-1", "usuario-1", fecha_inicio, fecha_fin
                ),
                repeticiones,
            )

            def preparar_y_sincronizar():
                servicios._guardar_pendiente(
                    "recurso-1", "usuario-1", fecha_inicio, fecha_fin
                )
                with patch.object(servicios, "_intentar_reserva", return_value="res-1"):
                    servicios.sincronizar_pendientes(detallado=True)

            resultados["sincronizar_pendiente"] = medir(
                preparar_y_sincronizar, repeticiones
            )
    return resultados


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeticiones", type=int, default=5)
    args = parser.parse_args()
    if args.repeticiones < 3:
        parser.error("--repeticiones debe ser 3 o mayor")
    for operacion, resultado in ejecutar(args.repeticiones).items():
        print(f"{operacion}: {resultado}")
