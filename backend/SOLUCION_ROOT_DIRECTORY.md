# 🔧 Solución: cd: backend: No such file or directory

## Problema Identificado

El error `bash: line 1: cd: backend: No such file or directory` indica que cuando Render ejecuta el comando, el directorio `backend` no existe en la ruta actual.

## Posibles Causas

1. **Root Directory incorrecto**: El Root Directory está como `.` pero Render no encuentra `backend`
2. **Estructura del repositorio**: El directorio `backend` podría no estar en la raíz del repo
3. **Problema de clonado**: Render podría no estar clonando correctamente el directorio

## Soluciones

### Solución 1: Cambiar Root Directory a `backend` (RECOMENDADO)

Si el Root Directory está configurado como `.` (raíz), pero Render no encuentra `backend`, la solución más simple es cambiar el Root Directory directamente a `backend`.

#### En Render Dashboard:

1. Ve a tu servicio **pagos-backend**
2. Ve a **"Root Directory"**
3. Cambia de `.` a `backend`
4. Actualiza los comandos:

**Build Command:**
```
pip install -r requirements.txt
```
(Sin `cd backend &&`)

**Start Command:**
```
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```
(Sin `cd backend &&`)

### Solución 2: Verificar Estructura del Repositorio

Verifica que en tu repositorio GitHub, la estructura sea:

```
pagos/
├── backend/
│   ├── app/
│   │   └── main.py
│   └── requirements.txt
├── frontend/
└── render.yaml
```

Si la estructura es diferente, ajusta los comandos según corresponda.

### Solución 3: Usar Ruta Absoluta (Alternativa)

Si el Root Directory debe ser `.`, puedes usar la ruta completa:

**Build Command:**
```
pip install -r backend/requirements.txt
```

**Start Command:**
```
PYTHONPATH=/opt/render/project/src/backend gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

Pero esto es más complejo y no recomendado.

## Recomendación Final

**Cambiar Root Directory a `backend`** es la solución más simple y limpia:

### Configuración Recomendada:

**Root Directory:** `backend`

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Actualizar render.yaml

Si cambias el Root Directory a `backend`, actualiza `render.yaml`:

```yaml
  # Backend
  - type: web
    name: pagos-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
    rootDir: backend  # Cambiar de . a backend
```

---

*Documento creado el 2026-02-01*
