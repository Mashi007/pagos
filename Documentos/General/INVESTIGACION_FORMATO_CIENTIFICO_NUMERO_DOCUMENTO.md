# 🔍 INVESTIGACIÓN: FORMATO CIENTÍFICO EN NUMERO_DOCUMENTO

**Fecha:** 2026-01-11  
**Estado:** Investigación completa - Resolución manual planificada

---

## 📊 RESUMEN EJECUTIVO

### Problema Identificado
- **3,092 pagos** afectados con formato científico en `numero_documento`
- **Monto total afectado:** $309,511.50
- **Documentos únicos afectados:** ~17 números diferentes
- **Préstamos afectados:** ~1,054 préstamos

### Formato Detectado
Los números aparecen en formato científico como:
- `7.40087E+14` (mayúscula, positivo)
- `1.23e+5` (minúscula, positivo)
- `7.40087E-14` (mayúscula, negativo - menos común)
- `1.23e-5` (minúscula, negativo - menos común)

---

## 🔍 ANÁLISIS DEL PROBLEMA

### Causa Raíz
El formato científico ocurre cuando:
1. **Excel/Pandas** convierte automáticamente números largos (>15 dígitos) a notación científica
2. Los números se importan **sin formato de texto** desde archivos Excel
3. Pandas lee los valores como `float` en lugar de `string`, perdiendo precisión

### Impacto

#### 1. Pérdida de Precisión
- Los números en formato científico **pierden dígitos significativos**
- Ejemplo: `7.40087E+14` podría representar cualquier número entre `740087000000000` y `740087999999999`
- **No se puede recuperar** la precisión original

#### 2. Duplicados Potenciales
- Múltiples números diferentes pueden aparecer como el mismo número científico
- Ejemplo: `740087123456789` y `740087987654321` ambos aparecen como `7.40087E+14`
- Esto causa problemas en la reconciliación de pagos

#### 3. Problemas de Integridad
- Imposible verificar si un número de documento ya existe
- Dificulta la detección de pagos duplicados
- Afecta la reconciliación automática

---

## ✅ SOLUCIONES IMPLEMENTADAS

### 1. Prevención en Importaciones (Backend)
**Archivos modificados:**
- `backend/app/api/v1/endpoints/pagos_upload.py`
- `backend/app/api/v1/endpoints/pagos_conciliacion.py`

**Funcionalidad:**
- Normalización automática durante la importación de Excel
- Conversión de formato científico a número completo antes de guardar
- Función `_normalizar_numero_documento()` aplicada automáticamente

### 2. Normalización en Edición (Backend)
**Archivo:** `backend/app/api/v1/endpoints/pagos.py`

**Funcionalidad:**
- Endpoint `PUT /api/v1/pagos/{pago_id}` normaliza automáticamente
- Función `_normalizar_numero_documento()` aplicada en actualizaciones

### 3. Interfaz de Edición Manual (Frontend)
**Archivos:**
- `frontend/src/components/reportes/TablaAmortizacionCompleta.tsx`
- `frontend/src/components/common/AdvertenciaFormatoCientifico.tsx`

**Funcionalidad:**
- Badge visual "Formato científico" en pagos afectados
- Campo de edición con normalización automática
- Advertencia visible para usuarios
- Permite corrección manual uno por uno

### 4. Script de Corrección Masiva (Preparado)
**Archivo:** `scripts/python/corregir_formato_cientifico_masivo.py`

**Características:**
- Identifica todos los pagos con formato científico
- Normaliza cada número
- Verifica duplicados antes de actualizar
- Procesa por lotes (100 pagos por lote)
- Modo dry-run para verificar antes de ejecutar
- Genera reportes detallados

**⚠️ ADVERTENCIA:**
- **Pérdida de datos:** No se puede recuperar la precisión perdida
- **Duplicados:** Pueden aparecer números duplicados después de normalizar
- **Requiere revisión manual** de casos conflictivos

---

## 📋 PLAN DE RESOLUCIÓN MANUAL

### Estrategia Recomendada

#### Fase 1: Identificación y Análisis
1. Ejecutar script SQL de investigación: `scripts/sql/investigar_formato_cientifico_numero_documento.sql`
2. Revisar reportes generados:
   - Resumen general
   - Top números más frecuentes
   - Duplicados potenciales
   - Conflictos con números existentes

#### Fase 2: Corrección Manual Priorizada
1. **Prioridad Alta:** Números con más pagos asociados
2. **Prioridad Media:** Números con montos altos
3. **Prioridad Baja:** Casos aislados

#### Fase 3: Proceso de Corrección
1. Acceder a `/reportes` en el frontend
2. Buscar pagos con badge "Formato científico"
3. Editar cada pago:
   - Verificar número de documento original (si está disponible en otra fuente)
   - Corregir manualmente con el número completo correcto
   - Guardar (normalización automática aplicada)

