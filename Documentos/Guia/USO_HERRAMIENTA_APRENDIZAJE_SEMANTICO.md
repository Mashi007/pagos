# 📚 Guía: Herramienta de Aprendizaje Semántico

**Fecha:** 2025-01-XX  
**Sistema:** RAPICREDIT - Chat AI

---

## 🎯 ¿Qué es la Herramienta de Aprendizaje Semántico?

Es una herramienta completa que permite:

1. **Diccionario Semántico**: Agregar palabras y definiciones para que el AI las reconozca
2. **Catálogo de Campos**: Definir todos los campos de la BD con sus descripciones para acceso rápido

---

## 📍 Ubicación

**Interfaz Web:**
```
Configuración → AI → Sistema Híbrido → Diccionario / Campos
```

**URL Directa:**
```
https://rapicredit.onrender.com/configuracion?tab=ai&subtab=diccionario-semantico
https://rapicredit.onrender.com/configuracion?tab=ai&subtab=definiciones-campos
```

---

## 🔤 Diccionario Semántico

### **¿Qué hace?**

Permite agregar palabras comunes con sus definiciones para que el AI las entienda mejor.

### **Ejemplo de Uso:**

**Agregar palabra "cédula":**
```
Palabra: cédula
Definición: Documento de identidad único de cada cliente. Se usa para buscar información del cliente en la base de datos.
Categoría: identificacion
Campo Relacionado: cedula
Tabla Relacionada: clientes
Sinónimos:
  documento
  DNI
  CI
  identificación
Ejemplos de Uso:
  ¿Cuál es el nombre del cliente con cédula V123456789?
  Buscar por documento V123456789
```

**Resultado:** El AI entenderá que cuando el usuario dice "cédula", "documento", "DNI", etc., se refiere al campo `cedula` en la tabla `clientes`.

---

## 📊 Catálogo de Campos

### **¿Qué hace?**

Define todos los campos de la base de datos con sus descripciones, tipos, y características para que el AI acceda rápidamente a la información correcta.

### **Ejemplo de Uso:**

**Agregar definición del campo `cedula`:**
```
Tabla: clientes
Campo: cedula
Definición: Número de cédula de identidad del cliente. Es único y se usa como identificador principal para búsquedas.
Tipo de Dato: VARCHAR
Obligatorio: ✅ Sí
Tiene Índice: ✅ Sí (búsquedas rápidas)
Valores Posibles: (dejar vacío - cualquier cédula válida)
Ejemplos de Valores:
  V123456789
  V987654321
Notas: Formato venezolano (V seguido de números)
```

**Resultado:** El AI sabrá exactamente qué es `cedula`, cómo se usa, y qué valores puede tener.

---

## 🎯 Flujo Completo de Entrenamiento

### **Paso 1: Agregar Palabras al Diccionario**

1. Ve a: **Configuración → AI → Sistema Híbrido → Diccionario**
2. Haz clic en **"+ Agregar Palabra"**
3. Completa el formulario:
   - **Palabra**: El término común (ej: "cédula")
   - **Definición**: Qué significa en el contexto del sistema
   - **Categoría**: Grupo al que pertenece (ej: "identificacion")
   - **Campo Relacionado**: Campo técnico correspondiente (ej: "cedula")
   - **Tabla Relacionada**: Tabla donde está el campo (ej: "clientes")
   - **Sinónimos**: Otras palabras que significan lo mismo
   - **Ejemplos de Uso**: Frases de ejemplo
4. Haz clic en **"Guardar"**

### **Paso 2: Definir Campos de BD**

1. Ve a: **Configuración → AI → Sistema Híbrido → Campos**
2. Haz clic en **"+ Agregar Campo"**
3. Completa el formulario:
   - **Tabla**: Nombre de la tabla (ej: "clientes")
   - **Campo**: Nombre del campo (ej: "cedula")
   - **Definición**: Descripción detallada del campo
   - **Tipo de Dato**: Tipo SQL (ej: "VARCHAR", "INTEGER")
   - **Obligatorio**: Si es NOT NULL
   - **Tiene Índice**: Si está indexado
   - **Clave Foránea**: Si es FK
   - **Valores Posibles**: Lista de valores permitidos (si aplica)
   - **Ejemplos**: Ejemplos de valores
   - **Notas**: Información adicional
4. Haz clic en **"Guardar"**

---

## ✅ Beneficios

### **Para el AI:**
- ✅ Entiende mejor las palabras comunes del usuario
- ✅ Accede rápidamente a información de campos
- ✅ Hace consultas más precisas
- ✅ Reduce errores de interpretación

### **Para los Administradores:**
- ✅ Agrega palabras sin modificar código
- ✅ Define campos una vez, el AI los usa siempre
- ✅ Cambios inmediatos (no requiere reinicio)
- ✅ Historial completo de entrenamiento

---

## 📋 Ejemplos Prácticos

### **Ejemplo 1: Entrenar "Pago"**

**Diccionario Semántico:**
```
Palabra: pago
Definición: Transacción donde un cliente cancela una cuota o parte de ella. Puede referirse a la tabla pagos o al concepto de pagar.
Categoría: transacciones
Campo Relacionado: monto_pagado
Tabla Relacionada: pagos, cuotas
Sinónimos:
  abono
  depósito
  transferencia
  cancelación
Ejemplos:
  ¿Cuántos pagos se hicieron hoy?
  Ver abonos del cliente
```

**Catálogo de Campos:**
```
Tabla: pagos
Campo: monto_pagado
Definición: Monto total pagado en esta transacción. Puede ser el monto completo de una cuota o un abono parcial.
Tipo: NUMERIC(12,2)
Obligatorio: ✅ Sí
Tiene Índice: ❌ No
Valores Posibles: (cualquier monto positivo)
Ejemplos: 500.00, 1250.50, 3000.00
```

---

## 🔍 Búsqueda y Filtros

### **En Diccionario Semántico:**
- **Buscar**: Por palabra o definición
- **Filtrar**: Por categoría
- **Ver**: Todas las palabras agrupadas por categoría

### **En Catálogo de Campos:**
- **Buscar**: Por tabla, campo o definición
- **Filtrar**: Por tabla
- **Ver**: Todos los campos agrupados por tabla

---

## ⚠️ Mejores Prácticas

### **Para Diccionario Semántico:**
- ✅ Agrega palabras que los usuarios usan comúnmente
- ✅ Incluye sinónimos regionales o coloquiales
- ✅ Proporciona ejemplos claros de uso
- ✅ Relaciona con campos técnicos cuando sea posible

### **Para Catálogo de Campos:**
- ✅ Define TODOS los campos importantes
- ✅ Incluye información sobre índices (para búsquedas rápidas)
- ✅ Especifica valores posibles para campos con opciones limitadas
- ✅ Agrega notas sobre restricciones o reglas especiales

---

## 🎯 Resultado Final

Después de entrenar palabras y campos:

**El AI podrá:**
- ✅ Entender cuando el usuario dice "cédula" → usar campo `cedula`
- ✅ Saber que `cedula` está en tabla `clientes`, es VARCHAR, tiene índice
- ✅ Hacer consultas más precisas y rápidas
- ✅ Responder mejor a preguntas del usuario

---

## 📝 Próximos Pasos

1. **Ejecutar migración SQL** para crear las tablas
2. **Agregar palabras comunes** al diccionario
3. **Definir campos principales** en el catálogo
4. **Probar consultas** en el Chat AI
5. **Agregar más palabras** según necesidad

---

**La herramienta está lista para usar. Solo necesitas ejecutar la migración SQL y comenzar a agregar palabras y definiciones.**
