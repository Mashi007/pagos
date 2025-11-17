# 📊 PROPUESTA: Componentes Dashboard con Modales

## 🎯 DECISIONES CONFIRMADAS

✅ **MODALES** - Las vistas detalladas se abrirán en modales
✅ **Gráficos Interactivos** - Conectados a filtros globales
✅ **Alto Desempeño Gráfico** - Visualizaciones de calidad profesional

---

## ⚙️ CONDICIONES GENERALES - APLICAN A TODOS LOS COMPONENTES

### **1. CONECTIVIDAD CON BASE DE DATOS**

✅ **TODOS los KPIs deben estar conectados a bases de datos reales**
- Cada métrica debe consultar tablas específicas de la base de datos
- No se usarán datos mock o simulados
- Conexión directa mediante SQLAlchemy/ORM o queries SQL optimizadas

✅ **Acceso a Tablas Específicas que se Actualizan**
- Cada KPI debe identificar claramente qué tablas consulta
- Las tablas deben reflejar actualizaciones en tiempo real
- Ejemplos de tablas a consultar:
  - `prestamos` - Para total de préstamos, créditos nuevos
  - `cuotas` / `amortizacion` - Para cuotas, morosidad, días
  - `pagos` - Para pagos, cobranza, conciliaciones
  - `clientes` - Para total de clientes
  - `analistas` - Para agrupaciones por analista
  - `concesionarios` - Para agrupaciones por concesionario

**Especificación por Componente:**
Cada componente debe documentar:
```yaml
Componente: [Nombre]
Tablas Consultadas:
  - tabla_principal: descripción
  - tabla_secundaria: descripción
Campos Utilizados:
  - campo_1: propósito
  - campo_2: propósito
Relaciones:
  - tabla_1 JOIN tabla_2 ON condición
```

---

### **2. FILTROS GLOBALES APLICABLES**

✅ **TODOS los KPIs deben poder filtrarse según filtros registrados**

**Filtros Estándar Disponibles:**
- ✅ **Analista** - Filtrar por analista específico
- ✅ **Concesionario** - Filtrar por concesionario específico
- ✅ **Modelo de Vehículo** - Filtrar por modelo
- ✅ **Rango de Fechas** - fecha_inicio y fecha_fin
- ✅ **Período** - Mes, Trimestre, Año, Personalizado

**Implementación:**
- Todos los endpoints deben aceptar estos parámetros de filtro
- Los filtros deben aplicarse a nivel de query SQL/ORM
- Los filtros deben ser opcionales (si no se envían, mostrar todos los datos)
- Los filtros deben poder combinarse (múltiples filtros simultáneos)

**Ejemplo de Filtrado:**
```python
# Backend - Aplicar filtros automáticamente
query = db.query(Prestamo)
query = FiltrosDashboard.aplicar_filtros_prestamo(
    query,
    analista=analista,
    concesionario=concesionario,
    modelo=modelo,
    fecha_inicio=fecha_inicio,
    fecha_fin=fecha_fin
)
```

**Frontend:**
- Componente `DashboardFiltrosPanel` debe estar disponible en todos los modales
- Los filtros deben actualizar automáticamente todos los gráficos y KPIs
- Los filtros deben persistir durante la sesión (opcional)

---

### **3. ALTA INTERACTIVIDAD EN GRÁFICOS**

✅ **TODOS los gráficos deben ser de alta interactividad**

#### **Características de Interactividad Requeridas:**

**A. Tooltips Detallados:**
Al señalar (hover) cualquier punto/barra/segmento del gráfico, debe mostrarse:

- ✅ **Fecha/Período** exacto del punto
- ✅ **Monto/Valor** exacto (formato: $1,234.56 o 1,234 unidades)
- ✅ **Información Contextual:**
  - Nombre del elemento (analista, concesionario, cliente, etc.)
  - Porcentaje (si aplica)
  - Cantidad (número de registros)
  - Variación vs período anterior (si aplica)
- ✅ **Datos Relacionados:**
  - Desglose por subcategorías
  - Comparativa con valores anteriores
  - Meta u objetivo (si aplica)

**B. Click en Puntos/Elementos:**
Al hacer click en cualquier punto/barra/segmento:

- ✅ **Ver Detalle Completo:**
  - Abrir modal o drawer con información detallada
  - Mostrar tabla con registros que componen ese punto
  - Filtros adicionales específicos para ese detalle

- ✅ **Ejemplo de Detalle al Click:**
  ```
  Click en: "Analista Juan Pérez - $450K morosidad"
  Modal muestra:
  - Lista de clientes en mora de ese analista
  - Tabla con: Cliente, Monto Morosidad, Días Atraso, Cuotas Vencidas
  - Filtros adicionales: Por concesionario, Por modelo
  - Botón: Exportar a Excel
  ```

**C. Zoom y Navegación:**
- ✅ **Zoom:** Click y arrastrar para hacer zoom en rangos específicos
- ✅ **Pan:** Arrastrar para navegar en el tiempo/espacio
- ✅ **Reset:** Botón para volver a vista completa

**D. Leyendas Interactivas:**
- ✅ **Click en Leyenda:** Mostrar/ocultar series de datos
- ✅ **Hover en Leyenda:** Resaltar serie correspondiente en el gráfico

**E. Exportación:**
- ✅ **Exportar Gráfico:** Como imagen (PNG, SVG)
- ✅ **Exportar Datos:** Como Excel/CSV del gráfico visible

---

### **4. ESPECIFICACIÓN DE DETALLES POR TIPO DE GRÁFICO**

#### **Line Chart (Líneas de Tendencia):**
**Hover:**
- Fecha exacta
- Valor de cada línea en esa fecha
- Variación vs punto anterior
- Tasa de crecimiento

**Click:**
- Modal con tabla de datos del período
- Desglose día a día (si es mensual) o mes a mes (si es anual)
- Gráfico de comparativa vs períodos anteriores

#### **Bar Chart (Barras):**
**Hover:**
- Nombre de la categoría
- Valor exacto
- Porcentaje del total
- Cantidad de registros

**Click:**
- Modal con lista de registros que componen esa barra
- Filtros para profundizar
- Exportación de datos

#### **Pie/Donut Chart:**
**Hover:**
- Nombre del segmento
- Valor absoluto
- Porcentaje
- Comparativa con otros segmentos

**Click:**
- Modal con lista de registros de ese segmento
- Opción de drill-down (si aplica)

#### **Treemap:**
**Hover:**
- Nombre del elemento
- Valor (monto/cantidad)
- Porcentaje
- Cantidad de sub-elementos

**Click:**
- Modal con drill-down jerárquico
- Lista de elementos que componen ese rectángulo
- Posibilidad de expandir niveles

#### **Area Chart:**
**Hover:**
- Fecha/período
- Valores de cada serie en ese punto
- Total acumulado
- Variación vs período anterior

**Click:**
- Modal con desglose temporal detallado
- Tabla con todos los puntos de datos

---

### **5. IMPLEMENTACIÓN TÉCNICA**

#### **Backend - Endpoints:**
Todos los endpoints deben:
- ✅ Aceptar todos los filtros estándar
- ✅ Retornar datos estructurados y consistentes
- ✅ Incluir metadatos (fecha de actualización, totales, etc.)
- ✅ Optimizar queries para performance
- ✅ Usar índices de base de datos apropiados

#### **Frontend - Componentes:**
Todos los gráficos deben:
- ✅ Usar librería de gráficos interactiva (Recharts, Chart.js, ApexCharts, etc.)
- ✅ Implementar tooltips personalizados con toda la información
- ✅ Manejar eventos de click para abrir modales de detalle
- ✅ Integrar con `DashboardFiltrosPanel` para filtros
- ✅ Actualizarse automáticamente cuando cambian los filtros

#### **Componentes de Detalle:**
- ✅ Crear componente genérico `DetailModal` para mostrar detalles
- ✅ Componente debe ser reutilizable para todos los tipos de gráficos
- ✅ Debe mostrar tablas, filtros adicionales, y opciones de exportación

---

### **6. DOCUMENTACIÓN OBLIGATORIA**

Cada componente debe documentar:

1. **Tablas y Campos:**
   - Qué tablas consulta
   - Qué campos utiliza
   - Qué relaciones tiene

2. **Filtros Aplicables:**
   - Lista de filtros que acepta
   - Cómo se aplican en la query
   - Ejemplos de uso

3. **Interactividad:**
   - Qué información muestra en tooltip
   - Qué detalle muestra al hacer click
   - Qué acciones adicionales están disponibles

4. **APIs:**
   - Endpoint(s) utilizado(s)
   - Parámetros requeridos y opcionales
   - Formato de respuesta

---

## 📋 CHECKLIST DE VALIDACIÓN POR COMPONENTE

Para cada componente, verificar:

- [ ] ✅ Conectado a base de datos real (no mocks)
- [ ] ✅ Identifica tablas específicas consultadas
- [ ] ✅ Acepta todos los filtros estándar
- [ ] ✅ Los filtros se aplican correctamente en queries
- [ ] ✅ Tooltips muestran información completa
- [ ] ✅ Click en elementos muestra detalle
- [ ] ✅ Detalle incluye tabla de datos relacionados
- [ ] ✅ Detalle permite exportación
- [ ] ✅ Gráfico es interactivo (zoom, pan si aplica)
- [ ] ✅ Leyendas son interactivas
- [ ] ✅ Documentación completa disponible

---

**Estas condiciones aplican a TODOS los componentes sin excepción.** ✅

---

## 📋 COMPONENTE 1: Cobranzas Mensuales vs Pagos y Meta Mensual

