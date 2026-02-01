# 🔧 Solución: ModuleNotFoundError: No module named 'app'

## Problema

El error `ModuleNotFoundError: No module named 'app'` ocurre porque Gunicorn no puede encontrar el módulo `app` cuando se ejecuta desde el directorio raíz del proyecto.

## Causa

Aunque `rootDir: backend` está configurado en `render.yaml`, Render ejecuta el comando desde el directorio raíz del repositorio, no desde el subdirectorio `backend`.

## Solución Aplicada

### Cambio en `render.yaml`

**Antes:**
```yaml
buildCommand: pip install -r requirements.txt
startCommand: gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
rootDir: backend
```

**Después:**
```yaml
buildCommand: cd backend && pip install -r requirements.txt
startCommand: cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
rootDir: .
```

### Explicación

1. **`cd backend &&`**: Cambia explícitamente al directorio `backend` antes de ejecutar el comando
2. **`rootDir: .`**: Configura el directorio raíz como el directorio del repositorio (donde está `render.yaml`)

## Comandos para Render Dashboard

Si actualizas manualmente en Render Dashboard, usa estos comandos:

### Build Command:
```
cd backend && pip install -r requirements.txt
```

### Start Command:
```
cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Alternativa (Si la solución anterior no funciona)

Si aún tienes problemas, puedes usar esta alternativa:

### Start Command Alternativo:
```
cd backend && PYTHONPATH=/opt/render/project/src/backend gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

O más simple, usando Python directamente:
```
cd backend && python -m gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Verificación

Después del deploy, verifica en los logs que:

1. ✅ El comando se ejecuta desde el directorio correcto
2. ✅ Gunicorn encuentra el módulo `app`
3. ✅ Los workers se inician correctamente

Deberías ver en los logs:
```
[INFO] Starting gunicorn 23.0.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [número]
```

## Troubleshooting

### Si aún ves "ModuleNotFoundError":

1. Verifica que el archivo `backend/app/__init__.py` existe
2. Verifica que `backend/app/main.py` existe
3. Verifica que `requirements.txt` está en `backend/`
4. Revisa los logs completos del build para ver desde dónde se ejecuta

### Comando de diagnóstico:

Puedes agregar temporalmente este comando para verificar:
```
cd backend && pwd && ls -la && python -c "import app; print('OK')"
```

---

*Documento creado el 2026-02-01*
