# 📋 AUDITORÍA INTEGRAL: TRAZABILIDAD CLIENTE → REPORTE PAGO

**Fecha**: 2026-03-01  
**Objetivo**: Verificar que reglas de negocio estén enlazadas desde creación de cliente hasta reporte de pago en cuota  
**Metodología**: Análisis de creación, transiciones de estado, y trazabilidad en cada etapa

---

## 📌 RESUMEN EJECUTIVO

| Etapa | Estado | Trazabilidad | Coherencia | Riesgos |
|-------|--------|--------------|-----------|---------|
| **Cliente** | ⚠️ Parcial | ❌ No auditada | ⚠️ Inconsistencias | Alto |
| **Préstamo** | ⚠️ Parcial | ⚠️ Incompleta | ⚠️ Debilidades | Medio |
| **Cuota** | ✅ Completa | ⚠️ Solo timestamps | ✅ Estados claros | Bajo |
| **Pago** | ⚠️ Parcial | ❌ Missing _hoy_local() | ❌ Crítica | MUY ALTO |

---

## 🔄 FLUJO COMPLETO: CLIENTE → PAGO

### **ETAPA 1: CREACIÓN DE CLIENTE**

#### ✅ Qué SÍ está trazado:
```
POST /api/v1/clientes
├─ cedula (UNIQUE, except Z999999999)
├─ nombres (UNIQUE)
├─ email (UNIQUE si no vacío)
├─ telefono (UNIQUE si >= 8 dígitos, sino reemplaza con placeholder)
├─ direccion (sin validación)
├─ estado (default: ACTIVO)
├─ fecha_registro: NOW() (auto via server_default)
└─ usuario_registro: NULL (BUG: no se popula)
```

#### ❌ Qué NO está trazado:
- **Sin auditoría**: No hay entrada en tabla `auditoria` al crear cliente
- **usuario_registro vacío**: No se guarda quién creó el cliente
- **Timestamp incorrecto**: `fecha_registro` tiene default hardcodeado = '2025-10-31' (futuro!)

#### ⚠️ Inconsistencias críticas:
1. **Estado duplicado para duplicados de teléfono**: Si hay duplicado, se reemplaza con "+589999999999" en silencio (diferente a cedula/email que lanzan 409)
   - Riesgo: Se pierden números de teléfono legítimos sin advertencia

2. **No hay constraint DB en estado**: A diferencia de `prestamos`, `cuotas`, `pagos` (que tienen CHECK), `clientes.estado` no tiene constraint
   - Riesgo: Estados inválidos pueden insertarse por debajo de validación de app

3. **Z999999999 especial**: Clientes sin cédula usan Z999999999; puede haber múltiples
   - Pregunta: ¿Cómo se distinguen clientes sin cédula?

#### 📊 Matriz de validación en Cliente:

| Campo | Frontend | Schema | App Logic | DB Constraint | Sincronizado |
|-------|----------|--------|-----------|----------------|--------------|
| cedula | Sí (V/E/J) | Z999999999 default | Check unique | Partial index | ✅ |
| nombres | No | "Revisar Nombres" | Check unique | NONE | ⚠️ |
| email | No | NONE | Check unique | NONE | ⚠️ |
| telefono | Sí (+58) | Placeholder default | Auto-replace | NONE | ❌ |
| estado | Dropdown | ACTIVO default | Whitelist | NONE | ⚠️ |

---

### **ETAPA 2: CREACIÓN DE PRÉSTAMO**

#### ✅ Qué SÍ está trazado:
```
POST /api/v1/prestamos
├─ cliente_id (FK)
├─ cedula_cliente (string, matches client)
├─ numero_cuotas: 1-12 (CHECK constraint ✓)
├─ total_financiamiento: > 0 (CHECK constraint ✓)
├─ tasa_interes: default 0.00% (flexible, sin constraint)
├─ modalidad_pago: MENSUAL|QUINCENAL|SEMANAL (default MENSUAL)
├─ estado: DRAFT (default)
├─ fecha_registro: NOW() ✓
├─ usuario_proponente: 'itmaster@rapicreditca.com' (hardcoded, no de usuario actual)
├─ usuario_aprobador: NULL (solo set en aprobar-manual)
└─ usuario_autoriza: 'operaciones@rapicreditca.com' (hardcoded)
```

