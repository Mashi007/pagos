# RESUMEN: CORRECCIÓN DE INCONSISTENCIAS EN CUOTAS

## Fecha: 2025-01-XX
## Base de datos: Sistema de cobranzas y gestión de créditos

---

## 🔍 PROBLEMAS DETECTADOS

### 1. Préstamos con Cuotas de Más (15 préstamos)
- **Causa:** Regeneraciones múltiples de la tabla de amortización
- **Patrón:** Multiplicadores de 2x, 3x, 4x las cuotas planificadas
- **Impacto:** Cuotas duplicadas con mismo `numero_cuota`
- **Estado:** Ninguno tiene pagos registrados (fácil de corregir)

### 2. Préstamos con Cuotas Faltantes (80 préstamos)
- **Causa:** Generación incompleta de cuotas
- **Patrón:** Exactamente 50% de cuotas generadas (18→9, 36→18, 12→6)
- **Impacto:** Préstamos incompletos, cálculos incorrectos
- **Estado:** Ninguno tiene pagos registrados (fácil de corregir)

---

## ✅ SOLUCIONES IMPLEMENTADAS

### Script 1: `corregir_cuotas_duplicadas.sql`
**Objetivo:** Eliminar cuotas extra manteniendo solo las primeras `numero_cuotas`

**Estrategia:**
- Mantener las primeras N cuotas (ordenadas por `numero_cuota`, `fecha_vencimiento`, `id`)
- Eliminar las cuotas con IDs más altos
- Solo eliminar cuotas sin pagos (`total_pagado = 0`)

**Uso:**
```sql
-- 1. Hacer backup primero
CREATE TABLE cuotas_backup_YYYYMMDD AS SELECT * FROM cuotas;

-- 2. Ejecutar script
\i scripts/sql/corregir_cuotas_duplicadas.sql
```

### Script 2: `corregir_cuotas_faltantes.sql`
**Objetivo:** Identificar préstamos con cuotas faltantes

**Nota:** Este script solo identifica. La regeneración se hace con Python.

### Script 3: `corregir_inconsistencias_cuotas.py`
**Objetivo:** Corrección automatizada completa

**Funcionalidades:**
1. **Elimina cuotas duplicadas/extra:**
   - Verifica si hay pagos en cuotas extra
   - Elimina solo cuotas sin pagos
   - Mantiene las primeras `numero_cuotas` cuotas

2. **Completa cuotas faltantes:**
   - Identifica préstamos con cuotas faltantes
   - Verifica que tengan `fecha_base_calculo`
   - Regenera tabla de amortización completa
   - Usa el servicio `generar_tabla_amortizacion()`

**Uso:**
```bash
python scripts/python/corregir_inconsistencias_cuotas.py
```

---

## 📊 ESTADÍSTICAS

### Antes de la Corrección:
- **Préstamos con cuotas extra:** 15
- **Total cuotas extra:** ~300-400 cuotas
- **Préstamos con cuotas faltantes:** 80
- **Total cuotas faltantes:** ~600-800 cuotas

### Después de la Corrección:
- **Préstamos con cuotas extra:** 0 (si no hay pagos)
- **Préstamos con cuotas faltantes:** 0 (si tienen fecha_base_calculo)

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### 1. Backup Obligatorio
**SIEMPRE hacer backup antes de ejecutar correcciones:**
```sql
CREATE TABLE cuotas_backup_YYYYMMDD AS SELECT * FROM cuotas;
```

### 2. Cuotas con Pagos
- Las cuotas extra **con pagos** NO se eliminan automáticamente
- Requieren revisión manual
- Puede ser necesario migrar pagos antes de eliminar

### 3. Préstamos sin fecha_base_calculo
- Los préstamos sin `fecha_base_calculo` NO pueden regenerar cuotas
- Necesitan asignar fecha primero
- Verificar en el script `corregir_cuotas_faltantes.sql`

### 4. Regeneración Completa
- Al regenerar cuotas faltantes, se **eliminan todas las cuotas existentes**
- Luego se generan todas las cuotas desde cero
- Esto es seguro si no hay pagos registrados

---

## 🔄 FLUJO DE CORRECCIÓN RECOMENDADO

### Paso 1: Verificación
```bash
python scripts/python/investigar_inconsistencias_cuotas.py
```

### Paso 2: Backup
```sql
CREATE TABLE cuotas_backup_202501XX AS SELECT * FROM cuotas;
```

### Paso 3: Corrección Automatizada
```bash
python scripts/python/corregir_inconsistencias_cuotas.py
```

### Paso 4: Verificación Final
```bash
python scripts/python/verificar_prestamos_con_amortizacion.py
```

---

## 📝 NOTAS TÉCNICAS

### Orden de Eliminación de Cuotas Extra
Las cuotas se ordenan por:
1. `numero_cuota` (ascendente)
2. `fecha_vencimiento` (ascendente)
3. `id` (ascendente)

Se mantienen las primeras N cuotas según este orden.

### Regeneración de Cuotas Faltantes
- Usa el servicio `generar_tabla_amortizacion()` del backend
- Este servicio elimina cuotas existentes antes de generar
- Genera todas las cuotas desde la `fecha_base_calculo`
- Calcula método Francés (cuota fija)

---

## 🎯 RESULTADO ESPERADO

Después de la corrección:
- ✅ Todos los préstamos tienen exactamente `numero_cuotas` cuotas
- ✅ No hay cuotas duplicadas (mismo `numero_cuota`)
- ✅ No hay cuotas faltantes
- ✅ Las cuotas están correctamente ordenadas y calculadas

---

**Última actualización:** 2025-01-XX
