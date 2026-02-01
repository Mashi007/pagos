# ✅ Comandos Finales para Backend - Render Dashboard

## Comandos Correctos para Backend

### ✅ Build Command:
```
cd backend && pip install -r requirements.txt
```

### ✅ Pre-Deploy Command:
```
(Dejar completamente vacío - es opcional)
```

### ✅ Start Command (COMPLETO):
```
cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Explicación

### Por qué `cd backend &&` al inicio:
- El **Root Directory** está configurado como `.` (raíz del proyecto)
- Render ejecuta comandos desde: `/opt/render/project/src/`
- El módulo `app` está en: `/opt/render/project/src/backend/app/`
- Necesitas cambiar al directorio `backend` antes de ejecutar los comandos

### Por qué NO incluir el `$`:
- El `$` es solo visual del sistema (prompt)
- Render lo muestra automáticamente
- NO debes incluirlo al escribir los comandos

## Verificación en Render Dashboard

### Build Command debe mostrar:
```
$ cd backend && pip install -r requirements.txt
```
(Pero tú escribes solo: `cd backend && pip install -r requirements.txt`)

### Start Command debe mostrar:
```
$ cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```
(Pero tú escribes solo: `cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker`)

## Logs Esperados Después del Deploy

### Build:
```
==> Running build command 'cd backend && pip install -r requirements.txt'...
Collecting packages...
Successfully installed gunicorn-23.0.0 uvicorn-0.38.0 ...
```

### Start:
```
==> Running 'cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker'
[INFO] Starting gunicorn 23.0.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [número]
[INFO] Booting worker with pid: [número]
[INFO] Application startup complete.
```

## Troubleshooting

### Si aún ves "ModuleNotFoundError: No module named 'app'"
1. Verifica que el Start Command tenga `cd backend &&` al inicio
2. Verifica que el Root Directory esté configurado como `.` (punto)
3. Verifica que `backend/app/__init__.py` exista
4. Verifica que `backend/app/main.py` exista

### Si ves "No such file or directory: requirements.txt"
1. Verifica que el Build Command tenga `cd backend &&` al inicio
2. Verifica que `backend/requirements.txt` exista

---

*Documento creado el 2026-02-01*
