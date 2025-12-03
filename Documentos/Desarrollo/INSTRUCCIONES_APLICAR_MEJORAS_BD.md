# 📋 INSTRUCCIONES PARA APLICAR MEJORAS DE BASE DE DATOS

**Fecha:** 2025-01-27  
**Objetivo:** Aplicar ForeignKeys faltantes y normalizar relaciones de catálogos

---

## ⚠️ IMPORTANTE: HACER BACKUP PRIMERO

**ANTES de ejecutar cualquier script, hacer backup completo de la base de datos:**

```sql
-- En DBeaver o pgAdmin, ejecutar:
pg_dump -h [HOST] -U [USER] -d [DATABASE] -F c -f backup_antes_migracion_20250127.dump
```

---

## 📝 PASOS A SEGUIR

### PASO 0: Verificar Tablas Existentes (NUEVO)

1. Abrir DBeaver
2. Conectarse a la base de datos PostgreSQL
3. Ejecutar el script: `scripts/sql/00_verificar_tablas_existentes.sql`
4. **Revisar qué tablas existen** - Las tablas `pagos_auditoria` y `prestamos_auditoria` son opcionales

**Nota:** Si las tablas de auditoría no existen, no es un problema. La migración las manejará correctamente.

---

### PASO 1: Validar Datos Existentes

1. Ejecutar el script: `scripts/sql/01_validar_datos_antes_migracion.sql`
2. **Revisar los resultados** - Verificar si hay datos inválidos
3. **Si las tablas de auditoría no existen**, verás mensajes informativos en lugar de errores

**Qué buscar:**
- Pagos con `prestamo_id` que no existe en `prestamos`
- Pagos con `cedula` que no existe en `clientes`
- Evaluaciones con `prestamo_id` inválido
- Auditorías con IDs inválidos
- Prestamos con concesionarios/analistas/modelos que no existen en sus tablas

---

### PASO 2: Corregir Datos Inválidos (Si es necesario)

**Solo si el PASO 1 encontró datos inválidos:**

1. Ejecutar el script: `scripts/sql/02_corregir_datos_invalidos.sql`
2. **Revisar cada corrección** antes de ejecutar
3. Algunas correcciones requieren decisión manual:
   - **Pagos con cédulas inválidas:** Decidir si crear clientes temporales o establecer a NULL
   - **Prestamos con concesionarios/analistas/modelos inválidos:** El script crea registros automáticamente

**⚠️ IMPORTANTE:** 
- Revisar cada sección del script antes de ejecutar
- Comentar las secciones que NO quieres ejecutar
- Hacer backup antes de ejecutar correcciones

---

### PASO 3: Aplicar Migraciones Alembic

**Desde el directorio `backend/`:**

```bash
# 1. Verificar estado actual
python -m alembic current

# 2. Ver qué migraciones se aplicarán
python -m alembic heads

# 3. Aplicar migraciones
python -m alembic upgrade head
```

**Las migraciones aplicarán:**
1. `20250127_01_critical_fks` - ForeignKeys críticos
2. `20250127_02_normalize_catalogs` - Normalización de catálogos

---

### PASO 4: Verificar Migraciones

**En DBeaver, ejecutar:**

```sql
-- Verificar ForeignKeys creados
SELECT 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN ('pagos', 'prestamos_evaluacion', 'pagos_auditoria', 'prestamos_auditoria', 'prestamos')
ORDER BY tc.table_name, tc.constraint_name;

-- Verificar nuevas columnas en prestamos
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'prestamos'
  AND column_name IN ('concesionario_id', 'analista_id', 'modelo_vehiculo_id')
ORDER BY column_name;

-- Verificar nueva columna en pagos
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'pagos'
  AND column_name = 'cliente_id';
```

---

## 🔄 ROLLBACK (Si es necesario)

**Si necesitas revertir las migraciones:**

```bash
# Revertir última migración
python -m alembic downgrade -1

# Revertir todas las migraciones de este cambio
python -m alembic downgrade 20251118_ml_impago_calculado
```

---

## ✅ VERIFICACIÓN FINAL

**Ejecutar nuevamente el script de validación:**

```sql
-- Ejecutar: scripts/sql/01_validar_datos_antes_migracion.sql
-- Debe mostrar 0 registros inválidos en todas las secciones
```

**Verificar que las relaciones funcionen:**

```sql
-- Probar relaciones
SELECT 
    p.id,
    p.cedula,
    c.nombres as cliente_nombre,
    pr.id as prestamo_id
FROM pagos p
LEFT JOIN clientes c ON p.cliente_id = c.id
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
LIMIT 10;

-- Verificar relaciones normalizadas en prestamos
SELECT 
    pr.id,
    pr.cedula,
    c.nombre as concesionario_nombre,
    a.nombre as analista_nombre,
    mv.modelo as modelo_vehiculo_nombre
FROM prestamos pr
LEFT JOIN concesionarios c ON pr.concesionario_id = c.id
LEFT JOIN analistas a ON pr.analista_id = a.id
LEFT JOIN modelos_vehiculos mv ON pr.modelo_vehiculo_id = mv.id
LIMIT 10;
```

---

## 📊 CAMBIOS APLICADOS

### ForeignKeys Críticos Agregados:
1. ✅ `pagos.prestamo_id` → `prestamos.id`
2. ✅ `pagos.cliente_id` → `clientes.id` (nueva columna)
3. ✅ `prestamos_evaluacion.prestamo_id` → `prestamos.id`
4. ✅ `pagos_auditoria.pago_id` → `pagos.id`
5. ✅ `prestamos_auditoria.prestamo_id` → `prestamos.id`

### Relaciones Normalizadas:
1. ✅ `prestamos.concesionario_id` → `concesionarios.id` (nueva columna)
2. ✅ `prestamos.analista_id` → `analistas.id` (nueva columna)
3. ✅ `prestamos.modelo_vehiculo_id` → `modelos_vehiculos.id` (nueva columna)

### Campos Legacy:
- Los campos `concesionario`, `analista`, `modelo_vehiculo` (strings) se mantienen para compatibilidad
- Se pueden eliminar en una migración futura una vez que el código use las nuevas relaciones

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Error: "violates foreign key constraint"
- **Causa:** Hay datos inválidos en la base de datos
- **Solución:** Ejecutar `02_corregir_datos_invalidos.sql` primero

### Error: "column already exists"
- **Causa:** La migración ya se ejecutó parcialmente
- **Solución:** Verificar estado con `alembic current` y continuar desde ahí

### Error: "relation does not exist"
- **Causa:** Falta alguna tabla en la base de datos
- **Solución:** Verificar que todas las tablas existan antes de ejecutar migraciones

---

## 📞 SOPORTE

Si encuentras problemas:
1. Revisar los logs de Alembic
2. Verificar el estado de la base de datos
3. Consultar el documento `Documentos/Analisis/MAPEO_RED_TABLAS_POSTGRES.md`

---

**Última actualización:** 2025-01-27

