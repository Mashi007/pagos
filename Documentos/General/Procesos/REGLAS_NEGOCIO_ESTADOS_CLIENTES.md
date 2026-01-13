# 📋 Reglas de Negocio: Estados de Clientes

> **Documento de Referencia Principal**
> Última actualización: 2026-01-XX

---

## 🎯 Estados Posibles

### 1. **ACTIVO** (Estado por Defecto) ⭐
- **Significado**: Cliente activo en el sistema
- **Cuándo se asigna**:
  - **Por defecto** al crear un nuevo cliente
  - Si tiene préstamo aprobado o cuotas pendientes
  - **O** tiene 3 o menos cuotas atrasadas sin pagar
  - Si está al día con sus pagos
  - Si termina de pagar todas las cuotas (siempre permanece ACTIVO, no cambia a FINALIZADO)
- **Transición**: 
  - `ACTIVO` → `INACTIVO` (automático cuando tiene 4+ cuotas atrasadas sin pagar)

### 2. **INACTIVO**
- **Significado**: Cliente con 4 o más cuotas atrasadas sin pagar (vencidas y con total_pagado < monto_cuota)
- **Cuándo se asigna**:
  - **Automáticamente** cuando tiene 4 o más cuotas atrasadas sin pagar (vencidas y con total_pagado < monto_cuota)
  - Manualmente por administrador (requiere observación)
- **Transición**: 
  - `INACTIVO` → `ACTIVO` (automático cuando tiene 3 o menos cuotas atrasadas sin pagar)

---

## 🔄 Transiciones Automáticas

### **ACTIVO → INACTIVO** (Automático)
**Trigger**: Cuando tiene 4 o más cuotas atrasadas sin pagar

```python
# Implementación en: backend/app/services/estado_cliente_service.py
# Llamado desde: 
#   - backend/app/api/v1/endpoints/pagos.py (_actualizar_estado_cuota)
#   - backend/app/api/v1/endpoints/pagos_conciliacion.py (_conciliar_pago)
```

**Condiciones**:
1. Cliente tiene préstamos con estado `APROBADO`
2. Tiene 4 o más cuotas atrasadas sin pagar:
   - `fecha_vencimiento < CURRENT_DATE` (vencida)
   - `total_pagado < monto_cuota` (pago incompleto)

**Acción**:
- `cliente.estado = 'INACTIVO'`
- `cliente.fecha_actualizacion = CURRENT_TIMESTAMP`

---

### **INACTIVO → ACTIVO** (Automático)
**Trigger**: Cuando tiene 3 o menos cuotas atrasadas sin pagar

```python
# Implementación en: backend/app/services/estado_cliente_service.py
# Llamado desde: 
#   - backend/app/api/v1/endpoints/pagos.py (_actualizar_estado_cuota)
#   - backend/app/api/v1/endpoints/pagos_conciliacion.py (_conciliar_pago)
```

**Condiciones**:
1. Cliente está en estado `INACTIVO`
2. Tiene 3 o menos cuotas atrasadas sin pagar (después de registrar un pago)
3. O tiene préstamo aprobado o cuotas pendientes

**Acción**:
- `cliente.estado = 'ACTIVO'`
- `cliente.fecha_actualizacion = CURRENT_TIMESTAMP`

---

### **Al Aprobar Préstamo**
**Trigger**: Al aprobar un préstamo (`prestamos.estado = 'APROBADO'`)

```python
# Implementación en: backend/app/services/estado_cliente_service.py
# Llamado desde: backend/app/api/v1/endpoints/prestamos.py (procesar_cambio_estado)
```

**Condiciones**:
- Préstamo cambia a estado `APROBADO`
- Cliente tiene cédula asociada al préstamo

**Acción**:
- `cliente.estado = 'ACTIVO'` (si no está ya en ACTIVO)
- `cliente.fecha_actualizacion = CURRENT_TIMESTAMP`

---

### **⚠️ IMPORTANTE: Clientes siempre permanecen ACTIVO si están al día**
- Si un cliente termina de pagar todas sus cuotas, **siempre permanece en ACTIVO**
- **NO cambia a FINALIZADO** automáticamente
- El estado FINALIZADO ya no se usa en las reglas automáticas

---

## 🗄️ Implementación en Base de Datos

### **Función PostgreSQL**
**Archivo**: `scripts/sql/funcion_actualizar_estado_cliente.sql`

```sql
CREATE OR REPLACE FUNCTION actualizar_estado_cliente_automatico(p_cedula VARCHAR)
RETURNS VOID AS $$
-- Implementa todas las reglas de negocio
END;
$$ LANGUAGE plpgsql;
```

### **Triggers Automáticos**

1. **Trigger en `prestamos`**:
   - Se ejecuta al `INSERT` o `UPDATE` de `estado`
   - Cuando `estado IN ('APROBADO', 'RECHAZADO')`
   - Llama a `actualizar_estado_cliente_automatico()`

2. **Trigger en `cuotas`**:
   - Se ejecuta al `UPDATE` de `estado` o `total_pagado`
   - Cuando `estado = 'PAGADO'` o `total_pagado` cambia
   - Llama a `actualizar_estado_cliente_automatico()`

