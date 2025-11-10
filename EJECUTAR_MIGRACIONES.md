# 📋 Cómo Ejecutar Migraciones de Alembic

## Opción 1: Desde el directorio backend (Recomendado)

```powershell
# 1. Navegar al directorio backend
cd backend

# 2. Ver el estado actual de las migraciones
py -m alembic current

# 3. Ver el historial de migraciones
py -m alembic history

# 4. Ejecutar todas las migraciones pendientes
py -m alembic upgrade head

# 5. Ver qué migraciones se ejecutarán (sin ejecutarlas)
py -m alembic upgrade head --sql
```

## Opción 2: Si tienes un entorno virtual activo

```powershell
# Activar el entorno virtual primero
.\venv\Scripts\Activate.ps1  # o el nombre de tu venv

# Luego ejecutar las migraciones
cd backend
alembic upgrade head
```

## Opción 3: Ejecutar una migración específica

```powershell
cd backend
py -m alembic upgrade 20251108_add_updated_at
```

## Comandos útiles

```powershell
# Ver migraciones pendientes
py -m alembic heads

# Ver la migración actual aplicada
py -m alembic current

# Revertir la última migración
py -m alembic downgrade -1

# Revertir a una migración específica
py -m alembic downgrade 20251104_critical_indexes

# Ver el SQL que se ejecutará (sin ejecutarlo)
py -m alembic upgrade head --sql
```

## ⚠️ Nota importante

Si obtienes errores de variables de entorno, asegúrate de tener configurado tu archivo `.env` en el directorio `backend` con las variables necesarias, especialmente `DATABASE_URL`.

## Migraciones creadas recientemente

1. `20251108_add_last_login` - Agrega columna `last_login` a la tabla `users`
2. `20251108_add_updated_at` - Agrega columna `updated_at` a la tabla `users`

Ambas se ejecutarán con `alembic upgrade head`.