### **Descripción:**
Gráfico que suma las **cobranzas mensuales** (amortizaciones/cuotas planificadas de todos los clientes) y las compara contra los **pagos reales**, mostrando también la **meta mensual** como línea objetivo.

### **Funcionalidad:**
- **Cobranzas Mensuales:** Suma de todas las cuotas/amortizaciones programadas para cada mes (basado en la tabla de amortizaciones)
- **Pagos:** Pagos reales recibidos en cada mes
- **Meta Mensual:** Objetivo de cobranza que se actualiza automáticamente el **día 1 de cada mes**

### **Especificaciones Técnicas:**

#### **Tipo de Gráfico:**
- **Gráfico de Área Multi-capa** o **Line Chart con área**
- Similar al de la imagen de referencia (área apilada/superpuesta)

#### **Estructura:**
```
┌──────────────────────────────────────────────────────────────────┐
│ COBRANZAS MENSUALES VS PAGOS Y META MENSUAL                     │
│ [Filtros integrados]                                             │
├──────────────┬───────────────────────────────────────────────────┤
│ TARJETAS KPI │                                                   │
│ (Izquierda)  │  [Gráfico de Área/Línea]                        │
│              │                                                   │
│ ┌──────────┐ │  Series:                                         │
│ │ Total    │ │  - Cobranzas Planificadas (Área azul/teal)      │
│ │ Préstamos│ │  - Pagos Reales (Área verde)                     │
│ │          │ │  - Meta Mensual (Línea horizontal o curva)      │
│ │ 1,245    │ │                                                   │
│ │          │ │  Eje X: Meses (últimos 12 meses o rango)        │
│ │      +5% │ │  Eje Y: Montos ($)                              │
│ └──────────┘ │                                                   │
│              │  Leyenda interactiva                            │
│ ┌──────────┐ │  Tooltips con valores exactos                    │
│ │ Créditos │ │  Zoom y pan (si es necesario)                    │
│ │ Nuevos   │ │                                                   │
│ │ Mes      │ │                                                   │
│ │          │ │                                                   │
│ │ 245      │ │                                                   │
│ │      +12%│ │                                                   │
│ └──────────┘ │                                                   │
│              │                                                   │
│ ┌──────────┐ │                                                   │
│ │ Total    │ │                                                   │
│ │ Clientes │ │                                                   │
│ │          │ │                                                   │
│ │ 8,450    │ │                                                   │
│ │      -2% │ │                                                   │
│ └──────────┘ │                                                   │
│              │                                                   │
│ ┌──────────┐ │                                                   │
│ │ Total    │ │                                                   │
│ │ Morosidad│ │                                                   │
│ │ ($)      │ │                                                   │
│ │          │ │                                                   │
│ │ $450K    │ │                                                   │
│ │     +8%  │ │                                                   │
│ └──────────┘ │                                                   │
└──────────────┴───────────────────────────────────────────────────┘
```

#### **Colores Propuestos:**
- **Cobranzas Planificadas:** Azul/Teal (`#14b8a6` o `#0891b2`)
- **Pagos Reales:** Verde (`#10b981` o `#059669`)
- **Meta Mensual:** Línea roja o naranja (`#ef4444` o `#f59e0b`)

#### **Filtros que Aplican:**
- ✅ Analista
- ✅ Concesionario
- ✅ Modelo de vehículo
- ✅ Rango de fechas
- ✅ Período (mes, trimestre, año)

#### **Actualización de Meta Mensual:**
- Se debe consultar/calcular automáticamente el día 1 de cada mes
- Puede venir de:
  - Base de datos (tabla de metas)
  - Cálculo basado en reglas de negocio
  - Configuración manual por administrador

#### **Tarjetas KPI (Panel Izquierdo):**
- **Diseño:** Cards tipo estadística con número grande y % variación
- **4 Tarjetas:**

1. **Total Préstamos**
   - Número: Conteo total de préstamos aprobados
   - % Variación: Comparación con mes anterior
   - Color: Azul/Cyan

2. **Créditos Nuevos en el Mes**
   - Número: Préstamos nuevos aprobados en el mes actual
   - % Variación: Comparación con mes anterior
   - Color: Verde

3. **Total Clientes**
   - Número: Conteo total de clientes únicos activos
   - % Variación: Comparación con mes anterior
   - Color: Púrpura

4. **Total Morosidad en Dólares**
   - Número: Suma de monto vencido (monto_mora) en dólares
   - % Variación: Comparación con mes anterior
   - Color: Rojo/Naranja

**Características de las Tarjetas:**
- Número grande y destacado (font-size grande)
- Título descriptivo del KPI
- Porcentaje de variación en esquina inferior derecha
- Color de fondo suave según el tipo de métrica
- Icono representativo (opcional)
- Actualización automática al cambiar filtros

**Cálculo de Variación:**
```
% Variación = ((Valor Mes Actual - Valor Mes Anterior) / Valor Mes Anterior) * 100
```
- Positivo (+X%): Verde o azul
- Negativo (-X%): Rojo o naranja
- Sin cambio (0%): Gris

#### **APIs Necesarias:**

**Endpoint 1: KPIs Principales con Variación**
```
GET /api/v1/dashboard/kpis-principales?
  analista=...
  concesionario=...
  modelo=...
  fecha_inicio=YYYY-MM-DD
  fecha_fin=YYYY-MM-DD

Response:
{
  total_prestamos: {
    valor_actual: 1245,
    valor_mes_anterior: 1185,
    variacion_porcentual: 5.06,
    variacion_absoluta: 60
  },
  creditos_nuevos_mes: {
    valor_actual: 245,
    valor_mes_anterior: 218,
    variacion_porcentual: 12.39,
    variacion_absoluta: 27
  },
  total_clientes: {
    valor_actual: 8450,
    valor_mes_anterior: 8620,
    variacion_porcentual: -1.97,
    variacion_absoluta: -170
  },
  total_morosidad_usd: {
    valor_actual: 450000.00,
    valor_mes_anterior: 416000.00,
    variacion_porcentual: 8.17,
    variacion_absoluta: 34000.00
  },
  mes_actual: "2024-01",
  mes_anterior: "2023-12"
}
```

**Endpoint 2: Cobranzas Mensuales**
```
GET /api/v1/dashboard/cobranzas-mensuales?
  fecha_inicio=YYYY-MM-DD
  fecha_fin=YYYY-MM-DD
  analista=...
  concesionario=...
  modelo=...

Response:
{
  meses: [
    {
      mes: "2024-01",
      nombre_mes: "Enero 2024",
      cobranzas_planificadas: 1500000.00,
      pagos_reales: 1200000.00,
      meta_mensual: 1800000.00
    },
    ...
  ],
  meta_actual: 1800000.00  // Meta del mes actual
}
```

---

## 📊 COMPONENTE 2: Por Día - Total a Cobrar, Pagos y Morosidad + Métricas Acumuladas

### **Descripción:**
Gráfico diario que muestra **Total a Cobrar**, **Pagos** y **Morosidad** por día. Incluye panel lateral con métricas acumuladas y contadores de clientes.

### **Funcionalidad:**

#### **Gráfico Principal (Por Día):**
- **Total a Cobrar:** Suma de cuotas que deberían cobrarse cada día
- **Pagos:** Pagos recibidos cada día
- **Morosidad:** Diferencia entre lo que se debería cobrar y lo pagado (cuotas atrasadas acumuladas)

#### **Panel Lateral con Métricas:**
1. **Acumulado Mensual:** Suma del mes actual (se pone a cero el día 1 de cada mes)
2. **Acumulado Anual:** Suma acumulada de todos los meses del año
3. **Clientes con 1 Pago Atrasado:** Contador de clientes únicos
4. **Clientes con 3 o Más Cuotas Atrasadas:** Contador de clientes únicos

### **Especificaciones Técnicas:**

#### **Layout:**
```
┌──────────────────────────────────────────────────────────────────┐
│ TOTAL A COBRAR, PAGOS Y MOROSIDAD POR DÍA                       │
│ [Filtros integrados]                                             │
├──────────────┬──────────────────────┬───────────────────────────┤
│ TARJETAS KPI │ GRÁFICO PRINCIPAL    │ MÉTRICAS ACUMULADAS       │
│ (Izquierda)  │ (Por Día)            │                           │
│              │                      │ ┌───────────────────────┐│
│ ┌──────────┐ │ [Line/Bar Chart]     │ │ Acumulado Mensual    ││
│ │ Total    │ │                      │ │ $450,000             ││
│ │ Préstamos│ │ Series:              │ │ (Desde día 1 del mes)││
│ │          │ │ - Total a Cobrar     │ └───────────────────────┘│
│ │ 1,245    │ │ - Pagos              │                           │
│ │      +5% │ │ - Morosidad          │ ┌───────────────────────┐│
│ └──────────┘ │                      │ │ Acumulado Anual      ││
│              │ Eje X: Días del mes  │ │ $5,200,000           ││
│ ┌──────────┐ │ Eje Y: Montos ($)    │ │ (Desde enero)         ││
│ │ Créditos │ │                      │ └───────────────────────┘│
│ │ Nuevos   │ │                      │                           │
│ │ Mes      │ │                      │ ┌───────────────────────┐│
│ │          │ │                      │ │ Clientes 1 Pago      ││
│ │ 245      │ │                      │ │ Atrasado             ││
│ │      +12%│ │                      │ │ 67 clientes          ││
│ └──────────┘ │                      │ └───────────────────────┘│
│              │                      │                           │
│ ┌──────────┐ │                      │ ┌───────────────────────┐│
│ │ Total    │ │                      │ │ Clientes 3+ Cuotas    ││
│ │ Clientes │ │                      │ │ Atrasadas            ││
│ │          │ │                      │ │ 32 clientes          ││
│ │ 8,450    │ │                      │ └───────────────────────┘│
│ │      -2% │ │                      │                           │
│ └──────────┘ │                      │                           │
│              │                      │                           │
│ ┌──────────┐ │                      │                           │
│ │ Total    │ │                      │                           │
│ │ Morosidad│ │                      │                           │
│ │ ($)      │ │                      │                           │
│ │          │ │                      │                           │
│ │ $450K    │ │                      │                           │
│ │     +8%  │ │                      │                           │
│ └──────────┘ │                      │                           │
└──────────────┴──────────────────────┴───────────────────────────┘
```

