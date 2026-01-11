# 📋 Scripts SQL para DBeaver - Prestamos

## 📁 Archivos Disponibles

### 1. `dbeaver_fix_prestamos_valor_activo_indices.sql`
**Propósito:** Aplicar las correcciones detectadas en la auditoría integral
- ✅ Agrega columna `valor_activo` si no existe
- ✅ Crea índice `ix_prestamos_id` si no existe
- ✅ Crea índice `ix_prestamos_fecha_registro` si no existe
- ✅ Incluye verificaciones antes y después

**Cuándo usar:** Para aplicar las mejoras detectadas en la auditoría

**Cómo ejecutar:**
1. Abrir DBeaver
2. Conectarse a la base de datos de producción
3. Abrir el archivo `dbeaver_fix_prestamos_valor_activo_indices.sql`
4. Ejecutar todo el script (Ctrl+Enter o F5)
5. Revisar los mensajes de confirmación

---

### 2. `dbeaver_verificar_estructura_prestamos.sql`
**Propósito:** Verificación completa de la estructura de la tabla `prestamos`
- ✅ Lista todas las columnas
- ✅ Verifica columnas críticas
- ✅ Lista todos los índices
- ✅ Verifica índices requeridos
- ✅ Muestra foreign keys y constraints
- ✅ Estadísticas de datos
- ✅ Verificación de integridad

**Cuándo usar:** Antes y después de aplicar migraciones, para diagnóstico

**Cómo ejecutar:**
1. Abrir en DBeaver
2. Ejecutar sección por sección o todo el script
3. Revisar resultados de cada verificación

---

### 3. `dbeaver_comandos_utiles_prestamos.sql`
**Propósito:** Colección de comandos SQL útiles para trabajar con préstamos
- ✅ Consultas básicas
- ✅ Estadísticas y reportes
- ✅ Verificaciones de integridad
- ✅ Análisis de valor_activo
- ✅ Mantenimiento y optimización
- ✅ Verificar rendimiento de índices
- ✅ Operaciones de actualización (comentadas)

**Cuándo usar:** Para consultas diarias, reportes, y mantenimiento

**Cómo ejecutar:**
1. Abrir en DBeaver
2. Ejecutar las consultas que necesites
3. Las operaciones de escritura están comentadas por seguridad

---

### 4. `dbeaver_ejecutar_migracion_manual.sql`
**Propósito:** Ejecutar manualmente los cambios de la migración Alembic
- ✅ Útil si Alembic no puede ejecutarse
- ✅ Usa transacciones (BEGIN/COMMIT)
- ✅ Incluye verificaciones de existencia
- ✅ Requiere confirmación manual del COMMIT

**Cuándo usar:** Si hay problemas con Alembic o necesitas ejecutar cambios manualmente

**Cómo ejecutar:**
1. ⚠️ **IMPORTANTE:** Hacer BACKUP primero
2. Abrir en DBeaver
3. Revisar el script completo
4. Ejecutar hasta el COMMIT
5. Verificar los resultados
6. Ejecutar `COMMIT;` manualmente si todo está correcto
7. O ejecutar `ROLLBACK;` si hay problemas

---

### 5. `dbeaver_resumen_auditoria_prestamos.sql`
**Propósito:** Resumen ejecutivo de la auditoría integral
- ✅ Estado de la estructura
- ✅ Verificación detallada de elementos críticos
- ✅ Estadísticas de datos
- ✅ Distribuciones por estado y modalidad
- ✅ Integridad de datos
- ✅ Rendimiento y tamaños
- ✅ Recomendaciones
- ✅ Checklist de verificación

**Cuándo usar:** Para obtener un resumen rápido del estado de la tabla

**Cómo ejecutar:**
1. Abrir en DBeaver
2. Ejecutar todo el script
3. Revisar cada sección del resumen

---

### 6. `dbeaver_aplicar_migracion_alembic_prestamos.sql`
**Propósito:** Aplicar migración Alembic manualmente y actualizar `alembic_version`
- ✅ Aplica los cambios de la migración `20260110_fix_prestamos_valor_activo_indices`
- ✅ Crea/actualiza la tabla `alembic_version` si no existe
- ✅ Registra la migración en `alembic_version`
- ✅ Usa transacciones (BEGIN/COMMIT) para seguridad
- ✅ Requiere confirmación manual del COMMIT

**Cuándo usar:** Si Alembic no puede ejecutarse o necesitas sincronizar el estado manualmente

