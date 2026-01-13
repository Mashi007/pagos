# 📋 MAPEO DE COLUMNAS: EXCEL → prestamos_temporal

## Objetivo
Este documento muestra cómo mapear las columnas de tu archivo Excel a la tabla `prestamos_temporal` para la importación de préstamos.

---

## 📊 ESTRUCTURA DEL ARCHIVO EXCEL

### Columnas obligatorias (deben estar en el Excel)

| # | Nombre en Excel | Tipo | Descripción | Ejemplo |
|---|-----------------|------|-------------|---------|
| 1 | **cedula** | Texto | Cédula del cliente (sin espacios, sin guiones) | `V12345678` |
| 2 | **nombres** | Texto | Nombre completo del cliente | `Juan Pérez` |
| 3 | **total_financiamiento** | Número | Monto total del préstamo | `50000.00` |
| 4 | **fecha_requerimiento** | Fecha | Fecha que necesita el préstamo (YYYY-MM-DD) | `2025-01-15` |
| 5 | **modalidad_pago** | Texto | MENSUAL, QUINCENAL o SEMANAL | `MENSUAL` |
| 6 | **numero_cuotas** | Número entero | Número de cuotas | `12` |
| 7 | **cuota_periodo** | Número | Monto por cuota | `4166.67` |
| 8 | **producto** | Texto | Modelo de vehículo (se usa para mapear modelo_vehiculo_id) | `Toyota Corolla` |
| 9 | **analista** | Texto | Nombre del analista asignado | `María González` |
| 10 | **usuario_proponente** | Email | Email del analista que propone | `maria@empresa.com` |

---

### Columnas opcionales (pueden estar vacías)

| # | Nombre en Excel | Tipo | Descripción | Ejemplo |
|---|-----------------|------|-------------|---------|
| 11 | **valor_activo** | Número | Valor del activo (vehículo) | `60000.00` |
| 12 | **fecha_base_calculo** | Fecha | Fecha base para generar tabla de amortización | `2025-01-15` |
| 14 | **concesionario** | Texto | Nombre del concesionario | `Concesionario ABC` |
| 15 | **estado** | Texto | Estado del préstamo (DRAFT, EN_REVISION, APROBADO, RECHAZADO, FINALIZADO) | `DRAFT` |
| 15 | **usuario_aprobador** | Email | Email del admin que aprueba | `admin@empresa.com` |
| 16 | **usuario_autoriza** | Email | Email del usuario que autoriza | `operaciones@empresa.com` |
| 17 | **observaciones** | Texto | Observaciones del préstamo | `Cliente preferencial` |
| 18 | **fecha_registro** | Fecha/Hora | Fecha de registro (si no se especifica, usa fecha actual) | `2025-01-15 10:30:00` |
| 19 | **fecha_aprobacion** | Fecha/Hora | Fecha cuando se aprueba el préstamo | `2025-01-20 14:00:00` |

---

### Columnas ML (opcionales, para análisis de riesgo)

| # | Nombre en Excel | Tipo | Descripción | Ejemplo |
|---|-----------------|------|-------------|---------|
| 20 | **ml_impago_nivel_riesgo_manual** | Texto | Alto, Medio, Bajo | `Medio` |
| 21 | **ml_impago_probabilidad_manual** | Número | Probabilidad manual (0.0 a 1.0) | `0.35` |

---

## 📝 FORMATO DEL ARCHIVO EXCEL

### Estructura recomendada:

```
| cedula | nombres | total_financiamiento | fecha_requerimiento | modalidad_pago | numero_cuotas | cuota_periodo | producto | analista | usuario_proponente | ... |
|--------|---------|---------------------|---------------------|----------------|---------------|---------------|----------|----------|---------------------|-----|
| V12345678 | Juan Pérez | 50000.00 | 2025-01-15 | MENSUAL | 12 | 4166.67 | Toyota Corolla | María González | maria@empresa.com | ... |
| V87654321 | Ana López | 75000.00 | 2025-01-20 | QUINCENAL | 24 | 3125.00 | Honda Civic | Pedro Martínez | pedro@empresa.com | ... |
```

---

## ✅ VALIDACIONES IMPORTANTES

### 1. Cédula
- ✅ Sin espacios ni guiones
- ✅ Máximo 20 caracteres
- ✅ Ejemplo correcto: `V12345678`
- ❌ Ejemplo incorrecto: `V-12345678` o `V 12345678`

