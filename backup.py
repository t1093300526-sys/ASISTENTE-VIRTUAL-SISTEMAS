"""Respaldo automático de la base de datos hacia Google Drive.

Pasos: copia segura -> verifica que la copia no esté dañada -> sube a Drive ->
comprueba que lo subido sea idéntico -> borra copias locales viejas.

Uso:
  python backup.py                 un respaldo ahora
  python backup.py --cada 24       un respaldo cada 24 horas (dejar corriendo)
  python backup.py --sin-drive     solo copia local (para probar)
"""
import argparse
import hashlib
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import database

BASE = Path(__file__).resolve().parent
CARPETA = BASE / "respaldos"
MANTENER_LOCALES = 7
PERMISOS = ["https://www.googleapis.com/auth/drive.file"]


def crear_copia_local():
    CARPETA.mkdir(exist_ok=True)
    destino = CARPETA / f"asistente_{datetime.now():%Y%m%d_%H%M%S}.db"
    origen = sqlite3.connect(database.ruta_db())
    copia = sqlite3.connect(destino)
    with copia:
        origen.backup(copia)   # copia consistente aunque la app esté en uso
    origen.close()
    copia.close()
    try:
        os.chmod(destino, 0o600)
    except OSError:
        pass
    return destino


def copia_es_valida(ruta):
    con = sqlite3.connect(ruta)
    try:
        return con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        con.close()


def _md5(ruta):
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def _servicio_drive():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token = BASE / "token.json"
    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), PERMISOS)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Primera vez: abre el navegador para iniciar sesión en la cuenta de respaldo
            flujo = InstalledAppFlow.from_client_secrets_file(
                str(BASE / "credentials.json"), PERMISOS)
            creds = flujo.run_local_server(port=0)
        token.write_text(creds.to_json())
        try:
            os.chmod(token, 0o600)
        except OSError:
            pass
    return build("drive", "v3", credentials=creds)


def subir_a_drive(ruta):
    from googleapiclient.http import MediaFileUpload

    servicio = _servicio_drive()
    datos = {"name": ruta.name}
    carpeta = os.environ.get("DRIVE_FOLDER_ID")
    if carpeta:
        datos["parents"] = [carpeta]
    archivo = servicio.files().create(
        body=datos,
        media_body=MediaFileUpload(str(ruta), mimetype="application/x-sqlite3"),
        fields="id,name,size,md5Checksum",
    ).execute()
    # Verificación: lo que está en Drive debe ser idéntico a la copia local
    igual = (archivo.get("md5Checksum") == _md5(ruta)
             and int(archivo.get("size", -1)) == ruta.stat().st_size)
    return igual, archivo


def limpiar_locales():
    copias = sorted(CARPETA.glob("asistente_*.db"))
    for vieja in copias[:-MANTENER_LOCALES]:
        vieja.unlink()


def respaldar(usar_drive=True):
    try:
        copia = crear_copia_local()
        if not copia_es_valida(copia):
            logging.error("La copia %s está dañada; no se subió.", copia.name)
            return False
        logging.info("Copia local creada y verificada: %s", copia.name)
        if usar_drive:
            ok, archivo = subir_a_drive(copia)
            if not ok:
                logging.error("Lo subido a Drive NO coincide con la copia local (%s).", archivo)
                return False
            logging.info("Subida a Drive verificada (id %s).", archivo["id"])
        limpiar_locales()
        return True
    except Exception:
        logging.exception("Falló el respaldo")
        return False


def main():
    CARPETA.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(CARPETA / "respaldo.log", encoding="utf-8"),
                  logging.StreamHandler()])
    p = argparse.ArgumentParser()
    p.add_argument("--cada", type=float, metavar="HORAS", help="repetir cada N horas")
    p.add_argument("--sin-drive", action="store_true", help="solo copia local")
    args = p.parse_args()

    if not args.cada:
        sys.exit(0 if respaldar(not args.sin_drive) else 1)
    while True:
        respaldar(not args.sin_drive)
        time.sleep(args.cada * 3600)


if __name__ == "__main__":
    main()
