import sqlite3
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from src import servicios


class ReservaFallbackTest(unittest.TestCase):
    def setUp(self):
        self.sqlite_path = str(Path(__file__).with_name("pendientes_test.db"))
        Path(self.sqlite_path).unlink(missing_ok=True)
        self.path_patch = patch.object(servicios.Config, "SQLITE_PATH", self.sqlite_path)
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        Path(self.sqlite_path).unlink(missing_ok=True)

    def reservar_de_prueba(self):
        return servicios.reservar(
            "recurso-1",
            "usuario-1",
            datetime(2026, 10, 23, 9, 0),
            datetime(2026, 10, 23, 10, 0),
        )

    def pendientes(self):
        conn = sqlite3.connect(self.sqlite_path)
        try:
            return conn.execute(
                "SELECT id_recurso, id_usuario, fecha_inicio, fecha_fin, sincronizado "
                "FROM pendientes"
            ).fetchall()
        finally:
            conn.close()

    @patch.object(servicios, "_intentar_reserva", side_effect=PyMongoError("Mongo caido"))
    def test_guarda_pendiente_si_mongo_falla(self, _intentar):
        resultado = self.reservar_de_prueba()

        self.assertEqual(resultado["estado"], "pendiente")
        self.assertIsInstance(resultado["id"], int)
        self.assertEqual(len(self.pendientes()), 1)
        self.assertEqual(self.pendientes()[0][-1], 0)

    @patch.object(servicios, "_intentar_reserva", side_effect=RedisError("Redis caido"))
    def test_guarda_pendiente_si_redis_falla(self, _intentar):
        resultado = self.reservar_de_prueba()

        self.assertEqual(resultado["estado"], "pendiente")
        self.assertEqual(len(self.pendientes()), 1)

    @patch.object(
        servicios,
        "_intentar_reserva",
        side_effect=[PyMongoError("Mongo caido"), "mongo-id"],
    )
    def test_sincroniza_pendiente_y_actualiza_estado(self, _intentar):
        self.reservar_de_prueba()

        confirmadas, rechazadas = servicios.sincronizar_pendientes()

        self.assertEqual((confirmadas, rechazadas), (1, 0))
        self.assertEqual(self.pendientes()[0][-1], 1)


if __name__ == "__main__":
    unittest.main()