#### **Tipo de Gráfico Principal:**
- **Bar Chart Agrupado** (3 barras por día) o
- **Line Chart con múltiples líneas** o
- **Combo Chart** (barras + línea)

#### **Colores Propuestos:**
- **Total a Cobrar:** Azul (`#3b82f6`)
- **Pagos:** Verde (`#10b981`)
- **Morosidad:** Rojo/Naranja (`#ef4444` o `#f59e0b`)

#### **Métricas Acumuladas (Panel Lateral):**
- Diseño tipo "cards" con números grandes y descriptivos
- Similar a la imagen de referencia (números circulares con descripción)
- Iconos descriptivos
- Colores diferenciados por tipo de métrica

#### **Actualización de Acumulados:**
- **Acumulado Mensual:** Se resetea automáticamente el día 1 de cada mes
- **Acumulado Anual:** Se acumula desde el 1 de enero hasta el 31 de diciembre (o fecha actual)

#### **Cálculo de Clientes Atrasados:**
- **1 Pago Atrasado:** Cuenta clientes únicos que tienen exactamente 1 cuota vencida
- **3+ Cuotas Atrasadas:** Cuenta clientes únicos que tienen 3 o más cuotas vencidas

#### **Filtros que Aplican:**
- ✅ Analista
- ✅ Concesionario
- ✅ Modelo de vehículo
- ✅ Rango de fechas
- ⚠️ **Importante:** Las métricas acumuladas deben respetar el filtro de fechas si se aplica

#### **APIs Necesarias:**

**Endpoint 1: Datos por día**
```
GET /api/v1/dashboard/cobranza-por-dia?
  fecha_inicio=YYYY-MM-DD
  fecha_fin=YYYY-MM-DD
  analista=...
  concesionario=...
  modelo=...

Response:
{
  dias: [
    {
      fecha: "2024-01-15",
      total_a_cobrar: 50000.00,
      pagos: 45000.00,
      morosidad: 5000.00
    },
    ...
  ]
}
```

**Endpoint 2: Métricas acumuladas**
```
GET /api/v1/dashboard/metricas-acumuladas?
  fecha_inicio=YYYY-MM-DD  // Para acumulado mensual
  fecha_fin=YYYY-MM-DD
  analista=...
  concesionario=...
  modelo=...

Response:
{
  acumulado_mensual: 450000.00,
  acumulado_anual: 5200000.00,
  clientes_1_pago_atrasado: 67,
  clientes_3mas_cuotas_atrasadas: 32,
  fecha_inicio_mes: "2024-01-01",
  fecha_inicio_anio: "2024-01-01"
}
```

---

## 🎨 DISEÑO VISUAL

### **Estilo General:**
- Fondo claro (como DashboardMenu actual)
- Cards con sombras suaves
- Colores vibrantes pero profesionales
- Tipografía clara y legible
- Animaciones suaves en hover y carga

### **Modal Design:**
- Tamaño: Grande (90% viewport o 1200px mínimo)
- Header con título y botón cerrar
- Body con scroll si es necesario
- Footer opcional con acciones

### **Interactividad:**
- Tooltips en gráficos al hover
- Leyendas clickeables para mostrar/ocultar series
- Zoom en gráficos si es necesario
- Filtros reactivos (actualizan gráficos en tiempo real)

---

## 🔧 IMPLEMENTACIÓN

### **Componentes a Crear:**

1. **`CobranzasMensualesModal.tsx`**
   - Modal con Componente 1
   - Integración de filtros
   - Carga de datos
   - Renderizado de gráfico

2. **`CobranzaPorDiaModal.tsx`**
   - Modal con Componente 2
   - Layout dividido (gráfico + métricas)
   - Integración de filtros
   - Carga de datos

3. **`KpiCardsPanel.tsx`**
   - Panel de 4 tarjetas KPI (reutilizable)
   - Props: kpisData, loading, error
   - Muestra: Total Préstamos, Créditos Nuevos, Total Clientes, Total Morosidad
   - Cada card con % variación mes anterior

4. **`KpiCard.tsx`**
   - Tarjeta individual de KPI
   - Props: title, value, variationPercent, variationAbs, color, icon
   - Renderiza número grande y % en esquina inferior derecha

5. **`MonthlyCobranzasChart.tsx`**
   - Gráfico reutilizable para Componente 1
   - Usa Recharts o similar
   - Props: data, filters, onFilterChange

6. **`DailyCobranzasChart.tsx`**
   - Gráfico reutilizable para Componente 2
   - Props: data, filters, onFilterChange

7. **`MetricCards.tsx`**
   - Cards para métricas acumuladas
   - Diseño tipo imagen de referencia

### **Librerías de Gráficos:**
- **Recharts** (ya en uso) - Para gráficos estándar
- Posiblemente **Chart.js** o **ApexCharts** para gráficos más avanzados

---

## ✅ PRÓXIMOS PASOS

1. ✅ Confirmar estructura de datos del backend
2. ✅ Crear/quedar pendiente endpoints necesarios
3. ✅ Implementar Componente 1
4. ✅ Implementar Componente 2
5. ✅ Integrar con filtros globales
6. ✅ Testing y refinamiento

---

## 📝 NOTAS

- Los modales se abrirán desde botones en las páginas de dashboard
- Los filtros deben persistir entre la página principal y el modal
- Las actualizaciones automáticas (meta mensual, reset acumulados) deben manejarse en el backend
- Considerar caché de datos para mejor performance
- **Las tarjetas KPI se actualizan automáticamente:**
  - Al cambiar filtros
  - Al refrescar datos
  - Comparación automática con mes anterior (backend calcula)
  - Formato de % variación: `+5.2%` (verde) o `-2.1%` (rojo)

## 📐 ESPECIFICACIONES DE TARJETAS KPI

### **Diseño Visual:**
```
┌─────────────────────────┐
│ Total Préstamos         │  ← Título
│                         │
│                         │
│     1,245               │  ← Número grande
│                         │
│                         │
│                  +5.2%  │  ← % variación (esquina inferior derecha)
└─────────────────────────┘
```

### **Dimensiones:**
- Ancho: ~250-300px
- Alto: ~150-180px
- Borde redondeado
- Sombra suave
- Padding interno cómodo

### **Colores por KPI:**
1. **Total Préstamos:** Fondo azul claro (`bg-blue-50`), texto azul (`text-blue-700`)
2. **Créditos Nuevos:** Fondo verde claro (`bg-green-50`), texto verde (`text-green-700`)
3. **Total Clientes:** Fondo púrpura claro (`bg-purple-50`), texto púrpura (`text-purple-700`)
4. **Total Morosidad:** Fondo rojo claro (`bg-red-50`), texto rojo (`text-red-700`)

### **Formato de Variación:**
- Positivo: `+5.2%` en verde (`text-green-600`)
- Negativo: `-2.1%` en rojo (`text-red-600`)
- Sin cambio: `0.0%` en gris (`text-gray-500`)
- Icono: ⬆️ (verde) para positivo, ⬇️ (rojo) para negativo, ➡️ (gris) para sin cambio

### **Responsive:**
- En pantallas grandes: 4 tarjetas en columna vertical (izquierda)
- En pantallas medianas: 2x2 grid
- En pantallas pequeñas: 1 columna (stack vertical)

---

## 🗺️ COMPONENTE 3: Treemap - Morosidad por Analista

### **Descripción:**
Gráfico tipo **Treemap** que representa la morosidad agrupada por analista, incluyendo **todos los clientes que tienen morosidad desde 1 día** (desde el primer día de atraso, no solo los que tienen múltiples cuotas atrasadas).

### **Funcionalidad:**
- **Agrupación:** Por Analista
- **Métrica Principal:** Morosidad (monto total o cantidad de clientes)
- **Incluye:** Todos los clientes con al menos 1 día de atraso
- **Visualización:** Rectángulos de diferentes tamaños según el valor

### **Especificaciones Técnicas:**

#### **Tipo de Gráfico:**
- **Treemap Chart** (similar a la imagen de referencia)
- Rectángulos anidados jerárquicamente
- Colores distintos por analista