**Cómo ejecutar:**
1. ⚠️ **IMPORTANTE:** Hacer BACKUP primero
2. Abrir en DBeaver
3. Revisar el script completo
4. Ejecutar hasta el COMMIT
5. Verificar los resultados
6. Ejecutar `COMMIT;` manualmente si todo está correcto
7. O ejecutar `ROLLBACK;` si hay problemas

---

### 7. `dbeaver_verificar_migraciones_alembic.sql`
**Propósito:** Verificar el estado de las migraciones Alembic
- ✅ Verifica si existe la tabla `alembic_version`
- ✅ Muestra la migración actual aplicada
- ✅ Verifica si la migración específica está registrada
- ✅ Compara estado de BD vs Alembic
- ✅ Detecta desincronizaciones

**Cuándo usar:** Para verificar el estado de las migraciones antes y después de aplicar cambios

**Cómo ejecutar:**
1. Abrir en DBeaver
2. Ejecutar todo el script
3. Revisar el estado de sincronización

---

### 8. `dbeaver_migrar_alembic_prestamos.sql`
**Propósito:** Registrar migración Alembic en `alembic_version` (solo registro, no aplica cambios)
- ✅ Verifica estado actual de migraciones
- ✅ Crea tabla `alembic_version` si no existe
- ✅ Registra la migración `20260110_fix_prestamos_valor_activo_indices`
- ✅ Usa `ON CONFLICT` para evitar errores si ya existe
- ✅ Compatible con múltiples heads en Alembic
- ✅ Usa transacciones (BEGIN/COMMIT) para seguridad

**Cuándo usar:** Cuando los cambios ya están aplicados en BD pero falta registrar la migración en Alembic

**Cómo ejecutar:**
1. ⚠️ **IMPORTANTE:** Verificar que los cambios (columna e índices) ya estén aplicados en BD
2. Abrir en DBeaver
3. Ejecutar todo el script (incluye COMMIT al final)
4. Verificar que la migración se registró correctamente

**Nota:** Este script SOLO registra la migración, NO aplica cambios. Si los cambios no están aplicados, usar primero `dbeaver_fix_prestamos_valor_activo_indices.sql`

---

### 9. `dbeaver_optimizar_prestamos_post_migracion.sql`
**Propósito:** Optimizar la tabla `prestamos` después de crear índices
- ✅ Ejecuta `ANALYZE prestamos` para actualizar estadísticas
- ✅ Muestra estadísticas de la tabla (filas vivas/muertas, último análisis)
- ✅ Muestra uso de índices (tamaño, veces usado, tuplas leídas)
- ✅ Muestra tamaños totales (tabla, índices, total)
- ✅ Ejecuta `EXPLAIN ANALYZE` para verificar uso de índices
- ✅ Verifica rendimiento de consultas con los nuevos índices

**Cuándo usar:** Después de crear índices nuevos para actualizar estadísticas y verificar rendimiento

**Cómo ejecutar:**
1. Abrir en DBeaver
2. Ejecutar todo el script
3. Revisar estadísticas y planes de ejecución
4. Verificar que los índices están siendo utilizados

---

## 🚀 Guía de Uso Rápida

### Escenario 1: Aplicar mejoras de auditoría
```sql
-- 1. Verificar estado actual
-- Ejecutar: dbeaver_resumen_auditoria_prestamos.sql

-- 2. Aplicar correcciones
-- Ejecutar: dbeaver_fix_prestamos_valor_activo_indices.sql

-- 3. Verificar cambios aplicados
-- Ejecutar: dbeaver_verificar_estructura_prestamos.sql
```

### Escenario 2: Diagnóstico de problemas
```sql
-- 1. Verificar estructura completa
-- Ejecutar: dbeaver_verificar_estructura_prestamos.sql

-- 2. Ver resumen ejecutivo
-- Ejecutar: dbeaver_resumen_auditoria_prestamos.sql

-- 3. Usar comandos útiles según necesidad
-- Ejecutar secciones específicas de: dbeaver_comandos_utiles_prestamos.sql
```

### Escenario 3: Migración manual (si Alembic falla)
```sql
-- 1. Hacer BACKUP de la base de datos
-- 2. Ejecutar: dbeaver_ejecutar_migracion_manual.sql
-- 3. Verificar resultados antes de COMMIT
-- 4. Ejecutar COMMIT o ROLLBACK según corresponda
```

---

## ⚠️ Precauciones Importantes

