# 📋 GUÍA: Mantenimiento de Sincronización BD-ORM-Schemas

**Fecha:** 2026-01-11  
**Propósito:** Guía para mantener coherencia entre Base de Datos, Modelos ORM y Schemas Pydantic

---

## 🎯 Objetivo

Esta guía proporciona un proceso claro para mantener la sincronización entre:
- **Base de Datos (PostgreSQL)** - Estructura real
- **Modelos ORM (SQLAlchemy)** - Definición en código Python
- **Schemas Pydantic** - Validación y serialización

---

## 📋 Checklist: Agregar Nuevo Campo

### **Paso 1: Decidir Dónde Agregar**

**¿El campo debe almacenarse en BD?**
- ✅ **SÍ** → Continuar con Paso 2
- ❌ **NO** → Es campo calculado, agregar solo al schema (ver `GUIA_CAMPOS_CALCULADOS.md`)

---

### **Paso 2: Agregar a Base de Datos**

1. ✅ Crear migración Alembic:
   ```bash
   alembic revision -m "agregar_campo_nuevo_a_tabla"
   ```

2. ✅ Definir la columna en la migración:
   ```python
   def upgrade():
       op.add_column('tabla', sa.Column('campo_nuevo', sa.String(100), nullable=True))
   ```

3. ✅ Ejecutar migración:
   ```bash
   alembic upgrade head
   ```

---

### **Paso 3: Agregar a Modelo ORM**

1. ✅ Abrir archivo del modelo: `backend/app/models/[modelo].py`

2. ✅ Agregar columna con tipo correcto:
   ```python
   campo_nuevo = Column(String(100), nullable=True, description="Descripción del campo")
   ```

3. ✅ Verificar:
   - Tipo de dato coincide con BD
   - `nullable` coincide con BD
   - Longitud coincide con BD (para VARCHAR)

---

### **Paso 4: Agregar a Schema Pydantic**

1. ✅ Abrir archivo del schema: `backend/app/schemas/[modelo].py`

2. ✅ Agregar al schema Response:
   ```python
   class ModeloResponse(BaseModel):
       campo_nuevo: Optional[str] = Field(None, max_length=100, description="Descripción")
   ```

3. ✅ Agregar al schema Create/Update si aplica:
   ```python
   class ModeloCreate(BaseModel):
       campo_nuevo: Optional[str] = Field(None, max_length=100)
   ```

---

### **Paso 5: Verificar Sincronización**

1. ✅ Ejecutar script de comparación:
   ```bash
   python scripts/python/comparar_bd_con_orm.py
   ```

2. ✅ Ejecutar auditoría integral:
   ```bash
   python scripts/python/auditoria_integral_coherencia.py
   ```

3. ✅ Verificar que no aparezcan discrepancias nuevas

---

## 🔄 Proceso: Modificar Campo Existente

### **Escenario 1: Cambiar Tipo de Dato**

1. ✅ **BD:** Crear migración Alembic para cambiar tipo
2. ✅ **ORM:** Actualizar tipo en `Column()`
3. ✅ **Schema:** Actualizar tipo en Pydantic
4. ✅ **Verificar:** Ejecutar scripts de auditoría

**Ejemplo:**
```python
# BD: VARCHAR(50) → VARCHAR(100)
# ORM: String(50) → String(100)
# Schema: max_length=50 → max_length=100
```

---

### **Escenario 2: Cambiar Nullable**

1. ✅ **BD:** Crear migración Alembic
2. ✅ **ORM:** Actualizar `nullable=True/False`
3. ✅ **Schema:** Actualizar `Optional` o requerido
4. ✅ **Verificar:** Ejecutar scripts de auditoría

**Ejemplo:**
```python
# BD: nullable=True → nullable=False
# ORM: nullable=True → nullable=False
# Schema: Optional[str] → str
```

---

### **Escenario 3: Cambiar Longitud VARCHAR**

1. ✅ **BD:** Crear migración Alembic
2. ✅ **ORM:** Actualizar `String(longitud)`
3. ✅ **Schema:** Actualizar `max_length`
4. ✅ **Verificar:** Ejecutar scripts de auditoría

---

## 🗑️ Proceso: Eliminar Campo

### **Paso 1: Verificar Uso**

1. ✅ Buscar referencias en código:
   ```bash
   grep -r "campo_a_eliminar" backend/
   grep -r "campo_a_eliminar" frontend/
   ```

2. ✅ Verificar uso en endpoints
3. ✅ Verificar uso en frontend

---

### **Paso 2: Eliminar en Orden Correcto**

1. ✅ **Schema:** Eliminar del schema primero
2. ✅ **ORM:** Eliminar del modelo
3. ✅ **BD:** Crear migración para eliminar columna