#### **Estructura:**
```
┌──────────────────────────────────────────────────────────────────┐
│ MOROSIDAD POR ANALISTA                                          │
│ [Filtros integrados]                                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    TREEMAP CHART                          │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │ Analista │  │ Analista │  │ Analista │               │  │
│  │  │    A     │  │    B     │  │    C     │               │  │
│  │  │ $450K    │  │ $320K    │  │ $280K    │               │  │
│  │  │ 45 client│  │ 32 client│  │ 28 client│               │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │ Analista │  │ Analista │  │ Analista │               │  │
│  │  │    D     │  │    E     │  │    F     │               │  │
│  │  │ $180K    │  │ $150K    │  │ $120K    │               │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  │                                                            │  │
│  │  [Más analistas...]                                       │  │
│  │                                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Leyenda:                                                        │
│  - Tamaño del rectángulo = [¿Monto total? / ¿Cantidad clientes?]│
│  - Color = Diferencia visual por analista                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### **Datos a Mostrar por Rectángulo:**
- **Label:** Nombre del Analista
- **Valor Principal:** Monto total de morosidad O cantidad de clientes (pendiente confirmación)
- **Información Adicional:**
  - Cantidad de clientes en mora
  - Monto promedio de morosidad por cliente
  - Días promedio de atraso (opcional)

#### **Criterio de Inclusión:**
- ✅ **Todos los clientes con morosidad desde 1 día**
- ✅ Incluye clientes con:
  - 1 cuota atrasada (1 día o más)
  - 2 cuotas atrasadas
  - 3+ cuotas atrasadas
- ✅ Suma total de `monto_mora` de todas las cuotas vencidas no pagadas

#### **Filtros que Aplican:**
- ✅ Concesionario
- ✅ Modelo de vehículo
- ✅ Rango de fechas
- ✅ Período de análisis
- ⚠️ **Nota:** El filtro por analista no aplica aquí (la agrupación ES por analista)

#### **Interactividad:**
- **Hover:** Mostrar tooltip con detalles:
  - Nombre del analista
  - Monto total de morosidad
  - Cantidad de clientes en mora
  - Monto promedio por cliente
  - Días promedio de atraso
- **Click:** (Opcional) Abrir detalle del analista en modal o navegar a vista detallada

#### **Colores:**
- Cada analista con color distintivo
- Paleta de colores vibrantes y contrastantes
- Los rectángulos más grandes (mayor morosidad) pueden tener colores más saturados

#### **APIs Necesarias:**

**Endpoint: Morosidad por Analista**
```
GET /api/v1/dashboard/morosidad-por-analista?
  fecha_corte=YYYY-MM-DD  // Fecha de referencia para calcular morosidad
  concesionario=...
  modelo=...
  fecha_inicio=YYYY-MM-DD  // Para filtrar préstamos/cuotas
  fecha_fin=YYYY-MM-DD

Response:
{
  analistas: [
    {
      analista_id: 1,
      analista_nombre: "Juan Pérez",
      monto_total_morosidad: 450000.00,
      cantidad_clientes_mora: 45,
      monto_promedio_por_cliente: 10000.00,
      dias_promedio_atraso: 15.5,
      cantidad_cuotas_vencidas: 67,
      distribucion_morosidad: {
        "1_cuota_atrasada": 20,
        "2_cuotas_atrasadas": 15,
        "3mas_cuotas_atrasadas": 10
      }
    },
    ...
  ],
  total_general: {
    monto_total_morosidad: 1850000.00,
    cantidad_total_clientes: 180,
    cantidad_analistas: 12
  },
  fecha_corte: "2024-01-15"
}
```

---

## ✅ DECISIONES CONFIRMADAS - COMPONENTE 3

### **1. Métrica del Tamaño del Rectángulo:**
✅ **RESPUESTA SUGERIDA:** **A) Monto total de morosidad del analista (en dólares)**

**Justificación:**
- El monto en dólares es la métrica más importante para tomar decisiones financieras
- Visualmente más impactante y fácil de interpretar
- Permite identificar rápidamente qué analistas tienen mayor exposición de riesgo

**Implementación:**
- Tamaño del rectángulo = Proporcional al monto total de morosidad
- Rectángulos más grandes = Mayor morosidad = Mayor atención requerida

### **2. Información en el Label:**
✅ **RESPUESTA SUGERIDA:** **D) Nombre + monto + cantidad de clientes (formato compacto)**

**Justificación:**
- Muestra toda la información relevante de un vistazo
- Formato: "Nombre Analista\n$450K\n45 clientes"
- Legible y completo sin saturar visualmente

**Implementación:**
- Primera línea: Nombre del analista (fuente más grande, bold)
- Segunda línea: Monto formateado (ej: "$450K" o "$450,000")
- Tercera línea: Cantidad de clientes (ej: "45 clientes" - fuente más pequeña)

### **3. Color del Rectángulo:**
✅ **RESPUESTA SUGERIDA:** **B) Nivel de morosidad (ej: rojo = alta, amarillo = media, verde = baja)**

**Justificación:**
- Proporciona información adicional además del tamaño
- Código de colores intuitivo: Rojo = Alerta, Amarillo = Atención, Verde = Bueno
- Facilita identificación rápida de analistas con mayor riesgo

**Implementación:**
- **Rojo (Alta):** Morosidad > 75% del promedio o > umbral crítico
- **Amarillo/Naranja (Media):** Morosidad entre 50-75% del promedio
- **Verde (Baja):** Morosidad < 50% del promedio
- Cálculo basado en desviación estándar o percentiles

### **4. Ubicación del Componente:**
✅ **RESPUESTA SUGERIDA:** **E) Compartir modal con Componente 4 (Donut)**

**Justificación:**
- Ambos componentes muestran distribuciones (por analista vs por concesionario)
- Permite comparación visual entre ambos análisis
- Mejor uso del espacio del modal
- Pueden compartir filtros y actualizarse juntos

**Implementación:**
- Modal: "Distribución de Préstamos y Morosidad"
- Layout: Treemap a la izquierda, Donut a la derecha
- O tabs para alternar entre vistas
- Filtros compartidos en header

### **5. Definición de "Morosidad desde 1 día":**
✅ **RESPUESTA SUGERIDA:** **A) Clientes con cuotas cuya fecha de vencimiento fue hace 1 día o más (ya vencidas)**

**Justificación:**
- Morosidad real: cuotas que ya deberían haberse pagado
- Incluye desde 1 día hasta cualquier cantidad de días vencidos
- Más relevante para gestión de cobranza que proyecciones preventivas

**Implementación:**
```sql
-- Cuotas vencidas (1 día o más)
WHERE fecha_pago < CURDATE()
AND estado != 'PAGADA'
```

### **6. Agrupación Adicional:**
✅ **RESPUESTA SUGERIDA:** **B) Analista → Cliente (jerárquico, hacer drill-down)**

**Justificación:**
- Permite profundizar desde analista a clientes específicos
- Jerarquía natural: Analista gestiona múltiples clientes
- Facilita análisis detallado cuando se necesita

**Implementación:**
- Click en rectángulo de analista → Expandir a rectángulos de clientes
- O abrir modal con lista de clientes en mora de ese analista
- Opción de drill-down jerárquico (nivel 1: Analista, nivel 2: Cliente)

### **7. Interactividad:**
✅ **RESPUESTA SUGERIDA:** **B) Abrir modal con detalle del analista (lista de clientes en mora)**

**Justificación:**
- Proporciona información accionable inmediatamente
- Permite ver qué clientes específicos están en mora
- Facilita seguimiento y gestión de cobranza

**Implementación:**
- Modal de detalle incluye:
  - Tabla con lista de clientes en mora del analista
  - Columnas: Cliente, Monto Morosidad, Días Atraso, Cuotas Vencidas, Concesionario
  - Filtros adicionales específicos del detalle
  - Botón de exportación
  - Opción de filtrar otros gráficos del dashboard por ese analista (opcional)

---

## 📝 NOTAS ADICIONALES

- El treemap debe ser **interactivo** con tooltips informativos
- Debe actualizarse automáticamente al cambiar filtros
- Considerar mostrar solo los top N analistas si son muchos (con opción "Ver todos")
- El cálculo de morosidad debe considerar todas las cuotas vencidas no pagadas desde 1 día de atraso

---

## 🥧 COMPONENTE 4: Gráfico de Pastel (Donut) - Préstamos por Concesionario

### **Descripción:**
Gráfico tipo **Donut/Pie Chart** que representa la distribución de préstamos agrupados por concesionario, expresado en **porcentajes** del total.

### **Funcionalidad:**
- **Agrupación:** Por Concesionario
- **Métrica:** Cantidad de préstamos o monto total (porcentajes)
- **Visualización:** Gráfico de donut/pastel con segmentos proporcionales
- **Expresión:** Porcentajes visibles en cada segmento

### **Especificaciones Técnicas:**

#### **Tipo de Gráfico:**
- **Donut Chart** o **Pie Chart** (preferiblemente donut con espacio central)
- Segmentos coloreados distintivamente por concesionario
- Etiquetas con porcentajes visibles

#### **Estructura:**
```
┌──────────────────────────────────────────────────────────────────┐
│ PRÉSTAMOS POR CONCESIONARIO                                     │
│ [Filtros integrados]                                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              DONUT CHART                                  │  │
│  │                                                            │  │
│  │         ┌──────────────┐                                  │  │
│  │         │   TOTAL      │                                  │  │
│  │         │  1,245       │                                  │  │
│  │         │ Préstamos    │                                  │  │
│  │         └──────────────┘                                  │  │
│  │                                                            │  │
│  │    ┌──────┐    ┌──────┐    ┌──────┐                      │  │
│  │    │ 25%  │    │ 18%  │    │ 15%  │                      │  │
│  │    │Conc. │    │Conc. │    │Conc. │                      │  │
│  │    │  A   │    │  B   │    │  C   │                      │  │
│  │    └──────┘    └──────┘    └──────┘                      │  │
│  │                                                            │  │
│  │    [Más segmentos...]                                     │  │
│  │                                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Leyenda:                                                        │
│  ┌─────┐ Concesionario A     25%  (311 préstamos)            │
│  ┌─────┐ Concesionario B     18%  (224 préstamos)            │
│  ┌─────┐ Concesionario C     15%  (187 préstamos)            │
│  ┌─────┐ Concesionario D     12%  (149 préstamos)            │
│  ┌─────┐ Concesionario E     10%  (125 préstamos)            │
│  ┌─────┐ Otros               20%  (249 préstamos)            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### **Datos a Mostrar:**
- **Por Segmento:**
  - Nombre del Concesionario
  - Porcentaje (grande y visible)
  - Cantidad de préstamos (opcional, pequeño)
  - Monto total (opcional)

