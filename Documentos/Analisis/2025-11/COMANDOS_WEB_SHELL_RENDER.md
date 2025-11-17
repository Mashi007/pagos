# 🖥️ COMANDOS PARA WEB SHELL DE RENDER

**Fecha:** 2025-11-06
**Servicio:** Backend (`pagos`)
**Propósito:** Ejecutar migraciones y verificar Redis

---

## 📋 COMANDOS A EJECUTAR

### **1. Verificar Directorio y Estructura**

```bash
# Ver dónde estás
pwd

# Ir al directorio backend
cd backend

# Ver estructura
ls -la
```

---

### **2. Verificar Estado de Migraciones**

```bash
# Ver migración actual
alembic current

# Ver historial de migraciones
alembic history

# Ver migraciones pendientes
alembic heads
```

---

### **3. Ejecutar Migraciones Pendientes**

```bash
# Ejecutar TODAS las migraciones pendientes (RECOMENDADO)
alembic upgrade head
```

**Resultado esperado:**
```
INFO  [alembic.runtime.migration] Running upgrade ... -> 20251030_add_cols_notificaciones, agregar columnas canal y asunto a notificaciones
INFO  [alembic.runtime.migration] Running upgrade 20251030_add_cols_notificaciones -> 20251102_add_leida_notificaciones, agregar columna leida a notificaciones
```

---

### **4. Verificar Variable REDIS_URL**

```bash
# Verificar que la variable está configurada
echo $REDIS_URL

# Debería mostrar: redis://red-d46dg4ripnbc73demdog:6379
```

---

### **5. Verificar Conexión a Redis (Opcional)**

```bash
# Instalar redis-cli si no está disponible
# O usar Python para probar conexión
python3 -c "
import os
import sys
sys.path.append('/opt/render/project/src/backend')
from app.core.config import settings
print(f'REDIS_URL configurada: {bool(settings.REDIS_URL)}')
if settings.REDIS_URL:
    print(f'REDIS_URL valor: {settings.REDIS_URL[:80]}...')
"
```

---

### **6. Verificar Columna 'canal' en Base de Datos**

```bash
# Conectar a PostgreSQL y verificar
# (Requiere acceso a la base de datos)
python3 -c "
import os
import sys
sys.path.append('/opt/render/project/src/backend')
from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text(\"\"\"
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'notificaciones'
          AND column_name = 'canal'
    \"\"\"))
    row = result.fetchone()
    if row:
        print(f'✅ Columna canal existe: {row[0]} ({row[1]}, nullable={row[2]})')
    else:
        print('❌ Columna canal NO existe')
"
```

---

## 🎯 SECUENCIA RECOMENDADA

### **Ejecutar en este orden:**

```bash
# 1. Ir al directorio backend
cd backend

# 2. Ver estado actual
alembic current

# 3. Ejecutar migraciones
alembic upgrade head

# 4. Verificar variable Redis
echo $REDIS_URL

# 5. Verificar columna (opcional)
python3 -c "
import sys
sys.path.append('/opt/render/project/src/backend')
from app.db.session import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name = 'notificaciones' AND column_name = 'canal'\"))
    print('✅ Columna existe' if result.fetchone() else '❌ Columna NO existe')
"
```

---

## ✅ RESULTADOS ESPERADOS

### **Después de ejecutar `alembic upgrade head`:**

**Si hay migraciones pendientes:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade ... -> 20251030_add_cols_notificaciones, agregar columnas canal y asunto a notificaciones
INFO  [alembic.runtime.migration] Running upgrade 20251030_add_cols_notificaciones -> 20251102_add_leida_notificaciones, agregar columna leida a notificaciones
```

**Si todas las migraciones ya están aplicadas:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade head -> head, (no migrations to run)
```

---

## 🔍 VERIFICACIÓN FINAL

### **Después de ejecutar migraciones:**

1. **Verificar logs del backend:**
   - Buscar: `✅ Redis cache inicializado correctamente`
   - O: `⚠️ ERROR al conectar a Redis`

2. **Probar endpoint:**
   ```bash
   curl -X GET "https://pagos-f2qf.onrender.com/api/v1/notificaciones/?page=1&per_page=20" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
   - Debería retornar 200 OK sin errores

---

## 📝 NOTAS IMPORTANTES

1. **Las migraciones son seguras:** Verifican si las columnas ya existen
2. **No duplican datos:** Si la columna existe, no la crea de nuevo
3. **Idempotente:** Puede ejecutarse múltiples veces sin problemas
4. **Orden cronológico:** Las migraciones se ejecutan en orden

---

## 🚨 SI HAY ERRORES

### **Error: "alembic: command not found"**

```bash
# Instalar Alembic
pip install alembic

# O usar Python directamente
python3 -m alembic upgrade head
```

### **Error: "No module named 'app'"**

```bash
# Asegurarse de estar en el directorio correcto
cd /opt/render/project/src/backend

# Verificar que existe app/
ls -la app/
```

### **Error: "DATABASE_URL not configured"**

```bash
# Verificar variable
echo $DATABASE_URL

# Si no existe, configurarla en Render Dashboard → Environment
```

---

## 🎯 RESUMEN

**Comandos principales:**
1. `cd backend`
2. `alembic current` (ver estado)
3. `alembic upgrade head` (ejecutar migraciones)
4. `echo $REDIS_URL` (verificar Redis)

**Después de ejecutar:**
- ✅ Columna 'canal' existe en BD
- ✅ Redis conecta correctamente
- ✅ Endpoints funcionan sin errores