### 2. Modalidad de Pago
- ✅ Valores permitidos: `MENSUAL`, `QUINCENAL`, `SEMANAL`
- ✅ Debe estar en mayúsculas
- ❌ No acepta: `mensual`, `Mensual`, `MENSUAL ` (con espacios)

### 3. Estado
- ✅ Valores permitidos: `DRAFT`, `EN_REVISION`, `APROBADO`, `RECHAZADO`, `FINALIZADO`
- ✅ Si no se especifica, se usa `DRAFT` por defecto

### 4. Fechas
- ✅ Formato: `YYYY-MM-DD` (ejemplo: `2025-01-15`)
- ✅ Para fecha/hora: `YYYY-MM-DD HH:MM:SS` (ejemplo: `2025-01-15 10:30:00`)

### 5. Números
- ✅ Usar punto (.) como separador decimal
- ✅ Ejemplo: `50000.00` o `50000`
- ❌ No usar comas: `50,000.00`

### 6. Tasa de Interés
- ✅ **NO se incluye en el Excel** - Se usa 0.00 por defecto en la tabla final
- ✅ Si necesitas tasa de interés, se asigna después de la importación

### 7. Consistencia de Cálculos
- ✅ Verificar que: `total_financiamiento = cuota_periodo × numero_cuotas`
- ✅ Ejemplo: `50000 = 4166.67 × 12` (con tolerancia de 1 centavo)

---

## 🔄 PROCESO DE IMPORTACIÓN

### Paso 1: Preparar Excel
1. Crear archivo Excel con las columnas indicadas arriba
2. Asegurar que los datos cumplan las validaciones
3. Guardar como CSV (opcional, para facilitar importación)

### Paso 2: Importar a prestamos_temporal
Puedes usar:
- **DBeaver**: Herramienta de importación de datos
- **COPY (PostgreSQL)**: Comando COPY desde CSV
- **INSERT manual**: Insertar fila por fila

### Paso 3: Ejecutar scripts de mapeo
1. `mapear_clientes_prestamos_temporal.sql` - Mapea cliente_id
2. `mapear_catalogos_prestamos_temporal.sql` - Mapea concesionarios, analistas, modelos
3. `validar_prestamos_temporal.sql` - Valida todos los datos
4. `importar_prestamos_temporal_a_final.sql` - Importa a tabla final

---

## 📋 EJEMPLO DE ARCHIVO EXCEL COMPLETO

| cedula | nombres | total_financiamiento | fecha_requerimiento | modalidad_pago | numero_cuotas | cuota_periodo | producto | analista | usuario_proponente | valor_activo | concesionario | estado |
|--------|---------|---------------------|---------------------|----------------|---------------|---------------|----------|----------|---------------------|--------------|---------------|--------|
| V12345678 | Juan Pérez González | 50000.00 | 2025-01-15 | MENSUAL | 12 | 4166.67 | Toyota Corolla | María González | maria@empresa.com | 60000.00 | Concesionario ABC | DRAFT |
| V87654321 | Ana López Martínez | 75000.00 | 2025-01-20 | QUINCENAL | 24 | 3125.00 | Honda Civic | Pedro Martínez | pedro@empresa.com | 90000.00 | Concesionario XYZ | DRAFT |

---

## ⚠️ NOTAS IMPORTANTES

1. **Nombres de columnas**: Deben coincidir exactamente con los nombres de la tabla (case-sensitive en algunos casos)
2. **Campos obligatorios**: No pueden estar vacíos
3. **Cliente debe existir**: La cédula debe existir en la tabla `clientes` con estado `ACTIVO`
4. **Analista obligatorio**: El campo `analista` es obligatorio
5. **producto**: El campo `producto` contiene el modelo de vehículo y se usará para mapear `modelo_vehiculo_id` en los catálogos
6. **Normalización**: Los datos se normalizarán automáticamente (mayúsculas, espacios) durante la importación

---

## 🔍 VERIFICACIÓN POST-IMPORTACIÓN

Después de importar a `prestamos_temporal`, ejecuta:

```sql
-- Verificar total de registros importados
SELECT COUNT(*) as total_importados FROM prestamos_temporal;

-- Verificar registros sin cliente mapeado
SELECT COUNT(*) as sin_cliente 
FROM prestamos_temporal 
WHERE cliente_id_mapeado IS NULL;

-- Verificar estado de validación
SELECT estado_validacion, COUNT(*) 
FROM prestamos_temporal 
GROUP BY estado_validacion;
```

---

**Última actualización:** 2025-01-27
