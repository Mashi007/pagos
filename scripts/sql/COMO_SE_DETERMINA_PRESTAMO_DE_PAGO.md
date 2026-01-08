# 🔍 ¿CÓMO SE SABE A QUÉ PRÉSTAMO CORRESPONDE UN PAGO?

> **Documento explicativo del proceso de vinculación**
> Última actualización: 2026-01-08

---

## 🎯 RESPUESTA DIRECTA

**El número de cédula es la forma principal de vincular pagos a cuotas y préstamos.**

**Cuando un usuario registra un pago con número de cédula, el sistema busca automáticamente el préstamo aprobado asociado a esa cédula y aplica el pago a las cuotas correspondientes.**

**El campo `pagos.prestamo_id` se asigna automáticamente basándose en la cédula.**

---

## 🔗 VINCULACIÓN POR CÉDULA (MECANISMO PRINCIPAL)

### **Flujo Visual:**

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO REGISTRA PAGO CON NÚMERO DE CÉDULA                  │
│  └─ pagos.cedula = "1234567890"                             │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  SISTEMA BUSCA PRÉSTAMO POR CÉDULA                          │
│  └─ Query: prestamos WHERE cedula = "1234567890"             │
│            AND estado = "APROBADO"                           │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  SISTEMA ASIGNA prestamo_id AUTOMÁTICAMENTE                  │
│  └─ pagos.prestamo_id = [ID_ENCONTRADO]                     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  SISTEMA OBTIENE CUOTAS DEL PRÉSTAMO                         │
│  └─ Query: cuotas WHERE prestamo_id = [ID_ENCONTRADO]       │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  SISTEMA APLICA PAGO A CUOTAS                                │
│  └─ Actualiza cuotas.total_pagado                            │
│  └─ Actualiza estado de cuotas                               │
└─────────────────────────────────────────────────────────────┘
```

**Conclusión:** La cédula es el campo que permite vincular pagos → préstamos → cuotas.

---

## 📋 PROCESO DE VINCULACIÓN

### **REGLA PRINCIPAL: La Cédula Vincula Pagos a Préstamos**

**El número de cédula es el mecanismo principal de vinculación:**

```
Usuario registra pago CON número de cédula
└─ pagos.cedula = "1234567890" (REQUERIDO)

Sistema busca automáticamente:
└─ Busca préstamo por: prestamos.cedula = "1234567890" AND estado = "APROBADO"
└─ Si encuentra → asigna pagos.prestamo_id automáticamente
└─ El pago se aplica a las cuotas del préstamo encontrado
```

**IMPORTANTE:**
- ✅ **La cédula es el campo principal** que vincula pagos a préstamos
- ✅ **El sistema busca automáticamente** el préstamo basándose en la cédula
- ✅ **El prestamo_id se asigna automáticamente** basándose en la cédula
- ✅ **El pago se aplica a las cuotas** del préstamo asociado a esa cédula

---

### **MÉTODO 1: Prestamo_id viene en el Request (Opcional)**

**Cuando el usuario también especifica el préstamo (opcional):**

```
1. Usuario registra pago con:
   └─ pagos.cedula = "1234567890" (REQUERIDO)
   └─ prestamo_id = 123 (OPCIONAL en request)

2. ✅ VALIDACIÓN: Se verifica que la cédula del pago coincida con la del préstamo
   └─ Si coincide → Se acepta el prestamo_id
   └─ Si NO coincide → Se busca automáticamente por cédula
```

**Código:**
```python
# El prestamo_id viene directamente del request
prestamo_id = pago_data.prestamo_id  # Del request

if prestamo_id:
    # Validar que la cédula del préstamo coincida con la del pago
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if prestamo and prestamo.cedula == pago_data.cedula:
        # ✅ Cédula coincide, se acepta el prestamo_id
        pagos.prestamo_id = prestamo_id
    else:
        # ⚠️ Cédula NO coincide, buscar automáticamente
        prestamo_id = None  # Se buscará automáticamente
```

---

### **MÉTODO 2: Búsqueda Automática por Cédula (PRINCIPAL)**

**Este es el método principal. El usuario solo necesita proporcionar la cédula:**

```
1. Usuario registra pago CON número de cédula
   └─ pagos.cedula = "1234567890" (REQUERIDO)
   └─ prestamo_id = NULL (opcional, se busca automáticamente)

2. ✅ BÚSQUEDA AUTOMÁTICA POR CÉDULA:
   └─ Busca préstamo por: prestamos.cedula = "1234567890" AND estado = "APROBADO"
   └─ Si encuentra UN préstamo → asigna pagos.prestamo_id automáticamente
   └─ Si encuentra MÚLTIPLES préstamos → toma el primero encontrado
   └─ Si NO encuentra → prestamo_id = NULL (no se aplica a cuotas)

3. ✅ APLICACIÓN A CUOTAS:
   └─ El pago se aplica a las cuotas del préstamo asociado a esa cédula
   └─ Las cuotas pertenecen al préstamo que tiene la misma cédula
