# 🔍 ANÁLISIS: Discrepancias Críticas Identificadas en FASE 3

**Fecha:** 2026-01-11  
**Estado:** ⚠️ **REQUIERE REVISIÓN MANUAL**

---

## 🎯 Discrepancias Críticas Encontradas

**Total:** 4 discrepancias críticas (Severidad ALTA)

**Tipo:** `ORM_SIN_BD` - Columnas en modelo ORM que no existen en Base de Datos

---

## 📋 Detalle de Discrepancias

### **1. prestamos.ml_impago_nivel_riesgo_calculado**

**Estado:** ⚠️ **EN MODELO ORM PERO NO EN BD**

**Definición en ORM:**
```python
ml_impago_nivel_riesgo_calculado = Column(String(20), nullable=True)
```

**Descripción:** Nivel de riesgo calculado por ML (Alto, Medio, Bajo)

**Migración Alembic:** `20251118_add_ml_impago_calculado_prestamos.py` (existe)

**Acción Requerida:**
- ✅ Verificar si la migración se ejecutó correctamente
- ✅ Si no se ejecutó: Ejecutar `alembic upgrade head`
- ✅ Si la migración falló: Revisar errores y corregir

---

### **2. prestamos.ml_impago_probabilidad_calculada**

**Estado:** ⚠️ **EN MODELO ORM PERO NO EN BD**

**Definición en ORM:**
```python
ml_impago_probabilidad_calculada = Column(Numeric(5, 3), nullable=True)
```

**Descripción:** Probabilidad calculada por ML (0.0 a 1.0)

**Migración Alembic:** `20251118_add_ml_impago_calculado_prestamos.py` (existe)

**Acción Requerida:**
- ✅ Verificar si la migración se ejecutó correctamente
- ✅ Si no se ejecutó: Ejecutar `alembic upgrade head`
- ✅ Si la migración falló: Revisar errores y corregir

---

### **3. prestamos.ml_impago_calculado_en**

**Estado:** ⚠️ **EN MODELO ORM PERO NO EN BD**

**Definición en ORM:**
```python
ml_impago_calculado_en = Column(TIMESTAMP, nullable=True)
```

**Descripción:** Fecha de última predicción calculada

**Migración Alembic:** `20251118_add_ml_impago_calculado_prestamos.py` (existe)

**Acción Requerida:**
- ✅ Verificar si la migración se ejecutó correctamente
- ✅ Si no se ejecutó: Ejecutar `alembic upgrade head`
- ✅ Si la migración falló: Revisar errores y corregir

---

### **4. prestamos.ml_impago_modelo_id**

**Estado:** ⚠️ **EN MODELO ORM PERO NO EN BD**

**Definición en ORM:**
```python
ml_impago_modelo_id = Column(Integer, ForeignKey("modelos_impago_cuotas.id"), nullable=True)
```

**Descripción:** ID del modelo ML usado para la predicción

**Migración Alembic:** `20251118_add_ml_impago_calculado_prestamos.py` (existe)

**Acción Requerida:**
- ✅ Verificar si la migración se ejecutó correctamente
- ✅ Si no se ejecutó: Ejecutar `alembic upgrade head`
- ✅ Si la migración falló: Revisar errores y corregir

---

## 🔍 Análisis de la Situación

### **Migración Alembic Existente:**

**Archivo:** `backend/alembic/versions/20251118_add_ml_impago_calculado_prestamos.py`

**Estado:** ✅ Migración existe en el código

**Posibles Causas:**

1. **Migración no ejecutada:**
   - La migración existe pero no se ha ejecutado en la BD
   - Solución: Ejecutar `alembic upgrade head`

2. **Migración ejecutada pero falló:**
   - La migración se intentó ejecutar pero falló
   - Solución: Revisar logs de Alembic y corregir errores

3. **BD diferente a la esperada:**
   - La BD en uso no tiene estas columnas
   - Solución: Verificar qué BD se está usando y ejecutar migración

---

## ✅ Plan de Acción Recomendado

### **Paso 1: Verificar Estado de Migraciones**

