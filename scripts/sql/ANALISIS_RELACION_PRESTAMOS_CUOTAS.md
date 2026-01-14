# 🔍 ANÁLISIS: Relación entre `prestamos` y `cuotas`

> **Fecha:** 2025-01-XX
> **Objetivo:** Verificar que todos los préstamos están correctamente relacionados con sus cuotas

---

## 📋 REGLAS DE NEGOCIO

### **Cuándo un Préstamo DEBE tener Cuotas:**

1. ✅ **Estado:** `prestamos.estado = 'APROBADO'`
2. ✅ **Fecha Base:** `prestamos.fecha_base_calculo IS NOT NULL`
3. ✅ **Número de Cuotas:** `prestamos.numero_cuotas > 0`
4. ✅ **Monto:** `prestamos.total_financiamiento > 0`

### **Cuándo un Préstamo NO debe tener Cuotas:**

- ❌ Estado diferente de `'APROBADO'` (DRAFT, RECHAZADO, etc.)
- ❌ Sin `fecha_base_calculo`
- ❌ `numero_cuotas = 0` o NULL

---

## ✅ VERIFICACIONES REALIZADAS

### **1. Préstamos Sin Cuotas**

**Consulta:** Identifica préstamos que deberían tener cuotas pero no las tienen.

**Criterios:**
- Estado = 'APROBADO'
- `fecha_base_calculo` IS NOT NULL
- Sin cuotas asociadas

**Acción si se encuentran:**
- Generar cuotas usando `generar_tabla_amortizacion()`

---

### **2. Préstamos con Cuotas Incompletas**

**Consulta:** Identifica préstamos con menos cuotas de las esperadas.

**Criterios:**
- Estado = 'APROBADO'
- `COUNT(cuotas) < prestamos.numero_cuotas`

**Acción si se encuentran:**
- Regenerar todas las cuotas o completar las faltantes

---

### **3. Cuotas Huérfanas**

**Consulta:** Identifica cuotas sin préstamo válido.

**Criterios:**
- `cuotas.prestamo_id` no existe en `prestamos`
- O préstamo existe pero estado != 'APROBADO'

**Acción si se encuentran:**
- Investigar origen de las cuotas
- Eliminar si son inválidas o corregir `prestamo_id`

---

### **4. Cuotas Duplicadas**

**Consulta:** Identifica números de cuota duplicados en el mismo préstamo.

**Criterios:**
- Mismo `prestamo_id` y `numero_cuota` repetido

**Acción si se encuentran:**
- Eliminar duplicados manteniendo la más reciente o la correcta

---

### **5. Coherencia de Montos**

**Consulta:** Verifica que la suma de `monto_cuota` coincida con `total_financiamiento`.

**Criterios:**
- `SUM(cuotas.monto_cuota) ≈ prestamos.total_financiamiento`

**Tolerancia:** Diferencia < 0.01 (1 centavo)

---

## 🔧 MEJORAS PROPUESTAS

### **MEJORA 1: Trigger para Generación Automática**

**Problema:**
- Las cuotas se generan manualmente o mediante código Python
- No hay garantía automática de que un préstamo aprobado tenga cuotas

**Solución:**
```sql
-- Trigger para generar cuotas automáticamente cuando se aprueba un préstamo
CREATE OR REPLACE FUNCTION generar_cuotas_al_aprobar()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = 'APROBADO' 
       AND OLD.estado != 'APROBADO'
       AND NEW.fecha_base_calculo IS NOT NULL
       AND NEW.numero_cuotas > 0 THEN
        -- Llamar a función Python o procedimiento almacenado
        -- para generar cuotas automáticamente
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generar_cuotas_al_aprobar
AFTER UPDATE ON public.prestamos
FOR EACH ROW
EXECUTE FUNCTION generar_cuotas_al_aprobar();
```

**Nota:** PostgreSQL no puede llamar directamente a Python, pero se puede implementar mediante:
- Función PL/pgSQL que llama a un script externo
- O mantener la lógica en Python pero agregar validación

---

### **MEJORA 2: Restricción CHECK para Validar Cuotas**

**Problema:**
- No hay validación a nivel BD que garantice que préstamos aprobados tengan cuotas

**Solución:**
```sql
-- Función para verificar que préstamo aprobado tiene cuotas
CREATE OR REPLACE FUNCTION verificar_cuotas_prestamo_aprobado()
RETURNS TRIGGER AS $$
DECLARE
    cantidad_cuotas INTEGER;
BEGIN
    IF NEW.estado = 'APROBADO' 
       AND NEW.fecha_base_calculo IS NOT NULL
       AND NEW.numero_cuotas > 0 THEN
        SELECT COUNT(*) INTO cantidad_cuotas
        FROM public.cuotas
        WHERE prestamo_id = NEW.id;
        
        IF cantidad_cuotas = 0 THEN
            RAISE WARNING 'Préstamo % aprobado sin cuotas. Se deben generar cuotas.', NEW.id;
        ELSIF cantidad_cuotas < NEW.numero_cuotas THEN
            RAISE WARNING 'Préstamo % tiene solo % cuotas de % esperadas.', 
                NEW.id, cantidad_cuotas, NEW.numero_cuotas;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_verificar_cuotas_prestamo
AFTER INSERT OR UPDATE ON public.prestamos
FOR EACH ROW
EXECUTE FUNCTION verificar_cuotas_prestamo_aprobado();
```

