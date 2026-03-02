# 🔴 Error: SQL Error [42P01] - Tabla "prestamo" no existe

## Error Exacto
```
SQL Error [42P01]: ERROR: relation "prestamo" does not exist
Position: 65
```

## 🔍 Causa Raíz

**La tabla en la BD de Render se llama `prestamos` (PLURAL)**

Pero el código ORM usa:
```python
class Prestamo(Base):
    __tablename__ = "prestamos"  # ✅ Correcto en modelo
```

Entonces SQLAlchemy genera:
```sql
SELECT * FROM "prestamos"  -- ✅ Nombre correcto
```

### Pero el error menciona "prestamo" (singular)

Esto significa que **en Render la tabla `prestamos` NO EXISTE** o está con otro nombre.

---

## ¿Por Qué Pasó Esto?

### Causa Probable 1: Base de Datos Vacía
Render inicia con BD limpia. Las tablas se crean mediante:
1. **Alembic migrations** (si existen)
2. **SQLAlchemy Base.metadata.create_all()** (en startup)

**Verificar en `app/main.py`:**
```python
from app.core.database import Base, engine

# ¿Existe esto?
Base.metadata.create_all(bind=engine)
```

### Causa Probable 2: Migrations No Ejecutadas
```bash
# En Render build, debería ejecutarse:
alembic upgrade head
```

### Causa Probable 3: Nombre Diferente en BD
Posible que en Render se haya creado con otro nombre:
- `prestamo` (sin s)
- `loan` (traducido)
- Algo más

---

## ✅ Soluciones

### Solución 1: Crear Tablas en Startup

**Archivo:** `backend/app/main.py`

```python
from app.core.database import Base, engine

# Al inicio de la app:
@app.on_event("startup")
async def startup():
    # Crear todas las tablas que no existan
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas/verificadas")
```

**Ventajas:**
- ✅ Automático
- ✅ No requiere migrations
- ✅ Funciona en primera carga

**Desventajas:**
- ❌ No es best practice para producción

### Solución 2: Ejecutar Migrations en Deploy

**En Render `render.yaml`:**

```yaml
services:
  - type: web
    name: backend
    buildCommand: |
      pip install -r requirements.txt
      cd src/backend
      alembic upgrade head  # ← Agregar esta línea
    startCommand: gunicorn app.main:app --bind 0.0.0.0:$PORT
```

**Ventajas:**
- ✅ Best practice
- ✅ Historial de cambios
- ✅ Rollback posible

**Desventajas:**
- ❌ Requiere que migrations existan y sean correctas

### Solución 3: Verificar y Corregir Nombre de Tabla

**SQL en Render psql:**

```sql
-- Ver qué tablas existen
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Si existe "prestamo" (sin s), renombrar:
ALTER TABLE prestamo RENAME TO prestamos;

-- Si no existe nada, crear:
CREATE TABLE prestamos AS SELECT * FROM loans;  -- Si existe con otro nombre
```

---

## 🔧 Recomendación Inmediata

### Paso 1: Verificar main.py

```python
# backend/app/main.py

from app.core.database import Base, engine

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
```

### Paso 2: En Render Console

```bash
# Verificar tablas existentes
psql YOUR_DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"

# Ver estructura de prestamos si existe
psql YOUR_DATABASE_URL -c "\d prestamos;"
```

### Paso 3: Reset BD si es necesario

```bash
# En Render console:
DROP TABLE IF EXISTS prestamos CASCADE;
DROP TABLE IF EXISTS prestamo CASCADE;

# Luego redeploy para que cree desde cero
```

---

## 📝 Verificación Actual

### Qué Existe en el Código
- ✅ Modelo: `app/models/prestamo.py`
- ✅ Tabla name: `__tablename__ = "prestamos"`
- ✅ Migrations: `alembic/versions/*.py`

### Qué Falta en Render
- ❌ Tabla `prestamos` en BD
- ❌ Posiblemente tabla `prestamo` con nombre incorrecto
- ❌ Posiblemente migrations no ejecutadas

---

## 🚀 Plan de Acción

### Opción A: Rápida (Temporal)
1. Agregar tabla creation en `main.py` startup
2. Redeploy a Render
3. La tabla se creará automáticamente

### Opción B: Correcta (Permanente)
1. Actualizar `render.yaml` con `alembic upgrade head`
2. Verificar que todas las migrations existan
3. Redeploy a Render
4. Migrations se ejecutarán antes de start

### Opción C: Manual (Debug)
1. Conectar a BD de Render con psql
2. Ver qué tablas existen
3. Crear manualmente si falta
4. O renombrar si existe con otro nombre

---

## SQL Queries para Debug

```sql
-- Ver todas las tablas
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Ver estructura de prestamos
\d prestamos

-- Ver columnas de prestamos
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'prestamos';

-- Contar registros
SELECT COUNT(*) FROM prestamos;

-- Ver si existe tabla singular "prestamo"
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_name = 'prestamo'
);
```

---

## 📌 Resumen

| Aspecto | Status |
|---------|--------|
| Código ORM | ✅ Correcto - usa "prestamos" |
| Migrations | ⚠️ Existen pero quizás no ejecutadas |
| BD Render | ❌ Tabla no existe |
| Solución | Agregar create_all() en startup |

**Próximo paso:** Actualizar `app/main.py` con tabla creation en startup.
