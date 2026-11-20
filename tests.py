"""Pruebas funcionales y de integración (metodología: etapa de pruebas).

Ejecutar:  python -m unittest tests -v
Usan una base de datos temporal, no tocan la real.
"""
import os
import tempfile
import unittest
from base64 import b64encode
from datetime import datetime
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
        self.assertIn("voucher", self.preguntar("Hola, qué requisitos piden para matricularme?")["respuesta"])

    def test_distingue_costo_de_constancia_y_de_matricula(self):
        self.assertIn("15 soles", self.preguntar("cuánto cuesta la constancia").get("respuesta").lower())
        self.assertIn("s/ 75.80", self.preguntar("cuánto cuesta la matrícula").get("respuesta").lower())

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

    # --- preguntas cargadas y reconocimiento ---
    def test_hay_cerca_de_100_preguntas(self):
        self.assertGreaterEqual(len(database.PREGUNTAS), 100)
        with database.conexion() as c:
            self.assertGreaterEqual(c.execute("SELECT COUNT(*) FROM preguntas_frecuentes").fetchone()[0], 100)

    def test_cada_pregunta_se_reconoce_a_si_misma(self):
        for _, pregunta, _, respuesta in database.PREGUNTAS:
            with self.subTest(pregunta=pregunta):
                self.assertEqual(self.preguntar(pregunta)["respuesta"], respuesta)

    # --- saludos, despedidas y charla no académica ---
    CHARLA = {
        "saludo": ["hola", "ola amigo", "hola amigo", "hola compa", "buenas amigo", "Buenas tardes", "buenos días", "holaaa", "saludos", "qué tal", "Hola, buenas noches"],
        "estado": ["cómo estás", "hola cómo estás", "todo bien"],
        "agradecimiento": ["gracias", "muchas gracias", "grasias", "gracias por tu ayuda", "ok gracias"],
        "despedida": ["adiós", "chau", "hasta luego", "nos vemos", "eso es todo"],
        "identidad": ["quién eres", "cómo te llamas", "eres un robot?", "quién te creó"],
        "ayuda": ["ayuda", "necesito ayuda", "qué puedes hacer", "tengo una duda", "por favor ayuda"],
        "otras": ["no lo sabía gracias", "gracias aajjsjd", "gracias jasjdjsa", "aajjsjd", "hola asdasd", "interesante", "qué hora es", "qué día es hoy", "cuéntame un chiste", "cómo está el clima",
                  "tienes novia", "hablas inglés", "eres tonto", "no entiendo", "jajaja", "si", "no gracias", "ok"],
    }

    def test_charla_social_no_se_deriva_ni_cuenta_como_consulta(self):
        for grupo, frases in self.CHARLA.items():
            for frase in frases:
                with self.subTest(frase=frase):
                    r = self.preguntar(frase)
                    self.assertFalse(r["derivada"])
                    self.assertIsNone(r["consulta_id"])
                    self.assertEqual(self.consultas()[-1]["tipo"], "social")

    def test_hora_y_fecha_son_reales(self):
        self.assertRegex(self.preguntar("qué hora es")["respuesta"], r"\d\d:\d\d")
        self.assertIn(str(datetime.now().year), self.preguntar("qué día es hoy")["respuesta"])

    def test_saludo_con_consulta_responde_la_consulta(self):
        r = self.preguntar("Hola, buenas tardes, cuánto cuesta la matrícula?")
        self.assertIn("S/", r["respuesta"])
        self.assertEqual(self.consultas()[-1]["tipo"], "faq")

    def test_solo_emojis(self):
        self.assertFalse(self.preguntar("😊")["derivada"])

    def test_estadisticas_no_cuentan_la_charla(self):
        from app import calcular_estadisticas
        self.preguntar("hola")
        self.preguntar("gracias")
        self.preguntar("cuánto cuesta la matrícula")
        self.preguntar("¿Hay estacionamiento para bicicletas?")
        est = calcular_estadisticas()
        self.assertEqual((est["total"], est["por_asistente"], est["derivadas"], est["sociales"]), (2, 1, 1, 2))
        self.assertEqual(est["porcentaje"], 50.0)

    # --- actualizar preguntas sin perder el historial ---
    def test_sincroniza_base_antigua_sin_borrar_historial(self):
        ruta = Path(self.carpeta.name) / "antigua.db"
        os.environ["ASISTENTE_DB"] = str(ruta)
        with database.conexion() as c:      # base "vieja": una pregunta y una consulta
            c.executescript(database.ESQUEMA)
            c.execute("INSERT INTO tramites (nombre, descripcion) VALUES ('Matrícula', 'x')")
            c.execute("INSERT INTO preguntas_frecuentes (tramite_id, pregunta, palabras_clave, respuesta) "
                      "VALUES (1, '¿Cuánto cuesta la matrícula?', 'costo', 'respuesta vieja')")
            c.execute("INSERT INTO preguntas_frecuentes (tramite_id, pregunta, palabras_clave, respuesta, activa) "
                      "VALUES (1, 'Pregunta del panel', 'panel', 'creada por la secretaria', 0)")
            c.execute("INSERT INTO consultas (fecha, mensaje, reconocida) VALUES ('2026-01-01', 'hola', 1)")
        nuevas, actualizadas = database.init_db()
        self.assertEqual(actualizadas, 1)
        self.assertEqual(nuevas, len(database.PREGUNTAS) - 1)
        with database.conexion() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM consultas").fetchone()[0], 1)
            self.assertEqual(c.execute("SELECT tipo FROM consultas").fetchone()[0], "social")
            self.assertNotEqual(c.execute("SELECT respuesta FROM preguntas_frecuentes WHERE id = 1").fetchone()[0],
                                "respuesta vieja")
            self.assertEqual(c.execute("SELECT activa FROM preguntas_frecuentes WHERE pregunta = 'Pregunta del panel'")
                             .fetchone()[0], 0)
        self.assertEqual(database.init_db(), (0, 0))     # repetirlo no cambia nada

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
