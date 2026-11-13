"""Capa de datos del asistente virtual (SQLite).

Tablas (como en la metodología):
  - tramites: lista de trámites de la escuela
  - preguntas_frecuentes: preguntas con palabras clave y respuesta
  - consultas: registro de todo lo que los estudiantes preguntan
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def ruta_db():
    # Se lee en cada llamada para poder cambiarla en las pruebas
    return os.environ.get("ASISTENTE_DB", str(BASE_DIR / "asistente.db"))


@contextmanager
def conexion():
    """Abre la base, guarda los cambios al terminar y la cierra."""
    conn = sqlite3.connect(ruta_db())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


ESQUEMA = """
CREATE TABLE IF NOT EXISTS tramites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS preguntas_frecuentes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tramite_id     INTEGER REFERENCES tramites(id),
    pregunta       TEXT NOT NULL,
    palabras_clave TEXT NOT NULL,
    respuesta      TEXT NOT NULL,
    activa         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS consultas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha               TEXT NOT NULL,
    mensaje             TEXT NOT NULL,
    faq_id              INTEGER REFERENCES preguntas_frecuentes(id),
    reconocida          INTEGER NOT NULL,
    derivada            INTEGER NOT NULL DEFAULT 0,
    tiempo_ms           REAL,
    atendida_secretaria INTEGER NOT NULL DEFAULT 0,
    nombre              TEXT,
    correo              TEXT,
    codigo              TEXT,
    detalle             TEXT
);
"""

# OJO: estos textos son de EJEMPLO. Lo que está entre [COMPLETAR: ...] debe
# reemplazarse con la información real que te dé la secretaría.
TRAMITES = [
    ("Matrícula", "Inscripción de cursos de cada ciclo"),
    ("Constancias", "Constancia de estudios y de matrícula"),
    ("Retiro y reserva", "Retiro de cursos y reserva de matrícula"),
    ("Certificados y convalidación", "Certificado de estudios y convalidación de cursos"),
    ("Titulacion", "Pasos para obtener el título de bachiller y para obtener el titulo de profesional"),
    ("Información general", "Horario y contacto de la secretaría"),
]

# (trámite, pregunta, palabras clave separadas por coma, respuesta)
PREGUNTAS = [
    ("Matrícula", "¿Cuáles son los requisitos para matricularme?",
     "matricula, matricular, matricularme, requisitos, documentos, papeles",
     "Para matricularte necesitas: \n1.Ingresar a la plataforma web SUV de la UNT, eligiendo los cursos sin pasarte del límite de créditos permitido.\n2.Generar la matrícula → el sistema emite una orden de pago con el código de cuenta de Interbank."
     "\n3.Pagar por agente, ventanilla, tesorería o medios digitales.\n4.Si pagas digital: imprimir el voucher y validarlo en tesorería antes de llevarlo a secretaría.\n5.Llevar el voucher y la orden de pago a secretaría para quedar matriculado(a). "
     "Revisa que tus documentos estén completos antes de ir a la secretaría."),
    ("Matrícula", "¿Cuándo son las fechas de matrícula?",
     "matricula, fecha, fechas, cuando, calendario, plazo, inicio, ciclo, inscripcion",
     "Las fechas de matrícula las define el calendario académico: \nPara el año 2027, todavia no está definido\n(Volver a consultar en marzo de 2027.). "
     "\nTe recomendamos no dejarlo para el último día."),
    ("Matrícula", "¿Cuánto cuesta la matrícula?",
     "matricula, costo, precio, cuanto, cuesta, pagar, pago, tarifa, monto",
     "El costo de la matrícula es Pago (Interbank):\n1.Nuevo ingreso: S/ 75.80\n2.Ciclo regular impar (1°, 3°, 5°, 7°, 9°): S/ 53.30\n3.Ciclo regular par (2°, 4°, 6°, 8°, 10°): S/ 47.30."),
    ("Constancias", "¿Cómo solicito una constancia de estudios?",
     "constancia, constancias, estudios, estudiante, solicitar, solicito, pedir",
     "Para pedir tu constancia se necesita ingresar a la pagina web: https://tramites-uraa.unitru.edu.pe/sign-in"
    "\nAllí deberás crearte una cuenta con tu correo institucional o ingresar si ya tienes una"
    "\nDespués deberás ingresar al apartado de registrar tramite, seleccionar 'CONSTANCIA' y rellenar los datos que se necesitan."),
    ("Constancias", "¿Cuánto demora y cuánto cuesta la constancia?",
     "constancia, constancias, demora, demoran, tiempo, cuanto, costo, cuesta, entrega, recoger",
     "Todas las solicitudes serán recepcionadas y trabajadas de Lunes a Viernes de 08:00hrs. a 14:00hrs, excepto días declarados como feriado público. "
     "\nTodos los trámites fuera del horario en mención serán considerados el próximo día hábil. "
     "\nEl costo es de 15 soles y se realiza de manera bancaria en los medios que se encuentran en la plataforma."
     "\nUna vez terminado el proceso, se recoge en la oficina de la secretaría de Ing. de Sistemas."),
    ("Retiro y reserva", "¿Cómo retiro un curso?",
     "retiro, retirar, retirarme, curso, asignatura, anular",
     "Para retirar un curso se requiere generalmente dentro de los primeros 15 días hábiles tras el inicio de clases \n"
     "Requisitos: \n1.No quedar matriculado en menos del mínimo de créditos exigido por la universidad (salvo excepciones como estar en el último ciclo)."
     "\n2.No puedes retirar el curso si es la única asignatura en la que te matriculaste."
     "\n3.Estar libre de deudas administrativas."),
    ("Retiro y reserva", "¿Cómo reservo mi matrícula?",
     "reserva, reservar, reservo, licencia, pausa, ausentarme",
     "Suele aprobarse cuando el estudiante presenta alguno de los siguientes motivos debidamente fundamentados:"
     "\nRazones de salud: Enfermedad grave, intervenciones médicas o gestación."
     "\nMotivos laborales o económicos: Cambio de trabajo, horario incompatible o falta de liquidez temporal."
     "\nRazones personales o familiares: Transferencia de residencia, cuidado de familiares directos, etc.\n"
     "\nRequisitos: \n 1.Solicitud u Oficio (FUT - Formulario Único de Trámite): Dirigido al Decano de la Facultad o a la Dirección de Admisión / Registro Académico."
     "\n2.Documentación sustentatoria(Certificados médicos oficiales o carta laboral o constancia de trabajo)"
     "\n3.Comprobante de Pago: Pago del derecho de trámite por reserva de matrícula."
     "\n4.No presentar deudas."),
    ("Certificados y convalidación", "¿Cómo pido el certificado de estudios?",
     "certificado, certificados, notas, historial, record",
     "Para pedir el certificado de estudios debes ingresar a la página web: https://uraa.unitru.edu.pe/procedure"
     "\nPosteriormente debes ir al apartado de certificado de estudios, donde hay un manual interactivo que indica los procesos paso a paso que deberás realizar para ello."),
    ("Certificados y convalidación", "¿Cómo convalido cursos?",
     "convalidacion, convalidar, convalido, traslado, validar, valido, valide, cursos, otra, universidad",
     "Para convalidar cursos: "
     "\n1.Presentar solicitud según formato (FUT)."
     "\n2.Constancia de aprobación de Asignatura."
     "\n3.Silabo del curso o cursos a convalidar."
     "\n4.Pago por cada curso a convalidar."
     "\nPago por cada curso a convalidar: Monto - S/ 10.00"
     "\nINTERBANK: Cta Cte. Soles Nº 6163001972909 CCI: 00361600300197290901 INTERBANK Código Servicio: 005-166-16 - Facultades Pregrado / Código de Servicio: 005-166-03 - Posgrado / Código de Servicio: 005-166-12- Tecnología Educativa"
     "\nSedes y horarios de atención: CIUDAD UNIVERSITARIA Lunes a Viernes de 07:00 a 14:45."
     "\nConsulta sobre el procedimiento: 474-839 Fac. Ingenieria"),
    ("Titulacion", "¿Cuáles son los pasos para tener mi titulo de bachiller?",
     "bachiller, grado, egreso, academico",
     "Los pasos para el titulo de bachiller son:"
     "\n1.Solicitud dirigida al Decano (Formato de solicitud múltiple incluido en carpeta)"
     "\n2.Una foto a color, en fondo blanco, reciente, tamaño pasaporte. (caballeros: con saco, camisa y corbata: damas con traje de vestir)."
     "\n3.Pago por derecho de bachillerato. "
     "\nAtención Presencial: Mesa de Partes de las Facultades"
     "\nPago por derecho de bachillerato: Monto - S/.223.90"
     "\nOtro medio de pago: Interbank Código de Servicio 005-186-17 (pagos en agente)"
     "\nSedes y horarios de atención: CIUDAD UNIVERSITARIA Lunes a Viernes de 07:00 a 14:45."
     "\nConsulta sobre el procedimiento: 474-839 Fac. Ingenieria "),
    ("Titulacion", "¿Cuáles son los pasos para titularme?",
     "titulacion, titularme, titular, titulo, tesis, profesional, decano",
     "Los pasos para el titulo profesional son:"
     "\n1.Solicitud dirigida al Decano (Formato de solicitud múltiple incluido en carpeta)"
     "\n2.Una foto a color, en fondo blanco, reciente, tamaño pasaporte. (caballeros: con saco, camisa y corbata: damas con traje de vestir)."
     "\n3.Un ejemplar de la Tesis, con su respectivo CD asi como un Resumen Ejecutivo de la Tesis impreso y en otro CD"
     "\n4.Pago por derecho de titulación."
     "\nAtención Presencial: Mesa de Partes de las Facultades"
     "\nPago por derecho de titulación: Monto - S/.275.90"
     "\nOtro medio de pago: Interbank Código de Servicio  005-166-17 (pagos en agente)"
     "\nSedes y horarios de atención: CIUDAD UNIVERSITARIA Lunes a Viernes de 07:00 a 14:45."
     "\nConsulta sobre el procedimiento: 474-839 Fac. Ingenieria "),
    ("Información general", "¿Cuál es el horario de atención de la secretaría?",
     "horario, atencion, atienden, hora, abierto, secretaria, atiende, abre, cierra",
     "La secretaría atiende Horario: lunes a viernes, 8:00 a.m. a 2:45 p.m. En semanas de matrícula suele haber más gente.\n(Feriados no atiende.)"),
    ("Información general", "¿Dónde queda la secretaría y cómo la contacto?",
     "donde, ubicacion, ubicada, queda, contacto, telefono, correo, whatsapp, oficina, secretaria",
     "La secretaría está en Segundo piso, cerca de la tercera puerta, al lado de registro técnico. Contacto: Presencial."),
]


def cargar_datos_iniciales(conn):
    ids = {}
    for nombre, desc in TRAMITES:
        cur = conn.execute(
            "INSERT INTO tramites (nombre, descripcion) VALUES (?, ?)", (nombre, desc)
        )
        ids[nombre] = cur.lastrowid
    for tramite, pregunta, claves, respuesta in PREGUNTAS:
        conn.execute(
            "INSERT INTO preguntas_frecuentes (tramite_id, pregunta, palabras_clave, respuesta) "
            "VALUES (?, ?, ?, ?)",
            (ids[tramite], pregunta, claves, respuesta),
        )


def init_db(con_datos=True):
    """Crea las tablas y, si la base está vacía, carga los datos de ejemplo."""
    with conexion() as conn:
        conn.executescript(ESQUEMA)
        columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(consultas)")}
        for nombre_col in ("nombre", "correo", "codigo", "detalle"):
            if nombre_col not in columnas:
                conn.execute(f"ALTER TABLE consultas ADD COLUMN {nombre_col} TEXT")
        vacia = conn.execute("SELECT COUNT(*) FROM tramites").fetchone()[0] == 0
        if con_datos and vacia:
            cargar_datos_iniciales(conn)
    try:
        os.chmod(ruta_db(), 0o600)  # solo el dueño del archivo puede leerlo
    except OSError:
        pass


if __name__ == "__main__":
    init_db()
    print("Base de datos lista en:", ruta_db())