---

### **MEJORA 3: Índice para Optimizar Consultas**

**Problema:**
- Consultas frecuentes para encontrar préstamos sin cuotas pueden ser lentas

**Solución:**
```sql
-- Índice para optimizar búsqueda de préstamos aprobados
CREATE INDEX IF NOT EXISTS idx_prestamos_estado_fecha_base
ON public.prestamos(estado, fecha_base_calculo)
WHERE estado = 'APROBADO' AND fecha_base_calculo IS NOT NULL;
```

---

### **MEJORA 4: Vista para Préstamos con Problemas**

**Problema:**
- Consultas repetitivas para encontrar préstamos con problemas

**Solución:**
```sql
-- Vista para identificar préstamos con problemas de cuotas
CREATE OR REPLACE VIEW v_prestamos_problemas_cuotas AS
SELECT 
    p.id as prestamo_id,
    p.cedula,
    p.estado,
    p.numero_cuotas as cuotas_esperadas,
    COUNT(c.id) as cuotas_existentes,
    CASE 
        WHEN COUNT(c.id) = 0 THEN 'SIN CUOTAS'
        WHEN COUNT(c.id) < p.numero_cuotas THEN 'INCOMPLETAS'
        WHEN COUNT(c.id) > p.numero_cuotas THEN 'EXCESO'
        ELSE 'OK'
    END as problema
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.estado, p.numero_cuotas
HAVING COUNT(c.id) != p.numero_cuotas OR COUNT(c.id) = 0;
```

---

## 📊 INTERPRETACIÓN DE RESULTADOS

### **Resultados Esperados:**

#### **PASO 1: RESUMEN GENERAL**
- `prestamos_sin_cuotas` debería ser 0 o solo préstamos no aprobados
- `prestamos_con_cuotas` debería ser igual a préstamos aprobados

#### **PASO 2: PRESTAMOS SIN CUOTAS**
- Debería estar vacío o solo mostrar préstamos no aprobados
- Si hay préstamos aprobados sin cuotas → **ACCIÓN REQUERIDA**

#### **PASO 3: PRESTAMOS CON CUOTAS INCOMPLETAS**
- Debería estar vacío
- Si hay préstamos con cuotas incompletas → **ACCIÓN REQUERIDA**

#### **PASO 4: CUOTAS HUERFANAS**
- Debería estar vacío
- Si hay cuotas huérfanas → **INVESTIGAR Y CORREGIR**

#### **PASO 5: COHERENCIA POR ESTADO**
- Préstamos APROBADOS: `prestamos_con_cuotas` = `total_prestamos`
- Otros estados: Pueden no tener cuotas (normal)

#### **PASO 6: PRESTAMOS APROBADOS CON PROBLEMAS**
- Debería estar vacío
- Si hay problemas → **GENERAR/COMPLETAR CUOTAS**

#### **PASO 7: CUOTAS DUPLICADAS**
- Debería estar vacío
- Si hay duplicados → **ELIMINAR DUPLICADOS**

---

## 🔧 ACCIONES RECOMENDADAS

### **Si hay Préstamos Aprobados Sin Cuotas:**

```python
# Usar script: backend/scripts/generar_cuotas_faltantes.py
python backend/scripts/generar_cuotas_faltantes.py --prestamo-id <ID>
```

### **Si hay Préstamos con Cuotas Incompletas:**

```python
# Regenerar todas las cuotas
python backend/scripts/generar_cuotas_faltantes.py --prestamo-id <ID> --regenerar
```

### **Si hay Cuotas Huérfanas:**

```sql
-- Investigar origen
SELECT * FROM public.cuotas 
WHERE prestamo_id NOT IN (SELECT id FROM public.prestamos);

-- Eliminar si son inválidas (después de verificar)
DELETE FROM public.cuotas 
WHERE prestamo_id NOT IN (SELECT id FROM public.prestamos);
```

---

## ✅ CONCLUSIÓN

El script `verificar_relacion_prestamos_cuotas.sql` verifica:

1. ✅ Todos los préstamos aprobados tienen cuotas
2. ✅ El número de cuotas coincide con `numero_cuotas`
3. ✅ No hay cuotas huérfanas
4. ✅ No hay números de cuota duplicados
5. ✅ Los montos son coherentes

**Ejecuta el script en DBeaver para ver el estado actual de tu base de datos.**
