# AuditorÃ­a: Centro de Reportes (/pagos/reportes)

**Fecha:** 2025-02-19  
**URL:** https://rapicredit.onrender.com/pagos/reportes

## 1. Resumen ejecutivo

| Aspecto | Estado | ObservaciÃ³n |
|---------|--------|-------------|
| Datos desde BD | âœ… | Todos los reportes usan `get_db` y consultas reales |
| Tablas BD usadas | `clientes`, `prestamos`, `cuotas` | Filtro: `Cliente.estado = 'ACTIVO'`, `Prestamo.estado = 'APROBADO'` |
| ExportaciÃ³n Excel | âœ… | Los 6 tipos tienen exportaciÃ³n Excel |
| ExportaciÃ³n PDF | âœ… | Los 6 tipos tienen exportaciÃ³n PDF (algunos usaban plantilla incorrecta, corregido) |
| Mock/Stub | âŒâ†’âœ… | Tabla "Reportes Generados" usaba mock; reemplazada por UI con datos reales |

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

## 4. ExportaciÃ³n Excel/PDF

| Reporte | Excel | PDF |
|---------|-------|-----|
| Cartera | âœ… | âœ… |
| Pagos | âœ… | âœ… (incluye tabla pagos_por_dia) |
| Morosidad | âœ… | âœ… (plantilla especÃ­fica) |
| Financiero | âœ… | âœ… (plantilla especÃ­fica) |
| Asesores | âœ… | âœ… (plantilla especÃ­fica) |
| Productos | âœ… | âœ… (plantilla especÃ­fica) |

## 5. Nota sobre "Reportes Generados"

No existe tabla en BD para historial de reportes generados. La secciÃ³n muestra los tipos disponibles con descarga bajo demanda.

---
## 9. Mejoras aplicadas (2026-02-25)

1. **Parametros de filtros (frontend-backend):** En rontend/src/services/reporteService.ts se corregio el nombre del query param enviado al API: de 'anos' (o variante con ene) a 'anos' de forma consistente, para que el backend reciba correctamente los filtros de anos en exportar/cartera, exportar/pagos, exportar/morosidad, exportar/asesores, exportar/productos y exportar/contable.

2. **Permisos y comentario en Reportes:** En rontend/src/pages/Reportes.tsx se anadio un comentario que aclara que el bloque \"Acceso Restringido\" se muestra cuando canViewReports() es false (por si en el futuro se restringe la pagina a solo admin); la restriccion por tipo de reporte se aplica con canAccessReport().

3. **Aviso cold start:** En la misma pagina, cuando loadingResumen es true se muestra un texto breve bajo la descripcion: \"Cargando indicadoresâ€¦ Si tarda, el servidor puede estar iniciando. Puedes reintentar en unos segundos.\"

### Recomendaciones pendientes (opcionales)

- **Rate limiting:** Valorar limite por usuario o IP en los endpoints de exportacion (ej. N descargas por minuto) para entornos productivos.
- **canViewReports():** Si se decide que solo administradores vean la pagina de reportes, cambiar canViewReports() en usePermissions.ts a return isAdmin() y la UI mostrara el bloque \"Acceso Restringido\" a operativos.
