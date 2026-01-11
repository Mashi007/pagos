# 📋 PLAN DE SOLUCIÓN: Problemas de Estructura y Coherencia

**Fecha:** 2026-01-11  
**Análisis:** `analisis_estructura_coherencia.py`  
**Total de problemas:** 6

---

## 🎯 RESUMEN EJECUTIVO

Este plan aborda los problemas identificados en el análisis de estructura y coherencia de la base de datos, agrupados por prioridad y tipo de solución requerida.

---

## 📊 PROBLEMAS IDENTIFICADOS

### **Prioridad ALTA** 🔴
1. **Falta Foreign Key en `cuotas.prestamo_id`** (Integridad referencial)
2. **Cédulas en préstamos sin cliente activo** (10 casos)
3. **Cédulas en pagos sin cliente activo** (10 casos)

### **Prioridad MEDIA** 🟡
4. **Columnas ML en modelo Prestamo sin BD** (4 columnas)
5. **Columnas en BD sin modelo ORM** (pagos: 21, cuotas: 2)

---

## 🔧 PLAN DE ACCIÓN DETALLADO

### **FASE 1: INTEGRIDAD REFERENCIAL** 🔴

#### **Problema 1.1: Falta Foreign Key en `cuotas.prestamo_id`**

**Impacto:** Riesgo de integridad referencial, posibles cuotas huérfanas

**Solución:**

1. **Verificar estado actual:**
   ```sql
   -- Verificar si hay cuotas con prestamo_id inválido
   SELECT COUNT(*) 
   FROM cuotas c
   LEFT JOIN prestamos p ON c.prestamo_id = p.id
   WHERE p.id IS NULL;
   ```

2. **Crear migración Alembic:**
   ```bash
   alembic revision -m "add_fk_cuotas_prestamo_id"
   ```

3. **Contenido de la migración:**
   ```python
   def upgrade():
       # Verificar que no haya cuotas huérfanas
       op.execute("""
           DELETE FROM cuotas 
           WHERE prestamo_id NOT IN (SELECT id FROM prestamos)
       """)
       
       # Crear Foreign Key
       op.create_foreign_key(
           'fk_cuotas_prestamo_id',
           'cuotas', 'prestamos',
           ['prestamo_id'], ['id'],
           ondelete='CASCADE'
       )
       
       # Crear índice si no existe
       op.create_index(
           'idx_cuotas_prestamo_id',
           'cuotas',
           ['prestamo_id']
       )
   ```

4. **Ejecutar migración:**
   ```bash
   alembic upgrade head
   ```

**Archivos a modificar:**
- `backend/alembic/versions/XXXX_add_fk_cuotas_prestamo_id.py` (nuevo)

**Tiempo estimado:** 30 minutos

---

### **FASE 2: COHERENCIA DE DATOS** 🔴

#### **Problema 2.1: Cédulas en préstamos sin cliente activo (10 casos)**

**Cédulas afectadas:**
- V10011397, V10041764, V10231714, V10337085, V10397607
- V10481633, V10538273, V10629779, V10802712, V10864894

**Solución:**

**Opción A: Activar clientes existentes (Recomendado)**
```sql
-- Verificar si existen clientes inactivos con estas cédulas
SELECT cedula, activo, COUNT(*) 
FROM clientes 
WHERE cedula IN (
    'V10011397', 'V10041764', 'V10231714', 'V10337085', 'V10397607',
    'V10481633', 'V10538273', 'V10629779', 'V10802712', 'V10864894'
)
GROUP BY cedula, activo;

-- Activar clientes si existen
UPDATE clientes 
SET activo = TRUE, 
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula IN (
    'V10011397', 'V10041764', 'V10231714', 'V10337085', 'V10397607',
    'V10481633', 'V10538273', 'V10629779', 'V10802712', 'V10864894'
) AND activo = FALSE;
```

**Opción B: Crear clientes faltantes**
```python
# Script: scripts/crear_clientes_faltantes.py
# Crear clientes básicos para préstamos huérfanos
```

**Opción C: Marcar préstamos como históricos**
```sql
-- Si los préstamos son antiguos y no se pueden vincular
UPDATE prestamos 
SET estado = 'HISTORICO',
    observaciones = observaciones || ' - Cliente no encontrado'
WHERE cedula IN (
    SELECT DISTINCT cedula 
    FROM prestamos p
    LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
    WHERE c.id IS NULL
);
```

