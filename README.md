# Asistente virtual de la Secretaría – Ing. de Sistemas (UNT)

Chatbot con Flask + Python + SQLite, siguiendo la metodología del proyecto.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `database.py` | Crea la base SQLite (trámites, preguntas frecuentes, consultas) y carga datos de ejemplo |
| `chatbot.py` | Lógica del asistente (NLP sencillo + qué hace si no entiende) |
| `app.py` | Interfaz web: chat de estudiantes y panel de la secretaria |
| `backup.py` | Respaldo automático de la base a Google Drive |
| `tests.py` | Pruebas funcionales y de integración |
| `templates/` | Páginas HTML (chat y panel) |

## Instalar y ejecutar

```
pip install -r requirements.txt
python database.py
```

Define la contraseña del panel (solo para la secretaria) y abre el servidor.

Windows (PowerShell):
```
$env:ADMIN_PASSWORD="pon-una-clave-segura"
$env:CONTACTO_SECRETARIA="el correo o teléfono de la secretaría"
python app.py
```
Mac/Linux:
```
export ADMIN_PASSWORD="pon-una-clave-segura"
export CONTACTO_SECRETARIA="el correo o teléfono de la secretaría"
python app.py
```

- Chat de estudiantes: http://127.0.0.1:5000/
- Panel de la secretaria: http://127.0.0.1:5000/admin (usuario `secretaria`, y la clave que definiste)

## Lo que tienes que completar

Las respuestas de ejemplo tienen marcas `[COMPLETAR: ...]`. Reemplázalas con la
información real (requisitos, fechas, costos, horario). Se puede hacer desde el
panel (agregar o desactivar preguntas) o editando `PREGUNTAS` en `database.py`
antes de crear la base. Esos datos salen de la entrevista a la secretaria.

## Pruebas

```
python -m unittest tests -v
```

## Respaldo a Google Drive

1. En Google Cloud Console crea un proyecto, activa la **Google Drive API** y crea
   credenciales **ID de cliente OAuth (aplicación de escritorio)**.
   Descarga el archivo y guárdalo como `credentials.json` en esta carpeta.
2. (Opcional) Crea una carpeta en Drive y copia su ID (lo que va al final del enlace):
   `DRIVE_FOLDER_ID`.
3. Primera vez: `python backup.py`. Se abre el navegador para iniciar sesión en la
   cuenta de respaldo (con contraseña segura). Queda guardado en `token.json`.
4. Para que se repita solo: `python backup.py --cada 24` (cada 24 horas), o
   prográmalo con el Programador de tareas de Windows / cron.

Cada respaldo se verifica: se revisa que la copia no esté dañada y que lo subido
a Drive sea idéntico (tamaño y MD5). El resultado queda en `respaldos/respaldo.log`.

Para **restaurar**: cierra la app y copia un archivo de `respaldos/` (o el de Drive)
sobre `asistente.db`.

## Para medir la efectividad en el piloto

En `/admin` ves total de consultas, porcentaje resuelto por el asistente, derivadas,
y media, mediana y moda del tiempo de respuesta. `/admin/exportar` descarga todo en
CSV para hacer la comparación antes/después en Excel o SPSS.

## Pendiente / ideas

- Para el piloto con varios estudiantes usa `waitress` en vez del servidor de desarrollo:
  `waitress-serve --host=0.0.0.0 --port=5000 app:app` (y protege el acceso a la red).
- Si quieres usar NLTK, como en Ndunagu et al. (2025), puedes cambiar `tokens()` en
  `chatbot.py` por su lematizador sin tocar el resto.


## Actualización: repetición de cursos y seguridad del panel

Se añadieron cinco preguntas frecuentes en `database.py` sobre segunda, tercera y cuarta matrícula, el cálculo del pago y el FUT/constancia. El cuadro utilizado está fechado **2024-II**: los importes por repetición provienen de esa tabla; los S/ 10 (FUT o derecho de trámite, contados una sola vez) y S/ 20 (constancia) fueron aportados como información adicional y deben confirmarse con secretaría. Los totales no incluyen la matrícula ordinaria.

El panel `/admin` conserva el acceso HTTP Basic mediante `ADMIN_USER` (por defecto `secretaria`) y `ADMIN_PASSWORD` (obligatoria). Se añadió `seguridad.py`: tras **5** claves erróneas hay **1 minuto** de bloqueo; después se conceden **3 intentos** y hay **5 minutos** de bloqueo; luego **1 intento** y **15 minutos**; desde entonces se aplica **1 hora** por intento fallido. El contador queda guardado en SQLite (`intentos_admin`) y se borra tras un inicio de sesión válido. No se modifica la contraseña ni se guarda en la base de datos. Durante el bloqueo la respuesta HTTP es 429 con `Retry-After`; el navegador puede mostrar un error en lugar de un temporizador.

**Importante:** el bloqueo es de la cuenta completa, por lo que una persona malintencionada también podría impedir temporalmente el acceso a la secretaría. Es mitigación básica contra intentos de contraseña, no una solución integral para publicar la app en Internet. Usa HTTPS, contraseña larga y única, copias de seguridad y, preferentemente, MFA y un sistema de sesión. Un flujo de recuperación por correo no está incluido: requiere correo verificado de la secretaría, tokens de un solo uso con caducidad y un servicio de envío. Con HTTP Basic no conviene improvisar esa función.

Para actualizar las preguntas de una base existente, conserva tu `asistente.db` original en la carpeta del proyecto y ejecuta `python database.py` (se sincronizan sin borrar consultas). **El ZIP entregado omite** `.venv`, `.git` y `asistente.db` para no redistribuir dependencias locales, historial de Git ni posibles datos personales. Crea un entorno virtual y usa `pip install -r requirements.txt`.
