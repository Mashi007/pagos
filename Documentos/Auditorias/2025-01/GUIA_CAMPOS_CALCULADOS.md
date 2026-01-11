# 📋 GUÍA: Campos Calculados en Schemas Pydantic

**Fecha:** 2026-01-11  
**Propósito:** Documentar campos calculados que existen en schemas pero NO en modelos ORM

---

## 🎯 ¿Qué son los Campos Calculados?

Los **campos calculados** son campos que se generan en tiempo de ejecución a partir de otros datos, pero **NO se almacenan en la base de datos**. Estos campos existen solo en los schemas Pydantic para facilitar la serialización y el uso en la API.

---

## ✅ ¿Por qué NO están en BD?

1. **Redundancia:** Se pueden calcular desde otros campos existentes
2. **Consistencia:** Evita datos desactualizados si se almacenan
3. **Performance:** Se calculan solo cuando se necesitan
4. **Flexibilidad:** Permiten diferentes cálculos según el contexto

---

## 📊 Campos Calculados por Modelo

### **1. Amortización (amortizacion.py)**

**Total:** 21 campos calculados

#### **Campos de Resumen:**
- `cuotas_pagadas` - Lista de cuotas pagadas (calculado desde estado)
- `cuotas_pendientes` - Lista de cuotas pendientes (calculado desde estado)
- `cuotas_vencidas` - Lista de cuotas vencidas (calculado desde fecha_vencimiento)
- `proximas_cuotas` - Próximas cuotas a vencer
- `total_mora` - Suma total de mora de todas las cuotas
- `total_mora_calculada` - Mora recalculada en una operación específica

#### **Campos de Cálculo:**
- `monto_financiado` - Monto total financiado (del préstamo asociado)
- `numero_cuotas` - Número total de cuotas (del préstamo asociado)
- `tasa_interes` - Tasa de interés (del préstamo asociado)
- `tasa_mora_diaria` - Tasa de mora diaria (configuración del sistema)
- `tipo_amortizacion` - Tipo de amortización (FRANCESA, ALEMANA, etc.)
- `fecha_inicio` - Fecha de inicio del préstamo
- `fecha_calculo` - Fecha en que se realizó el cálculo

#### **Campos de Operación:**
- `monto_pago` - Monto de pago a aplicar (entrada de usuario)
- `cuotas_afectadas` - Lista de cuotas afectadas por un pago
- `cuotas_actualizadas` - Número de cuotas actualizadas en una operación
- `nuevo_saldo_pendiente` - Saldo pendiente después de aplicar un pago
- `cuotas` - Lista completa de cuotas (serialización de relación)

#### **Campos de Respuesta:**
- `resumen` - Diccionario con resumen de la operación
- `mensaje` - Mensaje descriptivo de la operación

**Ubicación en código:**
- `backend/app/schemas/amortizacion.py`
- Schemas: `TablaAmortizacionResponse`, `RecalcularMoraResponse`, `EstadoCuentaResponse`, `ProyeccionPagoResponse`

---

### **2. Analista (analista.py)**

**Total:** 5 campos calculados (Paginación)

- `total` - Total de registros
- `page` - Página actual
- `pages` - Total de páginas
- `size` - Tamaño de página
- `items` - Lista de items en la página

**Razón:** Campos de paginación estándar para respuestas de listado.

**Ubicación en código:**
- `backend/app/schemas/analista.py`
- Schema: `AnalistaListResponse` (o similar)

---

### **3. Aprobación (aprobacion.py)**

**Total:** 3 campos calculados

- `monto` - Monto calculado de la aprobación
- `tipo` - Tipo de aprobación (calculado desde contexto)
- `descripcion` - Descripción generada automáticamente

**Razón:** Campos derivados de la lógica de negocio de aprobaciones.

**Ubicación en código:**
- `backend/app/schemas/aprobacion.py`

---

### **4. Cliente (cliente.py)**

**Total:** 4 campos calculados (estimados)

- `total_prestamos` - Total de préstamos del cliente
- `total_pagos` - Total de pagos realizados
- `saldo_pendiente` - Saldo total pendiente
- `monto_total_prestamos` - Monto total de préstamos

