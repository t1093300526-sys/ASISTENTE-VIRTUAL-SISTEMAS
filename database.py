"""Capa de datos del asistente virtual (SQLite).

Tablas (como en la metodología):
  - tramites: lista de trámites de la escuela
  - preguntas_frecuentes: preguntas con palabras clave y respuesta
  - consultas: registro de todo lo que los estudiantes preguntan
"""
import os
import shutil
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime
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
    tipo                TEXT,
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
    ("Preguntas frecuentes", "Informacion general de la Universidad Nacional de Trujillo"),
    
    ('Estatuto y gobierno universitario', 'Disposiciones generales del Estatuto Reformado de la UNT'),
    ('Evaluación académica', 'Asistencia, evaluaciones, aplazados y registro de notas'),
    ('Normativa y vigencia', 'Alcance, fecha y aplicabilidad de los documentos normativos'),
    ('Integridad académica', 'Similitud y disposiciones antiplagio'),
    ('Repositorio institucional', 'Registro de tesis y trabajos de investigación en el repositorio UNT'),
    ('Normativa académica UNT', 'Reglas generales de matrícula y procesos académicos'),
    # Trámites nuevos (modelo educativo, admisión, créditos, posgrado y servicios)
    ("Modelo educativo (MOEDUNT)", "Misión, visión, valores, enfoques y lineamientos del Modelo Educativo de la UNT"),
    ("Admisión y CEPUNT", "Sistema de ingreso (SINUNT), CEPUNT y modalidades de admisión"),
    ("Régimen de estudios y créditos", "Semestres, créditos, estudios generales, prácticas preprofesionales y modalidades de estudio"),
    ("Posgrado y segunda especialidad", "Maestrías, doctorados, diplomados, segunda especialidad y formación continua"),
    ("Servicios universitarios", "Bienestar, bibliotecas, laboratorios, idiomas, movilidad y ubicación de oficinas"),
    ("Movilidad estudiantil (RPU)", "Programa de movilidad para estudiantes de universidades de la RPU: requisitos, documentos y beneficios"),
    ("Carné universitario", "Solicitud, costo, pago, duplicado y convocatorias del carné universitario"),
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
     "reserva, reservar, reservo, reservacion, matricula, licencia, pausa, ausentarme",
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
     ("Preguntas frecuentes", "¿Cuál es el régimen económico de la Universidad Nacional de Trujillo?",
        "regimen economico, patrimonio, presupuesto UNT, ingresos y bienes",
        "El régimen económico de la UNT se sustenta en una gestión eficiente, transparente y descentralizada de sus recursos. "
        "Este incluye los ingresos provenientes del Tesoro Público, recursos directamente recaudados "
        "(tasas educativas, convenios, servicios, entre otros), donaciones, legados y el manejo de su patrimonio institucional conforme a la normatividad vigente del sector público."),
    ("Preguntas frecuentes", "¿Cómo se organiza el gobierno de la universidad?",
    "gobierno de la universidad, organos de gobierno, autoridad UNT, autoridades",
        "El gobierno de la UNT está estructurado de manera democrática y descentralizada a través de los siguientes órganos principales:"
        "\n Asamblea Universitaria"
        "\n Consejo Universitario"
        "\n Rectorado"
        "\n Decanatos y Consejos de Facultad"
        "\nOrganos de dirección academica y administrativa"),
    ("Preguntas frecuentes", "¿Cuáles son los requisitos básicos para ser elegido Rector de la UNT?",
     "rector, requisitos rector, autoridades unt, requisito rector, eleccion, candidato",
     "Para ser elegido Rector se requiere ser docente ordinario en la categoría de principal con los grados académicos exigidos por ley (Doctor), no haber sido condenado por delito doloso con sentencia firme, "
     "no estar incurso en incompatibilidades legales y cumplir con los requisitos específicos establecidos en el Estatuto de la universidad y la Ley Universitaria."),
    ("Preguntas frecuentes", "¿Cómo se regulan los grados y títulos que otorga la universidad?",
        "requisitos de graduación, regular, otorga, dar, entregar",
        "La UNT otorga los grados académicos de Bachiller, Maestro y Doctor, así como los títulos profesionales correspondientes a nombre de la Nación. Estos se obtienen tras cumplir con los planes de estudio, la aprobación de los créditos necesarios, "
        "el dominio de un idioma extranjero (o lengua nativa según corresponda) y la sustentación de un trabajo de investigación, tesis o proyecto, conforme a los reglamentos específicos de cada facultad."),

    ('Normativa académica UNT', 
     '¿Qué tipos de matrícula existen según la normativa académica?', 
     'tipos, tipo, matricula, regular, excepcional, modalidad', 
     'El documento de Normatividad Académica UNT distingue matrícula regular, especial y excepcional para facultades con currículo flexible. La escuela de Ing. de Sistemas debe cumplir con la normativa de la facultad.'),
    ('Normativa académica UNT', 
     '¿Cuántos créditos comprende la matrícula regular?', 
     'creditos, matricula regular, minimo, maximo, 12, 22', 
     'En la edición de Normatividad Académica, la matrícula regular en currículo flexible comprende de 12 a 22 créditos. La cantidad exacta depende del semestre.'),
    ('Normativa académica UNT', 
     '¿Cuántos créditos se permiten en el ciclo de verano?', 
     'verano, creditos, maximo, matricula, cursos extraordinarios', 'La Normatividad Académica señala un máximo de 12 créditos para el periodo académico de verano de dos meses.'),
    ('Normativa académica UNT', 
     '¿Qué es la matrícula especial?', 
     'matricula especial, menos de 12 creditos, especial', 
     'Según la Normatividad Académica, en currículo flexible se considera especial la matrícula de estudiantes que registran menos de 12 créditos. Se necesita consultar al Decanato por las condiciones de autorización.'),
    ('Normativa académica UNT',
      '¿Quiénes pueden solicitar matrícula excepcional?', 
      'matricula excepcional, promedio, catorce, 14, creditos adicionales', 
      'Se contempla matrícula excepcional para estudiantes con promedio ponderado igual o mayor a 14 en el ciclo anterior y ciertos casos de un solo curso pendiente. La autorización y aplicación deben confirmarse de manera presencial con la escuela.'),
    ('Normativa académica UNT', '¿Puedo matricularme en un curso si no aprobé su prerrequisito?', 
     'prerrequisito, requisito, curso, matricula, aprobar', 
     'La Normatividad Académica indica que para matricularse en una asignatura se deben acreditar los prerrequisitos aprobados. Si el sistema permite una matrícula que no cumple esa condición, consulta a Registro Técnico.'),
    ('Normativa académica UNT', '¿Qué cursos tienen prioridad al llenar la ficha de matrícula?', 
     'prioridad, ficha, matricula, cursos inferiores, prerrequisitos', 
     'Existe prioridad en los cursos de ciclos inferiores cuyos prerrequisitos hayan sido aprobados y, luego, los cursos sin prerrequisito.'),
    ('Normativa académica UNT', '¿Con cuánta anticipación se publica el horario de clases?', 
     'horario, publicacion, anticipacion, profesores, matricula', 
     'Normalmente, se dan los horarios en relación de los profesores con 15 días de anterioridad a la matrícula. Cabe mencionar que siempre hay casos particulares.'),
    ('Normativa académica UNT', '¿Quién asesora al estudiante durante la matrícula?', 
     'asesor, asesoria, matricula, tutor, profesor', 
     'El asesoramiento en Ing. de Sistemas se da por medio de un grupo de WhatsApp creado por alumnos de ciclos superiores.'
     '\nTambién existen videos publicados por la misma universidad que indican como un estudiante debe matricularse'),
    ('Normativa académica UNT', '¿Cuál es el plazo para solicitar retiro de cursos?', 
     'plazo, retiro, cursos, dias habiles, 15 dias', 
     'Se establece un plazo de 15 días hábiles después de iniciadas las clases para solicitar retiro de uno o más cursos en currículo flexible. Deberás confirmar el plazo vigente de tu periodo.'),
    ('Normativa académica UNT', '¿Puedo retirar el único curso en el que estoy matriculado?', 
     'unico curso, retiro, retirar, matricula',
     'La normativa indica que no se puede retirar matrícula cuando el estudiante se ha matriculado en un solo curso.'),
    ('Normativa académica UNT', '¿Cuál es el plazo para solicitar retiro y reserva de matrícula?', 
     'retiro, reserva, plazo, 30 dias, matricula', 
     'La edición de Normatividad Académica establece que el retiro y reserva pueden solicitarse dentro de los 30 días hábiles posteriores al inicio de clases. Verifica el reglamento y calendario actualmente vigentes.'),
    ('Normativa académica UNT', '¿Cuántos periodos puedo reservar mi matrícula?', 
     'reserva, periodos, continuo, no continuo, maximo', 
     'Comúnmente se señala un máximo de dos periodos lectivos continuos o tres no continuos para retiro y reserva de matrícula. La información varía de acuerdo al periodo, por lo que se recomienda consultar con la escuela.'),
    ('Normativa académica UNT', '¿Los estudiantes de primer ciclo pueden reservar matrícula?', 
     'primer ciclo, primer año, reserva, matricula', 
     'La Normatividad Académica indica que los estudiantes del primer año o primer ciclo no pueden solicitar retiro y reserva de matrícula.'),
    ('Normativa académica UNT', '¿Quién formaliza el retiro y reserva de matrícula?', 
     'formalizar, resolucion, decanato, retiro, reserva', 
     'Según la normativa, el Decanato oficializa el retiro y reserva mediante resolución. El documento también menciona la entrega del carné universitario para su entrada en vigencia.'),
    ('Normativa académica UNT', '¿En qué casos se puede anular una matrícula?', 
     'anular, anulacion, matricula, oficio, registro tecnico', 
     'La normativa contempla anulaciones, entre otros casos, cuando se registran cursos que no pertenecen al currículo aprobado, cursos no ofertados o matrículas que exceden los límites permitidos. La Oficina de Registro Técnico aplica las disposiciones señaladas.'),
    ('Normativa académica UNT', '¿Se pueden matricular cursos que no se ofrecen en el semestre?', 
     'curso no ofertado, matricula, semestre, oferta academica', 
     'La Normatividad Académica señala que la matrícula en cursos no ofertados en el periodo lectivo puede ser anulada de oficio.'),
    ('Normativa académica UNT', '¿Cómo se realiza la convalidación para estudiantes trasladados?', 
     'convalidacion, traslado, cursos, resolucion rectoral', 
     'Para ingresos por traslado o segunda profesionalización, la resolución rectoral debe indicar los cursos convalidados y que el proceso se realiza en un solo momento, antes de la primera matrícula.'),
    ('Normativa académica UNT', '¿Puedo convalidar cursos después de ingresar por examen de admisión?', 
     'convalidar, examen admision, ingresante, cursos posteriores', 
     'La Normatividad Académica indica que no procede convalidar cursos llevados después de ingresar a la UNT mediante examen de admisión.'),
    ('Normativa académica UNT', '¿Qué ocurre si un ingresante no confirma su matrícula?', 
     'ingresante, confirmar, matricula, plazo, admision', 
     'Terminado el plazo de matrícula, la Facultad informa a la Oficina Central de Admisión sobre los ingresantes que no se acercaron a confirmar su matrícula.'),
    ('Evaluación académica', '¿Qué porcentaje de inasistencias puede inhabilitarme en un curso?', 
     'inasistencia, faltas, porcentaje, 30, inhabilitado', 
     'La Normatividad Académica indica que los estudiantes con más del 30% de inasistencias son considerados inhabilitados en la asignatura. Cabe recalcar que depende del criterio de cada docente.'),
    ('Evaluación académica', '¿Qué significa estar inhabilitado en una asignatura?', 
     'inhabilitado, inhabilitacion, faltas, asistencia', 
     'Superar el 30 % de inasistencias determina la condición de inhabilitado; además, se considera matrícula utilizada.'),
    ('Evaluación académica', '¿Qué pasa si falto a una evaluación parcial?', 
     'faltar, examen, parcial, rezagado, evaluacion', 
     'La normativa contempla una evaluación de rezagados. Señala que la evaluación parcial rezagada debe rendirse antes de la evaluación de la última parte, unidad o módulo. Se debe consultar al docente y el calendario del curso.'),
    ('Evaluación académica', '¿Qué nota me colocan si no rindo una evaluación rezagada?', 
     'rezagado, nota cero, evaluacion, inasistencia examen', 
     'Si el estudiante no se presenta a la oportunidad prevista para rendir la evaluación rezagada, el profesor asigna nota cero.'),
    ('Evaluación académica', '¿Qué es el examen de aplazados?', 
     'aplazados, examen, evaluacion especial, desaprobado', 
     'El reglamento de evaluación incluido define la evaluación de aplazados como una evaluación que comprende la totalidad del contenido del curso y se realiza según la programación y fechas establecidas.'),
    ('Evaluación académica', '¿Qué requisitos se necesitan para rendir el examen de aplazados?', 
     'requisitos, aplazados, dos tercios, evaluaciones parciales', 
     'La normativa señala que el estudiante debe haber participado por lo menos en dos tercios de las evaluaciones parciales programadas para pasar a evaluación de aplazados.'),
    ('Evaluación académica', '¿La nota del examen de aplazados se promedia con la nota desaprobatoria?', 
     'nota, aplazados, promedio, independiente', 
     'El documento señala que la nota de aplazados es independiente y no se promedia con la nota final desaprobatoria de la asignatura.'),
    ('Evaluación académica', '¿Qué información debe registrar el docente sobre las evaluaciones?', 
     'docente, registro oficial, evaluacion, inasistencias, notas', 
     'La Normatividad Académica menciona el Registro Oficial de Evaluación, que contiene las evaluaciones parciales, el promedio final y el cómputo de inasistencias; también contempla los resultados de la evaluación de aplazados.'),
    ('Evaluación académica', '¿Dónde puedo consultar si mi nota fue registrada correctamente?', 
     'nota, reclamo, registro, evaluacion, acta, promedio', 
     'La normativa contempla el Registro Oficial de Evaluación y el acta de evaluación como documentos académicos. Para revisar un error en tu nota, solicita orientación a tu docente, Departamento Académico o Secretaría.'),
    ('Evaluación académica', '¿Qué sucede si desapruebo un curso varias veces?', 
     'desaprobar, tercera matricula, cuarta matricula, repetir curso', 
     'La Normatividad Académica establece consecuencias para determinadas situaciones de tercera y cuarta matrícula, incluso restricciones o anulación de matrícula en ciertos supuestos. El caso debe revisarse con el historial académico y el reglamento vigente.'),
    ('Repositorio institucional', '¿Para qué sirve el Repositorio Institucional de la UNT?', 
     'repositorio, institucional, tesis, trabajos investigacion, publicar', 
     'La Directiva de Repositorio establece procedimientos para registrar tesis y trabajos de investigación en el Repositorio Institucional de la UNT, siguiendo estándares establecidos.'),
    ('Repositorio institucional', '¿Qué documentos se registran en el Repositorio Institucional?', 
     'repositorio, registrar, tesis, trabajos investigacion, grado', 
     'La directiva regula el registro de tesis y trabajos de investigación, incluidos los trabajos conducentes a grados académicos y títulos profesionales.'),
    ('Repositorio institucional', '¿A quiénes alcanza la directiva del repositorio?', 
     'alcance, directiva, repositorio, comunidad universitaria', 
     'La directiva indica que su alcance comprende a la comunidad universitaria en sus diferentes niveles académicos y que su cumplimiento es obligatorio.'),
    ('Repositorio institucional', '¿Qué diferencia hay entre una tesis digitalizada y una sin digitalizar?', 
     'tesis digitalizada, sin digitalizar, repositorio, documento fisico', 
     'La directiva distingue la tesis digitalizada, cuyo documento físico ha sido incorporado en versión digital al repositorio, de la tesis sin digitalizar, que está pendiente de digitalización y registro.'),
    ('Repositorio institucional', '¿Qué se entiende por trabajo de investigación?', 
     'trabajo investigacion, definicion, estudio, fenomeno, documento', 
     'La directiva incluida lo describe como un estudio sobre un fenómeno o hecho, físico o social, cuyas conclusiones se exponen ordenadamente y que puede basarse en documentos, encuestas o entrevistas.'),
    ('Repositorio institucional', '¿Qué es una tesis de grado según la directiva?', 
     'tesis grado, definicion, investigacion, pregrado, posgrado', 
     'La directiva define la tesis de pregrado como un trabajo de investigación al término de la carrera que profundiza en un área del conocimiento, aporta una novedad o revisión crítica y aplica métodos científicos.'),
    ('Repositorio institucional', '¿Qué normativa respalda el registro de tesis en el repositorio?', 
     'base legal, normativa, repositorio, ley universitaria, renati', 
     'La directiva cita, entre otras normas, la Ley Universitaria 30220, la Ley 30035 sobre repositorio nacional digital y disposiciones de SUNEDU sobre RENATI. Para trámites actuales, verifica las normas y directivas vigentes.'),
    ('Integridad académica', '¿Qué resolución incluida regula el grado de similitud de las tesis?', 
     'similitud, tesis, porcentaje, resolucion, 043, 2022', 
     'La Resolución de Consejo Universitario N.° 043-2022-UNT relacionada con el grado de similitud de la tesis. Para conocer el porcentaje permitido y el procedimiento, debe consultarse el texto íntegro y confirmar si hay una norma posterior.'),
    ('Integridad académica', '¿Qué debo hacer si mi tesis presenta un porcentaje alto de similitud?', 
     'similitud alta, tesis, corregir, antiplagio, observacion', 
     'Existe una resolución sobre grado de similitud y una directiva de antiplagio. El chatbot no debe fijar un porcentaje ni declarar una tesis aprobada sin verificar el texto normativo vigente; corresponde revisar el informe y consultar al asesor o unidad responsable.'),
    ('Estatuto y gobierno universitario', '¿Qué documento establece la organización y normas generales de la UNT?', 
     'estatuto, organizacion, universidad, normas, UNT', 
     'El Estatuto Reformado de la Universidad Nacional de Trujillo, que establece disposiciones sobre la organización y funcionamiento universitario. Para una consulta concreta se debe revisar el artículo correspondiente.'),

    # ======== Preguntas basadas en el MOEDUNT (Modelo Educativo de la UNT) ========
    ("Preguntas frecuentes", "¿Quién fundó la Universidad Nacional de Trujillo?",
     "fundo, fundador, fundadores, fundacion, fundada, historia, bolivar, republicana",
     "La Universidad Nacional de Trujillo es la primera universidad republicana del Perú. Fue fundada por "
     "Simón Bolívar y José Faustino Sánchez Carrión."),
    ("Preguntas frecuentes", "¿Cuántas facultades y programas de estudio tiene la UNT?",
     "facultades, programas, carreras, escuelas profesionales, cuantas, cantidad, oferta academica",
     "Según el MOEDUNT, la UNT cuenta con 13 facultades y 45 programas de estudio de pregrado, además de "
     "86 programas de maestría, 26 de doctorado y 76 de segundas especialidades profesionales.\n"
     "(Son cifras del documento; pueden haber cambiado.)"),
    ("Preguntas frecuentes", "¿Dónde están las filiales de la UNT?",
     "filial, filiales, sede, sedes, huamachuco, santiago de chuco, jequetepeque, valle, descentralizadas",
     "La UNT tiene tres filiales en la región La Libertad: Valle Jequetepeque, Huamachuco y Santiago de "
     "Chuco. La sede principal y la ciudad universitaria están en Trujillo."),
    ("Preguntas frecuentes", "¿Cuántos estudiantes y docentes tiene la UNT?",
     "estudiantes, docentes, poblacion, alumnos, profesores, cuantos, servidores, administrativos",
     "Según el MOEDUNT, la UNT atiende a más de 18,000 estudiantes entre pregrado, posgrado y segundas "
     "especialidades. Cuenta con 1,166 docentes y más de 500 servidores administrativos.\n"
     "(Son cifras del documento; pueden haber cambiado.)"),
    ("Preguntas frecuentes", "¿La UNT está licenciada por la SUNEDU?",
     "licenciamiento, licenciada, sunedu, acreditacion, acreditada, acreditados",
     "Según el MOEDUNT, la UNT logró en 2018 su licenciamiento institucional por ocho años de parte de la "
     "SUNEDU, y varios de sus programas de estudio están acreditados. Como ese licenciamiento tiene un "
     "plazo, conviene verificar la situación vigente en el portal de la SUNEDU."),
    ("Preguntas frecuentes", "¿La educación en la UNT es gratuita?",
     "gratuita, gratuito, gratis, gratuidad, publica, pension, mensualidad",
     "Sí. La UNT es una universidad pública que brinda educación superior gratuita; el ingreso es por "
     "concurso público y se basa en el mérito de las capacidades del postulante.\n"
     "Ten en cuenta que la matrícula y los trámites sí tienen derechos de pago (consulta los costos de "
     "matrícula y constancias)."),
    ("Modelo educativo (MOEDUNT)", "¿Qué es el MOEDUNT?",
     "moedunt, modelo educativo, definicion, significa, documento de gestion",
     "El MOEDUNT es el Modelo Educativo de la Universidad Nacional de Trujillo: un documento de gestión "
     "que reúne de forma articulada la concepción, los procesos académicos, administrativos e "
     "interinstitucionales y los fines de la educación universitaria, orientados a formar personas y "
     "profesionales de excelencia, socialmente responsables y comprometidos con el desarrollo sostenible "
     "de la región y del país."),
    ("Modelo educativo (MOEDUNT)", "¿Cuál es la misión de la UNT?",
     "mision, universidad, unt",
     "Según el MOEDUNT, la misión de la UNT es ser la primera universidad republicana del Perú que forma "
     "integralmente a personas y profesionales de excelencia para enfrentar los retos de un mundo complejo"
     " y globalizado, buscando el desarrollo responsable y sostenible de la región y del país."),
    ("Modelo educativo (MOEDUNT)", "¿Cuál es la visión de la UNT?",
     "vision, universidad, unt",
     "La visión planteada en el MOEDUNT era que, al 2025, la UNT estuviera entre las cinco primeras "
     "universidades peruanas, formando personas y profesionales de excelencia que practiquen la "
     "integridad, la identidad y el compromiso institucional y social para impulsar el desarrollo local, "
     "regional y del país.\n"
     "Como esa meta estaba fijada al 2025, conviene confirmar si existe una visión actualizada."),
    ("Modelo educativo (MOEDUNT)", "¿Cuáles son los valores de la UNT?",
     "valores, valor, verdad, justicia, solidaridad, universidad, unt",
     "Los valores de la UNT según el MOEDUNT son: verdad, justicia, excelencia, respeto, libertad, "
     "solidaridad, responsabilidad e integridad."),
    ("Modelo educativo (MOEDUNT)", "¿Cuáles son los principios institucionales de la UNT?",
     "principios, principio, autonomia, interes superior, mejoramiento continuo",
     "La UNT asume los principios de la Ley Universitaria 30220 y, además:\n"
     "a) Búsqueda, cultivo y difusión de la verdad.\n"
     "b) Ejercicio pleno y racional de la autonomía.\n"
     "c) Desarrollo de la sensibilidad y el compromiso social.\n"
     "d) Cultivo del espíritu creativo, crítico, innovador e investigativo.\n"
     "e) Respeto al interés superior del estudiante.\n"
     "f) Valoración de la vida humana en su diversidad cultural.\n"
     "g) Práctica y mejoramiento continuo de la calidad académica.\n"
     "h) Ética pública, profesional y respeto al bien común."),
    ("Modelo educativo (MOEDUNT)", "¿Cuáles son las funciones de la UNT según su modelo educativo?",
     "funciones, funcion, socio-personal, humanista, innovacion, universidad, unt",
     "Según el MOEDUNT, la UNT cumple tres funciones:\n"
     "1. Formación socio-personal y profesional humanista.\n"
     "2. Formación en investigación e innovación para el desarrollo del país.\n"
     "3. Formación en responsabilidad social, con compromiso humano y ecológico."),
    ("Modelo educativo (MOEDUNT)", "¿Qué es el enfoque por competencias?",
     "competencia, competencias, enfoque por competencias, competencia educativa, desempeno",
     "En el MOEDUNT, una competencia educativa es un desempeño complejo, integral e idóneo que compromete "
     "diversas dimensiones humanas (motrices, cognitivas, afectivas y volitivas) para resolver problemas "
     "de la vida y del desempeño profesional, con autonomía, creatividad, criticidad, civismo, conciencia "
     "ecológica y ética.\n"
     "Las competencias pueden ser genéricas (las que todo estudiante debe desarrollar, de forma "
     "transversal en todos los cursos) o específicas (propias de cada carrera profesional)."),
    ("Modelo educativo (MOEDUNT)", "¿Qué enfoques educativos adopta la UNT?",
     "enfoques, modelo educativo, inclusiva, intercultural, ambiental, igualdad, genero, etico, pensamiento complejo",
     "El MOEDUNT adopta estos enfoques:\n"
     "• Educación inclusiva e intercultural\n"
     "• Ambiental\n"
     "• Calidad educativa\n"
     "• Ético y de derechos\n"
     "• Igualdad de género\n"
     "• Desarrollo del pensamiento complejo y crítico\n"
     "• Investigación formativa y desarrollo autónomo\n"
     "• Por competencias"),
    ("Modelo educativo (MOEDUNT)", "¿Qué son los ejes transversales del currículo?",
     "ejes, eje, transversales, transversal",
     "Los ejes transversales son los núcleos que dan soporte y sentido a las experiencias del plan "
     "curricular. El MOEDUNT señala siete:\n"
     "1. Responsabilidad social universitaria\n"
     "2. Investigación formativa\n"
     "3. I+D+i (investigación, desarrollo e innovación)\n"
     "4. Sostenibilidad ambiental\n"
     "5. Ética y ciudadanía\n"
     "6. Identidad, interculturalidad e inclusividad\n"
     "7. Multidisciplinariedad e interdisciplinariedad"),
    ("Modelo educativo (MOEDUNT)", "¿Qué es el sílabo y qué debe contener?",
     "silabo, silabos, sumilla, estructura",
     "El sílabo es un instrumento de gestión académica y curricular que da los lineamientos generales para"
     " desarrollar una asignatura. Su estructura básica incluye: información general, sumilla, "
     "competencias, unidades de aprendizaje, capacidades, contenidos, estrategias metodológicas, "
     "evaluación de los aprendizajes y bibliografía."),
    ("Modelo educativo (MOEDUNT)", "¿Qué es la guía de aprendizaje?",
     "guia, guias, sesion, sesiones, aprendizaje",
     "La guía de aprendizaje es un instrumento de gestión didáctica que orienta el desarrollo de un tema "
     "en una sesión de aprendizaje. Incluye la competencia, las capacidades, el tema y el producto del "
     "aprendizaje, con una estructura de inicio (motivación y saberes previos), proceso (exposición y "
     "debate de la información) y salida (relación con la clase siguiente y tareas)."),
    ("Modelo educativo (MOEDUNT)", "¿Qué es la investigación formativa?",
     "formativa, actitud cientifica, capacidades investigativas",
     "La investigación formativa es una estrategia didáctica por la cual los estudiantes desarrollan de "
     "manera permanente sus competencias y capacidades investigativas dentro de las asignaturas, con el "
     "fin de fortalecer la actitud científica. En el MOEDUNT es además un eje transversal del currículo."),
    ("Modelo educativo (MOEDUNT)", "¿Qué política tiene la UNT sobre el uso de las TIC y la educación virtual?",
     "tic, tics, tecnologias, virtual, virtuales, plataforma, plataformas, digital, digitales",
     "La UNT asumió como política institucional el uso de las TIC y de herramientas y plataformas "
     "virtuales en los procesos de enseñanza-aprendizaje y de gestión institucional, sea cual sea la "
     "modalidad (presencial, semipresencial o no presencial). Quienes participan directamente deben "
     "desarrollar las competencias digitales correspondientes."),
    ("Modelo educativo (MOEDUNT)", "¿Qué perfil debe tener un ingresante a la UNT?",
     "perfil, ingresante, ingresantes, competencias instrumentales, interpersonales, sistemicas",
     "El MOEDUNT describe el perfil general del ingresante en tres tipos de competencias:\n"
     "• Instrumentales: formación básica en TIC, comunicación efectiva, inglés como segunda lengua, acervo"
     " cultural y científico básico, y uso de la lógica y la matemática para resolver problemas.\n"
     "• Interpersonales: actitud proactiva, ética y de respeto a las normas y al medioambiente; autonomía "
     "con equilibrio emocional y salud física y mental.\n"
     "• Sistémicas: aprendizaje autónomo, trabajo en equipo, convivencia democrática, apreciación crítica "
     "de lo artístico-cultural y emprendedurismo económico social."),
    ("Modelo educativo (MOEDUNT)", "¿Quién se encarga de gestionar el modelo educativo?",
     "gestiona, gestion, modelo educativo, vicerrectorado, vicerrectorado academico, encarga, responsable",
     "La gestión del modelo educativo compete directamente al Vicerrectorado Académico (planificación, "
     "implementación, ejecución y evaluación). La complementan los Decanos, los Directores de Escuelas "
     "Profesionales, los Directores de Departamentos Académicos y el estamento docente."),
    ("Admisión y CEPUNT", "¿Qué es el SINUNT?",
     "sinunt, sistema de ingreso",
     "SINUNT es el Sistema de Ingreso a la Universidad Nacional de Trujillo. Es obligatorio y semestral "
     "(16 semanas): prepara a los egresados de la educación básica mediante una evaluación integral, "
     "progresiva, cualitativa y cuantitativa, que pondera sus competencias según el área y el programa "
     "profesional al que postulan."),
    ("Admisión y CEPUNT", "¿Qué es el CEPUNT?",
     "cepunt, preuniversitario, centro preuniversitario",
     "El CEPUNT es el Centro Preuniversitario de la UNT, donde funciona el sistema de ingreso. Cuenta con "
     "docentes especialmente seleccionados, y la evaluación y acreditación de postulantes e ingresantes "
     "está a cargo de la Dirección de Admisión. Según el MOEDUNT, el programa es autofinanciado por los "
     "postulantes mediante escalas pensionarias."),
    ("Admisión y CEPUNT", "¿Cómo se desarrolla el proceso de admisión en la UNT?",
     "admision, postular, postulante, postulantes, unidades, orden de merito, lista de ingresantes",
     "El ingreso se desarrolla por asignaturas organizadas en tres unidades académicas. Al terminar cada "
     "unidad se dan a conocer los promedios y, al finalizar la tercera, se publica la lista de ingresantes"
     " a cada programa profesional en estricto orden de mérito. La evaluación está regulada por un "
     "reglamento específico, propuesto por la Dirección de Admisión y aprobado por el Consejo "
     "Universitario."),
    ("Admisión y CEPUNT", "¿Cuáles son las áreas académicas del sistema de ingreso?",
     "areas, area, ciencias de la vida, ciencias basicas, ciencias de la persona, ciencias economicas",
     "El sistema de ingreso se organiza en cuatro áreas académicas: Ciencias de la vida y la salud, "
     "Ciencias básicas y tecnológicas, Ciencias de la persona y Ciencias económicas. Cada una tiene sus "
     "planes curriculares y asignaturas por créditos."),
    ("Admisión y CEPUNT", "¿Qué diferencia hay entre admisión ordinaria y extraordinaria?",
     "ordinaria, extraordinaria, exceptuados, beneficiarios, nivelacion",
     "Admisión ordinaria: es el proceso selectivo único del SINUNT, abierto a quienes postulan por mérito.\n"
     "Admisión extraordinaria: está dirigida a beneficiarios exceptuados de la modalidad ordinaria por la "
     "Ley Universitaria y otras normas; igualmente pasan por un proceso de nivelación y evaluación "
     "integral de competencias y actitudes para acceder a una vacante. Quien no alcance vacante puede "
     "participar en el proceso ordinario o esperar otra oportunidad."),
    ("Admisión y CEPUNT", "¿Puedo convalidar asignaturas aprobadas en el CEPUNT?",
     "sobresaliente, 16, dieciseis, convalidar, asignaturas, ingresantes",
     "En algunos casos sí. Según el MOEDUNT, los ingresantes que aprobaron ciertas asignaturas del sistema"
     " de ingreso con nota sobresaliente (igual o mayor a 16) pueden convalidar hasta tres asignaturas de "
     "los estudios generales o específicos posteriores, previa evaluación de la Escuela Profesional "
     "correspondiente."),
    ("Régimen de estudios y créditos", "¿Cuántos años y ciclos dura una carrera de pregrado en la UNT?",
     "duracion, dura, duran, anos, ciclos, diez, cinco",
     "Los programas de pregrado duran cinco años, es decir, diez ciclos académicos de 22 créditos cada uno"
     " (220 créditos en total). Los programas de seis y siete años, como Derecho, Medicina y Farmacia, "
     "aumentan proporcionalmente su creditaje."),
    ("Régimen de estudios y créditos", "¿Cuánto dura un semestre académico?",
     "semestre, semestres, semanas, dieciseis, impares, pares",
     "Cada semestre dura 16 semanas y solo se desarrollan dos semestres por año académico. En el primer "
     "semestre se llevan los ciclos impares y en el segundo, los ciclos pares."),
    ("Régimen de estudios y créditos", "¿Cuántos créditos tiene una carrera de pregrado?",
     "creditos, creditaje, 220, carrera, pregrado, total, egresar, egreso",
     "Una carrera de pregrado tiene 220 créditos académicos (10 ciclos de 22 créditos). El creditaje se "
     "distribuye así: 16 % estudios generales, 24 % estudios específicos y 60 % estudios de especialidad."),
    ("Régimen de estudios y créditos", "¿Cuántos cursos se programan como máximo por ciclo?",
     "asignaturas, modulos, seis, programan, ciclo, maximo, cursos",
     "El MOEDUNT establece que en cada ciclo se programan y desarrollan como máximo seis (6) asignaturas o"
     " módulos. En los últimos ciclos se enfatiza el trabajo de investigación científica orientado a la "
     "graduación y titulación, y las prácticas preprofesionales."),
    ("Régimen de estudios y créditos", "¿Qué son los estudios generales y cuántos créditos tienen?",
     "generales, general, estudios generales, humanisticas",
     "Los estudios generales son el inicio de la formación integral del estudiante: desarrollan "
     "competencias humanísticas, científicas y tecnológicas. En la UNT se desarrollan de forma escalonada "
     "a lo largo de toda la carrera, con un mínimo de 35 créditos (alrededor del 16 % del creditaje), y "
     "los gestionan las Escuelas Profesionales bajo la supervisión del Vicerrectorado Académico."),
    ("Régimen de estudios y créditos", "¿Qué modalidades de estudio existen y cuánto puede ser virtual?",
     "modalidad, modalidades, presencial, semipresencial, virtual, virtuales, clases virtuales, distancia, setenta",
     "Los estudios pueden desarrollarse en modalidad presencial, semipresencial o a distancia (no "
     "presencial), según las disposiciones legales. La educación no presencial puede llegar hasta el 70 % "
     "del creditaje total de los programas de pregrado, posgrado y segundas especialidades."),
    ("Régimen de estudios y créditos", "¿Cuándo empiezan las prácticas preprofesionales?",
     "practicas, practica, preprofesionales, preprofesional, pre profesional",
     "Las prácticas preprofesionales se diseñan y ejecutan en tres niveles (iniciales, intermedias y "
     "finales) a partir del quinto ciclo de estudios, según las particularidades de cada programa. "
     "Consulta con tu Escuela los requisitos específicos para realizarlas."),
    ("Régimen de estudios y créditos", "¿Puedo obtener un certificado por módulos de competencia profesional?",
     "modulo, modulos, modular, certificado, articulo 40",
     "Según la Ley Universitaria 30220 (art. 40), las carreras de pregrado pueden organizarse por módulos "
     "de competencia profesional. Al concluir un módulo se puede obtener un certificado que facilite la "
     "incorporación al mercado laboral; para ello el estudiante debe elaborar y sustentar un proyecto que "
     "demuestre la competencia alcanzada.\n"
     "Consulta con tu Escuela si tu plan de estudios está organizado por módulos."),
    ("Evaluación académica", "¿Cuál es la nota mínima para aprobar un curso?",
     "nota minima, curso, aprobar, apruebo, aprueba, aprobado, aprobada, aprobatoria, aprobatorio, catorce, 14, vigesimal",
     "La nota mínima aprobatoria en la UNT es catorce (14). El sistema de calificación es vigesimal, de 0 "
     "a 20."),
    ("Evaluación académica", "¿Cómo es la escala de calificación cualitativa?",
     "escala, cualitativa, excelente, bueno, regular, deficiente, calificacion",
     "En casos específicos puede usarse una escala cualitativa: Excelente = 20; Muy bueno = 17 a 19; Bueno"
     " = 14 a 16; Regular = 11 a 13; Deficiente = 0 a 10. La nota mínima aprobatoria sigue siendo 14."),
    ("Evaluación académica", "¿El medio punto favorece al estudiante en el promedio?",
     "medio punto, redondeo, redondear, decimal, favorece",
     "Sí. Según el MOEDUNT, el medio punto en los promedios favorece al estudiante. Recuerda que la nota "
     "mínima aprobatoria es 14."),
    ("Evaluación académica", "¿Qué tipos de evaluación se aplican en la UNT?",
     "tipos, evaluacion, autoevaluacion, coevaluacion, heteroevaluacion, diagnostica, sumativa",
     "El MOEDUNT contempla la autoevaluación (del estudiante), la coevaluación (entre pares) y la "
     "heteroevaluación (del docente al estudiante), así como evaluación de inicio, de proceso y de salida,"
     " de tipo diagnóstica, formativa o sumativa. Se recomienda usar principalmente la evaluación de "
     "proceso y la formativa."),
    ("Evaluación académica", "¿Qué técnicas e instrumentos de evaluación se usan?",
     "instrumentos, tecnicas, rubrica, portafolio, lista de cotejo, observacion, interrogatorio",
     "El MOEDUNT sugiere:\n"
     "• Observación: guía de observación, registro anecdótico, diario de clase, escala de actitudes.\n"
     "• Desempeño de los alumnos: preguntas sobre el procedimiento, cuadernos, organizadores gráficos.\n"
     "• Análisis del desempeño: portafolio, rúbrica, lista de cotejo.\n"
     "• Interrogatorio: debate, ensayo, pruebas orales o escritas."),
    ("Posgrado y segunda especialidad", "¿Cuántos créditos mínimos tienen los programas de posgrado?",
     "posgrado, postgrado, diplomado, diplomados, creditos minimos, minimos",
     "Los programas de posgrado son semestrales y tienen estos créditos mínimos: diplomados, 24; "
     "maestrías, 48; doctorados, 64; y segunda especialidad profesional, 40."),
    ("Posgrado y segunda especialidad", "¿Qué tipos de maestría existen y cuánto duran?",
     "maestria, maestrias, maestro, magister, dura, duran, duracion",
     "Hay dos tipos de maestría: de especialidad, que dura dos semestres académicos, y de investigación, "
     "que dura cuatro semestres académicos. Toda maestría requiere un mínimo de 48 créditos."),
    ("Posgrado y segunda especialidad", "¿Qué es una segunda especialidad profesional y qué requisitos tiene?",
     "segunda especialidad, segundas especialidades, residentado",
     "La segunda especialidad profesional conduce a un segundo título. Según la Ley Universitaria 30220 "
     "requiere licenciatura u otro título profesional equivalente, haber aprobado estudios de mínimo dos "
     "semestres académicos con al menos 40 créditos, y aprobar una tesis o un trabajo académico. El "
     "residentado médico se rige por sus propias normas."),
    ("Posgrado y segunda especialidad", "¿Para qué sirven los estudios de doctorado?",
     "doctorado, doctorados, doctor, doctoral",
     "Los programas de doctorado buscan perfeccionar las capacidades académicas y de investigación en "
     "redes nacionales e internacionales, para contribuir a resolver problemas sociales, económicos, "
     "políticos y culturales de la región y del país. Requieren un mínimo de 64 créditos y conducen al "
     "grado de Doctor."),
    ("Posgrado y segunda especialidad", "¿Qué es la formación continua?",
     "formacion, continua, talleres, actualizacion, perfeccionamiento",
     "Son estudios complementarios a la formación profesional que permiten actualizarse y perfeccionarse "
     "durante toda la vida profesional. Pueden ser presenciales, semipresenciales o no presenciales, "
     "mediante talleres, cursos, diplomados y otras actividades."),
    ("Servicios universitarios", "¿Qué servicios de bienestar universitario ofrece la UNT?",
     "bienestar, comedor, medica, odontologica, psicologica, social, salud, medico",
     "Según el MOEDUNT, la UNT ofrece servicios de bienestar universitario como comedor universitario, "
     "atención médica, odontológica y psicológica, asistencia social, y espacios para prácticas artísticas"
     " y deportivas. También cuenta con una clínica de estomatología."),
    ("Servicios universitarios", "¿Qué bibliotecas y laboratorios tiene la UNT?",
     "donde, biblioteca, bibliotecas, laboratorio, laboratorios, computo, auditorio",
     "Según el MOEDUNT, la UNT cuenta con una biblioteca central, una biblioteca de posgrado y bibliotecas"
     " por facultades y escuelas; laboratorios experimentales y de cómputo; un auditorio central con "
     "capacidad para más de 500 personas y cuatro auditorios más pequeños; institutos de investigación, "
     "terreno deportivo y áreas verdes."),
    ("Servicios universitarios", "¿Dónde puedo estudiar idiomas en la UNT?",
     "idiomas, idioma, ingles, cidunt, centro de idiomas, lengua",
     "La UNT cuenta con el Centro de Idiomas (CIDUNT). Para conocer los idiomas, niveles, horarios y "
     "costos, consulta directamente en ese centro. Recuerda además que para obtener el grado se exige el "
     "dominio de un idioma extranjero o lengua nativa, según el reglamento de cada facultad."),
    ("Servicios universitarios", "¿Puedo hacer movilidad o intercambio con otras universidades?",
     "convenios, internacionalizacion, redes, universidades, otras universidades",
     "La UNT impulsa la movilidad de estudiantes y docentes desde y hacia otras universidades mediante "
     "convenios nacionales e internacionales, y busca integrar redes académicas para el intercambio y la "
     "cooperación. Para conocer las convocatorias vigentes, consulta con tu Escuela."),
    ("Servicios universitarios", "¿Dónde queda la ciudad universitaria y el Rectorado?",
     "ciudad, universitaria, rectorado, vicerrectorados, local central, campus",
     "Según el MOEDUNT, la ciudad universitaria de la sede Trujillo alberga a 44 escuelas profesionales, y"
     " la Facultad de Medicina tiene su propio campus. La mayor parte de las oficinas administrativas, "
     "incluido el Rectorado y los Vicerrectorados, funcionan en el local central del Centro de Trujillo. "
     "Las filiales tienen sus propios campus."),
     ("Movilidad estudiantil (RPU)", "¿Qué es el Programa de Movilidad Estudiantil de la UNT?",
         "movilidad, intercambio, intercambios, rpu, programa, red peruana, intercambio estudiantil, estudiantes de otras universidades",
          "Es el programa con el que la UNT recibe a estudiantes de las universidades de la RPU (Red Peruana de Universidades) que quieran hacer una movilidad en la UNT. Cada universidad participante es responsable de seleccionar a sus estudiantes.\n"
        "(La información viene de la página de movilidad de la UNT, que cita la convocatoria 2020-1; confirma las fechas vigentes con la oficina de movilidad.)"),
    ("Movilidad estudiantil (RPU)", "¿Qué requisitos piden para postular a la movilidad estudiantil?",
        "movilidad, intercambio, intercambios, requisitos, postular, postulacion, quinto superior, cincuenta, mitad de la carrera",
        "Cada universidad selecciona a sus estudiantes, que deben cumplir estos requisitos:\n"
        "• Haber aprobado al menos el 50 % de la carrera.\n"
        "• Estar matriculado en la universidad de origen al momento de postular.\n"
        "• Pertenecer al quinto superior entre los estudiantes de su especialidad.\n"
        "• No haber realizado antes un semestre de intercambio en la universidad de destino."),
     ("Movilidad estudiantil (RPU)", "¿Qué documentos debo presentar para la movilidad estudiantil?",
        "movilidad, intercambio, intercambios, documentos, carta de presentacion, dni, seguro, sis, fotografias, ficha de inscripcion, firmados",
        "Adjunta solo lo solicitado:\n"
        "1. Carta de presentación de la universidad de origen.\n"
        "2. Fotocopia del DNI.\n"
        "3. Ficha de matrícula.\n"
        "4. Dos fotografías tamaño pasaporte, a color y con fondo blanco.\n"
        "5. Fotocopia de un seguro (puede ser el SIS).\n"
        "6. Certificado de notas o historial académico de la universidad de origen (copia simple).\n"
        "7. Ficha de inscripción.\n"
        "Los documentos 3, 4, 5 y 6 deben estar firmados por el coordinador RPU de la universidad de origen."),
    ("Movilidad estudiantil (RPU)", "¿Qué beneficios tienen los estudiantes de movilidad en la UNT?",
        "movilidad, intercambio, intercambios, beneficios, beneficio, comedor, derechos, obligaciones",
        "A los estudiantes de movilidad se les gestiona el beneficio del comedor universitario, y tienen los mismos derechos y obligaciones que los estudiantes regulares de la UNT."),
    ("Movilidad estudiantil (RPU)", "¿Cuánto cuesta la movilidad estudiantil?",
        "movilidad, intercambio, intercambios, costo, cuesta, pago, pagar, exoneracion, gastos, alimentacion, alojamiento, transporte",
        "La UNT ofrece exoneración de costos académicos. Quien hace la movilidad asume sus gastos personales de alimentación, alojamiento y transporte (el comedor universitario se gestiona como beneficio)."),
    ("Movilidad estudiantil (RPU)", "¿Dónde me inscribo y con quién me comunico para la movilidad estudiantil?",
        "movilidad, intercambio, intercambios, inscribo, inscripcion, inscribirme, convocatoria, contacto, comunico, correo, oia, coordinador, rpu",
        "La ficha de inscripción está en: http://oia.unitru.edu.pe/images/movilidadestudiantilunt.pdf\n"
        "La convocatoria se publica en: https://rpu.edu.pe/convocatoria/universidad-nacional-trujillo-unt/\n"
        "Para más información escribe al coordinador de la RPU en la UNT: oia@unitru.edu.pe o rpu@unitru.edu.pe."),
        # ======== Carné universitario ========
    ("Carné universitario", "¿Cómo solicito mi carné universitario?",
     "carne, carnet, universitario, solicitar, solicito, tramitar, sacar, obtener, renovar, primera, vez, caducidad, requisitos",
     "Para solicitar tu carné universitario:\n"
     "1.Ingresa a https://tramites-uraa.unitru.edu.pe y crea tu cuenta con tu correo institucional (o inicia sesión si ya tienes una).\n"
     "2.Entra a registrar trámite y elige el trámite del carné.\n"
     "3.Sube tu foto y el comprobante de pago.\n"
     "4.Envía la solicitud.\n"
     "El carné se tramita solo durante las convocatorias de cada semestre."),
    ("Carné universitario", "¿Cuánto cuesta el carné universitario?",
     "carne, carnet, costo, cuanto, regular, duplicado",
     "Regular (primera vez o renovación por caducidad): S/ 20.70.\n"
     "Duplicado (si lo extraviaste o se deterioró): S/ 30.00."),
    ("Carné universitario", "¿Qué hago si perdí o se deterioró mi carné?",
     "carne, carnet, perdi, perdio, perdida, extravie, extravio, extraviado, deterioro, deteriorado, duplicado, robaron, malogrado",
     "Debes solicitar un duplicado en https://tramites-uraa.unitru.edu.pe durante una convocatoria. "
     "Sube tu foto y el comprobante de pago. Costo del duplicado: S/ 30.00."),
    ("Carné universitario", "¿Cómo pago el carné?",
     "carne, carnet, pago, pagar, banco, interbank, codigo, tesoreria, ventanilla",
     "Código de pago: 005-166-17 Registro Técnico.\n"
     "Alumnos de la Sede Trujillo: de preferencia en Ventanilla de Tesorería.\n"
     "Opcional: en los canales del Banco Interbank (ventanillas, agentes o transferencias Interbank a Interbank)."),
    ("Carné universitario", "¿Cuándo es la convocatoria para el carné?",
     "carne, carnet, convocatoria, convocatorias, fecha, fechas, plazo, inicio, cierre, cuando, abre",
     "El carné se tramita solo en las convocatorias de cada semestre y las fechas cambian. "
     "Revisa los comunicados de la URA (Unidad de Registro Académico) o la plataforma https://tramites-uraa.unitru.edu.pe."),

    # ======== Bachiller y certificado (PDF de la escuela) ========
    ("Titulacion", "¿Cuánto cuesta el bachiller?",
     "bachiller, grado, costo, cuanto, carpeta, derecho, bachillerato",
     "Para el grado de bachiller hay dos pagos:\n"
     "1.Carpeta de bachiller: S/ 200.00 (Tesorería o Cta. Cte. Interbank).\n"
     "2.Derecho de bachillerato: S/ 223.90 (Interbank, código de servicio 005-186-17).\n"
     "Si tienes dudas sobre cuál aplica a tu caso, confirma en la secretaría."),
    ("Titulacion", "¿Qué documentos presento en la carpeta para obtener el grado de bachiller?",
     "carpeta, bachiller, grado, documentos, requisitos, presentar, mesa, partes, decanato, obtener",
     "Presenta la carpeta en Mesa de Partes de Decanato (presencial o por correo a mesadepartes_ingenieria@unitru.edu.pe) con:\n"
     "1.Formato de Grado de Bachiller (viene en la carpeta), debidamente llenado.\n"
     "2.Voucher de pago (S/ 200.00).\n"
     "3.Certificado de estudios por 5 años.\n"
     "4.DNI.\n"
     "5.Una foto tamaño pasaporte con logo UNT, tomada en el estudio fotográfico de la UNT.\n"
     "6.Constancia de no adeudo (se solicita en Biblioteca)."),
    ("Titulacion", "¿Cómo saco la constancia de no adeudo?",
     "constancia, adeudo, deuda, biblioteca, adeudar",
     "La constancia de no adeudo se solicita en Biblioteca. Contacto: Sr. Valerio Ynfantes, 940643220."),
    ("Certificados y convalidación", "¿Cuánto cuesta el certificado de estudios?",
     "certificado, costo, cuanto, pago, pagar",
     "El certificado de estudios cuesta S/ 75.00. Se paga en Tesorería (local central) o en la Cta. Cte. Interbank (código de servicio 005-166-17)."),
    ("Certificados y convalidación", "¿Qué necesito para registrar mi trámite de certificado de estudios?",
     "certificado, requisitos, registrar, registro, documentos, adjuntar, voucher, operacion",
     "En el formulario de registro debes ingresar:\n"
     "1.Tus datos personales, la Facultad y la Escuela.\n"
     "2.El motivo (solicita certificado digital de estudios).\n"
     "3.La entidad donde pagaste y el número de operación bancaria (adjunta la evidencia).\n"
     "4.Una foto actual a color, tamaño carnet, con fondo blanco y logo de la UNT.\n"
     "5.Tu DNI.\n"
     "Consultas: ort@unitru.edu.pe"),   
]