**Archivos a crear:**
- `scripts/solucionar_clientes_prestamos.py` (nuevo)

**Tiempo estimado:** 1 hora

---

#### **Problema 2.2: Cédulas en pagos sin cliente activo (10 casos)**

**Cédulas afectadas:**
- V14781713, V15899104, V17301178, V20698426, V24439294, V6681572
- V10011397, V10337085, V12103339, V12122176

**Solución:**

**Similar al Problema 2.1**, pero considerar:

1. **Verificar si son pagos históricos:**
   ```sql
   SELECT cedula, COUNT(*), MIN(fecha_pago), MAX(fecha_pago)
   FROM pagos
   WHERE cedula IN (
       'V14781713', 'V15899104', 'V17301178', 'V20698426', 'V24439294',
       'V6681572', 'V10011397', 'V10337085', 'V12103339', 'V12122176'
   )
   GROUP BY cedula;
   ```

2. **Activar o crear clientes:**
   - Aplicar misma lógica que Problema 2.1

3. **Validar integridad:**
   ```sql
   -- Verificar que todos los pagos tengan cliente activo
   SELECT COUNT(*) 
   FROM pagos p
   LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
   WHERE p.activo = TRUE AND c.id IS NULL;
   ```

**Archivos a crear:**
- `scripts/solucionar_clientes_pagos.py` (nuevo)

**Tiempo estimado:** 1 hora

---

### **FASE 3: SINCRONIZACIÓN MODELO ORM vs BD** 🟡

#### **Problema 3.1: Columnas ML en modelo Prestamo sin BD (4 columnas)**

**Columnas faltantes:**
- `ml_impago_calculado_en`
- `ml_impago_modelo_id`
- `ml_impago_nivel_riesgo_calculado`
- `ml_impago_probabilidad_calculada`

**Solución:**

**Opción A: Eliminar columnas del modelo ORM (Recomendado si no se usan)**
```python
# backend/app/models/prestamo.py
# Comentar o eliminar estas columnas del modelo Prestamo
# ml_impago_calculado_en = Column(DateTime, nullable=True)
# ml_impago_modelo_id = Column(Integer, nullable=True)
# ml_impago_nivel_riesgo_calculado = Column(String(20), nullable=True)
# ml_impago_probabilidad_calculada = Column(Numeric(5, 2), nullable=True)
```

**Opción B: Crear columnas en BD (Si se planea usar ML)**
```python
# Migración Alembic
def upgrade():
    op.add_column('prestamos', 
        sa.Column('ml_impago_calculado_en', sa.DateTime(), nullable=True)
    )
    op.add_column('prestamos',
        sa.Column('ml_impago_modelo_id', sa.Integer(), nullable=True)
    )
    op.add_column('prestamos',
        sa.Column('ml_impago_nivel_riesgo_calculado', sa.String(20), nullable=True)
    )
    op.add_column('prestamos',
        sa.Column('ml_impago_probabilidad_calculada', sa.Numeric(5, 2), nullable=True)
    )
```

**Archivos a modificar:**
- `backend/app/models/prestamo.py`
- `backend/alembic/versions/XXXX_add_ml_columns_prestamos.py` (si Opción B)

**Tiempo estimado:** 30 minutos

---

#### **Problema 3.2: Columnas en BD sin modelo ORM**

**Tabla `pagos` (21 columnas):**
- banco, codigo_pago, comprobante, creado_en, descuento
- dias_mora, documento, fecha_vencimiento, hora_pago, metodo_pago
- monto, monto_capital, monto_cuota_programado, monto_interes
- monto_mora, monto_total, numero_operacion, observaciones
- referencia_pago, tasa_mora, tipo_pago

**Tabla `cuotas` (2 columnas):**
- actualizado_en, creado_en

**Solución:**

