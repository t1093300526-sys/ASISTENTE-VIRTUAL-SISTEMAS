"""Límite persistente de intentos de autenticación del panel (SQLite)."""
import math
import sqlite3
import time

import database

# 5 errores -> 1 min; 3 adicionales -> 5 min; 1 -> 15 min;
# desde entonces, 1 error -> 60 min. No se reinicia por cerrar el navegador.
UMBRAL_POR_ETAPA = (5, 3, 1, 1)
DURACION_POR_ETAPA = (60, 300, 900, 3600)


def verificar_acceso(usuario, credenciales_correctas, ahora=None):
    """Devuelve (permitido, segundos_de_bloqueo). La operación es transaccional.

    Se agrupan los intentos por cuenta, no por dirección IP (que es fácil variar).
    Incluso una contraseña correcta debe esperar hasta terminar un bloqueo.
    """
    ahora = time.time() if ahora is None else ahora
    usuario = str(usuario)[:100].lower()
    with database.conexion() as conn:
        conn.execute('BEGIN IMMEDIATE')
        fila = conn.execute(
            'SELECT fallos, etapa, bloqueado_hasta FROM intentos_admin WHERE usuario = ?',
            (usuario,)).fetchone()
        if fila and fila['bloqueado_hasta'] > ahora:
            return False, max(1, math.ceil(fila['bloqueado_hasta'] - ahora))
        if credenciales_correctas:
            conn.execute('DELETE FROM intentos_admin WHERE usuario = ?', (usuario,))
            return True, 0
        fallos = (fila['fallos'] if fila else 0) + 1
        etapa = fila['etapa'] if fila else 0
        bloqueado_hasta = 0
        umbral = UMBRAL_POR_ETAPA[min(etapa, len(UMBRAL_POR_ETAPA) - 1)]
        if fallos >= umbral:
            bloqueado_hasta = ahora + DURACION_POR_ETAPA[min(etapa, len(DURACION_POR_ETAPA) - 1)]
            fallos = 0
            etapa += 1
        conn.execute(
            'INSERT INTO intentos_admin (usuario, fallos, etapa, bloqueado_hasta) '
            'VALUES (?, ?, ?, ?) ON CONFLICT(usuario) DO UPDATE SET '
            'fallos = excluded.fallos, etapa = excluded.etapa, bloqueado_hasta = excluded.bloqueado_hasta',
            (usuario, fallos, etapa, bloqueado_hasta))
        return False, max(0, math.ceil(bloqueado_hasta - ahora))
