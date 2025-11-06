# 🔍 Sistema de Alertas Mejorado: BD y Campos

## ✅ Mejoras Implementadas

He mejorado el sistema de alertas para incluir información crítica sobre:
1. **Tamaño de Base de Datos** - Qué espacio ocupa la BD
2. **Tablas y Columnas Usadas** - Qué campos emplea cada query

---

## 🎯 Nuevas Funcionalidades

### 1. **Analizador de Base de Datos** (`backend/app/utils/db_analyzer.py`)

Nuevo módulo que proporciona:
- ✅ Tamaño total de la BD (MB, GB)
- ✅ Tamaño de tablas individuales
- ✅ Tamaño de índices
- ✅ Información de columnas por tabla
- ✅ Información de índices por tabla

**Funciones principales:**
- `get_database_size()` - Tamaño total de BD
- `get_table_sizes()` - Tablas más grandes
- `get_table_columns()` - Columnas de una tabla
- `get_indexes_for_table()` - Índices de una tabla
- `get_database_info()` - Información completa
- `analyze_query_tables_columns()` - Analizar query para detectar tablas/columnas

---

### 2. **Alertas Mejoradas con Información de BD**

Las alertas ahora incluyen:

#### Ejemplo de Alerta Mejorada:
```
🚨 [ALERTA] KPIs principales muy lento: 6200ms - BD: 2.5 GB - Tablas: prestamos, cuotas, clientes - Revisar índices y optimizaciones
```

**Información incluida:**
- ⏱️ Tiempo de ejecución
- 💾 Tamaño de BD (formato legible: MB/GB)
- 📊 Tablas usadas en la query
- 🔤 Columnas usadas en la query

---

### 3. **Nuevos Endpoints de Monitoreo**

#### `/api/v1/monitoring/database/info`
Información completa de la base de datos:
```bash
GET /api/v1/monitoring/database/info
```

**Respuesta:**
```json
{
  "status": "success",
  "database": {
    "database": {
      "database_name": "pagos_db",
      "size_pretty": "2.5 GB",
      "size_bytes": 2684354560,
      "size_mb": 2560.0,
      "size_gb": 2.5
    },
    "total_tables": 15,
    "total_indexes": 28,
    "largest_tables": [
      {
        "table_name": "prestamos",
        "size_pretty": "1.2 GB",
        "total_size_mb": 1228.8
      }
    ]
  }
}
```

#### `/api/v1/monitoring/database/tables/{table_name}/columns`
Columnas de una tabla específica:
```bash
GET /api/v1/monitoring/database/tables/prestamos/columns
```

**Respuesta:**
```json
{
  "status": "success",
  "table_name": "prestamos",
  "columns": [
    {
      "column_name": "fecha_aprobacion",
      "data_type": "date",
      "nullable": true
    }
  ],
  "count": 25
}
```

#### `/api/v1/monitoring/database/tables/{table_name}/indexes`
Índices de una tabla específica:
```bash
GET /api/v1/monitoring/database/tables/prestamos/indexes
```

**Respuesta:**
```json
{
  "status": "success",
  "table_name": "prestamos",
  "indexes": [
    {
      "index_name": "idx_prestamos_fecha_aprobacion_ym",
      "definition": "CREATE INDEX ...",
      "size_pretty": "45 MB",
      "size_mb": 45.2
    }
  ],
  "count": 5
}
```

#### `/api/v1/monitoring/dashboard/performance` (Mejorado)
Ahora incluye información de BD:
```bash
GET /api/v1/monitoring/dashboard/performance
```

**Nueva sección en respuesta:**
```json
{
  "database": {
    "database": {
      "size_pretty": "2.5 GB"
    },
    "total_tables": 15,
    "largest_tables": [...]
  }
}
```

---

## 📊 Alertas con Información Completa

### Estructura de Alerta Mejorada:

```json
{
  "type": "critical_query",
  "severity": "HIGH",
  "query_name": "obtener_kpis_principales",
  "execution_time_ms": 6200,
  "threshold_ms": 5000,
  "message": "Query obtener_kpis_principales tomó 6200ms (umbral: 5000ms)",
  "timestamp": "2025-01-15T10:30:00",
  "query_sql": "SELECT ...",
  "tables_used": ["prestamos", "cuotas", "clientes"],
  "columns_used": [
    "fecha_aprobacion",
    "total_financiamiento",
    "estado",
    "fecha_vencimiento"
  ]
}
```

---

## 🔍 Queries Monitoreadas con BD y Campos