#### ❌ Qué NO está trazado:
- **usuario_proponente siempre igual**: Nunca se actualiza del usuario actual
- **usuario_aprobador**: Solo se set en `aprobar-manual`; otras transiciones no lo actualizan
- **Transiciones no auditadas**: DRAFT→EN_REVISION, DRAFT→APROBADO, etc. sin registro en `auditoria`

#### ⚠️ Inconsistencias:

1. **Transiciones de estado parcialmente auditadas**:
   - ✅ `aprobar-manual` → Auditoria log: "APROBACION_MANUAL"
   - ❌ `aplicar-condiciones-aprobacion` → NO auditado
   - ❌ `evaluar-riesgo` → NO auditado
   - ❌ `asignar-fecha-aprobacion` → NO auditado

2. **RECHAZADO estado**: Referenciado en frontend pero NO en CHECK constraint
   - Pregunta: ¿Hay flujo de rechazo implementado?

3. **modalidad_pago sin validation**: No hay CHECK constraint en DB
   - Riesgo: Valores inválidos pueden insertarse directamente a DB

4. **Usuarios hardcodeados**: usuario_proponente y usuario_autoriza siempre iguales
   - Pregunta: ¿Debería reflejar el usuario actual?

#### 📊 Matriz de trazabilidad en Préstamo:

| Campo | Cuando se Set | Quien lo actualiza | Auditado | Problema |
|-------|---------------|--------------------|----------|----------|
| usuario_proponente | CREATE | App (hardcoded) | ❌ | Nunca del usuario real |
| usuario_aprobador | aprobar-manual | Sistema | ✅ | Falta en otras transiciones |
| usuario_autoriza | CREATE | App (hardcoded) | ❌ | Nunca del usuario real |
| fecha_aprobacion | aprobar-manual / asignar-fecha | Sistema | Partial | Inconsistente |

---

### **ETAPA 3: GENERACIÓN DE CUOTAS**

#### ✅ Qué SÍ está trazado:
```
Triggers:
1. POST /{id}/aprobar-manual → Regenera cuotas (DELETE + INSERT)
2. POST /{id}/aplicar-condiciones → Crea si no existen (1 sola vez)
3. POST /{id}/asignar-fecha-aprobacion → Crea si no existen (1 sola vez)

Campos inicializados:
├─ prestamo_id (FK ✓)
├─ numero_cuota: 1..N (UNIQUE (prestamo_id, numero_cuota) ✓)
├─ monto_cuota: Flat o French amortization ✓
├─ saldo_capital_inicial/final: Cálculo running balance ✓
├─ monto_capital: saldo_inicial - saldo_final (stored [B3] ✓)
├─ monto_interes: monto_cuota - monto_capital (stored [B3] ✓)
├─ dias_mora: 0 (inicialmente)
├─ estado: PENDIENTE (inicial)
├─ fecha_vencimiento: Calculada desde modalidad_pago ✓
├─ fecha_pago: NULL (se set al pagar)
└─ creado_en: NOW() ✓
```

#### ❌ Qué NO está trazado:
- **Sin auditoría de cambios de estado**: Cuota puede pasar PENDIENTE→VENCIDO→MORA sin registro
- **PAGO_ADELANTADO no implementado**: Constraint lo permite, pero código no lo clasifica

#### ⚠️ Inconsistencias:

1. **Transiciones de estado CALCULADAS, no ALMACENADAS**:
   - VENCIDO = hoy > fecha_vencimiento Y dias < 90 (NOT STORED)
   - MORA = dias_mora > 90 (NOT STORED)
   - Se recalculan cada vez que se aplica pago
   - Riesgo: Si pagos stale, estado no refleja realidad actual

2. **Validación de transiciones bypass**:
   - _validar_transicion_estado_cuota solo conoce PENDIENTE/PAGO_ADELANTADO/PAGADO
   - VENCIDO/MORA pasan sin validar (solo warning log)

3. **pago_id se SOBRESCRIBE**:
   - Cada aplicación de pago actualiza pago_id
   - Resultado: Solo el ÚLTIMO pago que completó queda registrado
   - Se pierden todos los pagos parciales anteriores

#### 📊 Ciclo de vida de Cuota:

