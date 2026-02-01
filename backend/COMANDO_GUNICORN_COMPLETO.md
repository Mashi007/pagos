# ✅ Comando Gunicorn Completo - Verificación

## Comando Completo Verificado

```
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## ✅ Verificación de Cada Parte

### 1. `gunicorn`
- ✅ Comando correcto
- ✅ Instalado en `requirements.txt` (gunicorn==23.0.0)

### 2. `app.main:app`
- ✅ Módulo: `app.main` (archivo `backend/app/main.py`)
- ✅ Objeto: `app` (instancia de FastAPI)
- ✅ Sintaxis correcta: `modulo:objeto`

### 3. `--bind 0.0.0.0:$PORT`
- ✅ `0.0.0.0`: Escucha en todas las interfaces de red
- ✅ `$PORT`: Variable de entorno de Render (automática)
- ✅ Formato correcto

### 4. `--workers 2`
- ✅ 2 procesos worker
- ✅ Adecuado para producción ligera/media
- ✅ Puedes ajustar según recursos disponibles

### 5. `--timeout 120`
- ✅ 120 segundos de timeout
- ✅ Adecuado para requests largos
- ✅ Evita que workers se queden colgados

### 6. `--worker-class uvicorn.workers.UvicornWorker`
- ✅ **CRÍTICO**: Necesario para FastAPI
- ✅ Usa Uvicorn como worker class
- ✅ Permite async/await de FastAPI
- ✅ Requiere `uvicorn[standard]` en requirements.txt

## Comando Completo para Render Dashboard

### Start Command (con `cd backend &&`):
```
cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

**Importante**: 
- Agrega `cd backend &&` al inicio porque el Root Directory es `.` (raíz)
- NO incluyas el `$` que Render muestra visualmente

## Verificación de Dependencias

Asegúrate de que `requirements.txt` tenga:

```txt
gunicorn==23.0.0
uvicorn[standard]==0.38.0
```

Ambas están presentes ✅

## Logs Esperados Después del Deploy

Cuando el comando funcione correctamente, deberías ver:

```
[INFO] Starting gunicorn 23.0.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [número]
[INFO] Booting worker with pid: [número]
[INFO] Application startup complete.
```

## Troubleshooting

### Si ves "No module named 'uvicorn.workers'"
**Solución**: Verifica que `uvicorn[standard]` esté instalado (no solo `uvicorn`)

### Si ves "ModuleNotFoundError: No module named 'app'"
**Solución**: Asegúrate de que el comando tenga `cd backend &&` al inicio

### Si ves "Address already in use"
**Solución**: Render maneja esto automáticamente, pero verifica que `$PORT` esté disponible

## Ajustes Opcionales

### Más Workers (si tienes más recursos):
```
--workers 4
```

### Menos Workers (si tienes limitaciones de memoria):
```
--workers 1
```

### Timeout más largo (para requests muy largos):
```
--timeout 300
```

---

*Documento creado el 2026-02-01*