```

**Código:**
```python
# backend/app/api/v1/endpoints/pagos.py - línea 614
prestamo_id = pago_data.prestamo_id  # Del request (puede ser None)

if not prestamo_id:
    # ✅ BUSCAR PRÉSTAMO AUTOMÁTICAMENTE
    prestamo = db.query(Prestamo).filter(
        Prestamo.cedula == pago_data.cedula,
        Prestamo.estado == "APROBADO"
    ).first()
    
    if prestamo:
        prestamo_id = prestamo.id  # ✅ ASIGNADO AUTOMÁTICAMENTE
        logger.info(f"✅ Préstamo encontrado automáticamente: prestamo_id={prestamo_id}")
    else:
        logger.warning(f"⚠️ No se encontró préstamo APROBADO para cédula {pago_data.cedula}")
        prestamo_id = None  # ⚠️ NO se encontró préstamo
```

---

## 🔍 CRITERIOS DE BÚSQUEDA

### **Búsqueda Automática por Cédula:**

**La cédula es el campo principal que vincula pagos a préstamos y cuotas.**

**Campos utilizados:**
1. ✅ `pagos.cedula` = cédula del cliente (REQUERIDO - campo principal)
2. ✅ `prestamos.cedula` = cédula del préstamo (debe coincidir exactamente)
3. ✅ `prestamos.estado` = `"APROBADO"` (solo préstamos aprobados tienen cuotas)

**Query SQL equivalente:**
```sql
-- Buscar préstamo por cédula
SELECT id 
FROM prestamos 
WHERE cedula = '1234567890'  -- Cédula del pago
  AND estado = 'APROBADO'    -- Solo préstamos aprobados tienen cuotas
LIMIT 1;

-- Una vez encontrado el préstamo, las cuotas se obtienen por prestamo_id
SELECT * 
FROM cuotas 
WHERE prestamo_id = [ID_ENCONTRADO]
  AND estado != 'PAGADO';    -- Solo cuotas pendientes
```

**Resultado:**
- Si encuentra 1 préstamo → `pagos.prestamo_id` = ID del préstamo encontrado → **Pago se aplica a cuotas**
- Si encuentra múltiples préstamos → `pagos.prestamo_id` = ID del primero encontrado → **Pago se aplica a cuotas del primer préstamo**
- Si NO encuentra → `pagos.prestamo_id` = `NULL` → **Pago NO se aplica a cuotas**

**Flujo completo:**
```
Cédula → Préstamo → Cuotas → Aplicación de Pago
```

---

## ⚠️ CASOS ESPECIALES

### **Caso 1: Cliente con Múltiples Préstamos Aprobados**

**Escenario:**
```
Cliente: cédula = "1234567890"
Préstamos aprobados:
- Préstamo 1: id = 100, estado = "APROBADO"
- Préstamo 2: id = 200, estado = "APROBADO"
- Préstamo 3: id = 300, estado = "APROBADO"

Pago registrado: cedula = "1234567890", prestamo_id = NULL
```

**Comportamiento:**
- ✅ El sistema busca automáticamente
- ⚠️ Encuentra múltiples préstamos aprobados
- ⚠️ Toma el primero encontrado (puede ser cualquiera según el orden de la query)
- ⚠️ **RECOMENDACIÓN:** Especificar `prestamo_id` en el request para evitar ambigüedad

**Solución:**
```python
# Si hay múltiples préstamos, el usuario DEBE especificar prestamo_id
# O el sistema puede tomar el más reciente:
prestamo = db.query(Prestamo).filter(
    Prestamo.cedula == cedula,
    Prestamo.estado == "APROBADO"
).order_by(Prestamo.fecha_aprobacion.desc()).first()  # Más reciente primero
```

---

### **Caso 2: Cliente sin Préstamos Aprobados**

**Escenario:**
```
Cliente: cédula = "1234567890"
Préstamos:
- Préstamo 1: id = 100, estado = "DRAFT" (no aprobado)
- Préstamo 2: id = 200, estado = "RECHAZADO"

Pago registrado: cedula = "1234567890", prestamo_id = NULL
```

**Comportamiento:**
- ✅ El sistema busca automáticamente
- ❌ NO encuentra préstamos con `estado = "APROBADO"`
- ❌ `pagos.prestamo_id` = `NULL`
- ⚠️ El pago NO se aplicará a cuotas (no tiene préstamo asociado)

**Resultado:**
- El pago se registra pero NO se aplica a cuotas
- El usuario debe vincularlo manualmente después

---

### **Caso 3: Cédula del Pago NO coincide con Cédula del Préstamo**

**Escenario:**
```
Pago registrado:
- cedula = "1234567890"
- prestamo_id = 100 (especificado en request)

