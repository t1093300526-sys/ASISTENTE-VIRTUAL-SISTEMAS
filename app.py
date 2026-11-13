"""Interfaz web (Flask) del asistente virtual.

Rutas:
  /                  chat para los estudiantes
  /api/chat          recibe el mensaje y devuelve la respuesta (JSON)
  /admin             panel de la secretaria (protegido con contraseña)
  /admin/exportar    descarga las consultas en CSV
"""
import csv
import hmac
import io
import os
import re
import statistics
from datetime import datetime
from functools import wraps

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

import database
from chatbot import responder

app = Flask(__name__)


# ---------- Seguridad: panel solo para personal autorizado ----------
def requiere_admin(vista):
    @wraps(vista)
    def protegida(*args, **kwargs):
        clave = "MICLAVE2026"
        if not clave:
            return Response("Panel desactivado: define la variable ADMIN_PASSWORD.", 503)
        usuario = os.environ.get("ADMIN_USER", "secretaria")
        auth = request.authorization
        ok = (
            auth is not None
            and hmac.compare_digest((auth.username or "").encode(), usuario.encode())
            and hmac.compare_digest((auth.password or "").encode(), clave.encode())
        )
        if not ok:
            return Response("Acceso restringido", 401,
                            {"WWW-Authenticate": 'Basic realm="Secretaria"'})
        return vista(*args, **kwargs)
    return protegida


def ocultar_datos_personales(texto):
    """No guardamos números largos (DNI, código) ni correos que escriba el estudiante."""
    texto = re.sub(r"\d{6,}", "[número oculto]", texto)
    return re.sub(r"\S+@\S+", "[correo oculto]", texto)


# ---------- Chat de estudiantes ----------
@app.get("/")
def inicio():
    with database.conexion() as c:
        sugerencias = [r["pregunta"] for r in c.execute(
            "SELECT pregunta FROM preguntas_frecuentes WHERE activa = 1 ORDER BY id LIMIT 6")]
    return render_template("index.html", sugerencias=sugerencias)

@app.post("/api/chat")
def chat():
    datos = request.get_json(silent=True) or {}
    mensaje = str(datos.get("mensaje", "")).strip()[:500]
    if not mensaje:
        return jsonify(error="Escribe tu consulta."), 400

    contexto = str(datos.get("contexto", ""))[:80] or None
    r = responder(mensaje, contexto=contexto)
    with database.conexion() as c:
        cur = c.execute(
            "INSERT INTO consultas (fecha, mensaje, faq_id, reconocida, derivada, tiempo_ms) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), ocultar_datos_personales(mensaje),
             r["faq_id"], int(r["reconocida"]), int(r["derivada"]), r["tiempo_ms"]),
        )
        consulta_id = cur.lastrowid
    return jsonify(respuesta=r["respuesta"], sugerencias=r["sugerencias"],
                   derivada=r["derivada"], tramite=r["tramite"],
                   consulta_id=consulta_id if r["derivada"] else None)

DOMINIO_INSTITUCIONAL = os.environ.get("DOMINIO_INSTITUCIONAL", "unitru.edu.pe")
MIN_PALABRAS_DETALLE = 25     # el estudiante debe explicar su consulta con al menos 25 palabras
MAX_CARACTERES_DETALLE = 1500


def contar_palabras(texto):
    return len(texto.split())


@app.post("/api/contacto")
def contacto():
    """El estudiante deja sus datos para que la secretaría le responda."""
    datos = request.get_json(silent=True) or {}
    nombre = " ".join(str(datos.get("nombre", "")).split())[:100]
    correo = str(datos.get("correo", "")).strip().lower()[:100]
    codigo = str(datos.get("codigo", "")).strip()
    # Se conservan los saltos de línea, pero se limpian espacios sobrantes
    detalle = "\n".join(" ".join(l.split()) for l in str(datos.get("detalle", "")).strip().splitlines())
    detalle = detalle[:MAX_CARACTERES_DETALLE]
    try:
        consulta_id = int(datos.get("consulta_id"))
    except (TypeError, ValueError):
        return jsonify(error="Consulta no válida."), 400

    if len(nombre.split()) < 2:
        return jsonify(error="Escribe tu nombre completo (nombre y apellido)."), 400
    if not re.fullmatch(r"[\w.+-]+@" + re.escape(DOMINIO_INSTITUCIONAL), correo):
        return jsonify(error=f"Usa tu correo institucional (termina en @{DOMINIO_INSTITUCIONAL})."), 400
    if not re.fullmatch(r"\d{10}", codigo):
        return jsonify(error="Tu código de estudiante debe tener 10 dígitos."), 400
    if contar_palabras(detalle) < MIN_PALABRAS_DETALLE:
        return jsonify(error=f"Explica tu consulta con al menos {MIN_PALABRAS_DETALLE} palabras "
                             f"(ahora tienes {contar_palabras(detalle)})."), 400
    if datos.get("acepto") is not True:
        return jsonify(error="Debes aceptar que la secretaría use tus datos para responderte."), 400

    with database.conexion() as c:
        cur = c.execute(
            "UPDATE consultas SET nombre = ?, correo = ?, codigo = ?, detalle = ? "
            "WHERE id = ? AND derivada = 1 AND correo IS NULL",
            (nombre, correo, codigo, detalle, consulta_id))
        guardado = cur.rowcount
    if not guardado:
        return jsonify(error="No se pudieron registrar tus datos para esa consulta."), 400
    return jsonify(mensaje="¡Listo! La secretaría revisará tu consulta y te responderá "
                           "a tu correo institucional.")


