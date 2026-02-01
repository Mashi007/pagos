# Confirmación: Gráficos del dashboard y conexión a BD

Todos los endpoints del dashboard usan **`get_db`** (sesión de BD). Los que pueden obtener datos reales desde la tabla **`clientes`** lo hacen; el resto devuelve datos stub hasta que existan las tablas/columnas necesarias.

---

## Claridad: Tabla → Campo(s) → Gráfico

Cada gráfico queda unívocamente ligado a una tabla y a unos campos. Esta es la correspondencia.

### Gráficos con datos reales (tabla `clientes`)

| Gráfico (frontend) | Endpoint | Tabla | Campo(s) usados | Qué se calcula |
|-------------------|----------|-------|------------------|----------------|
| **KPIs principales** (Total préstamos, Créditos nuevos, Total clientes, Por estado) | `kpis-principales` | `prestamos` + `clientes` | **Total préstamos:** count(`prestamos`) donde `estado` = APROBADO. **Créditos nuevos:** suma `prestamos.total_financiamiento` solo del **mes en curso** (estado = APROBADO); indicador % = total mes presente vs mes anterior. **Clientes:** `clientes.estado`, `clientes.fecha_registro` | Total préstamos = count; Créditos nuevos = sum(total_financiamiento) mes actual; % = (mes actual − mes anterior) / mes anterior × 100 |
| **Evolución mensual** (Cartera, Cobrado, Morosidad) | `admin` | `clientes` | `fecha_registro`, `total_financiamiento` | Por cada mes: suma de `total_financiamiento` de clientes con `fecha_registro` ≤ fin de mes (cobrado/morosidad = 0 hasta tener tabla pagos) |
| **Indicadores financieros** (áreas por mes) | `financiamiento-tendencia-mensual` | `clientes` | `fecha_registro`, `total_financiamiento` | Igual que Evolución mensual: cartera por mes; resto de series en 0 |
| **Distribución por bandas de $200** | `financiamiento-por-rangos` | `clientes` | `total_financiamiento` | Conteo y suma por rangos: $0–200, $200–400, …, $1.000+ |
| **Composición de morosidad** (1–30, 31–60, 61–90, 90+ días) | `composicion-morosidad` | `clientes` | `dias_mora`, `total_financiamiento` | Por banda de `dias_mora`: conteo de clientes y suma de `total_financiamiento` |
| **Evolución de morosidad** (línea por mes) | `evolucion-morosidad` | `clientes` | `fecha_registro`, `dias_mora`, `total_financiamiento` | Por mes: suma de `dias_mora * total_financiamiento` (proxy de morosidad) |
| **Opciones de filtros** (dropdowns) | `opciones-filtros` | `clientes` | (ninguno aún) | Listas vacías hasta tener `analista`, `concesionario`, `modelo` en Cliente o tablas relacionadas |

### Gráficos stub: tabla/campo que faltan

| Gráfico (frontend) | Endpoint | Tabla que debería usarse | Campo(s) necesarios | Notas |
|-------------------|----------|---------------------------|----------------------|-------|
| **Préstamos por concesionario** | `prestamos-por-concesionario` | `clientes` (o tabla préstamos) | `concesionario` | Falta columna en `clientes` o tabla con relación cliente–concesionario |
| **Préstamos por modelo** | `prestamos-por-modelo` | `clientes` (o tabla préstamos) | `modelo` | Falta columna en `clientes` o tabla con relación cliente–modelo |
| **Cobranza planificada vs real** | `cobranza-fechas-especificas` | Tabla pagos/cobranzas | `fecha`, `monto_planificado`, `monto_real` | Requiere modelo de pagos o cobranzas |
| **Cobranzas semanales** | `cobranzas-semanales` | Tabla pagos/cobranzas | `semana`, `planificado`, `real` | Mismo origen que cobranza por fechas |
| **Morosidad por analista** | `morosidad-por-analista` | `clientes` o tabla asignación | `analista` (o tabla cliente–analista) | Falta columna o tabla de asignación |
| **Evolución de pagos** | `evolucion-pagos` | Tabla pagos | `fecha`, `cantidad`, `monto` | Requiere tabla de pagos con fecha y monto |

---

## Endpoints con **datos reales** desde BD (tabla `clientes`)

| Endpoint | Gráfico / Uso | Origen de datos |
|----------|----------------|------------------|
| `GET /api/v1/dashboard/opciones-filtros` | Filtros (analistas, concesionarios, modelos) | BD: listas vacías hasta tener columnas en Cliente |
| `GET /api/v1/dashboard/kpis-principales` | KPIs principales (préstamos, clientes, estados, créditos nuevo mes) | BD: **Total préstamos** desde `prestamos` (count donde estado = APROBADO). Resto desde `clientes` (estado, fecha_registro). **Total financiamiento** = sum(prestamos.total_financiamiento) donde estado = APROBADO |
| `GET /api/v1/dashboard/admin` | Evolución mensual (cartera, cobrado, morosidad) | BD: suma `total_financiamiento` por mes; fallback a demo si no hay datos |
| `GET /api/v1/dashboard/financiamiento-tendencia-mensual` | Indicadores financieros (áreas por mes) | BD: misma lógica que admin (cartera por mes desde Cliente) |
| `GET /api/v1/dashboard/financiamiento-por-rangos` | Bandas de $200 USD | BD: agrupa `Cliente.total_financiamiento` por rangos ($0–200, $200–400, …) |
| `GET /api/v1/dashboard/composicion-morosidad` | Composición de morosidad (1–30, 31–60, 61–90, 90+ días) | BD: agrupa `Cliente.dias_mora` y suma `total_financiamiento` por banda |
| `GET /api/v1/dashboard/evolucion-morosidad` | Evolución de morosidad por mes | BD: suma `dias_mora * total_financiamiento` por mes (proxy de morosidad) |

