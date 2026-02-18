# Auditoría integral: Filtro Cliente.estado == ACTIVO en KPIs

**Fecha:** 2025-02-18  
**Alcance:** Endpoints, backend, frontend — verificación de que todos los KPIs y cálculos relacionados solo incluyen clientes con `estado = 'ACTIVO'`.

---

## 1. Resumen ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Dashboard** | ✅ Completo | 15+ endpoints con filtro ACTIVO |
| **KPIs** | ✅ Completo | kpis-principales, kpis/dashboard |
| **Reportes** | ✅ Completo | dashboard/resumen, cartera, pagos, morosidad, financiero, asesores, productos, concesionarios |
| **Pagos** | ✅ Corregido | GET /pagos/kpis y GET /pagos/stats con filtro ACTIVO |
| **Opciones filtros** | ✅ Corregido | opciones-filtros con filtro ACTIVO |
| **Cobranzas** | ℹ️ Operacional | Lista clientes atrasados — no es KPI; puede incluir INACTIVO para cobranza |
| **Frontend** | ✅ Sin cambios | Consume datos del API; no requiere filtros adicionales |

---

## 2. Endpoints auditados

### 2.1 Dashboard (`/api/v1/dashboard`)

| Endpoint | Filtro ACTIVO | Notas |
|----------|---------------|-------|
| `GET /opciones-filtros` | ✅ | Analistas, concesionarios, modelos (solo clientes ACTIVOS) |
| `GET /kpis-principales` | ✅ | total_clientes=activos, préstamos, morosidad, cuotas |
| `GET /admin` | ✅ | Evolución mensual: cartera y cobrado |
| `GET /morosidad-por-dia` | ✅ | Cartera y cobrado por día |
| `GET /proyeccion-cobro-30-dias` | ✅ | Programado y pendiente |
| `GET /monto-programado-proxima-semana` | ✅ | Monto programado |
| `GET /financiamiento-tendencia-mensual` | ✅ | Cartera por mes |
| `GET /prestamos-por-concesionario` | ✅ | Por mes y acumulado |
| `GET /prestamos-por-modelo` | ✅ | Por mes y acumulado |
| `GET /financiamiento-por-rangos` | ✅ | Bandas por total_financiamiento |
| `GET /composicion-morosidad` | ✅ | Cuotas vencidas por rango días |
| `GET /cobranzas-semanales` | ✅ | Pagos reales por semana |
| `GET /morosidad-por-analista` | ✅ | Cuotas vencidas por analista |
| `GET /evolucion-morosidad` | ✅ | Morosidad por mes |
| `GET /evolucion-pagos` | ✅ | Pagos por mes |

### 2.2 KPIs (`/api/v1/kpis`)

| Endpoint | Filtro ACTIVO | Notas |
|----------|---------------|-------|
| `GET /dashboard` | ✅ | total_prestamos, total_morosidad |

### 2.3 Reportes (`/api/v1/reportes`)

| Endpoint | Filtro ACTIVO | Notas |
|----------|---------------|-------|
| `GET /dashboard/resumen` | ✅ | total_clientes, total_prestamos, total_pagos, cartera_activa, prestamos_mora, pagos_mes |
| `GET /cartera` (datos) | ✅ | _datos_cartera: cartera_total, prestamos_activos, mora, distribuciones |
| `GET /pagos` | ✅ | total_pagos, cantidad_pagos, pagos_por_dia |
| `GET /morosidad` | ✅ | prestamos_ids desde subq con Cliente.estado |
| `GET /financiero` | ✅ | total_ingresos, cantidad_pagos, cartera, morosidad, total_desembolsado |
| `GET /asesores` | ✅ | analistas y préstamos por analista |
| `GET /productos` | ✅ | productos y préstamos por producto |
| `GET /concesionarios` | ✅ | concesionarios y préstamos por concesionario/producto |

### 2.4 Pagos (`/api/v1/pagos`)