### 1. `obtener_kpis_principales`
- **Tablas:** `prestamos`, `cuotas`, `clientes`
- **Columnas:** `fecha_aprobacion`, `total_financiamiento`, `estado`, `fecha_vencimiento`, `capital_pendiente`, `interes_pendiente`, `monto_mora`

### 2. `financiamiento_tendencia_nuevos`
- **Tablas:** `prestamos`
- **Columnas:** `fecha_aprobacion`, `total_financiamiento`, `estado`, `analista`, `concesionario`, `modelo_vehiculo`

### 3. `financiamiento_tendencia_cuotas`
- **Tablas:** `cuotas`, `prestamos`
- **Columnas:** `fecha_vencimiento`, `monto_cuota`, `estado`, `prestamo_id`

### 4. `financiamiento_tendencia_pagos`
- **Tablas:** `cuotas`, `prestamos`
- **Columnas:** `fecha_vencimiento`, `total_pagado`, `estado`, `prestamo_id`

### 5. `obtener_resumen_prestamos_cliente_cuotas`
- **Tablas:** `prestamos`, `cuotas`
- **Columnas:** `prestamo_id`, `capital_pendiente`, `interes_pendiente`, `monto_mora`, `fecha_vencimiento`

---

## 📝 Ejemplos de Logs Mejorados

### Alerta Normal (sin problemas):
```
📊 [kpis-principales] Completado en 450ms (query: 420ms)
```

### Alerta con BD y Campos (Query Lenta):
```
⚠️ [ALERTA] KPIs principales lento: 2300ms - BD: 2.5 GB - Tablas: prestamos, cuotas, clientes - Considerar optimización
```

### Alerta Crítica con BD y Campos:
```
🚨 [ALERTA] KPIs principales muy lento: 6200ms - BD: 2.5 GB - Tablas: prestamos, cuotas, clientes - Revisar índices y optimizaciones
```

### Alerta de Query Individual:
```
⚠️ [ALERTA] Query nuevos financiamientos lenta: 2800ms - BD: 2.5 GB - Tablas: prestamos
🚨 [ALERTA CRÍTICA] Query cuotas programadas muy lenta: 7500ms - BD: 2.5 GB - Tablas: cuotas, prestamos
```

---

## 🎯 Casos de Uso

### 1. **Problema de Configuración en Dashboard**

Cuando hay un problema, las alertas ahora muestran:
- ✅ Qué BD está usando (tamaño)
- ✅ Qué tablas está consultando
- ✅ Qué columnas está usando

**Ejemplo:**
```
🚨 [ALERTA] KPIs principales muy lento: 8500ms - BD: 2.5 GB - Tablas: prestamos, cuotas, clientes - Revisar índices y optimizaciones
```

Esto te dice:
- La BD es de 2.5 GB (puede ser grande)
- Está usando 3 tablas principales
- Necesita revisar índices en esas tablas

### 2. **Debugging de Queries Lentas**

Puedes ver:
```bash
# Ver información de BD
GET /api/v1/monitoring/database/info

# Ver columnas de una tabla
GET /api/v1/monitoring/database/tables/prestamos/columns

# Ver índices de una tabla
GET /api/v1/monitoring/database/tables/prestamos/indexes

# Ver alertas con tablas y columnas
GET /api/v1/monitoring/alerts/recent?severity=CRITICAL
```

### 3. **Análisis de Rendimiento**

El endpoint `/api/v1/monitoring/dashboard/performance` ahora incluye:
- Métricas de endpoints
- Métricas de queries
- **Información de BD** (nuevo)
- Alertas con tablas y columnas

---

## ✅ Beneficios

1. **Debugging más rápido** - Sabes exactamente qué BD y campos están involucrados
2. **Identificación de problemas** - Puedes ver si el problema es tamaño de BD o falta de índices
3. **Optimización dirigida** - Sabes qué tablas/columnas optimizar
4. **Monitoreo completo** - Información de BD, tablas, columnas e índices en un solo lugar

---

## 🔧 Próximos Pasos

1. **Monitorear alertas** después de ejecutar índices
2. **Verificar información de BD** con `/api/v1/monitoring/database/info`
3. **Analizar tablas usadas** cuando hay alertas
4. **Revisar índices** de las tablas más usadas

---

## 📊 Resumen

Ahora las alertas incluyen:
- ✅ Tamaño de BD (MB/GB)
- ✅ Tablas usadas en cada query
- ✅ Columnas usadas en cada query
- ✅ Endpoints para consultar información detallada de BD

**Resultado:** Sistema de alertas más completo y útil para debugging de problemas de configuración del dashboard.

