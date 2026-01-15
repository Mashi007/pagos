# 📊 Análisis: Mapeo de Palabras Comunes en el Chat AI

**Fecha:** 2025-01-XX  
**Sistema:** RAPICREDIT - Chat AI

---

## ✅ Estado Actual

### **Mapeo Semántico Implementado**

El sistema **SÍ tiene** un mapeo semántico de palabras comunes que se incluye en el system prompt del Chat AI.

**Ubicación:** `backend/app/api/v1/endpoints/configuracion.py`  
**Función:** `_obtener_mapeo_semantico_campos()` (línea ~5352)

---

## 📋 Palabras Comunes Actualmente Mapeadas

### **👤 IDENTIFICACIÓN DE CLIENTES:**
```
✅ cedula, cédula, documento, documento identidad, DNI, CI, identificación
✅ nombres, nombre, nombre completo, cliente, persona, titular
✅ telefono, teléfono, tel, número teléfono, contacto, celular
✅ email, correo, correo electrónico, e-mail, mail
✅ cliente_id, id cliente, identificador cliente, código cliente
```

### **💳 PAGOS Y TRANSACCIONES:**
```
✅ pago, pagos, transacción, abono, depósito, transferencia
✅ numero_documento, número documento, comprobante, referencia, número referencia
✅ activo, activo pago, pago activo, pago válido, pago vigente
```

### **📋 PRÉSTAMOS Y CRÉDITOS:**
```
✅ prestamo_id, id préstamo, préstamo, crédito, loan, préstamo número
✅ estado, estado préstamo, situación, condición, status
```

### **💰 MONTOS Y VALORES:**
```
✅ monto_cuota, cuota, monto de cuota, valor cuota, pago cuota, cuota mensual
✅ monto_pagado, pagado, monto pagado, cantidad pagada, abonado
✅ total_financiamiento, monto préstamo, valor préstamo, monto total, financiamiento
```

---

## ✅ Verificación: ¿Está Funcionando?

### **Inclusión en System Prompt:**

**Sí, el mapeo se incluye** en el system prompt a través de:

```python
# Línea ~7668 en configuracion.py
info_esquema = "\n\n" + _obtener_mapeo_semantico_campos()
info_esquema += "\n\n" + _obtener_inventario_campos_bd(db)
```

Y luego se pasa a `_construir_system_prompt_default()` como parte de `{info_esquema}`.

---

## ⚠️ Posibles Mejoras

### **1. Destacar Más el Mapeo en el Prompt**

**Problema:** El mapeo está incluido pero puede no ser lo suficientemente visible para el AI.

**Solución Sugerida:** Agregar una sección destacada al inicio del system prompt:

```python
⚠️⚠️⚠️ MAPEO SEMÁNTICO - LEE PRIMERO ⚠️⚠️⚠️

El usuario puede usar palabras comunes en lugar de nombres técnicos de campos.
SIEMPRE consulta el "MAPEO SEMÁNTICO DE CAMPOS" más abajo para entender qué campo corresponde.

Ejemplos:
- Usuario dice "cédula" → Campo: cedula
- Usuario dice "nombre" → Campo: nombres
- Usuario dice "pago" → Considera tablas: pagos Y cuotas
- Usuario dice "cuota" → Campo: monto_cuota o tabla: cuotas

SIEMPRE usa inferencia semántica para mapear palabras comunes a campos técnicos.
```

---

### **2. Agregar Más Variaciones Comunes**

**Palabras que podrían agregarse:**

#### **Para "cédula":**
- ✅ Ya incluye: cedula, cédula, documento, documento identidad, DNI, CI, identificación
- ➕ Podría agregar: "ced", "doc", "identidad", "carnet", "pasaporte" (si aplica)

#### **Para "nombre":**
- ✅ Ya incluye: nombres, nombre, nombre completo, cliente, persona, titular
- ➕ Podría agregar: "apellido", "apellidos", "nombre y apellido", "razón social" (si aplica)

#### **Para "pago":**
- ✅ Ya incluye: pago, pagos, transacción, abono, depósito, transferencia
- ➕ Podría agregar: "abonar", "cancelar", "liquidar", "saldar", "pagar"

