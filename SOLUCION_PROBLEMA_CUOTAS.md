# 🔧 Solución: Problema de Cuotas en Aprobación Automática

## ❌ Problema Detectado

Al aprobar automáticamente un préstamo (decision_final = "APROBADO_AUTOMATICO"), el sistema estaba:
- ✅ Cambiando correctamente el estado a "APROBADO"
- ✅ Generando la tabla de amortización
- ❌ **Modificando el numero_cuotas de 12 a 36** (INCORRECTO)

### Ejemplo:
- Préstamo original: **12 cuotas de $38.85**
- Después de aprobación: **36 cuotas de $12.95** ← INCORRECTO

---

## ✅ Solución Aplicada

### Código Corregido

**Archivo:** `backend/app/api/v1/endpoints/prestamos.py`  
**Líneas:** 795-819

**Cambio realizado:**
- ❌ ANTES: Aplicaba `plazo_maximo` automáticamente, modificando numero_cuotas
- ✅ AHORA: Mantiene el `numero_cuotas` original del préstamo

```python
# NOTA: No cambiar numero_cuotas, mantener el original del préstamo
# El plazo_maximo solo es informativo, no se aplica para aprobación automática

# NO ejecutar: actualizar_cuotas_segun_plazo_maximo() ❌
# SÍ mantener: numero_cuotas original del préstamo ✅
```

---

## 📋 Corregir Préstamos Ya Afectados

Si ya aprobaste préstamos con 36 cuotas que deberían tener 12:

### Opción 1: Usar SQL Directo (Rápido)

Ejecuta en DBeaver:

```sql
-- 1. Ver préstamos afectados
SELECT id, nombres, numero_cuotas, estado
FROM prestamos
WHERE estado = 'APROBADO' AND numero_cuotas = 36;

-- 2. Eliminar cuotas incorrectas
DELETE FROM cuotas
WHERE prestamo_id IN (
    SELECT id FROM prestamos 
    WHERE estado = 'APROBADO' AND numero_cuotas = 36
);

-- 3. Corregir numero_cuotas
UPDATE prestamos
SET 
    numero_cuotas = 12,
    cuota_periodo = total_financiamiento / 12.0
WHERE 
    estado = 'APROBADO' 
    AND numero_cuotas = 36;

-- 4. Verificar
SELECT id, nombres, numero_cuotas, cuota_periodo
FROM prestamos
WHERE estado = 'APROBADO' AND numero_cuotas = 36;
```

### Opción 2: Regenerar desde API

Para cada préstamo afectado, desde Postman o curl:

```bash
# Regenerar tabla de amortización con 12 cuotas
POST https://tu-api.com/api/v1/prestamos/{prestamo_id}/generar-amortizacion
```

---

## ✅ Verificación

Ejecuta en DBeaver:

```sql
SELECT 
    id,
    nombres,
    numero_cuotas,
    cuota_periodo,
    estado
FROM 
    prestamos
WHERE 
    estado = 'APROBADO'
ORDER BY 
    id DESC
LIMIT 5;
```

**Resultado esperado:**
- numero_cuotas = **12** (no 36)
- cuota_periodo = total_financiamiento / 12

---

## 📝 Próximos Pasos

1. ✅ Código corregido: Ya NO modificará numero_cuotas en futuras aprobaciones
2. ⚠️  Corregir BD: Ejecutar SQL o script para préstamos ya afectados
3. ✅ Probar: Crear nuevo préstamo y aprobar → Debe mantener 12 cuotas

---

## 🎯 Resultado Final

**ANTES (INCORRECTO):**
```
Préstamo 12 cuotas → Aprobación Automática → 36 cuotas ❌
```

**AHORA (CORRECTO):**
```
Préstamo 12 cuotas → Aprobación Automática → 12 cuotas ✅
```