- **En el Centro (Donut):**
  - Total de préstamos
  - O monto total financiado

#### **Cálculo de Porcentajes:**
```
% Concesionario = (Préstamos del Concesionario / Total Préstamos) * 100
```

#### **Agrupación de Segmentos Pequeños:**
- Si hay muchos concesionarios, agrupar los más pequeños en "Otros"
- Mostrar solo los top N concesionarios + "Otros"
- Ejemplo: Top 5 + "Otros"

#### **Filtros que Aplican:**
- ✅ Analista
- ✅ Modelo de vehículo
- ✅ Rango de fechas
- ✅ Estado de préstamo (Aprobado, Pendiente, etc.)
- ⚠️ **Nota:** El filtro por concesionario no aplica aquí (la agrupación ES por concesionario)

#### **Interactividad:**
- **Hover:**
  - Resaltar segmento
  - Mostrar tooltip con:
    - Nombre del concesionario
    - Porcentaje exacto
    - Cantidad de préstamos
    - Monto total (opcional)

- **Click:** (Opcional)
  - Filtrar otros gráficos del dashboard por ese concesionario
  - O abrir detalle del concesionario

#### **Colores:**
- Cada concesionario con color distintivo
- Paleta de colores vibrantes y contrastantes
- Colores consistentes (siempre el mismo concesionario = mismo color)

#### **Opciones de Visualización:**
- **Vista 1:** Solo porcentajes
- **Vista 2:** Porcentajes + cantidad de préstamos
- **Vista 3:** Porcentajes + monto total
- Toggle para cambiar entre vistas (opcional)

#### **APIs Necesarias:**

**Endpoint: Préstamos por Concesionario**
```
GET /api/v1/dashboard/prestamos-por-concesionario?
  analista=...
  modelo=...
  fecha_inicio=YYYY-MM-DD
  fecha_fin=YYYY-MM-DD
  estado=APROBADO  // Opcional: filtro por estado

Response:
{
  concesionarios: [
    {
      concesionario_id: 1,
      concesionario_nombre: "Concesionario A",
      cantidad_prestamos: 311,
      monto_total: 12450000.00,
      porcentaje: 25.0,
      porcentaje_formateado: "25.0%"
    },
    {
      concesionario_id: 2,
      concesionario_nombre: "Concesionario B",
      cantidad_prestamos: 224,
      monto_total: 8960000.00,
      porcentaje: 18.0,
      porcentaje_formateado: "18.0%"
    },
    ...
  ],
  total_general: {
    cantidad_total_prestamos: 1245,
    monto_total_financiado: 49800000.00,
    cantidad_concesionarios: 8
  },
  otros: {
    // Si se agrupan los pequeños
    cantidad_prestamos: 249,
    monto_total: 9960000.00,
    porcentaje: 20.0,
    cantidad_concesionarios_agrupados: 15
  }
}
```

---

## ✅ DECISIONES CONFIRMADAS - COMPONENTE 4

### **1. Métrica del Porcentaje:**
✅ **RESPUESTA SUGERIDA:** **C) Ambas opciones (toggle para cambiar)**

**Justificación:**
- Diferentes métricas proporcionan diferentes perspectivas
- Cantidad de préstamos: muestra volumen de operaciones
- Monto total: muestra impacto financiero
- Toggle permite cambiar según necesidad de análisis

**Implementación:**
- Toggle/switch en el header del gráfico: "Cantidad" ↔ "Monto"
- Por defecto: Monto total (más relevante financieramente)
- Los porcentajes se recalculan automáticamente al cambiar

### **2. Información en Cada Segmento:**
✅ **RESPUESTA SUGERIDA:** **D) Porcentaje + nombre + cantidad (todo junto)**

**Justificación:**
- Información completa y concisa
- Formato compacto pero completo
- Legible sin saturar visualmente

**Implementación:**
- **En segmentos grandes (>10%):**
  - Línea 1: Nombre del concesionario (abreviado si es largo)
  - Línea 2: Porcentaje grande (ej: "25%")
  - Línea 3: Cantidad pequeña (ej: "311 préstamos" o "$12.4M")
- **En segmentos pequeños (<10%):** Solo porcentaje (nombre en tooltip)

### **3. Centro del Donut:**
✅ **RESPUESTA SUGERIDA:** **C) Ambos (uno arriba, otro abajo)**

**Justificación:**
- Muestra información completa del total
- Facilita comprensión rápida del panorama general
- Espacio central permite mostrar ambas métricas sin saturar

**Implementación:**
- Centro del donut:
  - Línea superior: Total de préstamos (número grande, bold)
  - Texto pequeño: "Préstamos"
  - Línea inferior: Monto total financiado (número grande, bold)
  - Texto pequeño: "$XX.XM" o formateado

### **4. Agrupación de Segmentos:**
✅ **RESPUESTA SUGERIDA:** **C) Top N con porcentaje > X% (ej: >5%) + "Otros"**

**Justificación:**
- Mantiene legibilidad sin saturar con muchos segmentos
- Los segmentos pequeños se agrupan automáticamente
- Proporciona flexibilidad basada en datos reales

**Implementación:**
- Mostrar segmentos con porcentaje > 5% individualmente
- Resto agrupar en "Otros"
- Configurable: Usuario puede cambiar umbral (3%, 5%, 7%, 10%)
- Opción "Mostrar todos" para ver todos los segmentos (si son pocos)

### **5. Ubicación del Componente:**
✅ **RESPUESTA SUGERIDA:** **E) Compartir modal con Componente 3 (Treemap)**

**Justificación:**
- Ambos componentes muestran distribuciones (por analista vs por concesionario)
- Permite comparación visual entre ambos análisis
- Mejor uso del espacio del modal
- Pueden compartir filtros y actualizarse juntos

**Implementación:**
- Modal: "Distribución de Préstamos y Morosidad"
- Layout: Treemap a la izquierda, Donut a la derecha
- O tabs para alternar entre vistas
- Filtros compartidos en header

### **6. Tipo de Donut:**
✅ **RESPUESTA SUGERIDA:** **A) Donut (con espacio central)**

**Justificación:**
- Espacio central útil para mostrar totales
- Más moderno visualmente
- Permite mejor uso del espacio para información

### **7. Interactividad:**
✅ **RESPUESTA SUGERIDA:** **C) Abrir modal con detalle del concesionario**

**Justificación:**
- Consistente con Componente 3 (analista)
- Proporciona información detallada accionable
- Permite análisis profundo cuando se necesita

**Implementación:**
- Modal de detalle incluye:
  - Tabla con lista de préstamos del concesionario
  - Columnas: ID Préstamo, Cliente, Monto, Estado, Fecha Aprobación
  - Gráficos adicionales: Evolución temporal, Por analista, etc.
  - Filtros adicionales
  - Botón de exportación

---

## 📝 NOTAS ADICIONALES COMPONENTE 4

- El gráfico debe actualizarse automáticamente al cambiar filtros
- Los porcentajes deben sumar 100% (redondeo inteligente si es necesario)
- Considerar animaciones suaves al cargar/cambiar datos
- Posibilidad de exportar como imagen (opcional)

---

## 📊 COMPONENTE 5: Gráfico de Barras Divergentes - Distribución de Préstamos

### **Descripción:**
Gráfico tipo **Bar Chart Divergente** (barras horizontales que se extienden desde un eje central) que muestra la distribución de préstamos según diferentes categorías y dimensiones.

### **Funcionalidad:**
- **Formato:** Barras horizontales divergentes (izquierda y derecha desde eje central)
- **Categorías:** Por estado, por tipo, por modelo, etc. (pendiente confirmación)
- **Visualización:** Barras proporcionales con porcentajes o valores absolutos
- **Colores:** Dos colores diferenciados para cada lado

### **Especificaciones Técnicas:**

#### **Tipo de Gráfico:**
- **Diverging Bar Chart** (barras horizontales)
- Eje Y: Categorías (ej: Estados, Tipos, Modelos)
- Eje X: Porcentajes o valores (centro = 0%)
- Barras extendiéndose a izquierda y derecha

