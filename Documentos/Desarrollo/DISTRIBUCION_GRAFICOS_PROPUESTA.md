# 📊 Distribución de Gráficos - Propuesta Basada en Imagen

## 📋 ANÁLISIS DE LA IMAGEN PROPORCIONADA

Según la descripción de la imagen "Strategic Monitoring Room":

### **KPIs en Header:**
1. **"1 mill. Primary Qty"** - Número grande izquierda
2. **"65 mil Secondary Qty"** - Número grande izquierda
3. **"2,2 ... Primary"** - Métrica resumen derecha
4. **"1,4 m... Secondary"** - Métrica resumen derecha
5. **Selector de año** - 2017, 2018, 2019 (seleccionado), 2020

### **Gráficos Totales: 5**

1. **"Primary & Secondary Sales by Period"** (Bar Chart - Top Left)
   - Eje X: Meses (Jan 2019, Feb 2019, Mar 2019, Apr 2019)
   - Series: Primary (rojo), Secondary (teal), Inventory Valuation (verde/rojo)
   - Tipo: **Bar Chart Multi-series**

2. **"Inventory Valuation per Month Year"** (Bar Chart - Top Right)
   - Eje X: Meses + "Total"
   - Series: Aumento (verde), Disminución (rojo), Total (teal)
   - Tipo: **Bar Chart Agrupado**

3. **"Inventory Valuation by Sector"** (Donut Chart - Bottom Left)
   - Distribución por sectores (SHA, RAN, NEP, etc.)
   - Múltiples segmentos con valores
   - Tipo: **Donut/Pie Chart**

4. **"Inventory Valuation by Center Area"** (Donut Chart - Bottom Middle)
   - Distribución por áreas (UDA, TAL, SUR, etc.)
   - Similar al anterior pero diferente dimensión
   - Tipo: **Donut/Pie Chart**

5. **"Inventory Valuation per Spoke"** (Treemap - Bottom Right)
   - Rectángulos de diferentes tamaños según valor
   - KOC (71 mil), LUC (65 mil), JAL (61 mil), etc.
   - Tipo: **Treemap**

---

## 🎯 DISTRIBUCIÓN PROPUESTA PARA NUESTRO SISTEMA

### **LAYOUT GENERAL (igual a la imagen):**

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER                                                          │
│ ┌──────────┐ ┌──────────┐    [Filtros]  ┌────┐ ┌────┐        │
│ │ KPI 1    │ │ KPI 2    │                │KPI3│ │KPI4│        │
│ │ Grande   │ │ Grande   │                │    │ │    │        │
│ └──────────┘ └──────────┘                └────┘ └────┘        │
├─────────────────────────────────────────────────────────────────┤
│ GRÁFICOS PRINCIPALES                                             │
│ ┌─────────────────────────┐  ┌─────────────────────────┐      │
│ │ GRÁFICO 1               │  │ GRÁFICO 2               │      │
│ │ (Bar Chart Multi)       │  │ (Bar Chart Agrupado)    │      │
│ │ Top Left                │  │ Top Right               │      │
│ │                         │  │                         │      │
│ │                         │  │                         │      │
│ └─────────────────────────┘  └─────────────────────────┘      │
│                                                                  │
│ ┌─────────────────────────┐  ┌─────────────────────────┐      │
│ │ GRÁFICO 3               │  │ GRÁFICO 4               │      │
│ │ (Donut Chart)           │  │ (Donut Chart)           │      │
│ │ Bottom Left             │  │ Bottom Middle           │      │
│ │                         │  │                         │      │
│ └─────────────────────────┘  └─────────────────────────┘      │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ GRÁFICO 5                                                 │  │
│ │ (Treemap)                                                 │  │
│ │ Bottom Right                                              │  │
│ │                                                           │  │
│ └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 PROPUESTA POR CATEGORÍA

### **1. DASHBOARD FINANCIAMIENTO**

#### **KPIs Header (4 métricas):**
1. **Total Financiamiento** - `$50.2M` (grande, izquierda)
2. **Financiamientos Totales** - `1,245` préstamos (grande, izquierda)
3. **Financiamiento Activo** - `$35.1M` (resumen, derecha)
4. **Monto Promedio** - `$40,320` (resumen, derecha)

