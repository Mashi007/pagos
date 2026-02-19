# Auditoría: Centro de Reportes (/pagos/reportes)

**Fecha:** 2025-02-19  
**URL:** https://rapicredit.onrender.com/pagos/reportes

## 1. Resumen ejecutivo

| Aspecto | Estado | Observación |
|---------|--------|-------------|
| Datos desde BD | ✅ | Todos los reportes usan `get_db` y consultas reales |
| Tablas BD usadas | `clientes`, `prestamos`, `cuotas` | Filtro: `Cliente.estado = 'ACTIVO'`, `Prestamo.estado = 'APROBADO'` |
| Exportación Excel | ✅ | Los 6 tipos tienen exportación Excel |
| Exportación PDF | ✅ | Los 6 tipos tienen exportación PDF (algunos usaban plantilla incorrecta, corregido) |
| Mock/Stub | ❌→✅ | Tabla "Reportes Generados" usaba mock; reemplazada por UI con datos reales |

## 2. Endpoints y mapeo a BD

| Endpoint | Tablas | Campos principales |
|----------|--------|---------------------|
| `GET /reportes/dashboard/resumen` | clientes, prestamos, cuotas | estado, fecha_pago, fecha_vencimiento, monto |
| `GET /reportes/cartera` | cuotas, prestamos, clientes | monto, fecha_pago, fecha_vencimiento |
| `GET /reportes/pagos` | cuotas, prestamos, clientes | fecha_pago, monto |
| `GET /reportes/morosidad` | cuotas, prestamos, clientes | fecha_vencimiento, fecha_pago, monto, analista |
| `GET /reportes/financiero` | cuotas, prestamos, clientes | fecha_pago, monto, fecha_vencimiento |
| `GET /reportes/asesores` | prestamos, clientes, cuotas | analista, monto, fecha_pago |
| `GET /reportes/productos` | prestamos, clientes, cuotas | producto, concesionario, monto |

## 3. Campos BD por reporte

### Cartera
- `Cuota.monto`, `Cuota.fecha_pago`, `Cuota.fecha_vencimiento`
- `Prestamo.id`, `Prestamo.total_financiamiento`
- `Cliente.estado`

### Pagos
- `Cuota.fecha_pago`, `Cuota.monto`
- Agrupado por `date(Cuota.fecha_pago)`

### Morosidad
- `Cuota.fecha_vencimiento`, `Cuota.fecha_pago`, `Cuota.monto`
- `Prestamo.analista`, `Prestamo.cedula`, `Prestamo.nombres`, `Prestamo.concesionario`

### Financiero
- `Cuota.monto`, `Cuota.fecha_pago`, `Cuota.fecha_vencimiento`
- `Prestamo.total_financiamiento`

### Asesores
- `Prestamo.analista`
- `Cuota.monto`, `Cuota.fecha_pago`, `Cuota.fecha_vencimiento`

### Productos
- `Prestamo.producto`, `Prestamo.concesionario`
- `Cuota.monto`, `Cuota.fecha_pago`

## 4. Exportación Excel/PDF

| Reporte | Excel | PDF |
|---------|-------|-----|
| Cartera | ✅ | ✅ |
| Pagos | ✅ | ✅ (incluye tabla pagos_por_dia) |
| Morosidad | ✅ | ✅ (plantilla específica) |
| Financiero | ✅ | ✅ (plantilla específica) |
| Asesores | ✅ | ✅ (plantilla específica) |
| Productos | ✅ | ✅ (plantilla específica) |

## 5. Nota sobre "Reportes Generados"

No existe tabla en BD para historial de reportes generados. La sección muestra los tipos disponibles con descarga bajo demanda.
