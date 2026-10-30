import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

from src.crud import solicitudes_pendientes
from src.db import sqlite_store


class SolicitudesPendientesTest(unittest.TestCase):
    def setUp(self):
        self.path = str(Path(__file__).with_name("solicitudes_store_test.db"))
        Path(self.path).unlink(missing_ok=True)
        self.patch = patch.object(sqlite_store.Config, "SQLITE_PATH", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        Path(self.path).unlink(missing_ok=True)

    def test_crud_guarda_lista_y_actualiza_estado(self):
        solicitud_id = solicitudes_pendientes.crear({"id_recurso": "r1"})
        self.assertEqual(solicitudes_pendientes.listar("pendiente")[0]["id"], solicitud_id)

        actualizada = solicitudes_pendientes.cambiar_estado(solicitud_id, "conflicto")

        self.assertEqual(actualizada["estado"], "conflicto")
        self.assertEqual(solicitudes_pendientes.listar("pendiente"), [])

    def test_esquema_tiene_payload_y_fecha(self):
        sqlite_store.guardar({"dato": "valor"})
        with sqlite3.connect(self.path) as conexion:
            columnas = {fila[1] for fila in conexion.execute(
                "PRAGMA table_info(solicitudes_pendientes)"
            )}
        self.assertTrue({"id", "payload", "estado", "creado_en"}.issubset(columnas))


if __name__ == "__main__":
    unittest.main()
