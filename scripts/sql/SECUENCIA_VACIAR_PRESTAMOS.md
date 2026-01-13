# 📋 SECUENCIA DE SCRIPTS PARA VACIAR TABLA prestamos

## ⚠️ ADVERTENCIA
Esta operación eliminará TODOS los registros de la tabla `prestamos`.
**Asegúrate de hacer un BACKUP antes de ejecutar.**

---

## 🔄 SECUENCIA DE EJECUCIÓN

### **PASO 1: Verificar estado actual**
```sql
SELECT 
    COUNT(*) AS total_prestamos
FROM prestamos;

SELECT 
    COUNT(*) AS total_pagos_con_prestamo_id
FROM pagos
WHERE prestamo_id IS NOT NULL;
```

**Resultado esperado:** Ver cuántos registros hay antes de eliminar.

---

### **PASO 2: Actualizar pagos (poner prestamo_id a NULL)**
```sql
UPDATE pagos 
SET prestamo_id = NULL 
WHERE prestamo_id IS NOT NULL;
```

**Propósito:** Eliminar la referencia de foreign key antes de vaciar prestamos.

**Verificar resultado:**
```sql
SELECT 
    COUNT(*) AS pagos_con_prestamo_id_despues
FROM pagos
WHERE prestamo_id IS NOT NULL;
```

**Resultado esperado:** `0` (todos los pagos ahora tienen `prestamo_id = NULL`)

---

### **PASO 3: Eliminar cuotas relacionadas**
```sql
DELETE FROM cuotas WHERE prestamo_id IN (SELECT id FROM prestamos);
```

**Propósito:** Eliminar todas las cuotas asociadas a préstamos.

**Verificar resultado:**
```sql
SELECT 
    COUNT(*) AS cuotas_restantes
FROM cuotas;
```

**Resultado esperado:** `0` (si había cuotas) o el número de cuotas que no pertenecían a préstamos.

---

### **PASO 4: Eliminar evaluaciones relacionadas**
```sql
DELETE FROM prestamos_evaluacion WHERE prestamo_id IN (SELECT id FROM prestamos);
```

**Propósito:** Eliminar todas las evaluaciones asociadas a préstamos.

---

### **PASO 5: Eliminar auditorías relacionadas**
```sql
DELETE FROM prestamos_auditoria WHERE prestamo_id IN (SELECT id FROM prestamos);
```

**Propósito:** Eliminar todas las auditorías asociadas a préstamos.

---

### **PASO 6: Verificar que no quedan relaciones**
```sql
SELECT 
    'cuotas' AS tabla,
    COUNT(*) AS registros_restantes
FROM cuotas
WHERE prestamo_id IN (SELECT id FROM prestamos)
UNION ALL
SELECT 
    'pagos (con prestamo_id)' AS tabla,
    COUNT(*) AS registros_restantes
FROM pagos
WHERE prestamo_id IS NOT NULL
UNION ALL
SELECT 
    'prestamos_evaluacion' AS tabla,
    COUNT(*) AS registros_restantes
FROM prestamos_evaluacion
UNION ALL
SELECT 
    'prestamos_auditoria' AS tabla,
    COUNT(*) AS registros_restantes
FROM prestamos_auditoria;
```

**Resultado esperado:** Todos deben mostrar `0`.

---

### **PASO 7: VACIAR TABLA prestamos**
```sql
TRUNCATE TABLE prestamos RESTART IDENTITY;
```

**Propósito:** Eliminar todos los registros y reiniciar el contador de IDs.

**⚠️ CRÍTICO:** Solo ejecutar después de verificar que el PASO 6 muestra todos `0`.

---

### **PASO 8: Verificar que está vacía**
```sql
SELECT 
    COUNT(*) AS total_prestamos
FROM prestamos;
```

**Resultado esperado:** `0`

---

### **PASO 9: Resetear secuencia (opcional)**
```sql
ALTER SEQUENCE prestamos_id_seq RESTART WITH 1;
```

**Propósito:** Asegurar que el próximo ID empiece desde 1.

---

## 📝 RESUMEN DE LA SECUENCIA

1. ✅ Verificar estado actual
2. ✅ Actualizar `pagos.prestamo_id` a NULL
3. ✅ Eliminar `cuotas` relacionadas
4. ✅ Eliminar `prestamos_evaluacion` relacionadas
5. ✅ Eliminar `prestamos_auditoria` relacionadas
6. ✅ Verificar que no quedan relaciones
7. ✅ **TRUNCATE TABLE prestamos**
8. ✅ Verificar que está vacía
9. ✅ Resetear secuencia (opcional)

---

## ⚠️ IMPORTANTE

- **Ejecuta cada paso por separado**
- **Verifica cada resultado antes de continuar**
- **Si algún paso falla, detente y revisa**
- **Haz BACKUP antes de empezar**

---

## 🔧 Si el PASO 7 sigue fallando

Si después de ejecutar todos los pasos anteriores el `TRUNCATE` sigue fallando, ejecuta esto para eliminar temporalmente el constraint:

```sql
-- Obtener nombre del constraint
SELECT constraint_name 
FROM information_schema.table_constraints 
WHERE table_name = 'pagos' 
AND constraint_type = 'FOREIGN KEY'
AND constraint_name LIKE '%prestamo%';

-- Eliminar constraint (reemplaza 'nombre_del_constraint' con el nombre real)
ALTER TABLE pagos DROP CONSTRAINT nombre_del_constraint;

-- Ahora ejecutar TRUNCATE
TRUNCATE TABLE prestamos RESTART IDENTITY;

-- Restaurar constraint
ALTER TABLE pagos 
ADD CONSTRAINT nombre_del_constraint 
FOREIGN KEY (prestamo_id) REFERENCES prestamos(id) ON DELETE SET NULL;
```