---

### **3. Instrucciones Más Explícitas**

**Actual:**
```
⚠️ INSTRUCCIONES PARA EL AI:
  1. Si el usuario usa un término que no aparece exactamente en los campos,
     busca en este mapeo para encontrar el campo equivalente
  2. Si estás confundido entre dos campos similares, puedes hacer una pregunta
     aclaratoria como: '¿Te refieres a fecha_vencimiento o fecha_pago?'
  3. Usa inferencia semántica: si preguntan 'cuándo vence', usa fecha_vencimiento
  4. Si preguntan sobre 'pagos', considera tanto la tabla 'pagos' como 'cuotas'
  5. Para términos como 'morosidad', considera campos: dias_morosidad, monto_morosidad, estado='MORA'
  6. Si no estás seguro, pregunta al usuario para aclarar antes de responder
```

**Mejora Sugerida:**
```
⚠️⚠️⚠️ INSTRUCCIONES CRÍTICAS PARA MAPEO SEMÁNTICO ⚠️⚠️⚠️

1. **SIEMPRE consulta el mapeo primero**: Antes de buscar en la BD, verifica si el usuario usó una palabra común.
   Ejemplo: Usuario dice "cédula" → Busca en mapeo → Encuentra que corresponde a campo "cedula" → Usa "cedula" en consulta

2. **Inferencia semántica obligatoria**: 
   - "nombre" → Campo: nombres
   - "pago" → Tablas: pagos Y cuotas (ambas)
   - "cuota" → Tabla: cuotas, Campo: monto_cuota
   - "cliente" → Tabla: clientes, Campo: nombres

3. **Múltiples interpretaciones**: Si un término puede referirse a varios campos, considera TODOS:
   - "pago" puede ser: tabla pagos, tabla cuotas, campo monto_pagado, campo fecha_pago
   - Busca en TODAS las opciones antes de responder

4. **Preguntas aclaratorias solo si es necesario**: 
   - Primero intenta inferir del contexto
   - Solo pregunta si hay ambigüedad real entre campos muy diferentes

5. **Ejemplos comunes que DEBES reconocer**:
   - "¿Cuál es el nombre del cliente con cédula V123456789?" → Busca en tabla clientes, campo cedula='V123456789', retorna campo nombres
   - "¿Cuántos pagos hay?" → Cuenta en tabla pagos (activos)
   - "¿Cuánto debe el cliente?" → Busca cuotas pendientes o en mora
   - "¿Tiene préstamos?" → Busca en tabla prestamos por cliente_id o cedula
```

---

## 🎯 Recomendaciones de Mejora

### **Prioridad Alta:**

1. **Destacar el mapeo al inicio del prompt** con una sección visible
2. **Agregar ejemplos concretos** de cómo mapear palabras comunes
3. **Reforzar instrucciones** sobre inferencia semántica

### **Prioridad Media:**

4. **Agregar más variaciones** de palabras comunes (sinónimos adicionales)
5. **Incluir ejemplos de consultas** que usen palabras comunes

### **Prioridad Baja:**

6. **Crear un diccionario expandido** con más términos coloquiales
7. **Agregar mapeo contextual** (ej: "debe" → cuotas pendientes)

---

## ✅ Conclusión

**Estado Actual:** ✅ **El sistema SÍ tiene mapeo de palabras comunes**

**Funcionalidad:**
- ✅ Mapeo semántico implementado
- ✅ Se incluye en el system prompt
- ✅ Cubre palabras comunes: cédula, nombre, pago, etc.

**Mejoras Sugeridas:**
- ⚠️ Destacar más el mapeo en el prompt
- ⚠️ Agregar instrucciones más explícitas
- ⚠️ Incluir más variaciones de palabras comunes

**El sistema debería entender palabras comunes, pero podría mejorarse la visibilidad y claridad de las instrucciones.**

---

## 📝 Próximos Pasos

1. **Verificar en producción** si el AI está usando correctamente el mapeo
2. **Implementar mejoras sugeridas** si hay problemas de comprensión
3. **Agregar más sinónimos** según feedback de usuarios
4. **Monitorear consultas** para identificar palabras comunes no mapeadas