**Razón:** Estadísticas calculadas desde relaciones con préstamos y pagos.

**Ubicación en código:**
- `backend/app/schemas/cliente.py`
- Schema: `ClienteDetallado` o similar

---

### **5. Pago (pago.py)**

**Total:** 1 campo calculado

- `cuotas` - Lista de cuotas asociadas al pago

**Razón:** Relación serializada para facilitar el uso en frontend.

**Ubicación en código:**
- `backend/app/schemas/pago.py`
- Schema: `PagoWithCuotas`

---

### **6. Préstamo (prestamo.py)**

**Total:** 4 campos calculados (estimados)

- `cuotas` - Lista de cuotas del préstamo
- `total_pagado` - Total pagado hasta la fecha
- `saldo_pendiente` - Saldo pendiente actual
- `proxima_cuota` - Próxima cuota a vencer

**Razón:** Campos calculados desde relaciones y operaciones.

**Ubicación en código:**
- `backend/app/schemas/prestamo.py`
- Schema: `PrestamoResponse` o similar

---

### **7. Usuario (user.py)**

**Total:** 5 campos calculados (Paginación)

- `total` - Total de usuarios
- `page` - Página actual
- `pages` - Total de páginas
- `size` - Tamaño de página
- `items` - Lista de usuarios

**Razón:** Campos de paginación estándar.

**Ubicación en código:**
- `backend/app/schemas/user.py`
- Schema: `UserListResponse`

---

## 🔍 Cómo Identificar Campos Calculados

### **Características Comunes:**

1. **No existen en modelo ORM:** No hay `Column()` correspondiente
2. **Se calculan en tiempo de ejecución:** En endpoints o servicios
3. **Dependen de otros campos:** Se derivan de relaciones o cálculos
4. **Solo en schemas Response:** No en schemas Create/Update

### **Ejemplo de Campo Calculado:**

```python
# Schema (amortizacion.py)
class EstadoCuentaResponse(BaseModel):
    total_mora: float  # ✅ Calculado - suma de monto_mora de todas las cuotas
    
# Modelo ORM (amortizacion.py)
class Cuota(Base):
    monto_mora = Column(Numeric(12, 2), nullable=True)  # ✅ Existe en BD
    # total_mora NO existe - se calcula en el endpoint
```

---

## ⚠️ Campos que NO son Calculados (Requieren Atención)

Si encuentras un campo en schema que:
- ✅ Debería estar en BD según lógica de negocio
- ✅ Se usa frecuentemente y afecta performance
- ✅ Requiere consistencia transaccional

**Acción:** Considerar agregarlo al modelo ORM y crear migración.

---

## 📝 Mejores Prácticas

### **✅ HACER:**

1. **Documentar campos calculados** en comentarios del schema
2. **Usar nombres descriptivos** que indiquen que son calculados
3. **Calcular solo cuando se necesitan** (lazy evaluation)
4. **Validar que los campos base existen** antes de calcular

### **❌ NO HACER:**

1. **No almacenar campos calculados** en BD (excepto por razones de performance documentadas)
2. **No usar campos calculados** en validaciones críticas sin verificar datos base
3. **No asumir que siempre están disponibles** (pueden ser None)

---

## 🔄 Mantenimiento

### **Al Agregar Nuevo Campo Calculado:**

1. ✅ Agregar al schema Pydantic
2. ✅ Documentar en comentarios por qué es calculado
3. ✅ Agregar a esta guía
4. ✅ Verificar que no debería estar en BD

### **Al Modificar Campo Base:**

1. ✅ Verificar campos calculados que dependen de él
2. ✅ Actualizar lógica de cálculo si es necesario
3. ✅ Actualizar tests

---

## 📚 Referencias

- `backend/app/schemas/amortizacion.py` - Ejemplos de campos calculados
- `backend/app/schemas/cliente.py` - Campos calculados de estadísticas
- `backend/app/api/v1/endpoints/amortizacion.py` - Lógica de cálculo

---

**Última actualización:** 2026-01-11  
**Mantenido por:** Equipo de desarrollo