#### **Estructura:**
```
┌──────────────────────────────────────────────────────────────────┐
│ DISTRIBUCIÓN DE PRÉSTAMOS                                       │
│ [Filtros integrados]                                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         DIVERGING BAR CHART                               │  │
│  │                                                            │  │
│  │  │         │         │         │         │             │  │
│  │  │   50%   │   25%   │   0%    │   25%   │   50%      │  │
│  │  │         │         │         │         │             │  │
│  │  │─────────┼─────────┼─────────┼─────────┼─────────│    │  │
│  │  │         │         │         │         │         │    │  │
│  │A│███████   │         │         │         │         │    │  │
│  │P│ (45%)    │         │         │         │         │    │  │
│  │R│          │         │         │         │         │    │  │
│  │O│          │         │   0%    │         │  ███████│    │  │
│  │B│          │         │         │         │  (55%)  │    │  │
│  │A│          │         │         │         │         │    │  │
│  │D│          │         │         │         │         │    │  │
│  │O│──────────┼─────────┼─────────┼─────────┼─────────│    │  │
│  │  │         │         │         │         │         │    │  │
│  │A│█████     │         │         │         │         │    │  │
│  │C│ (35%)    │         │         │         │         │    │  │
│  │T│          │         │   0%    │         │  ███████│    │  │
│  │I│          │         │         │         │  (65%)  │    │  │
│  │V│          │         │         │         │         │    │  │
│  │O│──────────┼─────────┼─────────┼─────────┼─────────│    │  │
│  │  │         │         │         │         │         │    │  │
│  │F│███       │         │         │         │         │    │  │
│  │I│ (15%)    │         │         │         │         │    │  │
│  │N│          │         │   0%    │         │  ███████│    │  │
│  │A│          │         │         │         │  (85%)  │    │  │
│  │L│          │         │         │         │         │    │  │
│  │  │         │         │         │         │         │    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Leyenda:                                                        │
│  ┌─────┐ Categoría A (Izquierda)                              │
│  ┌─────┐ Categoría B (Derecha)                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### **Opciones de Distribución (Pregunta):**

**Opción A: Por Estado**
- Izquierda: Préstamos Aprobados
- Derecha: Préstamos Finalizados
- Otras combinaciones de estados

**Opción B: Por Tipo de Producto**
- Izquierda: Tipo A (ej: Vehículos nuevos)
- Derecha: Tipo B (ej: Vehículos usados)

**Opción C: Por Período**
- Izquierda: Mes anterior
- Derecha: Mes actual
- Comparativa temporal

**Opción D: Por Género/Cliente**
- Izquierda: Clientes Femeninos
- Derecha: Clientes Masculinos

**Opción E: Por Analista**
- Izquierda: Analista A
- Derecha: Analista B
- (O top analistas vs otros)

**Opción F: Personalizado**
- Otra dimensión según necesidad

#### **Datos a Mostrar:**
- **En cada barra:**
  - Porcentaje o valor absoluto
  - Nombre de la categoría
  - Color distintivo

- **Eje central:**
  - Línea vertical en 0% o valor neutral
  - Marca clara de referencia

#### **Filtros que Aplican:**
- ✅ Analista
- ✅ Concesionario
- ✅ Modelo de vehículo
- ✅ Rango de fechas
- ✅ Período de análisis

#### **Interactividad:**
- **Hover:**
  - Resaltar barra completa
  - Mostrar tooltip con:
    - Categoría
    - Valor exacto (porcentaje y absoluto)
    - Cantidad de préstamos

- **Click:** (Opcional)
  - Filtrar otros gráficos por esa categoría
  - O abrir detalle de la categoría

#### **Colores:**
- Dos colores principales (uno para cada lado)
- Variaciones de saturación para diferentes categorías
- Colores consistentes y accesibles

#### **APIs Necesarias:**

**Endpoint: Distribución de Préstamos**
```
GET /api/v1/dashboard/distribucion-prestamos?
  tipo_distribucion=estado|tipo|periodo|analista|...  // Tipo de distribución
  analista=...
  concesionario=...
  modelo=...
  fecha_inicio=YYYY-MM-DD
  fecha_fin=YYYY-MM-DD

Response (Ejemplo - Por Estado):
{
  distribucion: [
    {
      categoria: "Aprobado",
      lado: "izquierda",  // o "derecha"
      cantidad_prestamos: 560,
      porcentaje: 45.0,
      monto_total: 22400000.00
    },
    {
      categoria: "Finalizado",
      lado: "derecha",
      cantidad_prestamos: 685,
      porcentaje: 55.0,
      monto_total: 27400000.00
    }
  ],
  categorias_agrupadas: [
    {
      nombre: "APROBADO",
      subcategorias: [
        {
          nombre: "Aprobado Activo",
          cantidad: 450,
          porcentaje: 36.0,
          lado: "izquierda"
        },
        {
          nombre: "Aprobado Inactivo",
          cantidad: 110,
          porcentaje: 9.0,
          lado: "izquierda"
        }
      ]
    },
    {
      nombre: "FINALIZADO",
      subcategorias: [
        {
          nombre: "Finalizado Normal",
          cantidad: 580,
          porcentaje: 46.5,
          lado: "derecha"
        },
        {
          nombre: "Finalizado Cancelado",
          cantidad: 105,
          porcentaje: 8.5,
          lado: "derecha"
        }
      ]
    }
  ],
  total_general: {
    cantidad_total: 1245,
    monto_total: 49800000.00
  }
}
```

---

## ✅ DECISIONES CONFIRMADAS - COMPONENTE 5

### **1. Tipo de Distribución:**
✅ **RESPUESTA SUGERIDA:** **A) Por Estado (Aprobado vs Finalizado) + Opción de cambiar**

**Justificación:**
- Distribución más relevante para gestión de préstamos
- Estados claros y accionables
- Permite ver balance entre cartera activa y finalizada

**Implementación:**
- **Vista Principal:** Por Estado
  - Izquierda: Aprobado (Activo + Inactivo)
  - Derecha: Finalizado
- **Selector/Toggle para cambiar a:**
  - Por Tipo de Producto (si aplica)
  - Por Período (Mes Anterior vs Mes Actual) - Comparativa temporal
  - Por Analista (Top Analistas vs Otros)

### **2. Subcategorías:**
✅ **RESPUESTA SUGERIDA:** **C) Múltiples categorías en cada lado (ej: Aprobado Activo, Aprobado Inactivo)**

**Justificación:**
- Proporciona mayor granularidad y detalle
- Permite ver desglose completo dentro de cada grupo principal
- Más informativo para toma de decisiones

**Implementación:**
- **Lado Izquierda (Aprobado):**
  - Aprobado Activo
  - Aprobado Inactivo
- **Lado Derecha (Finalizado):**
  - Finalizado Normal
  - Finalizado Cancelado
- Cada subcategoría con su propia barra apilada o agrupada

### **3. Métrica del Eje X:**
✅ **RESPUESTA SUGERIDA:** **D) Opción de cambiar entre ellas (toggle)**

**Justificación:**
- Diferentes métricas para diferentes análisis
- Porcentajes: Para ver proporciones relativas
- Cantidad: Para ver volumen absoluto
- Montos: Para ver impacto financiero

**Implementación:**
- Toggle en header: "Porcentajes" ↔ "Cantidad" ↔ "Monto"
- Por defecto: Porcentajes (más fácil de interpretar en gráfico divergente)
- El eje X se ajusta automáticamente según selección

### **4. Ubicación del Componente:**
✅ **RESPUESTA SUGERIDA:** **C) En un nuevo modal independiente (Componente 5)**

**Justificación:**
- Gráfico divergente necesita espacio para ser legible
- Permite enfoque completo en la visualización
- Consistente con otros componentes del sistema

### **5. Número de Categorías:**
✅ **RESPUESTA SUGERIDA:** **B) Múltiples categorías (cada una con sus barras izquierda/derecha)**

**Justificación:**
- Permite comparar múltiples dimensiones simultáneamente
- Más información en un solo gráfico
- Eje Y puede mostrar: Estados, Tipos, Modelos, etc.

**Implementación:**
- Eje Y con múltiples filas (cada fila = una categoría)
- Cada fila tiene barras izquierda y derecha
- Ejemplo:
  - Fila 1: "Por Estado" → Izquierda: Aprobado, Derecha: Finalizado
  - Fila 2: "Por Tipo" → Izquierda: Nuevo, Derecha: Usado
  - Fila 3: "Por Período" → Izquierda: Mes Anterior, Derecha: Mes Actual

### **6. Orientación:**
✅ **RESPUESTA SUGERIDA:** **A) Barras horizontales (categorías en eje Y, valores en eje X)**

**Justificación:**
- Más legible para múltiples categorías
- Facilita lectura de etiquetas (no rotadas)
- Estándar para gráficos divergentes
- Mejor para comparar visualmente barras

### **7. Comparativa:**
✅ **RESPUESTA SUGERIDA:** **A) Sí (ej: Aprobado vs Finalizado)**

**Justificación:**
- Gráfico divergente es ideal para comparar dos grupos opuestos
- Visualización clara de balance entre categorías
- Fácil interpretación: izquierda vs derecha

**Implementación:**
- Comparativa principal: Aprobado (izq) vs Finalizado (der)
- Puede configurarse para otras comparativas según necesidad

---

## 📝 NOTAS ADICIONALES COMPONENTE 5

- El gráfico debe actualizarse automáticamente al cambiar filtros
- Los porcentajes deben ser claros y legibles
- Considerar animaciones suaves al cargar/cambiar datos
- Si hay muchas categorías, considerar scroll vertical o agrupación
- El eje central debe ser claramente visible

---

## 📈 COMPONENTE 6: Líneas de Tendencia - Cuentas por Cobrar y Cuotas en Días

### **Descripción:**
Gráfico tipo **Line Chart** (líneas de tendencia) que muestra **Cuentas por Cobrar** y **Cuotas en Días**, con dos proyecciones:
1. **Proyección Diaria:** Proyectados en el mes actual (por día)
2. **Proyección Mensual:** Por mes

### **Funcionalidad:**
- **Tendencia Actual:** Datos históricos reales
- **Proyección Diaria:** Estimación día a día para el mes actual
- **Proyección Mensual:** Estimación mensual para los próximos meses
- **Actualización Automática:** Se actualiza cuando se generan nuevos créditos y se actualizan amortizaciones

### **Especificaciones Técnicas:**

#### **Tipo de Gráfico:**
- **Multi-Line Chart** (múltiples líneas de tendencia)
- Líneas sólidas para datos reales
- Líneas punteadas para proyecciones
- Marcadores en puntos de datos

#### **Estructura:**
```
┌──────────────────────────────────────────────────────────────────┐
│ CUENTAS POR COBRAR Y CUOTAS EN DÍAS - TENDENCIAS                │
│ [Filtros integrados]                                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LINE CHART - TENDENCIAS                     │  │
│  │                                                            │  │
│  │  400K│                                            ╱        │  │
│  │      │                                      ╱  ╱           │  │
│  │  300K│                                ╱  ╱  ╱              │  │
│  │      │                          ╱  ╱  ╱  ╱                 │  │
│  │  200K│                    ╱  ╱  ╱  ╱                       │  │
│  │      │              ╱  ╱  ╱  ╱                             │  │
│  │  100K│        ╱  ╱  ╱  ╱                                   │  │
│  │      │  ╱  ╱  ╱                                             │  │
│  │    0 │──────────────────────────────────────────────       │  │
│  │      │ Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec     │  │
│  │      │                                                    │  │
│  │  Leyenda:                                                  │  │
│  │  ─── Cuentas por Cobrar (Real)                            │  │
│  │  ─ ─ Cuentas por Cobrar (Proyección Mensual)             │  │
│  │  ─── Cuotas en Días (Real)                                │  │
│  │  ─ ─ Cuotas en Días (Proyección Diaria Mes Actual)        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [Panel de Proyecciones Detalladas]                             │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ Proyección Mes      │  │ Proyección Diaria   │              │
│  │ Actual              │  │ Mes Actual         │              │
│  │                     │  │                     │              │
│  │ Ene: $450K          │  │ Día 15: $125K      │              │
│  │ Feb: $520K          │  │ Día 20: $180K      │              │
│  │ Mar: $580K          │  │ Día 25: $220K      │              │
│  │ ...                 │  │ ...                 │              │
│  └─────────────────────┘  └─────────────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

