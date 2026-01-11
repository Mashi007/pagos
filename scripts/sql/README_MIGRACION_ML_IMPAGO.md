# 📋 Guía: Migración Manual ML Impago Calculado

**Fecha:** 2026-01-11  
**Migración Alembic:** `20251118_add_ml_impago_calculado_prestamos.py`

---

## 🎯 Objetivo

Agregar las 4 columnas ML (Machine Learning) faltantes a la tabla `prestamos` para permitir persistencia de predicciones de impago.

---

## ⚠️ Cuándo Usar Este Script

**Usa este script SQL si:**
- ✅ No puedes ejecutar Alembic directamente
- ✅ Prefieres ejecutar la migración manualmente
- ✅ Necesitas aplicar cambios en una BD específica sin Alembic
- ✅ Quieres verificar el proceso paso a paso

**Alternativa recomendada:**
```bash
cd backend
alembic upgrade head
```

---

## 📋 Columnas a Agregar

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| `ml_impago_nivel_riesgo_calculado` | VARCHAR(20) | Sí | Nivel de riesgo calculado (Alto, Medio, Bajo) |
| `ml_impago_probabilidad_calculada` | NUMERIC(5,3) | Sí | Probabilidad calculada (0.0 a 1.0) |
| `ml_impago_calculado_en` | TIMESTAMP | Sí | Fecha de última predicción |
| `ml_impago_modelo_id` | INTEGER | Sí | FK a `modelos_impago_cuotas.id` |

---

## 🚀 Cómo Ejecutar

### **Opción 1: DBeaver / Cliente SQL**

1. Abrir DBeaver o tu cliente SQL preferido
2. Conectarse a la base de datos
3. Abrir el archivo `MIGRACION_ML_IMPAGO_CALCULADO.sql`
4. Ejecutar todo el script (F5 o botón "Execute")
5. Revisar los mensajes de confirmación

### **Opción 2: psql (Línea de comandos)**

```bash
psql -U tu_usuario -d tu_base_de_datos -f scripts/sql/MIGRACION_ML_IMPAGO_CALCULADO.sql
```

### **Opción 3: Python (usando psycopg2)**

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="tu_bd",
    user="tu_usuario",
    password="tu_password"
)

with open('scripts/sql/MIGRACION_ML_IMPAGO_CALCULADO.sql', 'r') as f:
    script = f.read()
    
cur = conn.cursor()
cur.execute(script)
conn.commit()
cur.close()
conn.close()
```

---

## ✅ Verificación Post-Migración

### **1. Verificar Columnas Creadas:**

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'prestamos'
  AND column_name LIKE 'ml_impago%'
ORDER BY column_name;
```

**Resultado esperado:** 4 columnas listadas

### **2. Verificar Foreign Key:**

```sql
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name = 'prestamos'
  AND kcu.column_name = 'ml_impago_modelo_id';
```

**Resultado esperado:** FK `fk_prestamos_ml_impago_modelo` listado

### **3. Verificar Índice:**

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'prestamos'
  AND indexname = 'ix_prestamos_ml_impago_calculado_en';
```

**Resultado esperado:** Índice listado

---

## 🔍 Características del Script

### **Seguridad:**

- ✅ **Idempotente:** Puede ejecutarse múltiples veces sin errores
- ✅ **Verificación:** Verifica existencia antes de crear
- ✅ **Mensajes informativos:** Muestra qué se creó y qué se omitió

### **Manejo de Errores:**

- ✅ Verifica que la tabla `prestamos` existe
- ✅ Verifica existencia de columnas antes de crearlas
- ✅ Verifica existencia de FK antes de crearlo
- ✅ Verifica existencia de índice antes de crearlo
- ✅ Maneja caso donde `modelos_impago_cuotas` no existe

---

## 📊 Resultado Esperado

Después de ejecutar el script, deberías ver:

```
NOTICE: ✅ Columna ml_impago_nivel_riesgo_calculado agregada a tabla prestamos
NOTICE: ✅ Columna ml_impago_probabilidad_calculada agregada a tabla prestamos
NOTICE: ✅ Columna ml_impago_calculado_en agregada a tabla prestamos
NOTICE: ✅ Columna ml_impago_modelo_id agregada a tabla prestamos
NOTICE: ✅ Foreign key fk_prestamos_ml_impago_modelo creado
NOTICE: ✅ Índice ix_prestamos_ml_impago_calculado_en creado
```

Y al final, la verificación debe mostrar:
- **4 columnas ML** en la tabla `prestamos`
- **1 Foreign Key** creado
- **1 Índice** creado

---

## ⚠️ Notas Importantes

1. **Backup:** Siempre haz backup de la BD antes de ejecutar migraciones
2. **Permisos:** Asegúrate de tener permisos ALTER TABLE
3. **Tabla modelos_impago_cuotas:** Si no existe, el FK no se creará (pero las columnas sí)
4. **Reversión:** Para revertir, ejecutar `downgrade()` de la migración Alembic o eliminar manualmente

---

## 🔄 Reversión (Si es Necesario)

Si necesitas revertir la migración:

```sql
-- Eliminar índice
DROP INDEX IF EXISTS ix_prestamos_ml_impago_calculado_en;

-- Eliminar Foreign Key
ALTER TABLE prestamos 
DROP CONSTRAINT IF EXISTS fk_prestamos_ml_impago_modelo;

-- Eliminar columnas
ALTER TABLE prestamos DROP COLUMN IF EXISTS ml_impago_modelo_id;
ALTER TABLE prestamos DROP COLUMN IF EXISTS ml_impago_calculado_en;
ALTER TABLE prestamos DROP COLUMN IF EXISTS ml_impago_probabilidad_calculada;
ALTER TABLE prestamos DROP COLUMN IF EXISTS ml_impago_nivel_riesgo_calculado;
```

---

## 📝 Verificación con Script de Auditoría

Después de ejecutar la migración, ejecuta:

```bash
python scripts/python/comparar_bd_con_orm.py
```

**Resultado esperado:** Las 4 discrepancias críticas deben desaparecer.

---

**Última actualización:** 2026-01-11  
**Estado:** ✅ Listo para ejecutar