| Endpoint | Filtro ACTIVO | Notas |
|----------|---------------|-------|
| `GET /kpis` | ✅ | montoACobrarMes, montoCobradoMes, morosidad, clientesEnMora, clientesAlDia (solo ACTIVOS) |
| `GET /stats` | ✅ | total_pagos, cuotas_pagadas, cuotas_pendientes, cuotas_atrasadas (solo ACTIVOS) |

### 2.5 Cobranzas (`/api/v1/cobranzas`)

| Endpoint | Filtro ACTIVO | Notas |
|----------|---------------|-------|
| `GET /stats` | ℹ️ No aplica | Estadísticas operativas; incluir INACTIVO puede ser deseable para cobranza |
| `GET /clientes-atrasados` | ℹ️ No aplica | Lista operativa para cobradores; ver todos los atrasados |

### 2.6 Clientes (`/api/v1/clientes`)

| Endpoint | Filtro ACTIVO | Notas |
|----------|---------------|-------|
| `GET /stats` | N/A | Devuelve desglose: activos, inactivos, finalizados (no es filtro) |
| `GET /` (listado) | Parámetro | Filtro opcional `estado` (ACTIVO, INACTIVO, etc.) |

---

## 3. Backend — Patrón aplicado

```python
# Para consultas con Prestamo:
.join(Cliente, Prestamo.cliente_id == Cliente.id)
.where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO", ...)

# Para consultas con Cuota:
.join(Prestamo, Cuota.prestamo_id == Prestamo.id)
.join(Cliente, Prestamo.cliente_id == Cliente.id)
.where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO", ...)

# Para consultas con Pago:
.join(Prestamo, Pago.prestamo_id == Prestamo.id)
.join(Cliente, Prestamo.cliente_id == Cliente.id)
.where(Cliente.estado == "ACTIVO", ...)
```

**Nota:** `Pago.prestamo_id` puede ser NULL; esos pagos se excluyen al hacer el join.

---

## 4. Frontend — Consumo de datos

| Componente | Endpoint consumido | Cambios necesarios |
|------------|-------------------|---------------------|
| `DashboardMenu` | kpis-principales, admin, morosidad-por-dia, etc. | ❌ Ninguno — recibe datos ya filtrados |
| `DashboardPagos` | pagos/kpis, pagos/stats | ❌ Ninguno — tras corregir backend |
| `ClientesList` | clientes/stats | ❌ Ninguno — stats es desglose por estado |
| `ClientesKPIs` | clientes/stats | ❌ Ninguno |
| `Reportes` | reportes/dashboard/resumen, etc. | ❌ Ninguno |
| `DashboardFiltrosPanel` | opciones-filtros | ❌ Ninguno — tras corregir opciones-filtros |

**Conclusión frontend:** No se requieren cambios. Los componentes muestran lo que devuelve el API.

---

## 5. Filtros del dashboard

Los filtros (analista, concesionario, modelo) se envían como query params a los endpoints. El backend aplica:

- `Prestamo.analista == analista`
- `Prestamo.concesionario == concesionario`
- `Prestamo.modelo_vehiculo == modelo`

**Además** debe aplicarse siempre `Cliente.estado == "ACTIVO"` en las consultas que agregan préstamos/cuotas/pagos.

---

## 6. Acciones realizadas (2025-02-18)

1. ✅ **opciones-filtros:** Añadido join con Cliente y filtro `Cliente.estado == "ACTIVO"`.
2. ✅ **pagos/kpis:** Añadido join Cliente en todas las consultas Cuota y Prestamo.
3. ✅ **pagos/stats:** Añadido join Cliente en `_q_cuotas()` y consultas relacionadas.

---

## 7. Verificación

```bash
# Probar KPIs principales
curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/dashboard/kpis-principales"

# Probar pagos KPIs (tras corrección)
curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/pagos/kpis"
```
