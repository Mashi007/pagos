# 🔧 Solución: Tabla "prestamo" no existe

## Status Actual

### ✅ El código TIENE crear tablas:
```python
# app/main.py
@app.on_event("startup")
def on_startup():
    _startup_db_with_retry(engine)  # Crea tablas automáticamente
```

### ❌ Pero en Render la tabla NO existe

Esto indica que **`Base.metadata.create_all()` está fallando silenciosamente en Render**.

---

## 🔍 Por Qué Falla

### Posibilidad 1: BD no está lista al iniciar
```python
# En Render, la BD puede tardar en estar disponible
# El código INTENTA reintentos, pero quizás falla de todas formas
```

### Posibilidad 2: Permisos insuficientes
```sql
-- Si el usuario de BD no tiene permisos de CREATE TABLE
GRANT CREATE ON SCHEMA public TO db_user;
```

### Posibilidad 3: La tabla se crea con otro nombre
```sql
-- Posible que se cree como "prestamo" (singular) en lugar de "prestamos"
SELECT tablename FROM pg_tables WHERE tablename ILIKE '%prestamo%';
```

---

## ✅ Soluciones (3 Opciones)

### Opción 1: Mejorar Retry Logic (RECOMENDADO)

**Archivo:** `backend/app/main.py`

```python
def _startup_db_with_retry(engine, max_attempts: int = 10, delay_sec: float = 3.0):
    """Mejorado: reintentos más agresivos para Render"""
    import time
    from sqlalchemy import text
    
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            # Agregar timeout más largo
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))  # Verificar conexión
            
            Base.metadata.create_all(bind=engine)
            logger.info(f"✅ Tablas creadas (intento {attempt})")
            
            # Verificar que prestamos existe
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name='prestamos'"
                ))
                if result.fetchone():
                    logger.info("✅ Tabla 'prestamos' existe")
                    return
            
        except Exception as e:
            last_error = e
            logger.warning(f"Intento {attempt} falló: {e}")
            if attempt < max_attempts:
                logger.info(f"Reintentando en {delay_sec}s...")
                time.sleep(delay_sec)
                delay_sec *= 1.5  # Backoff exponencial
    
    logger.error(f"❌ Fallo después de {max_attempts} intentos: {last_error}")
    raise Exception(f"No se pudieron crear tablas: {last_error}")
```

### Opción 2: Script Manual en Render Deploy

**Archivo:** `render.yaml`

```yaml
services:
  - type: web
    name: backend
    buildCommand: |
      cd src/backend
      pip install -r requirements.txt
    startCommand: |
      cd src/backend
      python -c "
      from app.core.database import engine, Base
      Base.metadata.create_all(bind=engine)
      print('Tables created')
      " && gunicorn app.main:app --bind 0.0.0.0:\$PORT
```

### Opción 3: Inicializar desde BD Dump

Si tienes un backup de la BD local:

```bash
# Exportar BD local
pg_dump local_db > db_backup.sql

# En Render, ejecutar el dump
psql $DATABASE_URL < db_backup.sql
```

---

## 🚀 Recomendación

### Hacer en orden:

1. **Actualizar `main.py` con mejor retry logic** (Opción 1)
   - Aumentar intentos de 5 a 10
   - Agregar verificación de tabla
   - Mejorar logging

2. **Redeploy a Render**
   - Esto debería crear la tabla

3. **Si aun falla**, usar Opción 2:
   - Agregar script de inicialización en `render.yaml`

---

## 🔍 Debug en Render

### Conectarse a BD de Render:

```bash
# Obtener DATABASE_URL
echo $DATABASE_URL

# Conectarse
psql $DATABASE_URL

# Ver tablas
SELECT tablename FROM pg_tables WHERE schemaname='public';

# Ver si prestamos existe
SELECT * FROM prestamos LIMIT 1;  -- Si da error "doesn't exist", confirma el problema
```

---

## 📋 Plan de Acción

### Paso 1: Mejorar main.py
1. Aumentar max_attempts de 5 a 10
2. Agregar verificación post-creación
3. Mejorar logging

### Paso 2: Redeploy
1. Push cambios a GitHub
2. Trigger redeploy en Render
3. Monitorear logs

### Paso 3: Verificar
1. Conectar a BD con psql
2. Confirmar tabla `prestamos` existe
3. Intentar descarga de reporte

### Paso 4: Si falla
1. Usar Opción 2 (script en render.yaml)
2. O resetear BD en Render dashboard

---

## Comando Rápido para Verificar

En Render console:

```sql
-- Esto debería funcionar después del fix
SELECT COUNT(*) as total_prestamos FROM prestamos;
```

Si da error, la tabla no fue creada y necesitas:
1. Revisar logs de startup
2. Aumentar reintentos
3. Usar script manual
