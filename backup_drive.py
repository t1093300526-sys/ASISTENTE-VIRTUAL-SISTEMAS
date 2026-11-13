import sqlite3, os
from datetime import datetime

DB = "asistente.db"
CARPETA_DRIVE = r"G:\Mi unidad\Respaldos_chatbot"  # pega tu ruta y deja \Respaldos_chatbot al final

os.makedirs(CARPETA_DRIVE, exist_ok=True)
ruta = os.path.join(CARPETA_DRIVE, f"respaldo_{datetime.now():%Y%m%d_%H%M%S}.db")

origen = sqlite3.connect(DB)
destino = sqlite3.connect(ruta)
origen.backup(destino)
destino.close()
origen.close()
print("Respaldo creado:", ruta)