#### **Series de Datos (4 líneas):**

1. **Cuentas por Cobrar - Real** (Línea sólida azul)
   - Datos históricos reales
   - Desde fecha inicio hasta fecha actual

2. **Cuentas por Cobrar - Proyección Mensual** (Línea punteada azul)
   - Proyección mes a mes
   - A partir del mes actual hasta N meses adelante

3. **Cuotas en Días - Real** (Línea sólida verde)
   - Días promedio de cuotas por cobrar (datos históricos)
   - Desde fecha inicio hasta fecha actual

4. **Cuotas en Días - Proyección Diaria Mes Actual** (Línea punteada verde)
   - Proyección día a día para el mes actual
   - Basado en tendencia y nuevos créditos

#### **Definiciones:**

**Cuentas por Cobrar:**
- Suma de cuotas pendientes de pago (capital_pendiente + interes_pendiente + monto_mora)
- Total de dinero que se espera recibir de clientes

**Cuotas en Días:**
- **DEFINICIÓN CONFIRMADA:** Contar desde todas las amortizaciones las cuotas que se deben pagar por día
- Agrupar todas las cuotas por fecha de vencimiento
- Mostrar conteo diario de cuotas que vencen cada día
- Incluye: cuotas pendientes y vencidas (no pagadas)
- Métrica: cantidad de cuotas que vencen cada día del período analizado

#### **Proyecciones:**

**Proyección Diaria:**
- **Configurable confirmado:** Puede configurarse para:
  - Mes actual completo (por defecto)
  - Próximos N días (7, 14, 30, 60 días - selector)
  - Hasta fin del año
  - Rango personalizado (fecha inicio - fecha fin)
- Considera:
  - Tendencia histórica del mes
  - Nuevos créditos generados
  - Amortizaciones actualizadas
  - Tasa de crecimiento esperada

**Proyección Mensual:**
- Calcula mes a mes para los próximos **6 meses** (confirmado)
- Puede configurarse para otros períodos si se requiere
- Considera:
  - Tendencia histórica mensual
  - Tasa de crecimiento promedio
  - Estacionalidad (si aplica)
  - Nuevos créditos proyectados

#### **Actualización Automática:**
- ✅ **Cuando se genera un nuevo crédito:**
  - Se recalcula la proyección considerando el nuevo monto
  - Se actualiza el total de cuentas por cobrar

- ✅ **Cuando se actualizan amortizaciones:**
  - Se recalcula cuotas en días
  - Se ajusta proyección según nuevos vencimientos
  - Se actualizan las estimaciones

- ✅ **Actualización en tiempo real:**
  - **Polling confirmado:** Cada 10 minutos por defecto (configurable: 5, 10, 15, 30 min)
  - Refresh manual con botón siempre disponible
  - Indicador visual de última actualización y próxima actualización

#### **Filtros que Aplican:**
- ✅ Analista
- ✅ Concesionario
- ✅ Modelo de vehículo
- ✅ Rango de fechas (para datos históricos)
- ✅ Período de proyección (cuántos meses adelante mostrar)

#### **Interactividad:**
- **Hover:**
  - Mostrar tooltip con:
    - Fecha/período
    - Valor real vs proyectado
    - Diferencia (si aplica)
    - Fuente del dato (real vs proyección)

- **Click:** (Opcional)
  - Ver detalle del período
  - Ver desglose de cuentas por cobrar
  - Ver lista de cuotas

- **Zoom/Pan:**
  - Zoom en rangos de fechas específicos
  - Pan para navegar el tiempo

#### **Colores y Estilos:**
**Según tipo de gráfico confirmado:**

**Line Chart (este componente):**
- **Cuentas por Cobrar Real:** Azul sólido (`#3b82f6`) con marcadores
- **Cuentas por Cobrar Proyección:** Azul punteado (`#3b82f6` dashed) + zona sombreada
- **Cuotas en Días Real:** Verde sólido (`#10b981`) con marcadores
- **Cuotas en Días Proyección:** Verde punteado (`#10b981` dashed) + zona sombreada
- **Línea Divisoria:** Línea vertical gris marcando fin de datos reales
- **Meta (si aplica):** Línea horizontal naranja (`#f59e0b`)
- **Comparativa Período Anterior (si aplica):** Gris claro sólido (`#94a3b8`)

#### **Marcadores Visuales:**
- **Línea divisoria:** Entre datos reales y proyecciones
- **Zona sombreada:** Área de proyección (opcional)
- **Marcadores:** Círculos en puntos de datos importantes

#### **APIs Necesarias:**

**Endpoint 1: Datos Históricos y Proyecciones**
```
GET /api/v1/dashboard/cuentas-cobrar-tendencias?
  fecha_inicio=YYYY-MM-DD
  fecha_fin=YYYY-MM-DD
  meses_proyeccion=6  // Cuántos meses adelante proyectar (confirmado: 6 meses)
  granularidad_diaria=mes_actual|proximos_dias|fin_anio|personalizado  // Configurable
  dias_proyeccion_diaria=30  // Si proximos_dias, cuántos días
  fecha_inicio_proyeccion=YYYY-MM-DD  // Si personalizado
  fecha_fin_proyeccion=YYYY-MM-DD  // Si personalizado
  analista=...
  concesionario=...
  modelo=...

Response:
{
  datos_reales: {
    cuentas_por_cobrar: [
      {
        fecha: "2024-01-15",
        valor: 450000.00,
        tipo: "real"
      },
      ...
    ],
    cuotas_en_dias: [
      {
        fecha: "2024-01-15",
        valor: 45,  // Cantidad de cuotas que vencen este día
        monto_total: 125000.00,  // Monto total de esas cuotas
        tipo: "real"
      },
      ...
    ]
  },
  proyecciones: {
    diaria_mes_actual: [
      {
        fecha: "2024-01-16",
        cuentas_por_cobrar: 455000.00,
        cuotas_en_dias: 46.0,
        tipo: "proyeccion_diaria"
      },
      ...
    ],
    mensual: [
      {
        mes: "2024-02",
        cuentas_por_cobrar: 520000.00,
        cuotas_en_dias: 48.5,
        tipo: "proyeccion_mensual"
      },
      ...
    ]
  },
  metadatos: {
    fecha_ultima_actualizacion: "2024-01-15T10:30:00",
    proxima_actualizacion_estimada: "2024-01-15T10:40:00",  // 10 min después (polling)
    tasa_crecimiento_promedio: 5.2,
    nuevos_creditos_pendientes: 12,
    intervalo_polling_minutos: 10,  // Intervalo de polling configurado
    meta_cuentas_cobrar_mensual: 1800000.00  // Si aplica meta
  },
  metricas_adicionales: {
    meta_cuentas_cobrar: [
      {
        mes: "2024-01",
        meta: 1800000.00,
        tipo: "meta"
      },
      ...
    ],
    comparativa_anio_anterior: [
      {
        mes: "2024-01",
        valor_anio_anterior: 1650000.00,
        tipo: "comparativa"
      },
      ...
    ],
    tasa_crecimiento_mensual: [
      {
        mes: "2024-01",
        tasa: 5.2,
        tipo: "tasa_crecimiento"
      },
      ...
    ]
  }
}
```

**Endpoint 2: Actualización en Tiempo Real**
```
POST /api/v1/dashboard/cuentas-cobrar/actualizar
// Trigger para recalcular proyecciones cuando hay nuevos créditos o amortizaciones

Response:
{
  actualizado: true,
  fecha_actualizacion: "2024-01-15T10:30:00",
  cambios_detectados: {
    nuevos_creditos: 3,
    amortizaciones_actualizadas: 15
  }
}
```

#### **Cálculo de Proyecciones:**

