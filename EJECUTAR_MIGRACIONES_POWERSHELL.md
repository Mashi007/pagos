# 📋 Ejecutar Migraciones en PowerShell

## Comandos para PowerShell

### 1. Navegar al directorio backend
```powershell
cd backend
```

### 2. Ver el estado actual de las migraciones
```powershell
py -m alembic current
```

### 3. Ejecutar todas las migraciones pendientes
```powershell
py -m alembic upgrade head
```

### 4. Ver el historial de migraciones
```powershell
py -m alembic history
```

### 5. Ver el SQL que se ejecutará (sin ejecutarlo)
```powershell
py -m alembic upgrade head --sql
```

## Ejecutar todo en una línea (PowerShell)

```powershell
cd backend; py -m alembic upgrade head
```

## Si tienes un entorno virtual

```powershell
# Activar el entorno virtual
.\venv\Scripts\Activate.ps1

# Navegar al backend
cd backend

# Ejecutar migraciones
alembic upgrade head
```

## Comandos útiles adicionales

```powershell
# Ver migraciones pendientes
py -m alembic heads

# Revertir la última migración
py -m alembic downgrade -1

# Revertir a una migración específica
py -m alembic downgrade 20251104_critical_indexes
```

## ⚠️ Nota importante

Si obtienes errores de variables de entorno, asegúrate de tener configurado tu archivo `.env` en el directorio `backend` con `DATABASE_URL`.