# ---------- Panel de la secretaria ----------
def calcular_estadisticas():
    with database.conexion() as c:
        total = c.execute("SELECT COUNT(*) FROM consultas").fetchone()[0]
        por_asistente = c.execute(
            "SELECT COUNT(*) FROM consultas WHERE reconocida = 1").fetchone()[0]
        derivadas = c.execute(
            "SELECT COUNT(*) FROM consultas WHERE derivada = 1").fetchone()[0]
        tiempos = [r[0] for r in c.execute(
            "SELECT tiempo_ms FROM consultas WHERE tiempo_ms IS NOT NULL")]
        top = c.execute(
            "SELECT t.nombre, COUNT(*) n FROM consultas q "
            "JOIN preguntas_frecuentes f ON f.id = q.faq_id "
            "JOIN tramites t ON t.id = f.tramite_id "
            "GROUP BY t.nombre ORDER BY n DESC LIMIT 5").fetchall()
    est = {"total": total, "por_asistente": por_asistente, "derivadas": derivadas,
           "porcentaje": round(100 * por_asistente / total, 1) if total else 0,
           "top": [(r["nombre"], r["n"]) for r in top],
           "media": None, "mediana": None, "moda": None}
    if tiempos:
        est["media"] = round(statistics.mean(tiempos), 2)
        est["mediana"] = round(statistics.median(tiempos), 2)
        est["moda"] = statistics.multimode([round(t) for t in tiempos])[0]
    return est


@app.get("/admin")
@requiere_admin
def admin():
    with database.conexion() as c:
        pendientes = c.execute(
            "SELECT id, fecha, mensaje, detalle, nombre, correo, codigo FROM consultas "
            "WHERE derivada = 1 AND atendida_secretaria = 0 ORDER BY id DESC LIMIT 50").fetchall()
        tramites = c.execute("SELECT id, nombre FROM tramites ORDER BY nombre").fetchall()
        frecuentes = c.execute(
            "SELECT LOWER(TRIM(mensaje)) AS texto, COUNT(*) AS veces "
            "FROM consultas WHERE derivada = 1 "
            "GROUP BY texto ORDER BY veces DESC LIMIT 10").fetchall()
        faqs = c.execute(
            "SELECT f.id, f.pregunta, f.activa, t.nombre AS tramite "
            "FROM preguntas_frecuentes f LEFT JOIN tramites t ON t.id = f.tramite_id "
            "ORDER BY f.id").fetchall()
    return render_template("admin.html", est=calcular_estadisticas(), pendientes=pendientes,
                           tramites=tramites, faqs=faqs, frecuentes=frecuentes)


@app.post("/admin/faq")
@requiere_admin
def agregar_faq():
    f = request.form
    pregunta, claves, respuesta = (f.get(k, "").strip() for k in ("pregunta", "claves", "respuesta"))
    if pregunta and claves and respuesta:
        with database.conexion() as c:
            c.execute(
                "INSERT INTO preguntas_frecuentes (tramite_id, pregunta, palabras_clave, respuesta) "
                "VALUES (?, ?, ?, ?)", (f.get("tramite_id") or None, pregunta, claves, respuesta))
    return redirect(url_for("admin"))


@app.post("/admin/faq/<int:faq_id>/alternar")
@requiere_admin
def alternar_faq(faq_id):
    with database.conexion() as c:
        c.execute("UPDATE preguntas_frecuentes SET activa = 1 - activa WHERE id = ?", (faq_id,))
    return redirect(url_for("admin"))


@app.post("/admin/consulta/<int:consulta_id>/atendida")
@requiere_admin
def marcar_atendida(consulta_id):
    with database.conexion() as c:
        c.execute("UPDATE consultas SET atendida_secretaria = 1 WHERE id = ?", (consulta_id,))
    return redirect(url_for("admin"))


@app.get("/admin/exportar")
@requiere_admin
def exportar():
    salida = io.StringIO()
    escritor = csv.writer(salida)
    with database.conexion() as c:
        filas = c.execute(
            "SELECT id, fecha, mensaje, faq_id, reconocida, derivada, tiempo_ms, "
            "atendida_secretaria FROM consultas ORDER BY id").fetchall()
        escritor.writerow(filas[0].keys() if filas else
                          ["id", "fecha", "mensaje", "faq_id", "reconocida", "derivada",
                           "tiempo_ms", "atendida_secretaria"])
        escritor.writerows([tuple(f) for f in filas])
    return Response("﻿" + salida.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=consultas.csv"})


if __name__ == "__main__":
    database.init_db()
    # Solo en tu red local; para el piloto usa un servidor como waitress
    app.run(host="127.0.0.1", port=5000, debug=False)
