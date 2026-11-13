"""Pruebas funcionales y de integración (metodología: etapa de pruebas).

Ejecutar:  python -m unittest tests -v
Usan una base de datos temporal, no tocan la real.
"""
import os
import tempfile
import unittest
from base64 import b64encode
from pathlib import Path

import backup
import database


class PruebasAsistente(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        os.environ["ASISTENTE_DB"] = str(Path(self.carpeta.name) / "prueba.db")
        os.environ["ADMIN_PASSWORD"] = "clave-de-prueba"
        database.init_db()
        from app import app
        self.cliente = app.test_client()

    def tearDown(self):
        self.carpeta.cleanup()

    def preguntar(self, texto):
        return self.cliente.post("/api/chat", json={"mensaje": texto}).get_json()

    def consultas(self):
        with database.conexion() as c:
            return c.execute("SELECT * FROM consultas").fetchall()

    # --- flujo de conversación ---
    def test_responde_requisitos_de_matricula(self):
        self.assertIn("requisitos", self.preguntar("Hola, qué requisitos piden para matricularme?")["respuesta"])

    def test_distingue_costo_de_constancia_y_de_matricula(self):
        self.assertIn("constancia", self.preguntar("cuánto cuesta la constancia").get("respuesta").lower())
        self.assertIn("matrícula", self.preguntar("cuánto cuesta la matrícula").get("respuesta").lower())

    def test_tolera_errores_de_ortografia(self):
        r = self.preguntar("cuanto cuesta la matrikula")
        self.assertFalse(r["derivada"])

    def test_horario(self):
        self.assertIn("atiende", self.preguntar("horario de atencion de la secretaria")["respuesta"])

    def test_saludo_no_se_deriva(self):
        r = self.preguntar("Hola, buenas tardes")
        self.assertFalse(r["derivada"])

    # --- consulta no reconocida ---
    def test_consulta_desconocida_se_deriva_y_se_registra(self):
        r = self.preguntar("¿Hay estacionamiento para bicicletas?")
        self.assertTrue(r["derivada"])
        fila = self.consultas()[-1]
        self.assertEqual((fila["reconocida"], fila["derivada"]), (0, 1))

    def test_mensaje_vacio(self):
        self.assertEqual(self.cliente.post("/api/chat", json={"mensaje": "  "}).status_code, 400)

    # --- base de datos y privacidad ---
    def test_se_guarda_tiempo_y_se_ocultan_numeros(self):
        self.preguntar("mi dni es 12345678 y quiero la constancia")
        fila = self.consultas()[-1]
        self.assertNotIn("12345678", fila["mensaje"])
        self.assertIsNotNone(fila["tiempo_ms"])

    # --- consulta detallada (mínimo 25 palabras) ---
    DETALLE_OK = ("Buenas tardes, quisiera consultar si puedo reservar mi matrícula este ciclo "
                  "porque tengo un problema de salud y necesito saber qué documentos debo presentar "
                  "y en qué fecha límite.")

    def derivar(self):
        return self.preguntar("¿Hay estacionamiento para bicicletas?")["consulta_id"]

    def contacto(self, consulta_id, **cambios):
        datos = {"consulta_id": consulta_id, "nombre": "Ana Pérez",
                 "correo": "ana@unitru.edu.pe", "codigo": "1234567890",
                 "detalle": self.DETALLE_OK, "acepto": True}
        datos.update(cambios)
        return self.cliente.post("/api/contacto", json=datos)

    def test_contacto_guarda_consulta_detallada(self):
        self.assertEqual(self.contacto(self.derivar()).status_code, 200)
        self.assertEqual(self.consultas()[-1]["detalle"], self.DETALLE_OK)

    def test_contacto_rechaza_detalle_corto(self):
        r = self.contacto(self.derivar(), detalle="Quiero reservar mi matrícula por favor")
        self.assertEqual(r.status_code, 400)
        self.assertIn("25 palabras", r.get_json()["error"])
        self.assertIsNone(self.consultas()[-1]["correo"])

    def test_contacto_rechaza_detalle_vacio(self):
        self.assertEqual(self.contacto(self.derivar(), detalle="").status_code, 400)

    def test_panel_muestra_consulta_detallada(self):
        self.contacto(self.derivar())
        bien = {"Authorization": "Basic " + b64encode(b"secretaria:clave-de-prueba").decode()}
        self.assertIn("reservar mi matrícula", self.cliente.get("/admin", headers=bien).get_data(as_text=True))

    # --- seguridad del panel ---
    def test_panel_pide_contrasena(self):
        self.assertEqual(self.cliente.get("/admin").status_code, 401)
        mal = {"Authorization": "Basic " + b64encode(b"secretaria:incorrecta").decode()}
        self.assertEqual(self.cliente.get("/admin", headers=mal).status_code, 401)

    def test_panel_con_contrasena_correcta(self):
        self.preguntar("¿Hay estacionamiento para bicicletas?")
        bien = {"Authorization": "Basic " + b64encode(b"secretaria:clave-de-prueba").decode()}
        r = self.cliente.get("/admin", headers=bien)
        self.assertEqual(r.status_code, 200)
        self.assertIn("estacionamiento", r.get_data(as_text=True))
        self.assertEqual(self.cliente.get("/admin/exportar", headers=bien).status_code, 200)

    # --- respaldo ---
    def test_respaldo_local_valido(self):
        backup.CARPETA = Path(self.carpeta.name) / "respaldos"
        self.preguntar("horario de atencion")
        copia = backup.crear_copia_local()
        self.assertTrue(copia.exists())
        self.assertTrue(backup.copia_es_valida(copia))
        self.assertTrue(backup.respaldar(usar_drive=False))


if __name__ == "__main__":
    unittest.main()
