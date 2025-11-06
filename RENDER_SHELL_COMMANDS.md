# Comandos para Render Web Shell

## Paso 1: Navegar al directorio del backend
```bash
cd backend
```

## Paso 2: Verificar el estado actual de las migraciones
```bash
alembic current
```

## Paso 3: Ver las migraciones pendientes
```bash
alembic heads
```

## Paso 4: Ejecutar todas las migraciones pendientes
```bash
alembic upgrade head
```

## Paso 5 (Opcional): Verificar que se aplicaron correctamente
```bash
alembic current
```

---

## Si hay errores de transacción abortada:

### Opción A: Ejecutar nuevamente (Alembic maneja el rollback automáticamente)
```bash
alembic upgrade head
```

### Opción B: Hacer rollback manual y luego ejecutar
```bash
# Conectar a PostgreSQL y hacer rollback
psql $DATABASE_URL -c "ROLLBACK;"
# Luego ejecutar migraciones
alembic upgrade head
```

### Opción C: Marcar migración como ejecutada (si ya se aplicó parcialmente)
```bash
# Solo si la migración 014 ya se aplicó parcialmente
alembic stamp 014_remove_unique_cedula
# Luego continuar con el resto
alembic upgrade head
```

---

## Comandos útiles para diagnóstico:

### Ver historial de migraciones
```bash
alembic history
```

### Ver migraciones en formato verbose
```bash
alembic history --verbose
```

### Verificar sintaxis de todas las migraciones (si tienes el script)
```bash
python check_migrations.py
```

