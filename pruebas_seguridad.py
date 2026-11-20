"""Pruebas aisladas de la protección del panel; no necesitan Flask."""
import os
import tempfile
import unittest
from pathlib import Path
import database
from seguridad import verificar_acceso

class PruebasSeguridad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ['ASISTENTE_DB'] = str(Path(self.tmp.name) / 'test.db')
        database.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_bloqueo_y_reintentos(self):
        for _ in range(4):
            self.assertEqual(verificar_acceso('secretaria', False, 1000), (False, 0))
        self.assertEqual(verificar_acceso('secretaria', False, 1000), (False, 60))
        self.assertEqual(verificar_acceso('secretaria', True, 1030), (False, 30))
        for _ in range(2):
            self.assertEqual(verificar_acceso('secretaria', False, 1060), (False, 0))
        self.assertEqual(verificar_acceso('secretaria', False, 1060), (False, 300))
        self.assertEqual(verificar_acceso('secretaria', False, 1360), (False, 900))
        self.assertEqual(verificar_acceso('secretaria', False, 2260), (False, 3600))
        self.assertEqual(verificar_acceso('secretaria', True, 5860), (True, 0))
        self.assertEqual(verificar_acceso('secretaria', False, 5861), (False, 0))

    def test_faq(self):
        from chatbot import responder
        for numero, total in [('segunda','151.00'), ('tercera','199.50'), ('cuarta','247.50')]:
            self.assertIn(total, responder(f'cuanto cuesta la {numero} matricula')['respuesta'])

if __name__ == '__main__':
    unittest.main()