```
CREATE (PENDIENTE, dias_mora=0, total_pagado=0)
    ↓
[Time passes, fecha_vencimiento ~ fecha hoy]
    ↓
[Pago applied]
    ├─ 100% covered → PAGADO ✓
    ├─ 0% + dias=0 → PENDIENTE
    ├─ 0% + dias 1-90 → VENCIDO
    ├─ 0% + dias >90 → MORA
    └─ Parcial → Estado depends on dias_mora + coverage
    ↓
[UPDATE: estado stored, fecha_pago, total_pagado, pago_id, dias_mora]

⚠️ NO HAY AUDIT de esta transición
```

---

### **ETAPA 4: CREACIÓN DE PAGO**

#### ✅ Qué SÍ está trazado:
```
POST /api/v1/pagos
├─ cedula_cliente (string, NOT NULL, indexed)
├─ prestamo_id (FK, ON DELETE SET NULL)
├─ monto_pagado: > 0 (CHECK constraint ✓)
├─ numero_documento (UNIQUE, NULL allowed - multiple NULLs ok)
├─ fecha_pago (NOT NULL)
├─ estado: PENDIENTE (inicial, o PAGADO si desde guardar-fila-editable)
├─ conciliado: FALSE (default, true only via conciliación/update)
├─ fecha_registro: NOW() ✓
├─ fecha_conciliacion: NULL (set quando conciliado=TRUE)
└─ usuario_registro: NULL (BUG: never set)
```

#### ❌ Qué NO está trazado:
- **_hoy_local() UNDEFINED**: Función llamada 5 veces pero NO definida en código
  - Líneas: 204, 353, 1086, 1242, 1285 en pagos.py
  - **CRÍTICO**: Sistema CRASHES al calcular dias_mora

- **usuario_registro vacío**: No se guarda quién creó el pago

- **Sin FK a clientes.cedula**: cedula_cliente no está validada contra tabla clientes

#### ⚠️ Inconsistencias CRÍTICAS:

1. **BUG DE RUNTIME: _hoy_local() no existe**
   ```python
   # pagos.py línea 204
   dias_mora = (_hoy_local() - fecha_vencimiento.date()).days
   # NameError: name '_hoy_local' is not defined
   ```
   Impacto: **Sistema se cae cuando se aplica cualquier pago**

2. **pago_id se sobrescribe en cuota**:
   - Pago A paga 50% cuota 1 → cuota.pago_id = A
   - Pago B paga 50% restante → cuota.pago_id = B (sobrescribe!)
   - Pregunta: ¿Cuáles pagos completaron esta cuota? Solo B queda registrado

3. **No hay validación cedula → cliente**:
   - Pago puede tener cedula que no existe en clientes
   - No hay constraint que lo impida

4. **numero_documento UNIQUE pero NULL allowed**:
   - Múltiples pagos pueden tener numero_documento=NULL
   - Riesgo: Duplicados ocultos

#### 📊 Estados de Pago:

```
CREATE
├─ Estado: PENDIENTE (o PAGADO si entrada manual)
├─ conciliado: FALSE
├─ Si prestamo_id && monto > 0:
│  └─ Aplicar a cuotas (FIFO por numero_cuota)
│     └─ Si alguna cuota procesada: estado = PAGADO
│
UPDATE /pagos/{id}
├─ Si conciliado: FALSE → TRUE
│  ├─ fecha_conciliacion = NOW()
│  ├─ verificado_concordancia = "SI"
│  └─ Aplicar a cuotas (si no fue antes)
│
CONCILIACION
└─ Buscar pago por numero_documento
   ├─ conciliado = TRUE
   ├─ Aplicar a cuotas
   └─ estado = PAGADO
```

---

### **ETAPA 5: APLICACIÓN FIFO A CUOTAS**

#### ✅ Qué SÍ funciona:
```
_aplicar_pago_a_cuotas_interno(pago, db):
├─ Requiere: prestamo_id && monto > 0 ✓
├─ Query: SELECT cuotas WHERE fecha_pago IS NULL AND total_pagado < monto
│         ORDER BY numero_cuota ASC ✓ (FIFO)
└─ Para cada cuota:
   ├─ remaining = min(monto - aplicado, monto_cuota - total_pagado)
   ├─ cuota.total_pagado += remaining
   ├─ cuota.fecha_pago = hoy
   ├─ cuota.pago_id = pago.id (SOBRESCRIBE)
   ├─ cuota.dias_mora = (_hoy_local() - fecha_vencimiento).days ⚠️ BUG
   ├─ cuota.estado = _clasificar_nivel_mora(...) ✓
   └─ aplicado += remaining
```

