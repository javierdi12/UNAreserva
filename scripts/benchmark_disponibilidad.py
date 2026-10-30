"""Mide el tiempo de consulta de disponibilidad.

Requiere MongoDB configurado y recibe un recurso existente. Reporta mediana,
mínimo y máximo en milisegundos para facilitar la comparación de índices.
"""

import argparse
import statistics
import time
from datetime import date

from src.servicios import consultar_disponibilidad


def medir(id_recurso, dia, repeticiones):
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        consultar_disponibilidad(id_recurso, dia)
        tiempos.append((time.perf_counter() - inicio) * 1000)
    return {
        "repeticiones": repeticiones,
        "mediana_ms": round(statistics.median(tiempos), 3),
        "min_ms": round(min(tiempos), 3),
        "max_ms": round(max(tiempos), 3),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("id_recurso")
    parser.add_argument("--fecha", default=date.today().isoformat())
    parser.add_argument("--repeticiones", type=int, default=10)
    args = parser.parse_args()
    print(medir(args.id_recurso, date.fromisoformat(args.fecha), args.repeticiones))
