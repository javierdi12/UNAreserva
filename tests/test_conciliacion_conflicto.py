import sqlite3
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from pymongo.errors import PyMongoError

from src import servicios


class ConciliacionConflictoTest(unittest.TestCase):
    def setUp(self):
        self.path = str(Path(__file__).with_name("conflicto_test.db"))
        Path(self.path).unlink(missing_ok=True)
        self.patch = patch.object(servicios.Config, "SQLITE_PATH", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        Path(self.path).unlink(missing_ok=True)

    @patch.object(
        servicios,
        "_intentar_reserva",
        side_effect=[PyMongoError("offline"), servicios.ConflictoReserva("ocupado")],
    )
    def test_conflicto_no_se_acepta_como_reserva_nueva(self, _intentar):
        servicios.reservar(
            "recurso-1", "usuario-1", datetime(2026, 10, 30, 9), datetime(2026, 10, 30, 10)
        )
        resumen = servicios.sincronizar_pendientes(detallado=True)
        self.assertEqual(resumen["conflictos"], 1)
        self.assertEqual(resumen["aceptadas"], 0)
        with sqlite3.connect(self.path) as conexion:
            estado = conexion.execute(
                "SELECT sincronizado, resultado FROM pendientes"
            ).fetchone()
        self.assertEqual(estado, (-1, "conflicto"))


if __name__ == "__main__":
    unittest.main()
