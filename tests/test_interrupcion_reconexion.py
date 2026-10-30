import sqlite3
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from pymongo.errors import PyMongoError

from src import servicios


class InterrupcionReconexionTest(unittest.TestCase):
    def setUp(self):
        self.path = str(Path(__file__).with_name("interrupcion_test.db"))
        Path(self.path).unlink(missing_ok=True)
        self.patch = patch.object(servicios.Config, "SQLITE_PATH", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        Path(self.path).unlink(missing_ok=True)

    @patch.object(servicios, "_intentar_reserva", side_effect=PyMongoError("offline"))
    def test_interrupcion_deja_solicitud_pendiente_con_motivo(self, _intentar):
        resultado = servicios.reservar(
            "recurso-1", "usuario-1", datetime(2026, 10, 30, 9), datetime(2026, 10, 30, 10)
        )
        self.assertEqual(resultado["estado"], "pendiente")
        with sqlite3.connect(self.path) as conexion:
            fila = conexion.execute(
                "SELECT sincronizado, ultimo_error FROM pendientes"
            ).fetchone()
        self.assertEqual(fila[0], 0)
        self.assertEqual(fila[1], "offline")

    @patch.object(servicios, "_intentar_reserva", side_effect=[PyMongoError("offline"), "mongo-1"])
    def test_reconexion_reintenta_y_acepta(self, _intentar):
        servicios.reservar(
            "recurso-1", "usuario-1", datetime(2026, 10, 30, 9), datetime(2026, 10, 30, 10)
        )
        resumen = servicios.sincronizar_pendientes(detallado=True)
        self.assertEqual(resumen["aceptadas"], 1)
        self.assertEqual(resumen["pendientes"], 0)


if __name__ == "__main__":
    unittest.main()