#### **Gráficos (5 totales):**

**GRÁFICO 1 (Top Left) - Bar Chart Multi-series:**
- **Título:** "Financiamiento por Estado y Período"
- **Eje X:** Meses (últimos 4-6 meses)
- **Series:**
  - Financiamiento Activo (verde)
  - Financiamiento Inactivo (naranja)
  - Financiamiento Finalizado (azul)
- **Datos:** Montos mensuales por estado

**GRÁFICO 2 (Top Right) - Bar Chart Agrupado:**
- **Título:** "Nuevos Financiamientos por Mes"
- **Eje X:** Meses + "Total"
- **Series:**
  - Nuevos Aprobados (verde)
  - Nuevos Cancelados (rojo)
  - Total Acumulado (teal)
- **Datos:** Cantidad o monto de nuevos financiamientos

**GRÁFICO 3 (Bottom Left) - Donut Chart:**
- **Título:** "Distribución por Estado"
- **Segmentos:**
  - Activo (X%)
  - Inactivo (Y%)
  - Finalizado (Z%)
- **Datos:** Porcentajes de financiamiento por estado

**GRÁFICO 4 (Bottom Middle) - Donut Chart:**
- **Título:** "Distribución por Top Concesionarios"
- **Segmentos:**
  - Top 8-10 concesionarios con mayor financiamiento
  - Cada uno con su monto y porcentaje
- **Datos:** Montos por concesionario

**GRÁFICO 5 (Bottom Right) - Treemap:**
- **Título:** "Financiamiento por Concesionario (Detalle)"
- **Rectángulos:**
  - Tamaño = Monto total financiado
  - Color = Por estado o categoría
  - Labels = Nombre concesionario + monto
- **Datos:** Todos los concesionarios con sus montos

---

### **2. DASHBOARD CUOTAS**

#### **KPIs Header (4 métricas):**
1. **Total Cuotas del Mes** - `3,450` (grande)
2. **Cuotas Pagadas** - `2,890` (grande)
3. **Tasa de Recuperación** - `83.8%` (resumen)
4. **Cuotas Atrasadas** - `560` (resumen)

#### **Gráficos (5 totales):**

**GRÁFICO 1 (Top Left) - Bar Chart Multi-series:**
- **Título:** "Cuotas por Estado y Período"
- **Series:**
  - Pagadas (verde)
  - Pendientes (amarillo)
  - Atrasadas (rojo)
- **Eje X:** Últimos meses

**GRÁFICO 2 (Top Right) - Bar Chart Agrupado:**
- **Título:** "Cuotas por Estado de Conciliación"
- **Series:**
  - Conciliadas (verde)
  - No Conciliadas (rojo)
  - Pendientes (gris)
- **Eje X:** Meses + "Total"

**GRÁFICO 3 (Bottom Left) - Donut Chart:**
- **Título:** "Distribución de Cuotas por Estado"
- **Segmentos:** Pagadas, Pendientes, Atrasadas

**GRÁFICO 4 (Bottom Middle) - Donut Chart:**
- **Título:** "Distribución de Cuotas por Analista"
- **Segmentos:** Top analistas con más cuotas gestionadas

**GRÁFICO 5 (Bottom Right) - Treemap:**
- **Título:** "Cuotas por Cliente (con 2+ impagas)"
- **Rectángulos:** Clientes con morosidad, tamaño = cantidad cuotas impagas

---

### **3. DASHBOARD COBRANZA**

#### **KPIs Header (4 métricas):**
1. **Total Cobrado** - `$12.5M` (grande)
2. **Meta Mensual** - `$15.0M` (grande)
3. **Avance Meta** - `83.3%` (resumen)
4. **Tasa Recuperación** - `85.2%` (resumen)

#### **Gráficos (5 totales):**

**GRÁFICO 1 (Top Left) - Bar Chart Multi-series:**
- **Título:** "Cobranza por Día del Mes"
- **Series:**
  - Cobrado (verde)
  - Meta Diaria (línea/objetivo)
  - Acumulado (azul)
