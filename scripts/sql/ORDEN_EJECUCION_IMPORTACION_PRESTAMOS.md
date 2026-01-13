# 📋 ORDEN DE EJECUCIÓN: IMPORTACIÓN DE PRÉSTAMOS

## Objetivo
Importar préstamos desde otra base de datos a la tabla `prestamos` de forma segura y validada.

---

## 🔄 PROCESO PASO A PASO

### **PASO 1: Crear Tabla Temporal**
```sql
-- Ejecutar: crear_tabla_temporal_prestamos.sql
```
**Objetivo:** Crear la tabla `prestamos_temporal` con la misma estructura que `prestamos` más campos adicionales para validación.

**Resultado esperado:** Tabla `prestamos_temporal` creada con todos los campos necesarios.

---

### **PASO 2: Importar Datos a Tabla Temporal**
```sql
-- Importar datos desde tu fuente externa (Excel, CSV, otra BD, etc.)
-- Ejemplo usando COPY (PostgreSQL):
COPY prestamos_temporal (
    cedula, nombres, total_financiamiento, fecha_requerimiento,
    modalidad_pago, numero_cuotas, cuota_periodo,
    producto, concesionario, analista,
    estado, usuario_proponente, fecha_registro
)
FROM '/ruta/al/archivo.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');
```

**Nota:** Ajusta los campos según tu fuente de datos. Los campos adicionales de mapeo se llenarán en los siguientes pasos.

---

### **PASO 3: Mapear Clientes**
```sql
-- Ejecutar: mapear_clientes_prestamos_temporal.sql
```
**Objetivo:** Mapear `cliente_id_mapeado` basándose en la cédula del cliente.

**Resultado esperado:** 
- `cliente_id_mapeado` poblado para préstamos con cliente existente
- `estado_validacion` actualizado a 'VALIDADO' o 'ERROR'
- `errores_validacion` con mensajes si el cliente no existe

---

### **PASO 4: Mapear Catálogos**
```sql
-- Ejecutar: mapear_catalogos_prestamos_temporal.sql
```
**Objetivo:** Mapear IDs de catálogos (concesionarios, analistas, modelos_vehiculos) basándose en nombres.

**Resultado esperado:**
- `concesionario_id_mapeado` poblado
- `analista_id_mapeado` poblado
- `modelo_vehiculo_id_mapeado` poblado (mapeado desde el campo `producto`) (mapeado desde `producto`)

---

### **PASO 5: Validar Datos**
```sql
-- Ejecutar: validar_prestamos_temporal.sql
```
**Objetivo:** Validar todos los datos antes de importar a la tabla final.

**Validaciones realizadas:**
- ✅ Cliente existe
- ✅ Campos obligatorios presentes
- ✅ Modalidad de pago válida (MENSUAL, QUINCENAL, SEMANAL)
- ✅ Estado válido
- ✅ Tasa de interés válida (0-100)
- ✅ Fechas válidas
- ✅ Consistencia de cálculos (total_financiamiento = cuota_periodo * numero_cuotas)

**Resultado esperado:**
- `estado_validacion` = 'VALIDADO' para préstamos correctos
- `estado_validacion` = 'ERROR' para préstamos con problemas
- `errores_validacion` con detalles de los errores

---

### **PASO 6: Revisar Errores (OPCIONAL)**
```sql
-- Consultar préstamos con errores
SELECT 
    id,
    cedula,
    nombres,
    estado_validacion,
    errores_validacion
FROM prestamos_temporal
WHERE estado_validacion = 'ERROR'
ORDER BY id;
```

**Acciones posibles:**
- Corregir datos en la fuente y reimportar
- Corregir manualmente en la tabla temporal
- Crear clientes faltantes si es necesario
- Agregar catálogos faltantes si es necesario

---

### **PASO 7: Importar a Tabla Final**
```sql
-- Ejecutar: importar_prestamos_temporal_a_final.sql
```
**Objetivo:** Importar solo los préstamos validados a la tabla `prestamos`.

**Resultado esperado:**
- Préstamos validados insertados en `prestamos`
- `estado_validacion` actualizado a 'IMPORTADO' en temporal

---

### **PASO 8: Verificar Importación**
```sql
-- Verificar totales
SELECT 
    'Temporal validados' as origen,
    COUNT(*) as total
FROM prestamos_temporal
WHERE estado_validacion = 'VALIDADO'
UNION ALL
SELECT 
    'Final' as origen,
    COUNT(*) as total
FROM prestamos;

-- Ver últimos préstamos importados
SELECT 
    id,
    cedula,
    nombres,
    total_financiamiento,
    estado,
    fecha_registro
FROM prestamos
ORDER BY id DESC
LIMIT 10;
```

---

### **PASO 9: Limpiar Tabla Temporal (OPCIONAL)**
```sql
-- Si todo está correcto, puedes eliminar la tabla temporal
DROP TABLE IF EXISTS prestamos_temporal CASCADE;
```

**⚠️ IMPORTANTE:** Solo elimina la tabla temporal después de verificar que la importación fue exitosa.

---

## 📊 ESTRUCTURA DE LA TABLA TEMPORAL

La tabla `prestamos_temporal` incluye:
- ✅ Todos los campos de `prestamos`
- ✅ Campos adicionales para mapeo (`*_mapeado`)
- ✅ Campos de validación (`estado_validacion`, `errores_validacion`)
- ✅ Campo `cedula_original` para mantener referencia a la fuente

---

## ⚠️ CONSIDERACIONES IMPORTANTES

1. **Cliente debe existir:** Todos los préstamos deben tener un cliente válido en la tabla `clientes`.
2. **Analista obligatorio:** El campo `analista` es obligatorio en la tabla final.
3. **Normalización:** Los datos se normalizan (mayúsculas, espacios) durante la importación.
4. **Validación de cálculos:** Se valida que `total_financiamiento = cuota_periodo * numero_cuotas`.
5. **Fechas:** `fecha_requerimiento` no puede ser futura.

---

## 🔍 TROUBLESHOOTING

### Error: "Cliente no encontrado"
- Verificar que el cliente existe en `clientes` con la misma cédula
- Verificar normalización de cédula (mayúsculas, sin espacios)

### Error: "Catálogo no encontrado"
- Verificar que el concesionario/analista/modelo existe en sus respectivas tablas
- Verificar normalización de nombres (mayúsculas, espacios)

### Error: "Inconsistencia de cálculos"
- Verificar que `total_financiamiento = cuota_periodo * numero_cuotas`
- Ajustar datos en la fuente o en la tabla temporal

---

## ✅ CHECKLIST FINAL

- [ ] Tabla temporal creada
- [ ] Datos importados a temporal
- [ ] Clientes mapeados correctamente
- [ ] Catálogos mapeados correctamente
- [ ] Validación completada sin errores críticos
- [ ] Préstamos importados a tabla final
- [ ] Verificación de totales correcta
- [ ] Tabla temporal limpiada (opcional)

---

**Última actualización:** 2025-01-27