#### ❌ Fallas críticas:
1. **_hoy_local() undefined** → Runtime error

2. **pago_id overwrite**: Si cuota es pagada por múltiples pagos, solo el último queda
   - Pregunta: ¿Se necesita historial completo?

3. **No sincroniza prestamo.estado**: Pago aplicado pero estado de préstamo no se actualiza
   - Pregunta: ¿Debería cambiar a estado de finalizado si todas cuotas PAGADO?

---

### **ETAPA 6: CÁLCULO DE MORA**

#### ✅ Lógica (cuando funcione):
```python
def _clasificar_nivel_mora(dias_mora: int, total_pagado: float, monto_cuota: float) -> str:
    if total_pagado >= monto_cuota - 0.01:
        return "PAGADO"  # 100% covered
    if dias_mora == 0:
        return "PENDIENTE"  # Not yet due
    if dias_mora > 90:
        return "MORA"  # 91+ days
    return "VENCIDO"  # 1-90 days
```

#### ❌ Problemas:
1. **Depende de _hoy_local()** que no existe
2. **Estados NO se guardan persistentemente**: Se recalculan cada aplicación de pago
3. **No hay triggers diarios**: Si no hay pago, cuota no transiciona a VENCIDO/MORA

---

## 🚨 PREGUNTAS CRÍTICAS SIN RESPUESTA

### **Nivel CRÍTICO** (sistema no funciona)
1. ❌ **_hoy_local() ¿Dónde está?** → NameError hace crash TODO pago
   - Debería ser `date.today()` o `datetime.now(TZ_NEGOCIO).date()`?
   - Usar timezone "America/Caracas" o UTC?

2. ❌ **Cuota estado VENCIDO/MORA:** ¿Cuándo transiciona?
   - ¿Automáticamente cada día via scheduler?
   - ¿O solo cuando se aplica pago?
   - Si pago stale, cuota nunca se marca MORA?

### **Nivel ALTO** (trazabilidad rota)
3. ⚠️ **usuario_proponente/usuario_autoriza:** ¿Hardcodeados por diseño?
   - Debería ser from current_user en create?
   - Cómo se audita quién propuso?

4. ⚠️ **usuario_registro en pago:** Nunca se popula
   - Quién creó este pago? No se sabe
   - ¿Debería extraerse del JWT token?

5. ⚠️ **pago_id en cuota:** Se sobrescribe
   - ¿Queremos historial de ALL pagos que tocaron cuota?
   - ¿O solo el final es necesario?

6. ⚠️ **Auditoría de transiciones de estado:**
   - Creación: Cliente → No auditado
   - Transiciones Préstamo: Solo aprobar-manual
   - Transiciones Cuota: No auditado
   - ¿Se necesita audit log completo?

### **Nivel MEDIO** (coherencia)
7. ⚠️ **RECHAZADO estado:** ¿Existe o es fantasma?
   - Frontend lo muestra pero backend no lo soporta
   - ¿Se implementa? ¿Se elimina?

8. ⚠️ **Z999999999 múltiples clientes:** ¿Cómo se distinguen?
   - Todos sin cédula usan Z999999999
   - ¿Es intencional tener múltiples duplicados?

9. ⚠️ **Teléfono auto-reemplazado:** ¿Es correcto?
   - Si duplicado → +589999999999
   - Diferente a cedula/email que lanzan 409
   - ¿Intencional o inconsistencia?

10. ⚠️ **conciliado vs verificado_concordancia:** ¿Cuál es fuente de verdad?
    - Se syncan pero ¿cuál es canonical?
    - ¿Deprecar uno?

### **Nivel BAJO** (optimización)
11. ❓ **PAGO_ADELANTADO:** ¿Cuándo se usa?
    - Constraint lo permite, código no lo genera
    - ¿Eliminar o completar?

12. ❓ **fecha_registro hardcodeado en Cliente:** Bug real o intencional?
    - Tiene '2025-10-31' (future date)
    - Debería ser NOW()

13. ❓ **No hay CHECK en modalidad_pago:** ¿Por diseño?
    - MENSUAL|QUINCENAL|SEMANAL pero sin constraint
    - ¿Agregar protección DB?

---

## 🔗 TRAZABILIDAD COMPLETA (EJEMPLO REAL)