1. **Siempre hacer BACKUP** antes de ejecutar scripts de modificación
2. **Probar en desarrollo** antes de producción
3. **Revisar los scripts** antes de ejecutarlos
4. **Verificar resultados** después de cada ejecución
5. **Usar transacciones** para operaciones críticas

---

## 📊 Orden Recomendado de Ejecución

### Para Aplicar Mejoras de Auditoría:
1. **Primero:** `dbeaver_resumen_auditoria_prestamos.sql` - Ver estado actual
2. **Segundo:** `dbeaver_verificar_estructura_prestamos.sql` - Verificación detallada
3. **Tercero:** `dbeaver_fix_prestamos_valor_activo_indices.sql` - Aplicar correcciones
4. **Cuarto:** `dbeaver_optimizar_prestamos_post_migracion.sql` - Optimizar
5. **Quinto:** `dbeaver_resumen_auditoria_prestamos.sql` - Verificar cambios aplicados

### Para Sincronizar con Alembic:
1. **Primero:** `dbeaver_verificar_migraciones_alembic.sql` - Ver estado de migraciones
2. **Segundo (si cambios NO están aplicados):** `dbeaver_aplicar_migracion_alembic_prestamos.sql` - Aplicar cambios y registrar migración
3. **Segundo (si cambios YA están aplicados):** `dbeaver_migrar_alembic_prestamos.sql` - Solo registrar migración
4. **Tercero:** `dbeaver_verificar_migraciones_alembic.sql` - Verificar sincronización
5. **Cuarto:** `dbeaver_optimizar_prestamos_post_migracion.sql` - Optimizar y verificar rendimiento

---

## 🔍 Verificaciones Post-Migración

Después de ejecutar las correcciones, verificar:

```sql
-- 1. Columna valor_activo existe
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'prestamos' AND column_name = 'valor_activo';

-- 2. Índices creados
SELECT indexname 
FROM pg_indexes 
WHERE tablename = 'prestamos' 
  AND indexname IN ('ix_prestamos_id', 'ix_prestamos_fecha_registro');

-- 3. Estadísticas actualizadas
ANALYZE prestamos;
```

---

## 📝 Notas Adicionales

- Todos los scripts son **idempotentes** - pueden ejecutarse múltiples veces sin problemas
- Los scripts verifican existencia antes de crear/modificar
- Los mensajes de confirmación indican el estado de cada operación
- Los scripts están optimizados para PostgreSQL

---

## 🆘 Solución de Problemas

### Error: "column already exists"
- ✅ Normal - el script verifica existencia antes de crear
- ✅ Puede ignorarse o revisar el mensaje de confirmación

### Error: "index already exists"
- ✅ Normal - el script verifica existencia antes de crear
- ✅ Puede ignorarse o revisar el mensaje de confirmación

### Error: "relation does not exist"
- ❌ La tabla `prestamos` no existe
- ❌ Verificar conexión a la base de datos correcta
- ❌ Verificar que las migraciones base se hayan aplicado

### Error de permisos
- ❌ El usuario no tiene permisos para crear índices/columnas
- ❌ Usar un usuario con permisos de DDL (ALTER TABLE, CREATE INDEX)

---

## 📞 Soporte

Si encuentras problemas:
1. Revisar los mensajes de error en DBeaver
2. Verificar los logs de la aplicación
3. Consultar la documentación de Alembic
4. Revisar el script de migración correspondiente

---

**Última actualización:** 2026-01-10  
**Versión:** 1.1

---

## 📋 Resumen de Scripts por Funcionalidad

| Script | Aplica Cambios | Registra Alembic | Solo Lectura |
|--------|----------------|------------------|--------------|
| `dbeaver_fix_prestamos_valor_activo_indices.sql` | ✅ | ❌ | ❌ |
| `dbeaver_migrar_alembic_prestamos.sql` | ❌ | ✅ | ❌ |
| `dbeaver_aplicar_migracion_alembic_prestamos.sql` | ✅ | ✅ | ❌ |
| `dbeaver_optimizar_prestamos_post_migracion.sql` | ✅ (ANALYZE) | ❌ | ⚠️ (mayormente lectura) |
| `dbeaver_verificar_estructura_prestamos.sql` | ❌ | ❌ | ✅ |
| `dbeaver_resumen_auditoria_prestamos.sql` | ❌ | ❌ | ✅ |
| `dbeaver_verificar_migraciones_alembic.sql` | ❌ | ❌ | ✅ |
| `dbeaver_comandos_utiles_prestamos.sql` | ⚠️ (comentado) | ❌ | ✅ |