#### Fase 4: Validación
1. Ejecutar script SQL de investigación nuevamente
2. Verificar reducción de casos
3. Revisar duplicados generados
4. Corregir conflictos manualmente

---

## 🔧 HERRAMIENTAS DISPONIBLES

### Script SQL de Investigación
**Archivo:** `scripts/sql/investigar_formato_cientifico_numero_documento.sql`

**Reportes generados:**
1. Resumen general (totales y montos)
2. Distribución por tipo de formato
3. Top 20 números más frecuentes
4. Duplicados potenciales después de normalización
5. Conflictos con números ya existentes
6. Distribución por estado de conciliación
7. Distribución temporal (por mes)
8. Muestra de registros afectados
9. Impacto en préstamos
10. Comparación con números normalizados existentes

### Script Python de Corrección Masiva
**Archivo:** `scripts/python/corregir_formato_cientifico_masivo.py`

**Uso:**
```bash
# Modo dry-run (ver qué haría sin cambios)
python scripts/python/corregir_formato_cientifico_masivo.py

# Ejecutar corrección real
python scripts/python/corregir_formato_cientifico_masivo.py --execute

# Limitar cantidad de pagos a procesar (para pruebas)
python scripts/python/corregir_formato_cientifico_masivo.py --limit 100
```

**⚠️ NOTA:** Este script está disponible pero **NO se recomienda ejecutar** sin revisión manual previa debido a la pérdida de precisión.

---

## 📊 ESTADÍSTICAS ESPERADAS

### Distribución Estimada
- **Número más común:** `7.40087E+14` (~2,845 pagos)
- **Otros números:** Varios con menor frecuencia
- **Total documentos únicos:** ~17 números diferentes

### Impacto en Duplicados
- Después de normalizar, algunos números científicos diferentes pueden convertirse en el mismo número
- Requiere revisión manual para identificar y resolver conflictos

---

## ⚠️ RIESGOS Y CONSIDERACIONES

### Riesgos de Corrección Automática
1. **Pérdida de precisión:** No se puede recuperar los dígitos perdidos
2. **Duplicados falsos:** Números diferentes pueden normalizarse al mismo valor
3. **Conflictos:** Números normalizados pueden coincidir con números ya existentes

### Ventajas de Corrección Manual
1. **Precisión:** Puede verificar número correcto desde fuente original
2. **Control:** Revisa cada caso antes de corregir
3. **Trazabilidad:** Registra cambios con auditoría
4. **Menos errores:** Evita crear duplicados incorrectos

---

## 📝 RECOMENDACIONES

### Corto Plazo
1. ✅ **Usar interfaz manual** en `/reportes` para corregir casos prioritarios
2. ✅ **Ejecutar script SQL** de investigación para identificar casos críticos
3. ✅ **Priorizar corrección** de números con más pagos asociados

### Mediano Plazo
1. ✅ **Mantener prevención** activa en importaciones
2. ✅ **Monitorear** nuevos casos de formato científico
3. ✅ **Documentar** casos resueltos manualmente

### Largo Plazo
1. ⚠️ **Considerar corrección masiva** solo después de revisar todos los casos manualmente
2. ⚠️ **Implementar validación estricta** que rechace importaciones con formato científico
3. ⚠️ **Mejorar detección** de duplicados considerando formato científico

---

## 🔗 ARCHIVOS RELACIONADOS

### Scripts
- `scripts/sql/investigar_formato_cientifico_numero_documento.sql` - Investigación SQL
- `scripts/python/corregir_formato_cientifico_masivo.py` - Corrección masiva (no recomendado)

### Backend
- `backend/app/api/v1/endpoints/pagos.py` - Normalización en edición
- `backend/app/api/v1/endpoints/pagos_upload.py` - Prevención en importación
- `backend/app/api/v1/endpoints/pagos_conciliacion.py` - Prevención en conciliación

### Frontend
- `frontend/src/components/reportes/TablaAmortizacionCompleta.tsx` - Interfaz de edición
- `frontend/src/components/common/AdvertenciaFormatoCientifico.tsx` - Componente de advertencia

---

## 📈 PROGRESO ESPERADO

### Métricas de Éxito
- Reducción gradual de casos con formato científico
- Aumento de números de documento correctos
- Disminución de duplicados relacionados con formato científico
- Mejora en precisión de reconciliación

### Tiempo Estimado
- **Corrección manual:** Variable según cantidad de casos prioritarios
- **Recomendado:** Corregir casos críticos primero, luego casos restantes gradualmente

---

**Última actualización:** 2026-01-11  
**Estado:** Investigación completa - Resolución manual en progreso
