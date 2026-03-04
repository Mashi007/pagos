# ❓ PREGUNTAS CRÍTICAS - REQUIEREN RESPUESTA ANTES DE CORREGIR

## 🚨 BLOQUEADORES DE SISTEMA

### **P1: _hoy_local() UNDEFINED - ¿QUÉ IMPLEMENTAR?**

**Situación**: Función llamada 5 veces en `pagos.py` (líneas 204, 353, 1086, 1242, 1285) pero NO existe.
- Resultado: `NameError` cada vez que se aplica un pago
- **Sistema está ROTO** para pagos

**Opciones**:
```python
# OPCIÓN A: Fecha simple (UTC)
def _hoy_local() -> date:
    return date.today()

# OPCIÓN B: Timezone del negocio (Venezuela)
def _hoy_local() -> date:
    from zoneinfo import ZoneInfo
    from datetime import datetime
    tz = ZoneInfo("America/Caracas")
    return datetime.now(tz).date()

# OPCIÓN C: Usar variable global TZ_NEGOCIO (si existe)
def _hoy_local() -> date:
    # Usar settings.TZ_NEGOCIO = "America/Caracas"
    ...
```

**Pregunta**: ¿Cuál es la decisión de diseño?
- ¿Se necesita timezone "America/Caracas" para cobranza/mora?
- ¿O es suficiente date.today() (servidor UTC)?

---

### **P2: MORA/VENCIDO - ¿CUÁNDO TRANSICIONA ESTADO?**

**Situación**: Estados VENCIDO (1-90d) y MORA (91+d) se CALCULAN cada vez, NO se almacenan.

**Escenario actual**:
```
Cuota vencimiento: 2026-02-15
Cuota creada: 2026-02-01 (estado=PENDIENTE, dias_mora=0)

2026-03-15: Cuota está 28 días vencida, pero estado = PENDIENTE
            (Nadie lo sabe hasta que se aplique un pago)

2026-05-15: Cuota está 90 días vencida, pero estado = PENDIENTE
            (Sigue siendo PENDIENTE porque no hubo pago)

2026-06-15: Cuota está 91+ días vencida (MORA), pero estado = PENDIENTE
            (Si hay trigger de cobranza, no dispara porque estado ≠ MORA)
```

**Pregunta**: ¿Cómo debe funcionar?
- **OPCIÓN A**: Diariamente, scheduler ejecuta `detectar_cuotas_en_mora()` y actualiza estados
- **OPCIÓN B**: Estados transicionan SOLO cuando se aplica pago
- **OPCIÓN C**: Queries siempre calculan estado on-the-fly (actual, pero caro)

---

### **P3: USUARIO_PROPONENTE / USUARIO_AUTORIZA - ¿HARDCODEADOS O DINÁMICOS?**

**Situación actual**:
```python
# prestamos.py
usuario_proponente = "itmaster@rapicreditca.com"  # ← SIEMPRE igual
usuario_autoriza = "operaciones@rapicreditca.com"  # ← SIEMPRE igual
usuario_aprobador = current_user.email  # ← Solo en aprobar-manual
```

**Problema**: No se sabe quién REALMENTE creó/propuso el préstamo

**Pregunta**: ¿Debería ser dinámico?
- **OPCIÓN A**: Usar `current_user.email` de JWT en create_prestamo
- **OPCIÓN B**: Mantener hardcodeados (role de usuario?)
- **OPCIÓN C**: Definir tabla de usuarios_roles para mapear?

---

### **P4: pago_id EN CUOTA - ¿GUARDAR HISTORIAL O SOLO FINAL?**

**Situación actual**:
```
Pago A: +50 a cuota (total_pagado=50) → cuota.pago_id = A
Pago B: +50 a cuota (total_pagado=100) → cuota.pago_id = B (sobrescribe!)
Resultado: Solo B queda, A desaparece
```

**Pregunta**: ¿Se necesita historial de TODOS los pagos?
- **OPCIÓN A**: Guardar solo pago_id final (actual) - simple
- **OPCIÓN B**: Crear tabla `cuota_pagos` (join table) para historial completo
- **OPCIÓN C**: No guardar pago_id, solo relación via monto/fecha

