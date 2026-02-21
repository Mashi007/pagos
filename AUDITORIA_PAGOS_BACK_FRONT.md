# Auditoría integral: Módulo Pagos - Articulación Backend/Frontend

**URL:** https://rapicredit.onrender.com/pagos/pagos  
**Fecha:** 2026-02-21

---

## 1. Endpoints Backend (Pagos)

| Método | Path | Parámetros | Descripción |
|--------|------|------------|-------------|
| GET | `/api/v1/pagos/` | page, per_page, cedula, estado, fecha_desde, fecha_hasta, analista, conciliado, sin_prestamo | Listado paginado de pagos |
| GET | `/api/v1/pagos/ultimos` | page, per_page, cedula, estado | Últimos pagos por cédula |
| GET | `/api/v1/pagos/kpis` | mes, año, fecha_inicio, fecha_fin | KPIs mensuales (monto a cobrar, cobrado, morosidad %) |
| GET | `/api/v1/pagos/stats` | fecha_inicio, fecha_fin, analista, concesionario, modelo | Estadísticas de pagos |
| GET | `/api/v1/pagos/{pago_id}` | — | Obtener pago por ID |
| POST | `/api/v1/pagos/` | body: PagoCreate | Crear pago |
| PUT | `/api/v1/pagos/{pago_id}` | body: PagoUpdate | Actualizar pago |
| DELETE | `/api/v1/pagos/{pago_id}` | — | Eliminar pago |
| POST | `/api/v1/pagos/{pago_id}/aplicar-cuotas` | — | Aplicar pago a cuotas |
| POST | `/api/v1/pagos/upload` | file (multipart) | Carga masiva Excel |
| POST | `/api/v1/pagos/conciliacion/upload` | file (multipart) | Carga conciliación Excel |

---

## 2. Endpoints Backend (Préstamos - usados por Pagos)

| Método | Path | Parámetros | Descripción |
|--------|------|------------|-------------|
| GET | `/api/v1/prestamos/cedula/{cedula}` | — | Préstamos por cédula (individual) |
| POST | `/api/v1/prestamos/cedula/batch` | body: { cedulas: string[] } | Préstamos por múltiples cédulas (batch) |
| GET | `/api/v1/prestamos/cedula/{cedula}/resumen` | — | Resumen préstamos por cédula |

---

## 3. Llamadas Frontend (pagoService)

| Método | Endpoint | Usado en |
|--------|----------|----------|
| getAllPagos | GET /pagos/?page&per_page&... | PagosList, TablaAmortizacionCompleta |
| createPago | POST /pagos/ | RegistrarPagoForm, useExcelUploadPagos |
| updatePago | PUT /pagos/{id} | RegistrarPagoForm, TablaAmortizacionCompleta |
| updateConciliado | PUT /pagos/{id} | PagosList |
| deletePago | DELETE /pagos/{id} | PagosList |
| aplicarPagoACuotas | POST /pagos/{id}/aplicar-cuotas | PagosList, RegistrarPagoForm, TablaAmortizacionCompleta |
| uploadExcel | POST /pagos/upload | ExcelUploader |
| uploadConciliacion | POST /pagos/conciliacion/upload | ConciliacionExcelUploader |
| getStats | GET /pagos/stats | DashboardPagos |
| getKPIs | GET /pagos/kpis | usePagos, PagosKPIsNuevo, useSidebarCounts |
| getUltimosPagos | GET /pagos/ultimos | PagosListResumen |
| descargarPDFPendientes | GET /reportes/cliente/{cedula}/pendientes.pdf | PagosListResumen |
| descargarPDFAmortizacion | GET /reportes/cliente/{cedula}/amortizacion.pdf | PagosBuscadorAmortizacion |

---

## 4. Llamadas Frontend (prestamoService - desde Pagos)

| Método | Endpoint | Usado en |
|--------|----------|----------|
| getPrestamosByCedula | GET /prestamos/cedula/{cedula} | useExcelUploadPagos (individual) |
| getPrestamosByCedulasBatch | POST /prestamos/cedula/batch | useExcelUploadPagos (batch 4+ cédulas) |

