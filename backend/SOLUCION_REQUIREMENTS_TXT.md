# 🔧 Solución: requirements.txt No Encontrado

## Problema Identificado

El error `ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements.txt'` ocurre porque:

- **Root Directory**: Configurado como `backend`
- **Ubicación de requirements.txt**: En la raíz del proyecto (`/opt/render/project/src/requirements.txt`)
- **Render ejecuta desde**: `/opt/render/project/src/backend/`
- **Resultado**: No encuentra `requirements.txt` porque está en el directorio padre

## Solución Aplicada

### Cambio en Build Command:

**Antes (INCORRECTO):**
```yaml
buildCommand: pip install -r requirements.txt
```

**Después (CORRECTO):**
```yaml
buildCommand: pip install -r ../requirements.txt
```

El `../` indica que `requirements.txt` está en el directorio padre (raíz del proyecto).

## Estructura del Proyecto

```
pagos/
├── requirements.txt          ← Aquí está el archivo
├── backend/
│   ├── app/
│   │   └── main.py
│   └── (otros archivos)
└── frontend/
```

## Configuración Final

### Root Directory:
```
backend
```

### Build Command:
```
pip install -r ../requirements.txt
```

### Start Command:
```
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Alternativas (Si Prefieres)

### Opción 1: Cambiar Root Directory a `.` (Raíz)
```yaml
rootDir: .
buildCommand: pip install -r requirements.txt
startCommand: cd backend && gunicorn app.main:app ...
```

### Opción 2: Copiar requirements.txt a backend/
Mover o copiar `requirements.txt` a `backend/requirements.txt` y usar:
```yaml
rootDir: backend
buildCommand: pip install -r requirements.txt
```

**Pero la solución con `../requirements.txt` es la más simple y no requiere mover archivos.**

## Verificación Post-Corrección

Después de hacer commit y push, en los logs deberías ver:

```
==> Running build command 'pip install -r ../requirements.txt'...
Collecting packages...
Successfully installed gunicorn-23.0.0 uvicorn-0.38.0 ...
```

**Ya NO deberías ver:**
- ❌ `ERROR: Could not open requirements file`

---

*Documento creado el 2026-02-01*
