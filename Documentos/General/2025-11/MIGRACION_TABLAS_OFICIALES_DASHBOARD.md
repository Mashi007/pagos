# 📊 MIGRACIÓN A TABLAS OFICIALES DEL DASHBOARD

**Fecha:** 2025-01-04  
**Objetivo:** Migrar todas las consultas del dashboard a usar tablas oficiales de reporting

---

## 🎯 OBJETIVO

Cambiar todas las consultas del dashboard para que usen **tablas oficiales de reporting** en lugar de consultar directamente las tablas transaccionales (`cuotas`, `prestamos`, etc.).

---

## 📋 TABLAS OFICIALES CREADAS

### **1. `dashboard_morosidad_mensual`**
- **Propósito:** Evolución de morosidad por mes
- **Uso:** Gráfico "Evolución de Morosidad"
- **Campos:** año, mes, morosidad_total, cantidad_cuotas_vencidas, cantidad_prestamos_afectados

### **2. `dashboard_cobranzas_mensuales`**
- **Propósito:** Cobranzas planificadas vs pagos reales
- **Uso:** Gráfico "Cobranzas Mensuales"
- **Campos:** año, mes, nombre_mes, cobranzas_planificadas, pagos_reales, meta_mensual

### **3. `dashboard_kpis_diarios`**
- **Propósito:** KPIs principales calculados diariamente
- **Uso:** Tarjetas de KPIs en el dashboard
- **Campos:** fecha, total_prestamos, total_clientes, total_morosidad_usd, etc.

### **4. `dashboard_financiamiento_mensual`**
- **Propósito:** Tendencia mensual de financiamiento
- **Uso:** Gráfico "Tendencia Financiamiento"
- **Campos:** año, mes, nombre_mes, cantidad_nuevos, monto_nuevos, total_acumulado

### **5. `dashboard_morosidad_por_analista`**
- **Propósito:** Morosidad agrupada por analista
- **Uso:** Gráfico "Morosidad por Analista"
- **Campos:** analista, total_morosidad, cantidad_clientes, cantidad_cuotas_atrasadas

### **6. `dashboard_prestamos_por_concesionario`**
- **Propósito:** Distribución de préstamos por concesionario
- **Uso:** Gráfico "Préstamos por Concesionario"
- **Campos:** concesionario, total_prestamos, porcentaje

### **7. `dashboard_pagos_mensuales`**
- **Propósito:** Evolución de pagos por mes
- **Uso:** Gráfico "Evolución de Pagos"
- **Campos:** año, mes, nombre_mes, cantidad_pagos, monto_total

### **8. `dashboard_cobros_por_analista`**
- **Propósito:** Distribución de cobros por analista
- **Uso:** Gráficos de distribución
- **Campos:** analista, total_cobrado, cantidad_pagos

### **9. `dashboard_metricas_acumuladas`**
- **Propósito:** Métricas acumuladas hasta la fecha
- **Uso:** KPIs acumulados
- **Campos:** fecha, cartera_total, morosidad_total, total_cobrado, etc.

---

## 🔧 PASOS PARA IMPLEMENTAR

### **Paso 1: Crear las Tablas**

Ejecutar en DBeaver:
```sql
-- Abrir y ejecutar:
scripts/sql/CREAR_TABLAS_OFICIALES_DASHBOARD.sql
```

### **Paso 2: Poblar las Tablas Iniciales**

Ejecutar en DBeaver:
```sql
-- Abrir y ejecutar:
scripts/sql/ACTUALIZAR_TABLAS_OFICIALES_DASHBOARD.sql
```

### **Paso 3: Modificar Endpoints del Backend**

Los endpoints del dashboard deben consultar las tablas oficiales en lugar de hacer JOINs complejos.

**Ejemplo - Antes:**
```python
# Consulta directamente cuotas y prestamos
query = db.query(Cuota).join(Prestamo)...
```

**Ejemplo - Después:**
```python
# Consulta tabla oficial
query = db.query(DashboardMorosidadMensual)...
```

### **Paso 4: Configurar Actualización Automática**

Las tablas oficiales deben actualizarse periódicamente:
- **Diariamente:** Para KPIs diarios
- **Mensualmente:** Para tablas mensuales
- **On-demand:** Cuando se necesite actualización inmediata

---