3. **Trigger en `pagos`**:
   - Se ejecuta al `UPDATE` de `conciliado`
   - Cuando `conciliado` cambia de `FALSE` a `TRUE`
   - Llama a `actualizar_estado_cliente_automatico()`

---

## 💻 Implementación en Backend

### **Servicio Principal**
**Archivo**: `backend/app/services/estado_cliente_service.py`

**Funciones principales**:
- `actualizar_estado_cliente_por_prestamo()`: Actualiza estado según estado del préstamo
- `verificar_y_actualizar_estado_finalizado()`: Verifica si debe cambiar a FINALIZADO
- `actualizar_estado_cliente_automatico()`: Función principal que aplica todas las reglas

### **Integración en Endpoints**

1. **Aprobar/Rechazar Préstamo**:
   ```python
   # backend/app/api/v1/endpoints/prestamos.py
   def procesar_cambio_estado(...):
       # ... código existente ...
       if nuevo_estado in ("APROBADO", "RECHAZADO"):
           actualizar_estado_cliente_por_prestamo(db, prestamo.cedula, nuevo_estado)
   ```

2. **Actualizar Cuota**:
   ```python
   # backend/app/api/v1/endpoints/pagos.py
   def _actualizar_estado_cuota(...):
       # ... código existente ...
       if estado_completado:
           verificar_y_actualizar_estado_finalizado(db, prestamo.cedula)
   ```

3. **Conciliar Pago**:
   ```python
   # backend/app/api/v1/endpoints/pagos_conciliacion.py
   def _conciliar_pago(...):
       # ... código existente ...
       if cuotas_actualizadas > 0:
           verificar_y_actualizar_estado_finalizado(db, pago.cedula)
   ```

---

## 📊 Modelo de Datos

### **Tabla `clientes`**

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `estado` | VARCHAR(20) | `'FINALIZADO'` | Estado del cliente |
| `activo` | BOOLEAN | `FALSE` | Indica si el cliente está activo |

### **Relación con otras tablas**

- `prestamos.cedula` → `clientes.cedula`
- `pagos.cedula` → `clientes.cedula`
- `cuotas.prestamo_id` → `prestamos.id` → `prestamos.cedula` → `clientes.cedula`

---

## ⚠️ Casos Especiales

### **Cliente con múltiples préstamos**
- Si tiene al menos un préstamo `APROBADO` → `ACTIVO`
- Solo cambia a `FINALIZADO` cuando TODOS los préstamos tienen todas sus cuotas pagadas

### **Observaciones en `cliente.notas`**
- Se genera automáticamente cuando todas las cuotas están `PAGADAS` pero `total_pagado < monto_total_financiamiento`
- Formato: `"Cliente tiene todas las cuotas con estado PAGADO pero total_pagado ({total}) < monto_total_financiamiento ({monto}). Diferencia: {diferencia}. Revisar conciliación de pagos."`

### **Cambio manual de estado**
- Los administradores pueden cambiar manualmente el estado de un cliente
- Requiere observación en `cliente.notas` explicando el motivo
- El sistema puede revertir automáticamente el cambio si se cumplen las condiciones

---

## 🔍 Verificación y Debugging

### **Consultar estado actual**
```sql
SELECT 
    c.cedula,
    c.nombres,
    c.estado,
    c.activo,
    COUNT(DISTINCT p.id) FILTER (WHERE p.estado = 'APROBADO') AS prestamos_aprobados,
    COUNT(DISTINCT cu.id) AS total_cuotas,
    COUNT(DISTINCT cu.id) FILTER (WHERE cu.estado = 'PAGADO') AS cuotas_pagadas,
    SUM(cu.total_pagado) AS total_pagado,
    SUM(cu.monto_cuota) AS monto_total_financiamiento
FROM clientes c
LEFT JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON cu.prestamo_id = p.id
WHERE c.cedula = 'V12345678'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo;
```

### **Forzar actualización de estado**
```sql
SELECT actualizar_estado_cliente_automatico('V12345678');
```

---

## 📝 Notas de Implementación

1. **Ejecución en tiempo real**: Los cambios se ejecutan automáticamente al crear/actualizar préstamos, pagos o cuotas
2. **Doble verificación**: Tanto en base de datos (triggers) como en backend (servicios)
3. **Manejo de errores**: Los errores en la actualización de estado no bloquean las operaciones principales
4. **Logging**: Todas las transiciones de estado se registran en los logs del sistema

---

## ✅ Checklist de Implementación

- [x] Función PostgreSQL `actualizar_estado_cliente_automatico()`
- [x] Triggers en `prestamos`, `cuotas`, `pagos`
- [x] Servicio en backend `estado_cliente_service.py`
- [x] Integración en endpoint de aprobar/rechazar préstamo
- [x] Integración en lógica de actualización de cuotas
- [x] Integración en lógica de conciliación de pagos
- [x] Actualización de modelo `Cliente` (default `FINALIZADO`)
- [x] Actualización de enum `EstadoCliente` (incluir `FINALIZADO`)
- [x] Documentación completa

---

**Última revisión**: 2026-01-11
**Autor**: Sistema de Gestión de Créditos