def sincronizar_datos(conn):
    """Pone la base al día con los TRAMITES y PREGUNTAS escritos arriba.

    - Agrega lo que falta y actualiza el texto de lo que ya existe (se compara por
      el texto de la pregunta y por el nombre del trámite).
    - NO borra el historial de consultas, ni las preguntas creadas desde el panel,
      ni cambia si una pregunta está activa o desactivada.
    Devuelve (preguntas_nuevas, preguntas_actualizadas).
    """
    ids = {}
    for nombre, desc in TRAMITES:
        fila = conn.execute("SELECT id FROM tramites WHERE nombre = ?", (nombre,)).fetchone()
        if fila:
            conn.execute("UPDATE tramites SET descripcion = ? WHERE id = ?", (desc, fila["id"]))
            ids[nombre] = fila["id"]
        else: 
            ids[nombre] = conn.execute(
                "INSERT INTO tramites (nombre, descripcion) VALUES (?, ?)", (nombre, desc)
            ).lastrowid

    nuevas = actualizadas = 0
    for tramite, pregunta, claves, respuesta in PREGUNTAS:
        fila = conn.execute(
            "SELECT id, tramite_id, palabras_clave, respuesta FROM preguntas_frecuentes "
            "WHERE pregunta = ?", (pregunta,)).fetchone()
        if fila is None:
            conn.execute(
                "INSERT INTO preguntas_frecuentes (tramite_id, pregunta, palabras_clave, respuesta) "
                "VALUES (?, ?, ?, ?)", (ids[tramite], pregunta, claves, respuesta))
            nuevas += 1
        elif (fila["tramite_id"], fila["palabras_clave"], fila["respuesta"]) != (ids[tramite], claves, respuesta):
            conn.execute(
                "UPDATE preguntas_frecuentes SET tramite_id = ?, palabras_clave = ?, respuesta = ? "
                "WHERE id = ?", (ids[tramite], claves, respuesta, fila["id"]))
            actualizadas += 1
    return nuevas, actualizadas