## Endpoints **stub** (conexión a BD, datos de ejemplo hasta tener más tablas/columnas)

| Endpoint | Gráfico / Uso | Motivo stub |
|----------|----------------|-------------|
| `GET /api/v1/dashboard/prestamos-por-concesionario` | Préstamos por concesionario | Cliente no tiene campo `concesionario`; hace falta columna o tabla relacionada |
| `GET /api/v1/dashboard/prestamos-por-modelo` | Préstamos por modelo | Cliente no tiene campo `modelo`; hace falta columna o tabla relacionada |
| `GET /api/v1/dashboard/cobranza-fechas-especificas` | Cobranza planificada vs real (días) | Requiere tabla de pagos/cobranzas |
| `GET /api/v1/dashboard/cobranzas-semanales` | Cobranzas semanales | Requiere tabla de pagos/cobranzas |
| `GET /api/v1/dashboard/morosidad-por-analista` | Morosidad por analista | Cliente no tiene campo `analista`; hace falta tabla analistas o asignación |
| `GET /api/v1/dashboard/evolucion-pagos` | Evolución de pagos (cantidad y monto) | Requiere tabla de pagos |

## Modelo `Cliente` usado para datos reales

- **Obligatorios (ya en tabla):** id, cedula, nombres, telefono, email, direccion, fecha_nacimiento, ocupacion, estado, fecha_registro, fecha_actualizacion, usuario_registro, notas  
- **Opcionales (para dashboard):** `total_financiamiento` (Numeric), `dias_mora` (Integer).  
  Si la tabla no tiene estas columnas, hay que añadirlas (migración o ALTER TABLE). Si faltan, los endpoints que las usan hacen fallback a datos de ejemplo y registran el error en logs.

## Resumen

- **Conectados a BD con datos reales (desde `clientes`):** opciones-filtros, kpis-principales, admin, financiamiento-tendencia-mensual, financiamiento-por-rangos, composicion-morosidad, evolucion-morosidad.  
- **Conectados a BD pero con datos stub:** prestamos-por-concesionario, prestamos-por-modelo, cobranza-fechas-especificas, cobranzas-semanales, morosidad-por-analista, evolucion-pagos (requieren tablas/columnas adicionales).

Todos los endpoints del dashboard reciben sesión de BD (`Depends(get_db)`). Los que pueden leer de `clientes` devuelven datos reales; el resto devuelve stub hasta implementar las tablas/columnas indicadas.

---

## Resumen por tabla: qué campos usa cada gráfico

### Tabla `prestamos`

| Campo | Tipo | Gráficos que lo usan |
|-------|------|----------------------|
| `estado` | string | KPIs: **Total préstamos** = count donde estado = `APROBADO` |
| `total_financiamiento` | numeric(14,2) | **Total financiamiento** = sum donde estado = `APROBADO`. **Créditos nuevos** = sum solo del mes en curso (estado = APROBADO) |
| `fecha_creacion` | datetime | **Créditos nuevos:** filtro por mes en curso y mes anterior para el % vs mes anterior |

Reglas de negocio: **Total financiamiento** = `total_financiamiento` de tabla `prestamos` con `estado` = aprobado. **Créditos nuevos** = suma `total_financiamiento` de `prestamos` solo del mes en curso (estado APROBADO). El indicador % en el pie compara el total del mes presente vs mes anterior.

### Tabla `clientes`

| Campo | Tipo | Gráficos que lo usan |
|-------|------|----------------------|
| `estado` | string | KPIs principales (conteo por ACTIVO, INACTIVO, FINALIZADO) |
| `fecha_registro` | datetime | KPIs principales (créditos nuevo mes), Evolución mensual, Indicadores financieros, Evolución morosidad (corte por mes) |
| `total_financiamiento` | numeric(14,2) | KPIs principales (total préstamos), Evolución mensual (cartera), Indicadores financieros, Bandas $200, Composición morosidad, Evolución morosidad |
| `dias_mora` | integer | Composición morosidad (bandas 1–30, 31–60, 61–90, 90+), Evolución morosidad (dias_mora * total_financiamiento) |
| `analista` | — | No existe; requerido para Morosidad por analista |
| `concesionario` | — | No existe; requerido para Préstamos por concesionario |
| `modelo` | — | No existe; requerido para Préstamos por modelo |

### Otras tablas (pendientes)

- **pagos / cobranzas:** Cobranza planificada vs real, Cobranzas semanales, Evolución de pagos.