---

### **P5: AUDITORÍA - ¿NIVEL DE DETALLE?**

**Situación**: Transiciones de estado NO se auditan
```
Cliente creado → ❌ No auditado
Préstamo → EN_REVISION → ❌ No auditado
Préstamo → APROBADO → ✓ Auditado (solo aprobar-manual)
Cuota → VENCIDO → ❌ No auditado
Cuota → MORA → ❌ No auditado
Pago creado → ❌ No auditado
```

**Pregunta**: ¿Qué se debe auditar?
- **OPCIÓN A**: Todos los CREATE + UPDATE de estados
- **OPCIÓN B**: Solo cambios de "estado" (no otros campos)
- **OPCIÓN C**: Audit completo + historial de valores anteriores

---

## ⚠️ INCONSISTENCIAS DE DISEÑO

### **P6: Z999999999 MÚLTIPLES CLIENTES - ¿INTENCIONAL?**

**Situación**: Clientes sin cédula → cedula = Z999999999
- Unique index excluye Z999999999
- Resultado: Múltiples clientes con cedula=Z999999999
- Problema: ¿Cómo se distinguen?

**Pregunta**: ¿Es correcto?
- **OPCIÓN A**: Mantener (es para "sin datos", ok multiples)
- **OPCIÓN B**: Generar ID único por cliente (Z999999999-001, Z999999999-002)
- **OPCIÓN C**: Obligar cédula válida en create

---

### **P7: TELEFONO AUTO-REEMPLAZADO - ¿CORRECTO?**

**Situación**: Si telefono duplicado → reemplaza con "+589999999999"
- Diferente a cedula/email (que lanzan 409 Conflict)
- Silencioso (no advierte al usuario)

**Pregunta**: ¿Es intencional?
- **OPCIÓN A**: Mantener (teléfono secundario, ok perder)
- **OPCIÓN B**: Cambiar a 409 Conflict (como cedula/email)
- **OPCIÓN C**: Permitir múltiples teléfonos (tabla separada)

---

### **P8: RECHAZADO ESTADO - ¿EXISTE O NO?**

**Situación**: 
- Frontend lo referencia (embudo de clientes)
- Database CHECK constraint NO lo incluye
- No hay endpoint para rechazar

**Pregunta**: ¿Flujo de rechazo?
- **OPCIÓN A**: Implementar rechazo (crear endpoint, agregar a CHECK)
- **OPCIÓN B**: Eliminar del frontend y documentación
- **OPCIÓN C**: Usar "DRAFT" como rechazo (sobreescribir)

---

### **P9: PAGO_ADELANTADO - ¿CUÁNDO?**

**Situación**: 
- Constraint permite PAGO_ADELANTADO
- Código NUNCA lo retorna en `_clasificar_nivel_mora`
- Documentación menciona: "si cubres cuotas futuras"

**Pregunta**: ¿Se implementa?
- **OPCIÓN A**: Completar: agregar lógica de pago adelantado
  ```python
  if total_pagado > 0 and fecha_vencimiento > hoy:
      return "PAGO_ADELANTADO"
  ```
- **OPCIÓN B**: Eliminar (quitar de constraints, documentación)
- **OPCIÓN C**: Postergar (marcar TODO)

---

## 📝 TRAZABILIDAD - ¿CUÁNTO DETALLE?

### **P10: USUARIO_REGISTRO EN PAGO/CLIENTE - ¿OBLIGATORIO?**

**Situación**: Campo existe pero NUNCA se popula
- usuario_registro en Cliente: NULL
- usuario_registro en Pago: NULL
- usuario_registro en Préstamo: "itmaster@..." (hardcodeado)

**Pregunta**: ¿Se debe auditar usuario actual?
- **OPCIÓN A**: Auto-poblar desde JWT en TODOS los CREATE
- **OPCIÓN B**: Mantener como NULL (anonimizar)
- **OPCIÓN C**: Usar tabla separada de auditoría con usuario_id (FK)

