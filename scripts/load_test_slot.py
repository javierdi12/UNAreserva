"""Prueba concurrente de reservas sobre un mismo slot."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from src import servicios


def ejecutar(id_recurso, solicitudes):
    inicio = datetime.now().replace(second=0, microsecond=0)
    fin = inicio + timedelta(minutes=1)

    def reservar(numero):
        try:
            return servicios.reservar(
                id_recurso, f"load-test-{numero}", inicio, fin
            )
        except Exception as error:  # el resumen incluye fallos no esperados
            return {"estado": "error", "error": str(error)}

    with ThreadPoolExecutor(max_workers=solicitudes) as executor:
        resultados = list(executor.map(reservar, range(solicitudes)))
    return resultados


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("id_recurso")
    parser.add_argument("--solicitudes", type=int, default=50)
    args = parser.parse_args()
    resultados = ejecutar(args.id_recurso, args.solicitudes)
    estados = {}
    for resultado in resultados:
        estado = resultado["estado"]
        estados[estado] = estados.get(estado, 0) + 1
    confirmadas = estados.get("confirmada", 0)
    pendientes = estados.get("pendiente", 0)
    conflictos_evitados = len(resultados) - confirmadas - pendientes
    print({
        "total": len(resultados),
        "estados": estados,
        "confirmadas": confirmadas,
        "conflictos_evitados": conflictos_evitados,
        "doble_reserva_detectada": confirmadas > 1,
    })