**Opción A: Agregar columnas al modelo ORM (Recomendado)**
```python
# backend/app/models/pago.py
# Agregar columnas faltantes al modelo Pago
banco = Column(String(100), nullable=True)
codigo_pago = Column(String(30), nullable=True)
comprobante = Column(String(200), nullable=True)
creado_en = Column(DateTime, nullable=True)
descuento = Column(Numeric(12, 2), nullable=True)
dias_mora = Column(Integer, nullable=True)
documento = Column(String(50), nullable=True)
fecha_vencimiento = Column(Date, nullable=True)
hora_pago = Column(Time, nullable=True)
metodo_pago = Column(String(50), nullable=True)
monto = Column(Numeric(12, 2), nullable=True)
monto_capital = Column(Numeric(12, 2), nullable=True)
monto_cuota_programado = Column(Numeric(12, 2), nullable=True)
monto_interes = Column(Numeric(12, 2), nullable=True)
monto_mora = Column(Numeric(12, 2), nullable=True)
monto_total = Column(Numeric(12, 2), nullable=True)
numero_operacion = Column(String(50), nullable=True)
observaciones = Column(Text, nullable=True)
referencia_pago = Column(String(100), nullable=True)
tasa_mora = Column(Numeric(5, 2), nullable=True)
tipo_pago = Column(String(50), nullable=True)

# backend/app/models/amortizacion.py
# Agregar columnas faltantes al modelo Cuota
creado_en = Column(DateTime, nullable=True)
actualizado_en = Column(DateTime, nullable=True)
```

**Opción B: Documentar como columnas legacy (Si no se usan)**
```python
# Agregar comentarios en el modelo indicando que son columnas legacy
# que existen en BD pero no se usan en el código actual
```

**Archivos a modificar:**
- `backend/app/models/pago.py`
- `backend/app/models/amortizacion.py`

**Tiempo estimado:** 1 hora

---

## 📅 CRONOGRAMA DE EJECUCIÓN

### **Semana 1: Integridad Referencial**
- ✅ Día 1: Crear y ejecutar migración FK `cuotas.prestamo_id`
- ✅ Día 2: Script para resolver clientes faltantes en préstamos
- ✅ Día 3: Script para resolver clientes faltantes en pagos
- ✅ Día 4: Validación y pruebas

### **Semana 2: Sincronización ORM**
- ✅ Día 1: Decidir y aplicar solución para columnas ML
- ✅ Día 2: Agregar columnas faltantes a modelos ORM
- ✅ Día 3: Actualizar serializadores y endpoints si es necesario
- ✅ Día 4: Validación y pruebas

---

## ✅ CHECKLIST DE VALIDACIÓN

### **Después de Fase 1:**
- [ ] Foreign Key `cuotas.prestamo_id` creada y funcionando
- [ ] No hay cuotas huérfanas
- [ ] Índice en `cuotas.prestamo_id` creado

### **Después de Fase 2:**
- [ ] Todas las cédulas en préstamos tienen cliente activo
- [ ] Todas las cédulas en pagos tienen cliente activo
- [ ] Script de validación ejecutado sin errores

### **Después de Fase 3:**
- [ ] Modelos ORM sincronizados con BD
- [ ] No hay columnas en modelo sin BD (excepto las documentadas)
- [ ] No hay columnas críticas en BD sin modelo ORM
- [ ] Endpoints funcionando correctamente

---

## 🔍 SCRIPTS DE VALIDACIÓN

### **Script 1: Validar integridad referencial**
```python
# scripts/validar_integridad_referencial.py
# Verificar todas las Foreign Keys y relaciones
```

### **Script 2: Validar coherencia de cédulas**
```python
# scripts/validar_coherencia_cedulas.py
# Verificar que todas las cédulas tengan cliente activo
```

### **Script 3: Validar sincronización ORM**
```python
# Re-ejecutar analisis_estructura_coherencia.py
# Debe mostrar 0 problemas después de las correcciones
```

---

## 📝 NOTAS IMPORTANTES

1. **Backup antes de cambios:** Siempre hacer backup de la BD antes de ejecutar migraciones
2. **Ambiente de pruebas:** Probar todos los cambios en ambiente de desarrollo primero
3. **Rollback plan:** Tener plan de rollback para cada migración
4. **Documentación:** Actualizar documentación después de cada cambio
5. **Comunicación:** Notificar al equipo sobre cambios en estructura de BD

---

## 🚀 ORDEN DE EJECUCIÓN RECOMENDADO

1. **Primero:** Resolver problemas de integridad referencial (Fase 1)
2. **Segundo:** Corregir coherencia de datos (Fase 2)
3. **Tercero:** Sincronizar modelos ORM (Fase 3)
4. **Finalmente:** Ejecutar análisis completo para validar

---

## 📞 CONTACTO Y SOPORTE

Para dudas o problemas durante la ejecución del plan, consultar:
- Documentación de Alembic: `backend/alembic/README.md`
- Scripts de análisis: `scripts/README.md`
- Modelos ORM: `backend/app/models/`

---

**Última actualización:** 2026-01-11