---

### **P11: FK cedula_cliente → clientes.cedula - ¿NECESARIA?**

**Situación**: 
- Pago tiene cedula_cliente (string)
- NO hay FK a tabla clientes
- Pago puede tener cedula_cliente que no existe en clientes

**Pregunta**: ¿Validar relación?
- **OPCIÓN A**: Agregar FK cedula_cliente → clientes.cedula
- **OPCIÓN B**: Mantener como referencia débil (string)
- **OPCIÓN C**: Usar cliente_id (INT FK) en lugar de cedula_cliente

---

### **P12: ESTADO DEBE SER PERSISTENTE EN CUOTA?**

**Situación**: VENCIDO/MORA se calculan cada vez
- No se guardan en `cuota.estado`
- Cuota.estado solo vale PENDIENTE/PAGADO/PAGO_ADELANTADO
- Queries tienen que recalcular siempre

**Pregunta**: ¿Persistir estado?
- **OPCIÓN A**: Guardar estado calculado (VENCIDO/MORA) al aplicar pago
- **OPCIÓN B**: Mantener cálculo on-the-fly (queries más simples)
- **OPCIÓN C**: Tabla separada `cuota_mora_status` (historial)

---

## 🔧 CORRECCIONES TÉCNICAS

### **P13: fecha_registro EN CLIENTE - ¿BUG?**

**Situación**: 
```python
# models/cliente.py
fecha_registro = Column(DateTime(timezone=True), ..., 
                       server_default=text("'2025-10-31 00:00:00'"))
```
- Todos los clientes quedan con fecha = 2025-10-31 (futuro!)
- Debería ser: `func.now()` o `CURRENT_TIMESTAMP`

**Pregunta**: ¿Es bug real?
- **OPCIÓN A**: Sí, fix a `func.now()`
- **OPCIÓN B**: Intencional (legacy migration?)
- **OPCIÓN C**: Dejar como está (si data es correcta)

---

### **P14: MODALIDAD_PAGO CHECK CONSTRAINT - ¿AGREGAR?**

**Situación**: 
- Valores permitidos: MENSUAL, QUINCENAL, SEMANAL
- NO hay CHECK constraint en DB
- Valores inválidos podrían insertarse directamente

**Pregunta**: ¿Proteger en DB?
- **OPCIÓN A**: Agregar CHECK (modalidad_pago IN (...))
- **OPCIÓN B**: Mantener validación solo en app
- **OPCIÓN C**: Usar tabla de referencia + FK

---

### **P15: CONCILIADO vs VERIFICADO_CONCORDANCIA - ¿CUÁL ES CANONICAL?**

**Situación**: 
- Dos campos para lo mismo (casi)
- Se syncan pero ambos existen
- Comentario dice "legacy"

**Pregunta**: ¿Deprecar?
- **OPCIÓN A**: Remover verificado_concordancia, usar solo conciliado
- **OPCIÓN B**: Mantener ambos (backward compatibility)
- **OPCIÓN C**: Migrar datos y deprecar uno

---

## 🎯 RESUMEN: ¿QUÉ PREGUNTAS SON CRÍTICAS?

**DEBES RESPONDER AHORA**:
1. ✅ P1: _hoy_local() → ¿timezone o date.today()?
2. ✅ P2: MORA/VENCIDO → ¿cuándo transiciona?
3. ✅ P5: Auditoría → ¿qué nivel de detalle?
4. ✅ P10: usuario_registro → ¿auto-poblar desde JWT?

**IMPORTANTE PERO PUEDEN ESPERAR**:
5. P3, P4, P12 (diseño arquitectónico)

**PUEDO DECIDIR**:
6. P6, P7, P8, P9, P11, P13, P14, P15 (pasar después)

---

## 📋 PUEDES RESPONDER:

```
P1: [A/B/C]: Explicación opcional
P2: [A/B/C]: Explicación opcional
P3: [A/B/C]: Explicación opcional
P4: [A/B/C]: Explicación opcional
P5: [A/B/C]: Explicación opcional
(... resto si lo consideras necesario)
```