def init_db(con_datos=True):
    """Crea las tablas (si faltan) y sincroniza las preguntas con este archivo.

    Se ejecuta cada vez que arranca la app, así las preguntas nuevas aparecen sin
    borrar nada. Devuelve (preguntas_nuevas, preguntas_actualizadas).
    """
    resultado = (0, 0)
    with conexion() as conn:
        conn.executescript(ESQUEMA)
        columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(consultas)")}
        for nombre_col in ("nombre", "correo", "codigo", "detalle", "tipo"):
            if nombre_col not in columnas:
                conn.execute(f"ALTER TABLE consultas ADD COLUMN {nombre_col} TEXT")
        # Consultas antiguas (sin tipo): se clasifican con lo que ya se guardó.
        # faq = respondida con una pregunta frecuente; derivada = pasó a la secretaría;
        # social = saludos, despedidas y charla (no cuentan como consulta académica).
        conn.execute(
            "UPDATE consultas SET tipo = CASE WHEN faq_id IS NOT NULL THEN 'faq' "
            "WHEN derivada = 1 THEN 'derivada' ELSE 'social' END WHERE tipo IS NULL")
        if con_datos:
            resultado = sincronizar_datos(conn)
    try:
        os.chmod(ruta_db(), 0o600)  # solo el dueño del archivo puede leerlo
    except OSError:
        pass
    return resultado


def reiniciar_db():
    """Guarda una copia de la base actual y crea una nueva desde cero (pierde el historial)."""
    ruta = Path(ruta_db())
    copia = None
    if ruta.exists():
        copia = ruta.with_name(f"{ruta.stem}_anterior_{datetime.now():%Y%m%d_%H%M%S}{ruta.suffix}")
        shutil.copy2(ruta, copia)
        ruta.unlink()
    init_db()
    return copia


if __name__ == "__main__":
    if "--reiniciar" in sys.argv:
        copia = reiniciar_db()
        print("Base reiniciada desde cero." + (f" Copia de la anterior: {copia}" if copia else ""))
    else:
        nuevas, actualizadas = init_db()
        print(f"Base de datos lista en: {ruta_db()}")
        print(f"Preguntas agregadas: {nuevas} | actualizadas: {actualizadas}")
    with conexion() as c:
        total, activas = c.execute(
            "SELECT COUNT(*), COALESCE(SUM(activa), 0) FROM preguntas_frecuentes").fetchone()
    print(f"Preguntas en la base: {total} ({activas} activas)")
