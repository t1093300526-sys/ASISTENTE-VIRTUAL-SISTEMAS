"""Lógica del asistente: entiende el mensaje y busca la mejor respuesta.

Procesamiento de lenguaje natural (NLP) sencillo, sin librerías pesadas:
  1. Normalizar: minúsculas y sin tildes.
  2. Quitar palabras vacías ("el", "de", "quiero"...).
  3. Reducir plurales ("requisitos" -> "requisito").
  4. Comparar con las palabras clave de cada pregunta frecuente,
     tolerando errores de ortografía ("matrikula" -> "matricula").
Si ninguna pregunta se parece lo suficiente, la consulta se deriva a la secretaría.

Antes de buscar en las preguntas frecuentes se revisa si el mensaje es solo charla social
(saludos, despedidas, gracias, "¿qué hora es?"...): eso vive en intenciones.py.
"""
import os
import time
from difflib import SequenceMatcher

import database
import intenciones
from intenciones import palabras  # normaliza el texto (minúsculas, sin tildes, separado en palabras)

UMBRAL = 1.0          # puntaje mínimo para considerar que entendió la consulta
PESO_CLAVE = 1.0      # una palabra clave pesa más...
PESO_PREGUNTA = 0.4   # ...que una palabra que solo aparece en la pregunta
TOLERANCIA = 0.85     # parecido mínimo para aceptar una palabra mal escrita
BONUS_CONTEXTO = 0.6  # ventaja para el trámite del que se venía hablando
# Frases que piden ampliar el tema del que se venía hablando
MAS_INFO = {"informacion", "info", "detalle", "detalles", "mas", "más","ampliar",
            "continuar", "seguir", "cuentame", "explicame"}


def pide_mas(crudas):
    return len(crudas) <= 8 and any(p in MAS_INFO for p in crudas)

# Palabras que significan lo mismo: todas se convierten en "costo"
SINONIMOS = {
    "precio": "costo", "costo": "costo", "cuesta": "costo", "cuestan": "costo",
    "monto": "costo", "tarifa": "costo",
}

PALABRAS_VACIAS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a",
    "en", "y", "o", "u", "que", "como", "cual", "cuales", "por", "para", "con",
    "sin", "mi", "mis", "tu", "tus", "su", "sus", "se", "me", "te", "lo", "le",
    "es", "son", "esta", "este", "esto", "hay", "he", "yo", "quiero", "quisiera",
    "necesito", "puedo", "hago", "hacer", "saber", "sobre", "favor", "podria",
    "puede", "pueden", "tengo", "tiene", "ser", "si", "no", "muy", "mas", "ya",
}


def raiz(palabra):
    if palabra.endswith("ciones"):
        return palabra[:-6] + "cion"
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def tokens(texto):
    resultado = []
    for p in palabras(texto):
        if p in PALABRAS_VACIAS:
            continue
        r = raiz(p)
        resultado.append(SINONIMOS.get(r, r))
    return resultado


def parecido(token, conjunto):
    """1.0 si coincide exacto, 0.85 si es casi igual (error de tipeo), 0 si no."""
    if token in conjunto:
        return 1.0
    if len(token) >= 5:
        for otra in conjunto:
            if len(otra) >= 5 and SequenceMatcher(None, token, otra).ratio() >= TOLERANCIA:
                return 0.85
    return 0.0


def puntuar(mensaje_tokens, faq, contexto=None):
    claves = set(tokens(faq["palabras_clave"]))
    de_pregunta = set(tokens(faq["pregunta"])) - claves
    puntaje = 0.0
    for t in set(mensaje_tokens):
        p = parecido(t, claves)
        if p:
            puntaje += PESO_CLAVE * p
        else:
            puntaje += PESO_PREGUNTA * parecido(t, de_pregunta)
    if puntaje > 0 and contexto and faq["tramite"] == contexto:
        puntaje += BONUS_CONTEXTO
    return puntaje

def _faqs_activas():
    with database.conexion() as c:
        return c.execute(
            "SELECT f.id, f.pregunta, f.palabras_clave, f.respuesta, t.nombre AS tramite "
            "FROM preguntas_frecuentes f LEFT JOIN tramites t ON t.id = f.tramite_id "
            "WHERE f.activa = 1"
        ).fetchall()


def _resultado(respuesta, inicio, **extra):
    base = {
        "respuesta": respuesta, "faq_id": None, "tramite": None,
        "reconocida": True, "derivada": False, "sugerencias": [],
        "tipo": "faq",   # faq = respondida con una pregunta frecuente | social = charla | derivada
    }
    base.update(extra)
    base["tiempo_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
    return base


def responder(mensaje, faqs=None, contexto=None):
    inicio = time.perf_counter()
    faqs = _faqs_activas() if faqs is None else faqs
    crudas = palabras(mensaje)

    if not crudas:      # solo símbolos o emojis
        return _resultado("No pude leer tu mensaje. Escribe tu consulta con palabras, por favor.",
                          inicio, tipo="social")

    # 1) Charla social: saludos, despedidas, gracias, "¿qué hora es?"... (ver intenciones.py)
    sociales, es_pura = intenciones.detectar(crudas)
    if es_pura:
        texto, sugerencias = intenciones.responder_social(sociales, crudas, faqs)
        return _resultado(texto, inicio, sugerencias=sugerencias, tipo="social")

    # 2) Consulta académica: se busca la pregunta frecuente más parecida
    mt = tokens(mensaje)
    puntajes = sorted(((puntuar(mt, f, contexto), f) for f in faqs), key=lambda x: -x[0])
    if puntajes and puntajes[0][0] >= UMBRAL:
        mejor = puntajes[0][1]
        return _resultado(mejor["respuesta"], inicio,
                          faq_id=mejor["id"], tramite=mejor["tramite"])
    # 2b) Pidió "más información": se le muestran los demás temas del mismo trámite
    if contexto and pide_mas(crudas):
        preguntas = [f["pregunta"] for f in faqs if f["tramite"] == contexto]
        if preguntas:
            texto = (f"Sobre «{contexto}» puedes preguntarme, por ejemplo:\n• "
                     + "\n• ".join(preguntas[:8])
                     + "\nEscribe la que te interese.")
            return _resultado(texto, inicio, tramite=contexto)

    # 3) Pidió ayuda dentro de una frase que no se entendió: se muestran los temas
    if "ayuda" in sociales:
        texto, sugerencias = intenciones.INTENCIONES["ayuda"]["respuesta"](crudas, faqs)
        return _resultado(texto, inicio, sugerencias=sugerencias, tipo="social")

    # 4) No entendió: se deriva a la secretaría
    contacto = os.environ.get("CONTACTO_SECRETARIA", "la secretaría de la escuela")
    cercanas = [f["pregunta"] for p, f in puntajes[:3] if p >= 0.8]
    return _resultado(
        "No logré entender bien tu consulta. ¿Qué trámite o consulta quieres realizar? "
        "Puedes escribirla con más detalle. También puedes escribir tu consulta completa "
        "(mínimo 25 palabras) y dejar tu nombre, correo institucional y código aquí abajo; "
        "la secretaría te responderá por correo. "
        f"Si es urgente, comunícate directamente con {contacto}.",
        inicio, reconocida=False, derivada=True, sugerencias=cercanas, tipo="derivada",
    )