**Proyección Diaria (Mes Actual):**
```python
# Pseudocódigo
for dia in dias_restantes_mes_actual:
    # Base: Tendencia del mes
    base = promedio_historico_mes

    # Ajuste por nuevos créditos
    nuevos_creditos_hoy = sumar_nuevos_creditos(dia)

    # Ajuste por amortizaciones actualizadas
    amortizaciones_ajuste = calcular_impacto_amortizaciones(dia)

    # Proyección
    proyeccion = base + nuevos_creditos_hoy + amortizaciones_ajuste
```

**Proyección Mensual:**
```python
# Pseudocódigo
for mes in proximos_N_meses:
    # Tendencia histórica
    tendencia = calcular_tendencia_historica()

    # Tasa de crecimiento
    tasa_crecimiento = calcular_tasa_crecimiento_promedio()

    # Estacionalidad (si aplica)
    factor_estacional = obtener_factor_estacional(mes)

    # Proyección
    proyeccion = valor_actual * (1 + tasa_crecimiento) * factor_estacional
```

---

## ✅ DECISIONES CONFIRMADAS - COMPONENTE 6

### **1. Definición de "Cuotas en Días":**
✅ **RESPUESTA:** Contar desde todas las amortizaciones las cuotas que se deben pagar por día

**Implementación:**
- Agrupar todas las cuotas por fecha de vencimiento (fecha_pago en tabla `cuotas` o `amortizacion`)
- Contar cuántas cuotas vencen cada día
- Mostrar el conteo diario de cuotas a pagar
- Incluir cuotas pendientes y vencidas

**Cálculo:**
```sql
-- Pseudocódigo SQL
SELECT
    fecha_pago as fecha,
    COUNT(*) as cuotas_por_dia,
    SUM(capital_pendiente + interes_pendiente + monto_mora) as monto_total
FROM cuotas
WHERE estado != 'PAGADA'
GROUP BY fecha_pago
ORDER BY fecha_pago
```

### **2. Período de Proyección Mensual:**
✅ **RESPUESTA:** 6 meses adelante

**Implementación:**
- Proyección mensual por defecto: 6 meses
- Configurable mediante parámetro (opcional cambiar a 3, 9, 12 meses)
- Mostrar los próximos 6 meses desde el mes actual

### **3. Actualización en Tiempo Real:**
✅ **RESPUESTA:** Polling

**Implementación:**
- Polling automático cada **10 minutos** por defecto (configurable: 5, 10, 15, 30 minutos)
- Botón de refresh manual siempre disponible
- Indicador visual de última actualización y próxima actualización

**Configuración sugerida:**
```typescript
// Intervalo de polling por defecto
const POLLING_INTERVAL = 10 * 60 * 1000; // 10 minutos

// Opciones: 5, 10, 15, 30 minutos
```

### **4. Visualización de Proyecciones:**
✅ **RESPUESTA:** Aplicar según tipo de gráfico

**Implementación por Tipo:**

**Para Line Chart (este componente):**
- **Datos Reales:** Líneas sólidas con marcadores
- **Proyecciones:** Líneas punteadas (dashed) + zona sombreada de confianza
- **Divisoria:** Línea vertical marcando donde terminan datos reales

**Para Area Chart:**
- **Datos Reales:** Área sólida
- **Proyecciones:** Área con opacidad reducida (transparente)
- **Divisoria:** Línea vertical + cambio de color sutil

**Para Bar Chart:**
- **Datos Reales:** Barras sólidas
- **Proyecciones:** Barras con patrón rayado o sombreado
- **Colores:** Mismo color pero con transparencia/patrón

### **5. Ubicación del Componente:**
✅ **RESPUESTA:** Modal

**Implementación:**
- Modal independiente (Componente 6)
- Accesible desde botón en página principal o desde menú de dashboards
- Tamaño: Grande (90% viewport o 1400px mínimo)
- Header con título y botón cerrar
- Body con scroll si es necesario

### **6. Métricas Adicionales:**
✅ **RESPUESTA:** Sugerir otras métricas si aplican

**Métricas Adicionales Sugeridas:**

1. **Meta de Cuentas por Cobrar** (Recomendado)
   - Línea horizontal o curva con meta mensual
   - Comparativa visual: real vs meta vs proyección
   - Color: Naranja/Rojo para destacar

2. **Intervalo de Confianza** (Opcional - Avanzado)
   - Zona sombreada mostrando rango mínimo-máximo de proyección
   - Basado en desviación estándar histórica
   - Útil para mostrar incertidumbre de proyección

3. **Tasa de Crecimiento** (Recomendado)
   - Mostrar tasa de crecimiento mensual/anual
   - Indicador visual: +X% o -X% con flecha
   - Color: Verde (crecimiento), Rojo (decrecimiento)

4. **Promedio Móvil** (Opcional)
   - Línea de promedio móvil (ej: promedio 3 meses)
   - Ayuda a suavizar tendencias y ver patrones

5. **Comparativa con Período Anterior** (Recomendado)
   - Mostrar datos del mismo período del año anterior
   - Línea adicional con datos históricos comparativos
   - Útil para análisis de estacionalidad

**Implementación Sugerida:**
- Implementar al menos: **Meta de Cuentas por Cobrar** y **Comparativa con Período Anterior**
- Las demás opcionales pueden agregarse posteriormente

### **7. Granularidad de Proyección Diaria:**
✅ **RESPUESTA:** Configurable

**Implementación:**
- Opción por defecto: Mes actual completo
- Selector/configuración para elegir:
  - Mes actual (día a día hasta fin de mes)
  - Próximos N días (configurable: 7, 14, 30, 60 días)
  - Hasta fin del año
  - Rango personalizado (fecha inicio - fecha fin)

**UI de Configuración:**
```
┌─────────────────────────────────────┐
│ Configurar Proyección Diaria        │
├─────────────────────────────────────┤
│ ○ Mes actual                        │
│ ○ Próximos días: [30] días          │
│ ○ Hasta fin de año                  │
│ ○ Personalizado:                    │
│   Desde: [2024-01-16]               │
│   Hasta: [2024-03-31]               │
└─────────────────────────────────────┘
```

---

## 📝 IMPLEMENTACIÓN TÉCNICA - COMPONENTE 6

### **Cálculo de "Cuotas en Días" - Definición Confirmada:**

```python
# Pseudocódigo Backend
def calcular_cuotas_por_dia(fecha_inicio, fecha_fin, filtros):
    """
    Cuenta desde todas las amortizaciones las cuotas que se deben pagar por día
    """
    query = db.query(Cuota).filter(
        Cuota.estado != 'PAGADA',
        Cuota.fecha_pago >= fecha_inicio,
        Cuota.fecha_pago <= fecha_fin
    )

    # Aplicar filtros
    query = FiltrosDashboard.aplicar_filtros_cuota(query, filtros)

    # Agrupar por fecha de vencimiento
    resultado = query.with_entities(
        Cuota.fecha_pago.label('fecha'),
        func.count(Cuota.id).label('cantidad_cuotas'),
        func.sum(
            Cuota.capital_pendiente +
            Cuota.interes_pendiente +
            Cuota.monto_mora
        ).label('monto_total')
    ).group_by(Cuota.fecha_pago).order_by(Cuota.fecha_pago).all()

    return resultado
```

### **Polling - Configuración:**

```typescript
// Frontend - Hook para polling
const POLLING_INTERVALS = {
  rapid: 5 * 60 * 1000,    // 5 minutos
  normal: 10 * 60 * 1000,  // 10 minutos (default)
  lento: 15 * 60 * 1000,   // 15 minutos
  muyLento: 30 * 60 * 1000 // 30 minutos
};

// Uso en componente
useEffect(() => {
  const interval = setInterval(() => {
    refetch();
  }, POLLING_INTERVALS.normal);

  return () => clearInterval(interval);
}, [refetch]);
```

### **Configuración de Granularidad Diaria:**

```typescript
// Componente de configuración
interface ProyeccionDiariaConfig {
  tipo: 'mes_actual' | 'proximos_dias' | 'fin_anio' | 'personalizado';
  dias?: number;  // Si es proximos_dias
  fechaInicio?: string;  // Si es personalizado
  fechaFin?: string;  // Si es personalizado
}
```

### **Visualización por Tipo de Gráfico:**

```typescript
// Line Chart - Estilos
const lineStyles = {
  real: {
    strokeWidth: 2,
    strokeDasharray: '0',  // Sólido
    marker: { fill: 'currentColor', r: 4 }
  },
  proyeccion: {
    strokeWidth: 2,
    strokeDasharray: '5 5',  // Punteado
    opacity: 0.7,
    fill: 'rgba(currentColor, 0.1)'  // Zona sombreada
  },
  meta: {
    strokeWidth: 2,
    stroke: '#f59e0b',  // Naranja
    strokeDasharray: '3 3'
  }
};
```

---

## 📝 NOTAS ADICIONALES COMPONENTE 6

- ✅ El gráfico debe mostrar claramente dónde terminan los datos reales y comienzan las proyecciones (línea divisoria vertical)
- ✅ Las proyecciones deben actualizarse automáticamente cada 10 minutos (polling)
- ✅ Indicador visual de "última actualización" y "próxima actualización" visible
- ✅ Las proyecciones deben basarse en algoritmos de tendencia (promedio móvil, regresión lineal, etc.)
- ✅ Considerar validación de proyecciones vs datos reales cuando estos estén disponibles
- ✅ **Ubicación:** Modal independiente (Componente 6)
- ✅ **Métricas adicionales:** Implementar al menos Meta y Comparativa con Período Anterior
- ✅ **Granularidad:** Configurable con selector de opciones

---

**✅ Componente 6 completamente especificado y listo para implementación** 🚀

