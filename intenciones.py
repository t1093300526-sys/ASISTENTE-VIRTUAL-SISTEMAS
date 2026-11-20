"""Charla social del asistente: saludos, despedidas, agradecimientos y preguntas no académicas.

¿Cómo funciona?
  1. El mensaje se normaliza (minúsculas, sin tildes) y se separa en palabras.
  2. Se buscan las FRASES de cada intención dentro del mensaje (ver INTENCIONES).
  3. Si TODO el mensaje está formado por frases de cortesía (más palabras de relleno
     como "por favor"), es charla social y se responde aquí, sin consultar las preguntas
     frecuentes. Si el mensaje trae además una consulta ("hola, ¿cuánto cuesta la
     matrícula?"), se ignora el saludo y se responde la consulta.

¿Cómo agregar algo nuevo (por ejemplo, una nueva forma de saludar)?
  - Una frase nueva en una intención que ya existe: escribe la frase en la lista "frases"
    (en minúsculas; las tildes no importan).
  - Una intención nueva: agrega una entrada a INTENCIONES con "prioridad", "frases" y
    "respuesta" (un texto o una función). Después agrega una prueba en tests.py.
"""
import os
import re
import unicodedata
from datetime import datetime
from difflib import get_close_matches


def palabras(texto):
    """Minúsculas, sin tildes y separado en palabras ("holaaa" -> "hola")."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"([a-zñ])\1{2,}", r"\1", texto)   # letras repetidas 3+ veces: "holaaa", "graciaaas"
    return re.findall(r"[a-zñ0-9]+", texto)


# ---------------------------------------------------------------------------
# Respuestas (cada una recibe las palabras del mensaje y las preguntas activas)
# ---------------------------------------------------------------------------
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

TEMAS_BREVES = ("matrícula, constancias, retiros, certificados, titulación, normativa académica "
                "y datos de la universidad")


def _contacto():
    return os.environ.get("CONTACTO_SECRETARIA", "la secretaría de la escuela")


def _fija(texto):
    return lambda crudas, faqs: (texto, [])


def _saludo_corto(crudas):
    if "tardes" in crudas:
        return "¡Buenas tardes!"
    if "noches" in crudas:
        return "¡Buenas noches!"
    if "dias" in crudas or ("buen" in crudas and "dia" in crudas):
        return "¡Buenos días!"
    return "¡Hola!"


def _r_saludo(crudas, faqs):
    return (f"{_saludo_corto(crudas)} Soy el asistente virtual de la Escuela de Ingeniería de Sistemas de la UNT. "
            f"Puedo orientarte sobre {TEMAS_BREVES}. ¿En qué te ayudo?"), []


def _r_ayuda(crudas, faqs):
    temas = []
    for f in faqs:
        if f["tramite"] and f["tramite"] not in temas:
            temas.append(f["tramite"])
    ejemplos, vistos = [], set()
    for f in faqs:                       # una pregunta de ejemplo por cada uno de los primeros trámites
        if f["tramite"] and f["tramite"] not in vistos and len(ejemplos) < 5:
            vistos.add(f["tramite"])
            ejemplos.append(f["pregunta"])
    texto = ("¡Claro! Puedo ayudarte con: " + ", ".join(temas) + ". "
             "Escribe tu pregunta con tus palabras o prueba con alguna de estas.") if temas else \
            "¡Claro! Escribe tu pregunta con tus palabras y te ayudo."
    return texto, ejemplos


def _r_hora(crudas, faqs):
    ahora = datetime.now()
    articulo = "Es la" if ahora.hour == 1 else "Son las"
    return f"Según el reloj del sistema, {articulo.lower()} {ahora:%H:%M} h.", []


def _r_fecha(crudas, faqs):
    ahora = datetime.now()
    return f"Hoy es {DIAS[ahora.weekday()]} {ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}.", []


def _r_queja(crudas, faqs):
    return ("Lamento que no haya podido ayudarte como esperabas. Intenta escribir tu consulta con otras "
            "palabras o escribe «ayuda» para ver los temas que manejo. "
            f"Si tu caso es urgente, comunícate directamente con {_contacto()}."), []


# ---------------------------------------------------------------------------
# Intenciones. "prioridad": si el mensaje trae varias, se responde la de mayor prioridad
# (el saludo, que es la más baja, solo se antepone: "¡Hola! Muy bien, gracias...").
# Las frases van en minúsculas; las tildes no importan.
# ---------------------------------------------------------------------------
INTENCIONES = {
    "queja": {
        "prioridad": 8,
        "frases": ["no sirves", "no sirve", "eres tonto", "eres tonta", "eres inutil", "eres malo", "eres mala",
                   "eres estupido", "eres idiota", "eres un asco", "eres una basura", "estupido", "idiota",
                   "tonto", "inutil", "no me ayudas", "no me entiendes", "no entiendes", "no funciona",
                   "no me sirve", "mal servicio", "que mal servicio", "pesimo", "pesimo servicio",
                   "no me respondes", "no respondes", "no sabes", "no sabes nada", "que mala respuesta"],
        "respuesta": _r_queja,
    },
    "no_entendi": {
        "prioridad": 7,
        "frases": ["no entiendo", "no comprendo", "no entendi", "no te entiendo", "no me queda claro",
                   "no me quedo claro", "no esta claro", "explicame mejor", "explicalo mejor",
                   "puedes explicarlo mejor", "mas claro", "explica de nuevo", "otra vez", "de nuevo", "repite",
                   "puedes repetir"],
        "respuesta": _fija("Disculpa si no fui claro. Cuéntame qué parte no entendiste o escribe tu consulta con "
                           "otras palabras y la explico de otra manera."),
    },
    "despedida": {
        "prioridad": 6,
        "frases": ["adios", "chau", "chao", "bye", "hasta luego", "hasta pronto", "hasta manana",
                   "hasta la proxima", "hasta otro dia", "nos vemos", "nos vemos luego", "nos vemos pronto",
                   "me despido", "me voy", "que tengas buen dia", "que tengas buena tarde",
                   "que tengas buena noche", "que te vaya bien", "cuidate", "eso es todo", "eso seria todo",
                   "es todo", "nada mas", "ya no tengo mas dudas", "ya no tengo mas preguntas",
                   "no tengo mas dudas", "no tengo mas preguntas", "hasta aqui"],
        "respuesta": _fija("¡Hasta luego! Gracias por usar el asistente. Si más adelante tienes otra duda sobre tus "
                           "trámites, aquí estaré."),
    },
    "agradecimiento": {
        "prioridad": 6,
        "frases": ["gracias", "muchas gracias", "muchisimas gracias", "mil gracias", "gracias totales",
                   "te agradezco", "se agradece", "agradecido", "agradecida", "thanks", "thank you", "grax",
                   "gracias por tu ayuda", "gracias por la ayuda", "gracias por la informacion",
                   "gracias por todo", "gracias por responder", "gracias por tu respuesta",
                   "gracias por la respuesta", "gracias por ayudarme", "muchas gracias por tu ayuda",
                   "muchas gracias por la informacion", "muchas gracias por todo"],
        "respuesta": _fija("¡De nada! Me alegra haberte ayudado. Si tienes otra consulta, aquí estaré."),
    },
    "cumplido": {
        "prioridad": 5,
        "frases": ["eres inteligente", "eres genial", "eres muy util", "eres util", "eres el mejor",
                   "eres lo maximo", "buen trabajo", "buen bot", "excelente servicio", "muy buen servicio",
                   "te quiero", "te amo", "me encantas", "me caes bien", "bien hecho", "felicitaciones",
                   "felicidades", "eres amable", "muy amable"],
        "respuesta": _fija("¡Gracias por tus palabras! Me alegra poder ayudarte. ¿Hay algo más que quieras consultar?"),
    },
    "hora": {
        "prioridad": 5,
        "frases": ["que hora es", "que horas son", "dime la hora", "la hora", "hora actual", "tienes hora",
                   "me das la hora", "sabes que hora es", "me dices la hora", "me dices que hora es",
                   "podrias decirme la hora", "puedes decirme la hora", "me puedes decir la hora",
                   "que hora es ahora", "que hora es hoy"],
        "respuesta": _r_hora,
    },
    "fecha": {
        "prioridad": 5,
        "frases": ["que dia es", "que dia es hoy", "hoy que dia es", "que fecha es", "que fecha es hoy",
                   "fecha de hoy", "la fecha", "fecha actual", "a cuantos estamos", "que dia estamos",
                   "me dices la fecha", "dime la fecha", "dime que dia es", "sabes que dia es"],
        "respuesta": _r_fecha,
    },
    "clima": {
        "prioridad": 4,
        "frases": ["como esta el clima", "que clima hace", "va a llover", "hace frio", "hace calor", "temperatura",
                   "clima", "como esta el tiempo", "pronostico", "que tiempo hace", "el clima"],
        "respuesta": _fija("No tengo acceso a información del clima. Puedo orientarte con trámites y normas de la UNT; "
                           "escribe «ayuda» para ver los temas."),
    },
    "chiste": {
        "prioridad": 4,
        "frases": ["chiste", "dime un chiste", "cuentame un chiste", "un chiste", "cuenta un chiste",
                   "algo gracioso", "hazme reir", "cuentame algo gracioso"],
        "respuesta": _fija("Va uno de sistemas: ¿por qué los programadores confunden Halloween con Navidad? "
                           "Porque OCT 31 = DEC 25. Y si tienes alguna duda de trámites, aquí estoy."),
    },
    "identidad": {
        "prioridad": 4,
        "frases": ["quien eres", "que eres", "como te llamas", "cual es tu nombre", "tu nombre", "eres un robot",
                   "eres robot", "eres una persona", "eres humano", "eres real", "eres un bot", "eres una ia",
                   "eres inteligencia artificial", "hablo con una persona", "hablo con un humano",
                   "eres una persona real", "eres un humano", "quien habla", "con quien hablo"],
        "respuesta": _fija("Soy el asistente virtual de la Escuela de Ingeniería de Sistemas de la UNT. No soy una persona: "
                           "soy un programa que responde con la información registrada sobre trámites y normativa. "
                           "Si tu caso necesita atención personal, puedo derivar tu consulta a la secretaría."),
    },
    "creador": {
        "prioridad": 4,
        "frases": ["quien te creo", "quien te hizo", "quien te programo", "quien te desarrollo", "quien te diseno",
                   "quien es tu creador", "quienes te crearon", "para que te crearon", "quien te invento",
                   "quien te construyo", "cual es tu creador", "tu creador"],
        "respuesta": _fija("Fui desarrollado como parte de un proyecto de investigación de estudiantes de la Escuela de "
                           "Ingeniería de Sistemas de la Universidad Nacional de Trujillo, con el fin de orientar a los "
                           "estudiantes sobre sus gestiones administrativas."),
    },
    "personal": {
        "prioridad": 3,
        "frases": ["tienes novia", "tienes novio", "tienes pareja", "tienes amigos", "tienes hijos", "tienes familia",
                   "cuantos anos tienes", "que edad tienes", "cual es tu edad", "donde vives", "donde naciste",
                   "de donde eres", "eres hombre", "eres mujer", "eres chico", "eres chica", "te gusta",
                   "que te gusta", "cual es tu comida favorita", "cual es tu color favorito", "duermes", "comes",
                   "tienes sentimientos", "estas triste", "estas feliz", "te sientes bien"],
        "respuesta": _fija("Soy un programa, así que no tengo edad, familia ni gustos personales. Lo que sí puedo hacer es "
                           "orientarte con tus trámites y dudas de la escuela."),
    },
    "idioma": {
        "prioridad": 3,
        "frases": ["hablas ingles", "hablas otro idioma", "hablas espanol", "hablas quechua", "speak english",
                   "do you speak english", "english please", "in english"],
        "respuesta": _fija("Por ahora solo puedo responder en español. Escribe tu consulta sobre trámites de la escuela "
                           "y con gusto te ayudo."),
    },
    "ayuda": {
        "prioridad": 3,
        "frases": ["ayuda", "ayudame", "necesito ayuda", "me puedes ayudar", "puedes ayudarme", "me ayudas",
                   "me podrias ayudar", "podrias ayudarme", "menu", "opciones", "temas", "que temas",
                   "que puedes hacer", "que haces", "en que me puedes ayudar", "en que puedes ayudarme",
                   "como me ayudas", "para que sirves", "para que sirve", "que sabes", "de que puedes hablar",
                   "como funciona", "como te uso", "que informacion tienes", "que preguntas puedo hacerte",
                   "que te puedo preguntar", "una consulta", "una duda", "una pregunta", "unas preguntas",
                   "unas dudas", "consulta", "duda", "dudas", "preguntas", "te puedo preguntar algo",
                   "puedo preguntarte algo", "puedo hacerte una pregunta", "puedo hacer una consulta",
                   "puedo consultar algo", "pregunta", "preguntarte algo", "preguntar algo"],
        "respuesta": _r_ayuda,
    },
    "estado": {
        "prioridad": 3,
        "frases": ["como estas", "como te va", "como andas", "como te encuentras", "que tal estas", "como amaneciste",
                   "como estas hoy", "todo bien", "como has estado", "estas bien", "como esta usted",
                   "como se encuentra", "bien y tu", "y tu", "como te sientes", "como vas", "que cuentas"],
        "respuesta": _fija("¡Muy bien, gracias por preguntar! Estoy listo para ayudarte con tus trámites y dudas de la "
                           "escuela. ¿Qué necesitas?"),
    },
    "confirmacion": {
        "prioridad": 2,
        "frases": ["ok", "okey", "okay", "vale", "listo", "entiendo", "entendido", "entendi", "perfecto", "genial",
                   "excelente", "muy bien", "de acuerdo", "dale", "bien", "ya veo", "ya entendi", "comprendo",
                   "super", "increible", "estupendo", "chevere", "bacan", "buenisimo", "ya", "esta bien",
                   "no lo sabia", "no sabia", "interesante", "aja", "ahh", "wow",
                   "que bien", "que bueno", "bueno saberlo", "buen dato", "ya sabia", "ya lo sabia"],
        "respuesta": _fija("¡Perfecto! Si tienes otra consulta, escríbela y con gusto te ayudo."),
    },
    "afirmacion": {
        "prioridad": 2,
        "frases": ["si", "claro", "claro que si", "por supuesto", "asi es", "correcto", "exacto"],
        "respuesta": _fija("Entendido. Cuéntame, ¿qué trámite o duda quieres resolver?"),
    },
    "negacion": {
        "prioridad": 2,
        "frases": ["no", "no gracias", "nada", "por ahora no", "no por ahora", "ninguna", "ninguno"],
        "respuesta": _fija("De acuerdo. Si más adelante necesitas algo, aquí estaré."),
    },
    "ruido": {
        "prioridad": -1,
        "frases": [],   # se detecta con es_ruido(): "aajjsjd", "asdasd", "qwerty"...
        "respuesta": _fija("No logré entender tu mensaje. Escribe tu consulta con palabras, por favor."),
    },
    "risa": {
        "prioridad": 1,
        "frases": [],   # se detecta con RISA (más abajo): "jajaja", "xd", "jeje"...
        "respuesta": _fija("¡Me alegra que te haga gracia! Si tienes alguna consulta sobre tus trámites, escríbela."),
    },
    "saludo": {
        "prioridad": 0,
        "frases": ["hola", "holi", "holis", "ola", "hello", "hi", "hey", "buenas", "buenos dias", "buen dia",
                   "buenas tardes", "buenas noches", "saludos", "que tal", "q tal", "como va", "que onda",
                   "alo", "buenas buenas", "hola buenas", "buen dia a todos", "saludos cordiales",
                   "muy buenos dias", "muy buenas tardes", "muy buenas noches"],
        "respuesta": _r_saludo,
    },
}

# Palabras que acompañan a la charla sin cambiar su sentido ("por favor", "dime la hora")
RELLENO = {
    "por", "favor", "pues", "oye", "oiga", "disculpa", "disculpe", "bueno", "entonces", "amigo", "amiga",
    "bot", "asistente", "chatbot", "muy", "mucho", "un", "poco", "y", "e", "ah", "eh", "mm", "hmm", "uh",
    "puedes", "podrias", "podria", "puede", "me", "dime", "dices", "decir", "das", "sabes", "tienes",
    "quiero", "quisiera", "saber", "tengo", "hacer", "hacerte", "puedo", "algo", "te", "hoy",
    "amigos", "compa", "hermano", "estimado", "estimada", "senor", "senora", "bro", "claude",
}

SECUENCIAS_TECLADO = ("asd", "sdf", "dfg", "fgh", "ghj", "hjk", "jkl", "qwe", "wer", "ert", "zxc", "xcv")


def es_ruido(palabra):
    """Tecleo al azar: "aajjsjd", "jasjdjsa", "asdasd", "qwerty"."""
    if len(palabra) < 4 or not palabra.isalpha():
        return False
    if any(s in palabra for s in SECUENCIAS_TECLADO):
        return True
    return len(palabra) >= 5 and set(palabra) <= set("asdfghjkl") and bool(set(palabra) & {"j", "k"})


RISA = re.compile(r"(?:[jh][aeiu]){2,}s?|x+d+|lol+|(?:js)+|(?:kj)+|(?:ja)+")


def _preparar():
    frases = []
    for nombre, datos in INTENCIONES.items():
        for f in datos["frases"]:
            frases.append((tuple(palabras(f)), nombre))
    frases.sort(key=lambda x: -len(x[0]))          # primero las frases más largas
    vocabulario = sorted({w for f, _ in frases for w in f if len(w) >= 6})
    return frases, vocabulario


_FRASES, _VOCABULARIO = _preparar()
_CONOCIDAS = {w for frase, _ in _FRASES for w in frase} | RELLENO   # palabras que ya son de cortesía: no se corrigen


def _corregir(crudas):
    """Arregla errores de tipeo en palabras de cortesía: "grasias" -> "gracias"."""
    arregladas = []
    for w in crudas:
        if len(w) >= 5 and w not in _CONOCIDAS:
            cercana = get_close_matches(w, _VOCABULARIO, n=1, cutoff=0.84)
            if cercana:
                w = cercana[0]
        arregladas.append(w)
    return arregladas


def detectar(crudas):
    """Busca charla social en las palabras del mensaje.

    Devuelve (intenciones, pura):
      intenciones: nombres de las intenciones halladas, en el orden en que aparecen.
      pura: True si TODO el mensaje es charla social (no trae ninguna consulta).
    """
    palabras_msg = _corregir(crudas)
    n = len(palabras_msg)
    cubierto = [False] * n
    hallazgos = []
    for frase, nombre in _FRASES:
        k = len(frase)
        for i in range(n - k + 1):
            if tuple(palabras_msg[i:i + k]) == frase and not any(cubierto[i:i + k]):
                for j in range(i, i + k):
                    cubierto[j] = True
                hallazgos.append((i, nombre))
    for i, w in enumerate(palabras_msg):
        if not cubierto[i] and RISA.fullmatch(w):
            cubierto[i] = True
            hallazgos.append((i, "risa"))
        elif not cubierto[i] and es_ruido(w):
            cubierto[i] = True
            hallazgos.append((i, "ruido"))
    orden = []
    for _, nombre in sorted(hallazgos):
        if nombre not in orden:
            orden.append(nombre)
    pura = bool(orden) and all(cubierto[i] or palabras_msg[i] in RELLENO for i in range(n))
    return orden, pura


def responder_social(intenciones, crudas, faqs):
    """Arma la respuesta de charla. Devuelve (texto, sugerencias)."""
    ordenadas = sorted(intenciones, key=lambda nombre: -INTENCIONES[nombre]["prioridad"])
    principal = ordenadas[0]
    texto, sugerencias = INTENCIONES[principal]["respuesta"](crudas, faqs)
    if principal != "saludo" and "saludo" in intenciones:
        texto = f"{_saludo_corto(crudas)} {texto}"
    return texto, sugerencias
