# 🔍 Sistema de Auditoría Completa de Base de Datos

Este sistema proporciona herramientas completas para auditar la base de datos del sistema de cobranzas y gestión de créditos.

## 📋 Contenido

### Scripts Python

1. **`auditoria_completa_bd.py`** - Script principal de auditoría
   - Verifica conexiones de tablas (Foreign Keys)
   - Verifica integridad referencial
   - Verifica cálculos financieros
   - Verifica coherencia de datos entre tablas
   - Genera reporte completo

2. **`verificar_flujo_datos.py`** - Verificación de flujo de datos
   - Verifica flujo Cliente → Préstamo → Cuotas → Pagos
   - Verifica propagación de cálculos
   - Verifica actualización de estados

### Scripts SQL

1. **`auditoria_completa_bd.sql`** - Script SQL para DBeaver
   - Consultas de verificación de integridad referencial
   - Consultas de verificación de cálculos financieros
   - Consultas de verificación de coherencia de datos
   - Estadísticas generales

## 🚀 Uso

### Opción 1: Ejecutar desde Python (Recomendado)

```bash
# Desde el directorio raíz del proyecto
cd scripts/python
python auditoria_completa_bd.py
```

El script generará:
- Un reporte en consola
- Un archivo de reporte en `Documentos/Auditorias/REPORTE_AUDITORIA_BD_YYYYMMDD_HHMMSS.txt`

### Opción 2: Ejecutar desde DBeaver

1. Abrir DBeaver
2. Conectarse a la base de datos PostgreSQL
3. Abrir el archivo `scripts/sql/auditoria_completa_bd.sql`
4. Ejecutar el script completo (F5 o botón Ejecutar)
5. Revisar los resultados en las pestañas de resultados

### Opción 3: Verificar Flujo de Datos

```bash
cd scripts/python
python verificar_flujo_datos.py
```

## 📊 Qué Verifica

### 1. Conexiones de Tablas (Foreign Keys)

- ✅ Verifica que todas las Foreign Keys estén definidas correctamente
- ✅ Identifica Foreign Keys faltantes
- ✅ Lista todas las relaciones entre tablas

### 2. Integridad Referencial

- ✅ Pagos con `prestamo_id` inválido
- ✅ Pagos con `cliente_id` inválido
- ✅ Cuotas con `prestamo_id` inválido
- ✅ Préstamos con `cliente_id` inválido
- ✅ Evaluaciones con `prestamo_id` inválido
- ✅ Pagos con cédula que no existe en clientes

### 3. Cálculos Financieros

- ✅ Coherencia: `monto_cuota = monto_capital + monto_interes`
- ✅ Coherencia: `total_pagado = capital_pagado + interes_pagado + mora_pagada`
- ✅ Coherencia: `capital_pendiente + interes_pendiente = monto_cuota - total_pagado`
- ✅ Cálculo automático de mora cuando `fecha_pago > fecha_vencimiento`
- ✅ Coherencia de saldos de capital
- ✅ Suma de pagos vs suma de cuotas por préstamo

### 4. Coherencia de Datos

- ✅ Cédulas coinciden entre `prestamos` y `clientes`
- ✅ Número de cuotas coincide con `prestamos.numero_cuotas`
- ✅ Numeración correcta de cuotas (1, 2, 3, ...)
- ✅ Estados de cuotas coherentes con pagos
- ✅ Préstamos aprobados tienen cuotas generadas

### 5. Flujo de Datos

- ✅ Cliente → Préstamo: Datos se copian correctamente
- ✅ Préstamo → Cuotas: Cuotas se generan correctamente
- ✅ Pagos → Cuotas: Pagos se aplican correctamente
- ✅ Propagación de cálculos entre tablas
- ✅ Actualización de estados

## 📈 Interpretación de Resultados

### Niveles de Problemas

- **🔴 CRÍTICO**: Problemas que afectan la integridad de los datos o cálculos financieros
  - Ejemplo: Cuotas con cálculos incoherentes, préstamos sin cuotas

- **🟡 MEDIO**: Problemas que pueden causar inconsistencias pero no críticos
  - Ejemplo: Cédulas diferentes entre tablas, estados incorrectos

- **🟢 MENOR**: Problemas menores que no afectan la funcionalidad principal
  - Ejemplo: Nombres diferentes entre tablas, numeración de cuotas

### Estado General

- **CRITICO**: Hay problemas críticos que requieren atención inmediata
- **ATENCION**: Hay problemas medios que deben revisarse
- **OK**: No hay problemas o solo problemas menores
- **MENORES**: Solo hay problemas menores

## 🔧 Solución de Problemas

### Problema: "Pagos con prestamo_id inválido"

**Causa**: Hay pagos que referencian préstamos que no existen.

**Solución**:
```sql
-- Identificar los pagos problemáticos
SELECT p.id, p.prestamo_id, p.cedula, p.monto_pagado
FROM pagos p
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.prestamo_id IS NOT NULL AND pr.id IS NULL;

-- Opción 1: Eliminar pagos huérfanos (si son errores)
DELETE FROM pagos WHERE id IN (...);

-- Opción 2: Asignar a préstamo correcto
UPDATE pagos SET prestamo_id = ... WHERE id = ...;
```

### Problema: "Cuotas con cálculos incoherentes"

**Causa**: Los cálculos de montos no coinciden (posible error en aplicación de pagos).

**Solución**:
```sql
-- Identificar cuotas problemáticas
SELECT id, prestamo_id, numero_cuota, 
       monto_cuota, monto_capital, monto_interes,
       total_pagado, capital_pagado, interes_pagado, mora_pagada
FROM cuotas
WHERE ABS(monto_cuota - (monto_capital + monto_interes)) > 0.01;

-- Recalcular manualmente o ejecutar script de corrección
```

### Problema: "Préstamos aprobados sin cuotas"

**Causa**: Préstamos aprobados pero no se generaron las cuotas.

**Solución**:
```python
# Ejecutar script de generación de cuotas faltantes
python scripts/python/generar_cuotas_faltantes.py
```

## 📝 Notas Importantes

1. **Backup**: Siempre hacer backup de la base de datos antes de corregir problemas
2. **Horario**: Ejecutar auditorías en horarios de bajo tráfico
3. **Frecuencia**: Recomendado ejecutar auditoría semanal o después de cambios importantes
4. **Reportes**: Guardar reportes históricos para comparar tendencias

## 🔗 Archivos Relacionados

- `Documentos/Analisis/MAPEO_RED_TABLAS_POSTGRES.md` - Mapeo completo de tablas
- `backend/app/models/` - Modelos de base de datos
- `scripts/sql/` - Otros scripts SQL de verificación

## 📞 Soporte

Si encuentras problemas o tienes preguntas sobre la auditoría, revisa:
1. Los logs del script
2. El reporte generado
3. La documentación en `Documentos/Auditorias/`

---

**Última actualización**: 2025-01-27