## 📝 ENDPOINTS A MODIFICAR

### **Endpoints que deben cambiar:**

1. ✅ `/api/v1/dashboard/evolucion-morosidad`
   - **Antes:** JOIN cuotas + prestamos
   - **Después:** SELECT FROM dashboard_morosidad_mensual

2. ✅ `/api/v1/dashboard/cobranzas-mensuales`
   - **Antes:** JOIN cuotas + prestamos + pagos_staging
   - **Después:** SELECT FROM dashboard_cobranzas_mensuales

3. ✅ `/api/v1/dashboard/kpis-principales`
   - **Antes:** Múltiples queries a cuotas, prestamos, clientes
   - **Después:** SELECT FROM dashboard_kpis_diarios

4. ✅ `/api/v1/dashboard/financiamiento-tendencia-mensual`
   - **Antes:** JOIN prestamos
   - **Después:** SELECT FROM dashboard_financiamiento_mensual

5. ✅ `/api/v1/dashboard/morosidad-por-analista`
   - **Antes:** JOIN cuotas + prestamos con GROUP BY
   - **Después:** SELECT FROM dashboard_morosidad_por_analista

6. ✅ `/api/v1/dashboard/prestamos-por-concesionario`
   - **Antes:** GROUP BY de prestamos
   - **Después:** SELECT FROM dashboard_prestamos_por_concesionario

7. ✅ `/api/v1/dashboard/evolucion-pagos`
   - **Antes:** JOIN pagos_staging
   - **Después:** SELECT FROM dashboard_pagos_mensuales

---

## 🔄 ACTUALIZACIÓN DE TABLAS

### **Opción 1: Actualización Manual**

Ejecutar cuando se necesite:
```sql
SELECT actualizar_tablas_oficiales_dashboard();
```

O ejecutar el script completo:
```sql
-- scripts/sql/ACTUALIZAR_TABLAS_OFICIALES_DASHBOARD.sql
```

### **Opción 2: Actualización Automática (Cron Job)**

Configurar un cron job que ejecute diariamente:
```bash
# Ejecutar cada día a las 2:00 AM
0 2 * * * psql -U usuario -d database -f /ruta/ACTUALIZAR_TABLAS_OFICIALES_DASHBOARD.sql
```

### **Opción 3: Actualización desde Backend**

Crear un endpoint administrativo:
```python
@router.post("/admin/actualizar-tablas-oficiales")
def actualizar_tablas_oficiales(...):
    # Ejecutar función SQL
    db.execute(text("SELECT actualizar_tablas_oficiales_dashboard()"))
    return {"status": "Tablas actualizadas"}
```

---

## ✅ VENTAJAS DE USAR TABLAS OFICIALES

1. **Performance:** Consultas mucho más rápidas
2. **Consistencia:** Todos los dashboards usan los mismos datos
3. **Mantenibilidad:** Lógica de cálculo centralizada
4. **Escalabilidad:** Tablas pre-agregadas soportan más carga
5. **Historial:** Se mantiene historial de cambios
6. **Auditoría:** Fecha de actualización rastreable

---

## 📊 ESTRUCTURA DE DATOS

### **Ejemplo de Consulta Antes:**

```sql
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento >= :fecha_inicio
    AND c.fecha_vencimiento < :fecha_fin_total
    AND c.estado != 'PAGADO'
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes
```

### **Ejemplo de Consulta Después:**

```sql
SELECT 
    año,
    mes,
    morosidad_total as morosidad
FROM dashboard_morosidad_mensual
WHERE 
    (año, mes) >= (EXTRACT(YEAR FROM :fecha_inicio)::int, EXTRACT(MONTH FROM :fecha_inicio)::int)
    AND (año, mes) < (EXTRACT(YEAR FROM :fecha_fin)::int, EXTRACT(MONTH FROM :fecha_fin)::int)
ORDER BY año, mes
```

**Mucho más simple y rápido!**

---

## 🚀 PRÓXIMOS PASOS

1. ✅ Crear tablas oficiales (SQL scripts creados)
2. ⏳ Modificar endpoints del backend
3. ⏳ Crear modelos SQLAlchemy para las tablas oficiales
4. ⏳ Configurar actualización automática
5. ⏳ Probar y validar datos

---

**Documento generado automáticamente**  
**Última actualización:** 2025-01-04