Préstamo 100:
- cedula = "9876543210" (diferente)
```

**Comportamiento:**
- ⚠️ El sistema detecta la inconsistencia
- ⚠️ Puede rechazar el pago o buscar automáticamente
- ✅ **VALIDACIÓN:** Se verifica que `pago.cedula == prestamo.cedula` antes de aplicar a cuotas

**Código de validación:**
```python
def _verificar_prestamo_y_cedula(pago: Pago, db: Session):
    if not pago.prestamo_id:
        return False, "No tiene préstamo asociado"
    
    prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
    if not prestamo:
        return False, "Préstamo no encontrado"
    
    if prestamo.cedula != pago.cedula:
        return False, "Cédula del pago no coincide con cédula del préstamo"
    
    return True, "Validación exitosa"
```

---

## 🔄 FLUJO COMPLETO DE VINCULACIÓN

### **Paso 1: Registro del Pago**

```
Usuario registra pago:
├─ cedula = "1234567890"
├─ prestamo_id = NULL (opcional en request)
└─ monto_pagado = $500.00

Sistema:
├─ Si prestamo_id viene → usar ese
├─ Si prestamo_id NO viene → buscar automáticamente
│   └─ Query: prestamos WHERE cedula = "1234567890" AND estado = "APROBADO"
│   └─ Si encuentra → asignar prestamo_id
│   └─ Si NO encuentra → prestamo_id = NULL
└─ Guardar en tabla pagos
```

### **Paso 2: Validación al Aplicar a Cuotas**

```
Cuando se concilia el pago:
├─ Verificar que pagos.prestamo_id NO es NULL
├─ Verificar que el préstamo existe
├─ Verificar que pagos.cedula == prestamos.cedula
└─ Si todas las validaciones pasan → aplicar a cuotas
```

---

## 📊 TABLA DE VINCULACIÓN

| Escenario | `prestamo_id` en Request | Préstamos Encontrados | Resultado |
|-----------|-------------------------|----------------------|-----------|
| Usuario especifica | `123` | N/A | `pagos.prestamo_id = 123` |
| Búsqueda automática | `NULL` | 1 préstamo aprobado | `pagos.prestamo_id = ID encontrado` |
| Búsqueda automática | `NULL` | Múltiples préstamos | `pagos.prestamo_id = Primer ID encontrado` |
| Búsqueda automática | `NULL` | 0 préstamos aprobados | `pagos.prestamo_id = NULL` |
| Cédula no coincide | `123` | Préstamo existe pero cédula diferente | ⚠️ Error o búsqueda automática |

---

## ✅ RESUMEN

### **Cómo se determina el préstamo (Basado en Cédula):**

**REGLA PRINCIPAL: El número de cédula vincula pagos a préstamos y cuotas.**

1. **Usuario registra pago con número de cédula:**
   - ✅ `pagos.cedula` = número de cédula (REQUERIDO)
   - ✅ El sistema busca automáticamente el préstamo por `cedula` y `estado = "APROBADO"`
   - ✅ Si encuentra → asigna `pagos.prestamo_id` automáticamente
   - ✅ El pago se aplica a las cuotas del préstamo asociado a esa cédula

2. **Si también viene `prestamo_id` en el request (opcional):**
   - ✅ Se valida que la cédula del pago coincida con la del préstamo
   - ✅ Si coincide → se usa ese `prestamo_id`
   - ✅ Si NO coincide → se busca automáticamente por cédula

3. **Resultado de la búsqueda por cédula:**
   - ✅ Si encuentra 1 préstamo → `pagos.prestamo_id` = ID encontrado → **Pago se aplica a cuotas**
   - ✅ Si encuentra múltiples → `pagos.prestamo_id` = Primer ID encontrado → **Pago se aplica a cuotas del primer préstamo**
   - ❌ Si NO encuentra → `pagos.prestamo_id` = `NULL` → **Pago NO se aplica a cuotas**

### **Validación final:**

Antes de aplicar a cuotas, se verifica:
- ✅ `pagos.prestamo_id` NO es NULL (asignado por búsqueda de cédula)
- ✅ El préstamo existe
- ✅ `pagos.cedula == prestamos.cedula` (coincidencia de cédula)

---

## ⚠️ IMPORTANTE

**Regla crítica:**

- ✅ **El número de cédula es la forma principal de vincular pagos a préstamos y cuotas**
- ✅ **Cuando un usuario registra un pago con número de cédula, el sistema busca automáticamente el préstamo aprobado asociado a esa cédula**
- ✅ **El campo `pagos.prestamo_id` se asigna automáticamente basándose en la cédula**
- ✅ **El pago se aplica a las cuotas del préstamo que tiene la misma cédula**
- ⚠️ Si `prestamo_id = NULL` (no se encontró préstamo por cédula), el pago NO se aplica a cuotas
- ⚠️ La búsqueda automática funciona mejor si hay exactamente 1 préstamo aprobado para esa cédula
- ⚠️ Si hay múltiples préstamos aprobados para la misma cédula, se toma el primero encontrado (puede especificar `prestamo_id` para mayor precisión)

---

**Última actualización:** 2026-01-08
