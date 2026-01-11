# 📋 Scripts SQL: Gestión Automática de Estados de Clientes

> **Instrucciones de Ejecución**
> Última actualización: 2026-01-11

---

## 🎯 Objetivo

Implementar gestión automática de estados de clientes según reglas de negocio:
- **FINALIZADO** (por defecto): Cliente sin deudas
- **ACTIVO**: Cliente con préstamo aprobado
- **INACTIVO**: Cliente con préstamo rechazado o problemas legales

---

## 📁 Archivos

1. **`funcion_actualizar_estado_cliente.sql`**
   - Función PostgreSQL para actualizar estado automáticamente
   - Triggers en `prestamos`, `cuotas`, `pagos`

---

## 🚀 Instrucciones de Ejecución

### **Paso 1: Ejecutar Script SQL**

```bash
# Conectarse a la base de datos PostgreSQL
psql -h <host> -U <usuario> -d <base_datos> -f scripts/sql/funcion_actualizar_estado_cliente.sql
```

O ejecutar directamente en tu cliente SQL (pgAdmin, DBeaver, etc.)

### **Paso 2: Verificar Instalación**

```sql
-- Verificar que la función existe
SELECT proname, prosrc 
FROM pg_proc 
WHERE proname = 'actualizar_estado_cliente_automatico';

-- Verificar que los triggers existen
SELECT tgname, tgrelid::regclass 
FROM pg_trigger 
WHERE tgname LIKE 'trg_actualizar_estado_cliente%';
```

### **Paso 3: Probar Manualmente**

```sql
-- Probar con una cédula específica
SELECT actualizar_estado_cliente_automatico('V12345678');

-- Verificar resultado
SELECT cedula, nombres, estado, activo 
FROM clientes 
WHERE cedula = 'V12345678';
```

---

## ⚠️ Advertencias

1. **Backup**: Hacer backup de la base de datos antes de ejecutar
2. **Testing**: Probar primero en un ambiente de desarrollo
3. **Rollback**: Si es necesario, ejecutar:
   ```sql
   DROP TRIGGER IF EXISTS trg_actualizar_estado_cliente_prestamo ON prestamos;
   DROP TRIGGER IF EXISTS trg_actualizar_estado_cliente_cuota ON cuotas;
   DROP TRIGGER IF EXISTS trg_actualizar_estado_cliente_pago ON pagos;
   DROP FUNCTION IF EXISTS actualizar_estado_cliente_automatico(VARCHAR);
   DROP FUNCTION IF EXISTS trigger_actualizar_estado_cliente_prestamo();
   DROP FUNCTION IF EXISTS trigger_actualizar_estado_cliente_cuota();
   DROP FUNCTION IF EXISTS trigger_actualizar_estado_cliente_pago();
   ```

---

## 📊 Verificación Post-Instalación

### **Verificar Estados Actuales**

```sql
-- Ver distribución de estados
SELECT 
    estado,
    COUNT(*) AS cantidad,
    COUNT(CASE WHEN activo = TRUE THEN 1 END) AS activos_true,
    COUNT(CASE WHEN activo = FALSE THEN 1 END) AS activos_false
FROM clientes
GROUP BY estado
ORDER BY cantidad DESC;
```

### **Verificar Coherencia**

```sql
-- Clientes ACTIVO deben tener activo = TRUE
SELECT COUNT(*) AS inconsistencias_activo
FROM clientes
WHERE estado = 'ACTIVO' AND activo = FALSE;

-- Clientes FINALIZADO/INACTIVO deben tener activo = FALSE
SELECT COUNT(*) AS inconsistencias_inactivo
FROM clientes
WHERE estado IN ('FINALIZADO', 'INACTIVO') AND activo = TRUE;
```

---

## 🔄 Actualización Masiva (Opcional)

Si necesitas actualizar todos los estados de clientes existentes:

```sql
-- Actualizar todos los clientes según reglas actuales
DO $$
DECLARE
    cliente_record RECORD;
BEGIN
    FOR cliente_record IN SELECT DISTINCT cedula FROM clientes LOOP
        PERFORM actualizar_estado_cliente_automatico(cliente_record.cedula);
    END LOOP;
END $$;
```

---

## 📝 Notas

- Los triggers se ejecutan automáticamente en tiempo real
- Los cambios se registran en `clientes.fecha_actualizacion`
- Los errores en triggers no bloquean las operaciones principales
- Ver logs del sistema para debugging

---

**Última revisión**: 2026-01-11