```bash
cd backend
alembic current
alembic history
```

**Qué verificar:**
- ¿Cuál es la migración actual aplicada?
- ¿La migración `20251118_add_ml_impago_calculado_prestamos.py` está en el historial?
- ¿Se ha aplicado esta migración?

---

### **Paso 2: Ejecutar Migración (si no está aplicada)**

```bash
cd backend
alembic upgrade head
```

**Qué esperar:**
- Las 4 columnas ML deben agregarse a la tabla `prestamos`
- Verificar mensajes de confirmación

---

### **Paso 3: Verificar en BD**

Ejecutar SQL para verificar:
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'prestamos'
  AND column_name LIKE 'ml_impago%'
ORDER BY column_name;
```

**Resultado esperado:**
- Debe mostrar las 4 columnas ML

---

### **Paso 4: Verificar con Script de Auditoría**

```bash
python scripts/python/comparar_bd_con_orm.py
```

**Resultado esperado:**
- Las 4 discrepancias críticas deben desaparecer

---

## ⚠️ Alternativa: Si las Columnas NO Deben Estar en BD

Si después de revisar se determina que estas columnas **NO deben estar en BD**:

### **Opción A: Remover del Modelo ORM**

1. Comentar o eliminar las 4 columnas del modelo `Prestamo`
2. Actualizar schemas Pydantic si es necesario
3. Documentar la decisión

### **Opción B: Son Campos Calculados**

Si son campos que se calculan pero no se almacenan:

1. Mover a propiedades calculadas en el modelo
2. Mantener solo en schemas Pydantic
3. Documentar como campos calculados

---

## 📊 Impacto de las Discrepancias

### **Impacto Actual:**

1. ⚠️ **Errores potenciales:** Si el código intenta leer/escribir estas columnas
2. ⚠️ **Inconsistencias:** Datos ML no se pueden persistir
3. ⚠️ **Funcionalidad limitada:** Sistema ML de impago no puede guardar resultados

### **Riesgo:**

- **ALTO** si el código intenta usar estas columnas
- **MEDIO** si son columnas nuevas aún no usadas
- **BAJO** si son campos calculados que no se almacenan

---

## 🔍 Verificación de Uso en Código

**Verificar si estas columnas se usan:**

```bash
grep -r "ml_impago_nivel_riesgo_calculado" backend/
grep -r "ml_impago_probabilidad_calculada" backend/
grep -r "ml_impago_calculado_en" backend/
grep -r "ml_impago_modelo_id" backend/
```

**Si se usan:**
- ✅ **Acción:** Ejecutar migración Alembic inmediatamente

**Si NO se usan:**
- ⚠️ **Acción:** Decidir si deben agregarse a BD o removerse del ORM

---

## 📝 Recomendación Final

### **Escenario Más Probable:**

Las columnas **DEBEN estar en BD** porque:
1. ✅ Están definidas en el modelo ORM
2. ✅ Existe migración Alembic para crearlas
3. ✅ Son campos persistentes (no calculados)
4. ✅ Tienen ForeignKey (requieren BD)

### **Acción Recomendada:**

1. ✅ **Ejecutar migración Alembic:**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. ✅ **Verificar en BD:**
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'prestamos'
     AND column_name LIKE 'ml_impago%';
   ```

3. ✅ **Re-ejecutar auditoría:**
   ```bash
   python scripts/python/comparar_bd_con_orm.py
   ```

4. ✅ **Confirmar resolución:**
   - Las 4 discrepancias críticas deben desaparecer

---

## ✅ Checklist de Resolución

- [ ] Verificar estado de migraciones Alembic
- [ ] Ejecutar migración si no está aplicada
- [ ] Verificar columnas en BD con SQL
- [ ] Re-ejecutar script de comparación
- [ ] Confirmar que discrepancias desaparecieron
- [ ] Documentar resolución

---

**Última actualización:** 2026-01-11  
**Estado:** ✅ **RESUELTO** - Migración ejecutada exitosamente  
**Ver:** `RESOLUCION_MIGRACION_ML_IMPAGO.md` para detalles