- **Eje X:** Días del mes actual

**GRÁFICO 2 (Top Right) - Bar Chart Agrupado:**
- **Título:** "Recaudación Mensual Comparativa"
- **Series:**
  - Meta (objetivo)
  - Recaudado (verde)
  - Pendiente (rojo)
- **Eje X:** Meses + "Total"

**GRÁFICO 3 (Bottom Left) - Donut Chart:**
- **Título:** "Distribución de Cobros por Estado"
- **Segmentos:** Conciliados, Pendientes, Rechazados

**GRÁFICO 4 (Bottom Middle) - Donut Chart:**
- **Título:** "Distribución por Analista"
- **Segmentos:** Top analistas por monto cobrado

**GRÁFICO 5 (Bottom Right) - Treemap:**
- **Título:** "Cobranza por Cliente"
- **Rectángulos:** Clientes, tamaño = monto cobrado, color = por analista

---

### **4. DASHBOARD ANÁLISIS**

#### **KPIs Header (4 métricas):**
1. **Total Cobrado Mes** - `$15.2M` (grande)
2. **Variación Mes Anterior** - `+12.5%` (grande)
3. **Crecimiento Anual** - `+28.3%` (resumen)
4. **Clientes Activos** - `8,245` (resumen)

#### **Gráficos (5 totales):**

**GRÁFICO 1 (Top Left) - Bar Chart Multi-series:**
- **Título:** "Cobros Diarios del Mes"
- **Series:** Cobros día a día, tendencia

**GRÁFICO 2 (Top Right) - Bar Chart Agrupado:**
- **Título:** "Comparativa Mensual"
- **Series:** Este mes vs mes anterior vs mismo mes año anterior

**GRÁFICO 3 (Bottom Left) - Donut Chart:**
- **Título:** "Distribución por Tipo de Pago"
- **Segmentos:** Efectivo, Transferencia, Cheque, etc.

**GRÁFICO 4 (Bottom Middle) - Donut Chart:**
- **Título:** "Distribución por Modelo de Vehículo"
- **Segmentos:** Top modelos financiados

**GRÁFICO 5 (Bottom Right) - Treemap:**
- **Título:** "Análisis por Concesionario"
- **Rectángulos:** Concesionarios con métricas combinadas

---

### **5. DASHBOARD PAGOS**

#### **KPIs Header (4 métricas):**
1. **Total Pagos Mes** - `$15.2M` (grande)
2. **Pagos Conciliados** - `14,245` (grande)
3. **Tasa Conciliación** - `97.4%` (resumen)
4. **Pagos Pendientes** - `380` (resumen)

#### **Gráficos (5 totales):**

**GRÁFICO 1 (Top Left) - Bar Chart Multi-series:**
- **Título:** "Pagos por Día y Estado"
- **Series:** Conciliados, Pendientes, Rechazados

**GRÁFICO 2 (Top Right) - Bar Chart Agrupado:**
- **Título:** "Pagos Mensuales"
- **Series:** Por estado de conciliación

**GRÁFICO 3 (Bottom Left) - Donut Chart:**
- **Título:** "Distribución por Estado de Pago"
- **Segmentos:** Conciliados, Pendientes, Rechazados

**GRÁFICO 4 (Bottom Middle) - Donut Chart:**
- **Título:** "Distribución por Método de Pago"
- **Segmentos:** Efectivo, Transferencia, etc.

**GRÁFICO 5 (Bottom Right) - Treemap:**
- **Título:** "Pagos por Cliente"
- **Rectángulos:** Clientes, tamaño = cantidad/monto pagos

---

## ✅ RESUMEN

**Estructura Consistente:**
- ✅ 4 KPIs en header (2 grandes + 2 resumen)
- ✅ 5 gráficos en layout tipo grid:
  - Top Left: Bar Chart Multi-series
  - Top Right: Bar Chart Agrupado
  - Bottom Left: Donut Chart
  - Bottom Middle: Donut Chart
  - Bottom Right: Treemap

**Nota:** Puedes ajustar el contenido específico de cada gráfico según los datos disponibles en tus APIs. La estructura visual se mantiene igual.