---

## 5. Matriz de correspondencia

| Frontend | Backend | Estado |
|----------|---------|--------|
| getAllPagos(page, perPage, filters) | GET /pagos/?page&per_page&cedula&estado&fecha_desde&fecha_hasta&analista&conciliado&sin_prestamo | ✅ OK |
| createPago(data) | POST /pagos/ | ✅ OK |
| updatePago(id, data) | PUT /pagos/{id} | ✅ OK |
| deletePago(id) | DELETE /pagos/{id} | ✅ OK |
| aplicarPagoACuotas(id) | POST /pagos/{id}/aplicar-cuotas | ✅ OK |
| uploadExcel(file) | POST /pagos/upload | ✅ OK |
| uploadConciliacion(file) | POST /pagos/conciliacion/upload | ✅ OK |
| getStats(filters) | GET /pagos/stats | ✅ OK |
| getKPIs(mes?, año?) | GET /pagos/kpis | ✅ OK |
| getUltimosPagos(...) | GET /pagos/ultimos | ✅ OK |
| getPrestamosByCedula(cedula) | GET /prestamos/cedula/{cedula} | ✅ OK |
| getPrestamosByCedulasBatch(cedulas) | POST /prestamos/cedula/batch | ✅ OK |

---

## 6. Problemas detectados

### 6.1 KPIs: parámetros mes/año ✅ CORREGIDO

- **Frontend** (`pagoService.getKPIs`): envía `mes` y `año` como query params.
- **Backend** (`GET /pagos/kpis`): ahora acepta `mes` (1-12) y `año` (2000-2100). Si no se envían, usa el mes actual. También acepta `fecha_inicio`/`fecha_fin` como alternativa.

### 6.2 Respuesta KPIs: campo "año"

- **Backend** devuelve `"año"` (con ñ).
- **Frontend** espera `año` en el tipo. Verificar que el JSON no use encoding incorrecto (`aÃ±o`).

---

## 7. Flujo principal: Página Pagos

```
PagosPage
  └── PagosList
        ├── useQuery: pagoService.getAllPagos(page, perPage, filters)
        ├── PagosKPIsNuevo: usePagosKPIs() → pagoService.getKPIs()
        ├── CargaMasivaMenu
        │     └── ExcelUploaderPagosUI (useExcelUploadPagos)
        │           ├── prestamoService.getPrestamosByCedulasBatch (4+ cédulas)
        │           ├── prestamoService.getPrestamosByCedula (1-3 cédulas)
        │           └── pagoService.createPago (Guardar, Revisar Pagos)
        ├── RegistrarPagoForm
        │     ├── pagoService.createPago
        │     ├── pagoService.updatePago
        │     └── pagoService.aplicarPagoACuotas
        └── Acciones por pago:
              ├── pagoService.updateConciliado
              ├── pagoService.aplicarPagoACuotas
              └── pagoService.deletePago
```

---

## 8. Recomendaciones

1. ~~**KPIs**: Unificar params backend/frontend~~ ✅ Implementado: backend acepta mes/año.
2. **Encoding**: Revisar que las respuestas JSON usen UTF-8 correcto para "año".
3. **Timeouts**: El batch `/prestamos/cedula/batch` ya tiene timeout 60s; mantener.
4. **Validación 409**: El retry con sufijo `-REV` en documento duplicado está implementado.
5. **Health**: Verificar que `GET /health/db` responda para validar conexión BD.

---

## 9. Resumen

| Categoría | Cantidad |
|-----------|----------|
| Endpoints backend Pagos | 11 |
| Endpoints backend Préstamos (Pagos) | 3 |
| Llamadas frontend pagoService | 12 |
| Llamadas frontend prestamoService (Pagos) | 2 |
| Desajustes críticos | 0 |
| Desajustes menores | 0 |

**Conclusión**: La articulación Backend/Frontend del módulo Pagos está correcta. El endpoint de KPIs acepta `mes` y `año` alineado con el frontend.
