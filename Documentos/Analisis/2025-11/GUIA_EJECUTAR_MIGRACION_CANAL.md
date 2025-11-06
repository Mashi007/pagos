# 📋 GUÍA: Ejecutar Migración para Columna 'canal'

**Fecha:** 2025-11-06  
**Problema:** Columna 'canal' no existe en tabla 'notificaciones'  
**Solución:** Ejecutar migración de Alembic existente

---

## ✅ MIGRACIÓN YA EXISTE

**Archivo:** `backend/alembic/versions/20251030_add_cols_canal_asunto_notificaciones.py`

**Esta migración:**
- ✅ Agrega columna `canal` (String(20), nullable=True)
- ✅ Agrega columna `asunto` (String(255), nullable=True)
- ✅ Crea índice `ix_notificaciones_canal`
- ✅ Verifica si las columnas ya existen antes de agregarlas (segura)

---

## 🔍 PASO 1: Verificar Estado de Migraciones

### **En Local (Desarrollo):**

```bash
cd backend
alembic current
```

**Resultado esperado:**
- Muestra la revisión actual de la base de datos
- Si muestra `20251030_add_cols_notificaciones` o posterior → migración ya aplicada
- Si muestra una revisión anterior → migración pendiente

### **Ver Historial de Migraciones:**

```bash
cd backend
alembic history
```

**Ver todas las migraciones disponibles y su orden**

---

## 🚀 PASO 2: Ejecutar Migraciones Pendientes

### **Opción A: Ejecutar Todas las Migraciones Pendientes (Recomendado)**

```bash
cd backend
alembic upgrade head
```

**Esto:**
- ✅ Ejecuta todas las migraciones pendientes en orden
- ✅ Incluye la migración de 'canal' si está pendiente
- ✅ Es seguro (las migraciones verifican si las columnas ya existen)

### **Opción B: Ejecutar Migración Específica**

```bash
cd backend
alembic upgrade 20251030_add_cols_notificaciones
```

**Esto ejecuta solo la migración de 'canal' y 'asunto'**

---

## 🔧 PASO 3: Verificar en Base de Datos

### **Verificar que la Columna Existe:**

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'notificaciones'
  AND column_name = 'canal';
```

**Resultado esperado:**
```
column_name | data_type | is_nullable
------------|-----------|------------
canal       | character varying(20) | YES
```

### **Verificar Índice:**

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'notificaciones'
  AND indexname = 'ix_notificaciones_canal';
```

**Resultado esperado:**
```
indexname              | indexdef
-----------------------|----------------------------------------
ix_notificaciones_canal | CREATE INDEX ix_notificaciones_canal ON public.notificaciones USING btree (canal)
```

---

## 🌐 PASO 4: Ejecutar en Producción (Render)

### **Opción A: Usar Alembic en Render (Recomendado)**

**En Render Dashboard:**
1. Ve a `pagos` (backend service)
2. Settings → Build & Deploy
3. Agregar comando de build:
   ```
   cd backend && pip install -r requirements.txt && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

**O ejecutar manualmente después del deploy:**
1. Ve a `pagos` → Shell
2. Ejecutar:
   ```bash
   cd backend
   alembic upgrade head
   ```

### **Opción B: Ejecutar SQL Directo (Si Alembic no funciona)**

**En Render Dashboard:**
1. Ve a `pagos.post` (PostgreSQL service)
2. Connect → Usar cliente SQL
3. Ejecutar:

```sql
-- Verificar si la columna ya existe
SELECT column_name 
FROM information_schema.columns
WHERE table_name = 'notificaciones' 
  AND column_name = 'canal';

-- Si no existe, agregarla
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'notificaciones' 
          AND column_name = 'canal'
    ) THEN
        ALTER TABLE notificaciones 
        ADD COLUMN canal VARCHAR(20);
        
        CREATE INDEX IF NOT EXISTS ix_notificaciones_canal 
        ON notificaciones(canal);
        
        RAISE NOTICE 'Columna canal agregada exitosamente';
    ELSE
        RAISE NOTICE 'Columna canal ya existe';
    END IF;
END $$;
```

---

## ✅ PASO 5: Verificar que Funciona

### **Probar Endpoint:**

```bash
curl -X GET "https://pagos-f2qf.onrender.com/api/v1/notificaciones/?page=1&per_page=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Resultado esperado:**
- ✅ Status 200 OK
- ✅ Lista de notificaciones sin errores
- ✅ Sin mensaje de error sobre columna 'canal'

### **Revisar Logs del Backend:**

**Buscar:**
- ✅ Sin errores: `column notificaciones.canal does not exist`
- ✅ Endpoint funciona correctamente

---

## 🔄 SI LA MIGRACIÓN FALLA

### **Problema: Migración ya aplicada pero columna no existe**

**Solución:**
1. Verificar estado real de la BD:
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'notificaciones';
   ```

2. Si la columna realmente no existe:
   - Ejecutar SQL directo (Opción B arriba)
   - O marcar migración como "no aplicada" y re-ejecutar

### **Problema: Error de permisos**

**Solución:**
- Verificar que el usuario de la BD tiene permisos ALTER TABLE
- En Render, esto debería estar configurado automáticamente

---

## 📋 CHECKLIST COMPLETO

- [ ] Verificar estado de migraciones: `alembic current`
- [ ] Ejecutar migraciones pendientes: `alembic upgrade head`
- [ ] Verificar columna en BD: Query SQL
- [ ] Verificar índice en BD: Query SQL
- [ ] Probar endpoint: `/api/v1/notificaciones/`
- [ ] Revisar logs del backend
- [ ] Confirmar que no hay errores

---

## 🎯 RESULTADO ESPERADO

**Después de ejecutar la migración:**

✅ Columna `canal` existe en tabla `notificaciones`  
✅ Índice `ix_notificaciones_canal` creado  
✅ Endpoint `/api/v1/notificaciones/` funciona sin errores  
✅ Sin mensajes de error en logs del backend

---

## 📝 NOTAS IMPORTANTES

1. **La migración es segura:** Verifica si la columna existe antes de agregarla
2. **No duplica columnas:** Si ya existe, no la crea de nuevo
3. **Idempotente:** Puede ejecutarse múltiples veces sin problemas
4. **Orden importante:** Las migraciones se ejecutan en orden cronológico

---

## 🔗 REFERENCIAS

- **Migración:** `backend/alembic/versions/20251030_add_cols_canal_asunto_notificaciones.py`
- **Modelo:** `backend/app/models/notificacion.py` línea 50
- **Endpoint:** `backend/app/api/v1/endpoints/notificaciones.py` línea 213

