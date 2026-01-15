# 🔍 Cómo Funciona el Mapeo de Palabras Comunes

**Fecha:** 2025-01-XX  
**Sistema:** RAPICREDIT - Chat AI

---

## ✅ Respuesta Corta: SÍ, el Sistema Entiende Palabras Comunes

**El sistema SÍ está configurado** para entender cuando usas palabras comunes como "cédula", "pago", "nombre", etc., y mapearlas automáticamente a los campos técnicos de la base de datos.

---

## 🎯 Cómo Funciona Actualmente

### **Proceso de Mapeo:**

```
Usuario pregunta: "¿Cuál es el nombre del cliente con cédula V123456789?"
    ↓
System Prompt incluye: "MAPEO SEMÁNTICO DE CAMPOS"
    ↓
AI lee el mapeo y encuentra:
  • cedula, cédula, documento, DNI, CI, identificación
  • nombres, nombre, nombre completo, cliente
    ↓
AI entiende:
  - "cédula" → Campo técnico: cedula
  - "nombre" → Campo técnico: nombres
    ↓
AI busca en BD:
  SELECT nombres FROM clientes WHERE cedula = 'V123456789'
    ↓
AI responde con el nombre encontrado
```

---

## 📋 Palabras que el Sistema Entiende Actualmente

### **Ejemplos de Mapeo Funcional:**

| Palabra Común | Campo Técnico | Tabla |
|---------------|---------------|-------|
| **cédula** | `cedula` | clientes, prestamos, pagos |
| **nombre** | `nombres` | clientes |
| **pago** | `pagos` (tabla) o `monto_pagado` (campo) | pagos, cuotas |
| **cuota** | `monto_cuota` o tabla `cuotas` | cuotas |
| **cliente** | Tabla `clientes` | clientes |
| **préstamo** | Tabla `prestamos` | prestamos |
| **documento** | `cedula` | clientes, prestamos, pagos |
| **DNI** | `cedula` | clientes, prestamos, pagos |
| **teléfono** | `telefono` | clientes |
| **correo** | `email` | clientes |

---

## 🔧 Instrucciones que Recibe el AI

El system prompt incluye estas instrucciones explícitas:

```
⚠️⚠️⚠️ INSTRUCCIONES CRÍTICAS PARA MAPEO SEMÁNTICO ⚠️⚠️⚠️

1. **SIEMPRE consulta este mapeo primero**: Antes de buscar en la BD, verifica si el usuario usó una palabra común.
   Ejemplo: Usuario dice 'cédula' → Busca en mapeo → Encuentra que corresponde a campo 'cedula' → Usa 'cedula' en consulta

2. **Inferencia semántica obligatoria**:
   - 'nombre' → Campo: nombres
   - 'pago' → Tablas: pagos Y cuotas (ambas)
   - 'cuota' → Tabla: cuotas, Campo: monto_cuota
   - 'cliente' → Tabla: clientes, Campo: nombres
   - 'cédula' → Campo: cedula (en cualquier tabla)

3. **Múltiples interpretaciones**: Si un término puede referirse a varios campos, considera TODOS:
   - 'pago' puede ser: tabla pagos, tabla cuotas, campo monto_pagado, campo fecha_pago
   - Busca en TODAS las opciones antes de responder

4. **Ejemplos comunes que DEBES reconocer**:
   - '¿Cuál es el nombre del cliente con cédula V123456789?' → Busca en tabla clientes, campo cedula='V123456789', retorna campo nombres
   - '¿Cuántos pagos hay?' → Cuenta en tabla pagos (activos)
   - '¿Cuánto debe el cliente?' → Busca cuotas pendientes o en mora
   - '¿Tiene préstamos?' → Busca en tabla prestamos por cliente_id o cedula
```

---

## ✅ Ejemplos de Consultas que Funcionan

### **Ejemplo 1: Búsqueda por Cédula**
```
Usuario: "¿Cuál es el nombre del cliente con cédula V123456789?"

Sistema entiende:
- "cédula" → Campo: cedula
- "nombre" → Campo: nombres

Consulta ejecutada:
SELECT nombres FROM clientes WHERE cedula = 'V123456789'

Respuesta: "El cliente con cédula V123456789 se llama [NOMBRE]"
```

### **Ejemplo 2: Consulta de Pagos**
```
Usuario: "¿Cuántos pagos hay?"

Sistema entiende:
- "pago" → Tabla: pagos (y también considera cuotas)

Consulta ejecutada:
SELECT COUNT(*) FROM pagos WHERE activo = true

Respuesta: "Hay X pagos activos en el sistema"
```

### **Ejemplo 3: Consulta de Préstamos**
```
Usuario: "¿Tiene préstamos el cliente con documento V123456789?"

Sistema entiende:
- "documento" → Campo: cedula
- "préstamos" → Tabla: prestamos
- "cliente" → Tabla: clientes

Consulta ejecutada:
SELECT COUNT(*) FROM prestamos WHERE cedula = 'V123456789'

Respuesta: "El cliente con cédula V123456789 tiene X préstamos"
```

---

## ⚠️ Limitación Actual

**El mapeo está hardcodeado** en el código. Esto significa:

✅ **Funciona bien** para palabras ya mapeadas (cédula, nombre, pago, etc.)

❌ **NO puedes agregar nuevas palabras** fácilmente:
- Requiere modificar código Python
- Requiere deploy del backend
- Requiere reiniciar servidor

---

## 🎯 Conclusión

**¿El sistema entiende palabras comunes?** ✅ **SÍ**

**¿Funciona automáticamente?** ✅ **SÍ**, el AI recibe instrucciones explícitas para mapear palabras comunes

**¿Puedes agregar nuevas palabras fácilmente?** ❌ **NO**, requiere modificar código

**Palabras que SÍ entiende actualmente:**
- ✅ cédula, documento, DNI, CI → campo `cedula`
- ✅ nombre, nombres → campo `nombres`
- ✅ pago, pagos → tabla `pagos` o campo `monto_pagado`
- ✅ cuota, cuotas → tabla `cuotas` o campo `monto_cuota`
- ✅ cliente, clientes → tabla `clientes`
- ✅ préstamo, préstamos → tabla `prestamos`

---

## 💡 Si Necesitas Agregar Más Palabras

**Opción 1: Modificar código** (actual)
- Editar `_obtener_mapeo_semantico_campos()` en `configuracion.py`
- Hacer deploy

**Opción 2: Crear herramienta** (propuesta)
- Interfaz web para agregar sinónimos
- Cambios inmediatos sin deploy
- Ver documento: `HERRAMIENTA_ENTRENAMIENTO_PALABRAS.md`

---

**El sistema está diseñado para entender palabras comunes, pero el mapeo actual es estático y requiere código para expandirse.**