```
┌─────────────────────────────────────────────────────────────────────┐
│ CLIENTE: Juan Pérez (cedula V12345678)                              │
│ ├─ fecha_registro: ??? (2025-10-31 hardcodeado ⚠️)                  │
│ ├─ usuario_registro: NULL ⚠️ (quién lo creó?)                       │
│ ├─ estado: ACTIVO ✓                                                  │
│ └─ AUDITORÍA: ❌ No existe entrada                                   │
│                                                                     │
├─ PRÉSTAMO #101 (cliente V12345678)                                  │
│ ├─ fecha_registro: 2026-02-15 ✓                                     │
│ ├─ usuario_proponente: 'itmaster@rapicreditca.com' ⚠️ (hardcoded)   │
│ ├─ estado: DRAFT → EN_REVISION → EVALUADO → DESEMBOLSADO           │
│ ├─ numero_cuotas: 6                                                  │
│ ├─ tasa_interes: 0% ✓                                               │
│ ├─ modalidad_pago: MENSUAL ✓                                        │
│ └─ TRANSICIONES:                                                    │
│    1. DRAFT → EN_REVISION (manual PUT) ⚠️ NO auditado               │
│    2. EN_REVISION → EVALUADO (POST evaluar-riesgo) ⚠️ NO auditado   │
│    3. EVALUADO → DESEMBOLSADO (POST aprobar-manual) ✓ Auditado     │
│                                                                     │
├─ CUOTAS generadas (6 cuotas de 100 c/u)                            │
│ ├─ Cuota #1                                                         │
│ │  ├─ fecha_vencimiento: 2026-03-15 ✓                              │
│ │  ├─ estado: PENDIENTE → VENCIDO → MORA (calculated, not stored)  │
│ │  ├─ dias_mora: PENDING (_hoy_local() ❌ crash)                   │
│ │  └─ AUDITORÍA: ⚠️ Solo creado_en, sin registro de transiciones   │
│ │                                                                   │
│ ├─ Cuota #2 [similar]                                               │
│ └─ ... (Cuotas 3-6)                                                 │
│                                                                     │
├─ PAGO #9001 (2026-03-20, monto 150)                                │
│ ├─ fecha_registro: 2026-03-20 ✓                                     │
│ ├─ usuario_registro: NULL ⚠️ (quién lo creó?)                       │
│ ├─ estado: PENDIENTE → PAGADO ✓ (tras aplicación)                  │
│ ├─ conciliado: FALSE → TRUE (via reconciliacion) ✓                  │
│ ├─ APLICACIÓN FIFO:                                                 │
│ │  ├─ Cuota #1: total_pagado=0 → 100 (completa)                   │
│ │  │ ├─ pago_id = 9001 ✓                                           │
│ │  │ ├─ dias_mora = ??? ❌ (_hoy_local crash)                       │
│ │  │ ├─ estado = PAGADO (assumed si calc funciona) ✓               │
│ │  │ └─ fecha_pago = 2026-03-20 ✓                                  │
│ │  │                                                               │
│ │  └─ Cuota #2: total_pagado=0 → 50 (parcial)                      │
│ │     ├─ pago_id = 9001 ✓ (pero será sobrescrito por pago siguiente)
│ │     ├─ dias_mora = ??? ❌                                         │
│ │     ├─ estado = VENCIDO o MORA? (depends on days, if calc works) │
│ │     └─ fecha_pago = 2026-03-20 ✓                                 │
│ │                                                                  │
│ └─ AUDITORÍA: ⚠️ NO EXISTE entrada de creación ni de estados       │
│                                                                    │
└─ REPORTE (SELECT cuota + pago):                                    │
   ├─ ✓ Datos de cliente (cedula, nombres)                           │
   ├─ ✓ Datos de préstamo (monto, cuotas)                            │
   ├─ ✓ Datos de cuota (número, vencimiento, monto, estado)         │
   ├─ ✓ Datos de pago (monto, fecha, tipo)                           │
   ├─ ⚠️ Pero... trazabilidad INCOMPLETA:                            │
   │  ├─ ❓ Quién creó el cliente?                                    │
   │  ├─ ❓ Quién propuso el préstamo?                                │
   │  ├─ ❓ Quién aprobó transiciones?                                │
   │  ├─ ❓ Cuándo transicionó cuota a MORA?                          │
   │  └─ ❓ Quién creó el pago?                                        │
   │                                                                 │
   └─ FALLO TÉCNICO: ❌ (_hoy_local() makes entire system crash)     │
```