**⚠️ IMPORTANTE:** Orden inverso al de creación para evitar errores

---

## 🔍 Proceso: Verificación Periódica

### **Frecuencia Recomendada:**

- ✅ **Después de cada cambio** en estructura de datos
- ✅ **Antes de cada release** a producción
- ✅ **Mensualmente** como mantenimiento preventivo

---

### **Scripts de Verificación:**

1. **Comparar BD vs ORM:**
   ```bash
   python scripts/python/comparar_bd_con_orm.py
   ```
   - Verifica tipos, nullable, longitudes
   - Genera: `DISCREPANCIAS_BD_VS_ORM.md`

2. **Auditoría Integral:**
   ```bash
   python scripts/python/auditoria_integral_coherencia.py
   ```
   - Verifica BD, ORM, Schemas, Frontend
   - Genera: `AUDITORIA_INTEGRAL_COHERENCIA.md`

3. **Sincronización Schemas:**
   ```bash
   python scripts/python/sincronizar_schemas_fase2.py
   ```
   - Identifica campos faltantes en schemas
   - Genera: `SINCRONIZACION_SCHEMAS_FASE2.md`

---

## ⚠️ Problemas Comunes y Soluciones

### **Problema 1: Discrepancias Nullable**

**Síntoma:** Script reporta discrepancias nullable pero están correctas

**Causa:** Limitación del script que no puede parsear `nullable` cuando aparece después de otros parámetros

**Solución:**
- Verificar manualmente el modelo ORM
- Si está correcto, ignorar el reporte (falso positivo)

---

### **Problema 2: Campos Calculados Reportados como Discrepancias**

**Síntoma:** Script reporta campos en schemas que no están en ORM

**Causa:** Campos calculados (comportamiento correcto)

**Solución:**
- Verificar en `GUIA_CAMPOS_CALCULADOS.md`
- Si es campo calculado, está bien (no requiere acción)

---

### **Problema 3: Schema No Compila**

**Síntoma:** Error al importar schema

**Causas comunes:**
- Tipo de dato incorrecto
- Import faltante
- Campo requerido sin valor por defecto

**Solución:**
- Revisar errores de compilación
- Verificar tipos de datos
- Agregar imports necesarios

---

## 📝 Mejores Prácticas

### **✅ HACER:**

1. **Siempre crear migración Alembic** antes de modificar BD
2. **Sincronizar en orden:** BD → ORM → Schema
3. **Verificar después de cada cambio** con scripts de auditoría
4. **Documentar campos calculados** en comentarios
5. **Usar constantes** para longitudes (ej: `CEDULA_LENGTH = 20`)

### **❌ NO HACER:**

1. **No modificar BD directamente** sin migración Alembic
2. **No agregar campos a ORM** sin agregarlos a BD primero
3. **No ignorar discrepancias** sin verificar manualmente
4. **No almacenar campos calculados** en BD (excepto por razones documentadas)
5. **No usar tipos diferentes** entre BD, ORM y Schema

---

## 🔧 Herramientas Disponibles

### **Scripts de Auditoría:**

1. `scripts/python/comparar_bd_con_orm.py`
   - Compara estructura BD con modelos ORM
   - Detecta discrepancias de tipos, nullable, longitudes

2. `scripts/python/auditoria_integral_coherencia.py`
   - Auditoría completa BD-ORM-Schemas-Frontend
   - Identifica todos los tipos de discrepancias

3. `scripts/python/sincronizar_schemas_fase2.py`
   - Identifica campos faltantes en schemas
   - Documenta campos calculados

4. `scripts/python/corregir_nullable_fase1.py`
   - Corrige nullable automáticamente (usar con precaución)

---

## 📚 Referencias

- **Guía de Campos Calculados:** `GUIA_CAMPOS_CALCULADOS.md`
- **Reporte Final FASE 3:** `REPORTE_FINAL_FASE3.md`
- **Informe de Problemas Futuros:** `INFORME_CORRECCION_PROBLEMAS_FUTUROS.md`
- **Documentación Alembic:** https://alembic.sqlalchemy.org/
- **Documentación SQLAlchemy:** https://docs.sqlalchemy.org/
- **Documentación Pydantic:** https://docs.pydantic.dev/

---

## 🎯 Checklist de Mantenimiento Mensual

- [ ] Ejecutar `comparar_bd_con_orm.py`
- [ ] Ejecutar `auditoria_integral_coherencia.py`
- [ ] Revisar discrepancias encontradas
- [ ] Corregir discrepancias críticas
- [ ] Documentar nuevas discrepancias aceptables
- [ ] Actualizar esta guía si es necesario

---

**Última actualización:** 2026-01-11  
**Mantenido por:** Equipo de desarrollo  
**Revisión recomendada:** Mensual
