"""Sincroniza solicitudes locales pendientes y muestra un resumen JSON."""

import json

from src.servicios import sincronizar_pendientes


if __name__ == "__main__":
    print(json.dumps(sincronizar_pendientes(detallado=True), ensure_ascii=False))