---

## 📊 MATRIZ DE COHERENCIA

| Aspecto | Cliente | Préstamo | Cuota | Pago | Coherencia |
|---------|---------|----------|-------|------|-----------|
| **Validación de IDs** | Partial FK | ✓ FK | ✓ FK | ⚠️ No FK cedula | 🔴 |
| **CHECK constraints** | ❌ None | ✓ Some | ✓ All | ✓ Some | 🟡 |
| **Usuario tracking** | ❌ NULL | ⚠️ Hardcoded | ❌ None | ❌ NULL | 🔴 |
| **Auditoría de cambios** | ❌ None | ⚠️ Partial | ❌ None | ❌ None | 🔴 |
| **Timestamps** | ⚠️ Bug | ✓ | ✓ | ✓ | 🟡 |
| **Transiciones validadas** | N/A | ⚠️ App logic | ⚠️ Bypass | ✓ | 🟡 |
| **Estados normalizados** | ❌ Case sensitive | ✅ Uppercase | ✅ Uppercase | ✅ Uppercase | 🟡 |
| **Documentación clara** | ⚠️ | ⚠️ | ⚠️ | ❌ | 🟡 |

---

## 🎯 PRIORIDADES DE CORRECCIÓN

### **🔴 CRÍTICO (Bloquea trazabilidad)**
1. **[PAGO] Definir _hoy_local()** → Runtime error, todo se cae
2. **[PAGO] Usuario_registro vacío** → No se sabe quién creó pago
3. **[CLIENTE] Usuario_registro vacío** → No se sabe quién creó cliente
4. **[PAGO] FK cedula_cliente → clientes.cedula** → Validación referencial

### **🟠 ALTO (Rompe auditoría)**
5. **[TODOS] Auditoría de transiciones** → Log cambios de estado
6. **[PRÉSTAMO] usuario_proponente from current_user** → Tracking real
7. **[CUOTA] Guardar estado VENCIDO/MORA** → No más cálculos diarios
8. **[PAGO] Historial de pago_id** → Tabla join de pagos→cuotas?

### **🟡 MEDIO (Inconsistencias)**
9. **[CLIENTE] Telefono auto-replace → 409 error** → Coherencia con cedula/email
10. **[CLIENTE] Agregar CHECK estado** → Protección DB
11. **[PRÉSTAMO] RECHAZADO estado** → Definir o eliminar
12. **[CUOTA] PAGO_ADELANTADO** → Completar o eliminar

### **🟢 BAJO (Mejoras)**
13. **[CLIENTE] fecha_registro fix** → Usar NOW() en lugar de hardcoded
14. **[PRÉSTAMO] modalidad_pago CHECK constraint** → Validación DB
15. **[PAGO] conciliado / verificado_concordancia** → Deprecar uno

---

## ✅ RECOMENDACIONES INMEDIATAS

1. **Define _hoy_local() AHORA** antes de más pagos:
   ```python
   from datetime import date
   from zoneinfo import ZoneInfo
   
   def _hoy_local() -> date:
       # Usar timezone del negocio
       return datetime.now(ZoneInfo("America/Caracas")).date()
   ```

2. **Audita todos los CREATE/UPDATE**:
   - Interceptor en FastAPI que log a tabla auditoria
   - O helper en cada endpoint

3. **Valida relaciones**:
   - cedula_cliente → clientes.cedula (FK)
   - usuario_id en pagos/prestamos → usuarios table (FK)

4. **Documenta flujos**:
   - Cada transición de estado con ejemplo real
   - Quién puede disparar cada transición
   - Qué datos se guardan

---

## 📋 CHECKLIST TRAZABILIDAD

- [ ] _hoy_local() definida y funcional
- [ ] Todos los CREATE tienen usuario_registro
- [ ] Todas las transiciones auditadas en tabla auditoria
- [ ] usuario_proponente refleja usuario actual
- [ ] Validaciones de FK completas
- [ ] Estados persistentes (no solo calculados)
- [ ] Documentación de flujo completo
- [ ] Tests de trazabilidad end-to-end

---

**Generado por**: Auditoría Integral Sistema  
**Status**: ⚠️ MÚLTIPLES BRECHAS IDENTIFICADAS - REQUIERE ACCIONES INMEDIATAS
