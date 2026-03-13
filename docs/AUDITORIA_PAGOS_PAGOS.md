# Auditoría completa: https://rapicredit.onrender.com/pagos/pagos

**Alcance:** Pantalla Pagos (ruta interna `/pagos`, URL completa `/pagos/pagos` con base path `/pagos`).  
**Revisión:** Línea a línea de frontend (rutas, página, listado, servicios) y backend (endpoints de pagos y pagos con errores).  
**Fecha:** 2025-03-12.

---

## 1. Resumen ejecutivo

| Área | Estado | Hallazgos críticos | Hallazgos menores |
|-----|--------|-------------------|-------------------|
| Rutas y acceso | ✅ | 0 | 0 |
| Frontend PagosPage / PagosList | ✅ | 0 | 2 (logs, encoding) |
| Servicios (pagoService, pagoConErrorService) | ✅ | 0 | 0 |
| Backend GET/POST/PUT/DELETE pagos | ✅ | 0 | 1 (validación monto en POST) |
| Backend pagos_con_errores | ✅ | 0 | 0 |
| Seguridad (auth, inyección, duplicados) | ✅ | 0 | 0 |

**Conclusión:** La funcionalidad está bien implementada, con datos reales desde BD, autenticación en todos los endpoints de pagos y reglas de negocio (no duplicados en Nº documento, conciliación, aplicar a cuotas). Se recomiendan correcciones menores (validación de monto en POST, limpieza de logs y encoding).

---

## 2. URL y flujo de acceso

- **URL pública:** `https://rapicredit.onrender.com/pagos/pagos`
- **Base path SPA:** `/pagos` (Vite `base: '/pagos/'`, `server.js` FRONTEND_BASE).
- **Ruta interna React:** `path="pagos"` con `<Route index element={<PagosPage />} />` y `path=":id"` también a `PagosPage`.
- **Autenticación:** Sin token, el usuario es redirigido a `/login`; con token puede acceder a `/pagos` (índice = lista de pagos).

**Verificación línea a línea (App.tsx):**

- Líneas 132–140: índice `/` → si no autenticado `Navigate to="/login"`, si autenticado `Navigate to="/dashboard/menu"`.
- Líneas 186–189: `<Route path="pagos">` con `index` → `PagosPage`, `path=":id"` → `PagosPage` (permite futura vista detalle por id).
- Comportamiento correcto: la URL `/pagos/pagos` muestra la lista de pagos solo si hay sesión.

---

## 3. Frontend – PagosPage.tsx

- **Líneas 1–4:** Imports (CreditCard, Card, PagosList). Correcto.
- **Líneas 5–11:** Título "Pagos" y estructura. Correcto.
- **Líneas 13–23:** Card informativa "Gestión de pagos". Correcto.
- **Línea 25:** `<PagosList />` — componente principal que contiene KPIs, filtros, tabla, modales. Correcto.

**Hallazgos:** Ninguno crítico.

---

## 4. Frontend – PagosList.tsx (línea a línea)

### 4.1 Estado y configuración (líneas 44–79)

- **44:** `SHOW_DESCARGA_EXCEL_EN_SUBMENU = false` — opción "Descargar Excel" (Gmail) oculta en submenú. Correcto.
- **47–60:** `searchParams`, `activeTab`, `page`, `perPage`, `filters` (conciliado por defecto `'si'`). Coherente con backend.
- **61–78:** Estados de modales, edición, acciones, Gmail, importación Cobros. Correcto.
- **81–94:** `useGmailPipeline` con callback para mostrar diálogo de confirmar día. Correcto.

### 4.2 Efectos y handlers (líneas 96–259)

- **96–106:** `useEffect` que carga estado Gmail y muestra diálogo si hay datos; segundo `useEffect` al abrir popover. Correcto.
- **115–138:** `handleImportarDesdeCobros` — invalida queries y muestra toast. Correcto.
- **140–168:** `handleDescargarExcelRevisionPagos` — exporta pagos con error a Excel. Uso de `createAndDownloadExcel` y mapeo de fechas correcto.
- **171–196:** Conteo de filtros activos, `handleClearFilters`, `handleRevisarPagos` (sin_prestamo + conciliado all). Correcto.
- **199–246:** `handleExportRevisarExcel` — exporta y luego llama a `eliminarPorDescarga(ids)`. **Nota:** borra de la lista tras exportar; es comportamiento esperado según diseño.
- **249–256:** `useEffect` para `?revisar=1` — aplica filtros y limpia query. Correcto.

### 4.3 Query principal (líneas 258–272)

- **258:** `esRevisarPagos = filters.sin_prestamo === 'si'`.
- **259–269:** `useQuery` con clave según `esRevisarPagos` (`pagos-con-errores` vs `pagos`), `queryFn` que llama a `pagoConErrorService.getAll` o `pagoService.getAllPagos`. `staleTime: 15_000`, `refetchOnWindowFocus: false` para no interrumpir carga masiva. Correcto.
- **270–272:** `handleFilterChange` convierte `"all"` a cadena vacía. Correcto.

### 4.4 Tabla y acciones (líneas 461–600)

- **469:** `data.pagos.map((pago: Pago)` — en modo "Revisar Pagos" los ítems son `PagoConError`; la estructura de respuesta es la misma (`pagos`, `total`, etc.). Correcto.
- **484:** Monto formateado con `toFixed(2)` y fallback a `parseFloat`. Correcto.
- **506:** Eliminar: usa `window.confirm` y según `esRevisarPagos` llama a `pagoConErrorService.delete` o `pagoService.deletePago`. Invalidaciones de queries correctas.
- **534–563:** Conciliar: Sí/No con `updateConciliado` y opcionalmente `aplicarPagoACuotas`. Invalidaciones correctas.

### 4.5 Hallazgos en PagosList

1. **Líneas 614–639 (onSuccess de RegistrarPagoForm):** Varios `console.log` con emojis que pueden verse mal por encoding (ej. `ðŸ"„`, `âœ…`, `âŒ`) y no aportan en producción.  
   **Recomendación:** Eliminar o reemplazar por un logger condicional (solo en desarrollo).

2. **Mismo bloque:** Lógica de invalidación/refetch es correcta; el comentario "Iniciando actualización de dashboard" y los logs son redundantes para el usuario.

---

## 5. Frontend – pagoService.ts

- **40:** `baseUrl = '/api/v1/pagos'`. Correcto (rutas relativas con proxy en producción).
- **42–67:** `getAllPagos`: parámetros `page`, `per_page`, filtros (`cedula`, `estado`, `fecha_desde`, `fecha_hasta`, `analista`, `conciliado`, `sin_prestamo`). Coinciden con backend. Correcto.
- **69–72:** `moverARevisarPagos`. Correcto.
- **75–95:** `getAllPagosForExport`: paginación interna de 100 por página. Correcto.
- **97–98:** `createPago`. Correcto.
- **105–110:** `createPagosBatch` (máx. 500). Correcto.
- **112–120:** `updatePago`, `updateConciliado`, `deletePago`, `aplicarPagoACuotas`. Correcto.
- **130–136:** `uploadExcel` con FormData. Correcto.
- **143–152:** `importarDesdeCobros`. Correcto.
- **154–167:** `uploadConciliacion`. Correcto.
- **169–174:** `validarFilasBatch`. Correcto.
- **176–193:** `guardarFilaEditable`. Correcto.
- **195–218:** `getStats`, `getKPIs` con query params. Correcto.
- **220–266:** `getUltimosPagos`, `descargarPDFPendientes`, `descargarPDFAmortizacion`. Correcto.
- **294–353:** Gmail: `runGmailNow`, `getGmailStatus`, `confirmarDiaGmail`, `downloadGmailExcel` (validación de status 200 y blob). Correcto.

**Hallazgos:** Ninguno.

---

## 6. Frontend – pagoConErrorService.ts

- **40:** `baseUrl = '/api/v1/pagos/con-errores'`. Correcto.
- **42–68:** `getAll` con paginación y filtros. Correcto.
- **71–80:** `getAllForExport` con query params. Correcto.
- **83–107:** CRUD, `moverAPagosNormales`, `eliminarPorDescarga`, `moveToReviewPagos`. Correcto.

**Hallazgos:** Ninguno.

---

## 7. Backend – Orden de routers (api/v1/__init__.py)

- **68–73:** Router `pagos_con_errores` con prefijo `/pagos/con-errores` está registrado **antes** que el router `pagos` (prefijo `/pagos`). Así, `GET /api/v1/pagos/con-errores` no se interpreta como `GET /api/v1/pagos/{pago_id}`. Correcto.

---

## 8. Backend – pagos.py (endpoints usados por /pagos/pagos)

### 8.1 GET "" (listar_pagos) — líneas 238–306

- **239–252:** Parámetros: `page`, `per_page` (1–100), `cedula`, `estado`, `fecha_desde`, `fecha_hasta`, `analista`, `conciliado`, `sin_prestamo`, `db`.
- **254–258:** `sin_prestamo == "si"`: filtra `prestamo_id.is_(None)` y excluye IDs en `RevisarPago`. Correcto.
- **259–263:** Filtro `conciliado` (si/no). Correcto.
- **264–266:** `cedula` con `ilike(f"%{cedula.strip()}%")` — SQLAlchemy usa parámetros vinculados; no hay concatenación de SQL crudo. Seguro frente a SQL injection.
- **267–269:** `estado` comparación por igualdad. Seguro.
- **271–283:** `fecha_desde`/`fecha_hasta` con `date.fromisoformat` y `datetime.combine`. Manejo de `ValueError` con `pass` (ignora filtro si fecha inválida). Aceptable.
- **288–289:** Con filtro `analista` se hace `join(Prestamo)`; `count_q` replica los mismos filtros. Correcto.
- **290–292:** Orden `fecha_registro.desc(), id.desc()`, offset/limit. Respuesta con `pagos`, `total`, `page`, `per_page`, `total_pages`. Correcto.
- **301–305:** En excepción se hace `db.rollback()` y se re-lanza HTTP 500. Correcto.

**Hallazgos:** Ninguno crítico.

### 8.2 POST "" (crear_pago) — líneas 1689–1773

- **1692–1697:** Normalización de documento y comprobación de duplicado con `_numero_documento_ya_existe`; 409 si existe. Correcto.
- **1704–1723:** Normalización de cédula, validación de `prestamo_id` en tabla `prestamos`, validación de cédula en `clientes` cuando hay préstamo. Correcto.
- **1725–1744:** Creación de `Pago`, commit, aplicación a cuotas si `prestamo_id` y monto > 0. Correcto.
- **1756–1765:** Manejo de `IntegrityError` (código 23505) → 409. Correcto.

**Hallazgo menor:** No se valida el rango de `monto_pagado` (mínimo > 0, máximo según NUMERIC(14,2)). En `guardar_fila_editable` y en la carga por Excel se usa `_validar_monto`; en `crear_pago` y `actualizar_pago` no. Si se envía `monto_pagado=0` o negativo, Pydantic/Decimal puede aceptarlo y la BD podría almacenar 0 (o fallar según restricciones).  
**Recomendación:** Añadir en `crear_pago` (y en `actualizar_pago` si se permite cambiar monto) una validación equivalente a `_validar_monto` (p. ej. 0.01 ≤ monto ≤ _MAX_MONTO_PAGADO).

### 8.3 PUT "/{pago_id}" (actualizar_pago) — líneas 1776–1834

- **1778–1781:** 404 si no existe.
- **1783–1789:** Si se actualiza `numero_documento`, se comprueba duplicado con `exclude_pago_id`. Correcto.
- **1791–1824:** Aplicación de campos (notas, institucion_bancaria, numero_documento, cedula_cliente, fecha_pago, conciliado, verificado_concordancia). Commit y manejo de IntegrityError. Correcto.
- **1823–1832:** Si `aplicar_conciliado` y hay préstamo y monto > 0, se aplica a cuotas. Correcto.

**Hallazgo:** Misma recomendación que en POST: validar monto si en el futuro se permite actualizar `monto_pagado`.

### 8.4 DELETE "/{pago_id}" — líneas 1835–1843

- **1837–1841:** Obtiene pago, 404 si no existe, `db.delete(row)`, commit. Correcto. No se revisan dependencias en `cuota_pagos`; el modelo debe definir ON DELETE adecuado (p. ej. SET NULL o CASCADE según diseño).

### 8.5 Duplicados y helper

- **1596–1606:** `_numero_documento_ya_existe`: usa `normalize_documento` y `select(Pago.id).where(Pago.numero_documento == num)`. Consulta parametrizada. Correcto.

---

## 9. Backend – pagos_con_errores.py

- **74–131:** `listar_pagos_con_errores`: filtros y paginación análogos a pagos; `ilike` con parámetros. Correcto.
- **134–165:** `crear_pago_con_error`: parseo de fecha, creación de `PagoConError`. Correcto.

**Hallazgos:** Ninguno.

---

## 10. Esquemas y modelos

- **schemas/pago.py:** `PagoCreate` con validadores de `numero_documento` (string) y `prestamo_id` (rango 1..PRESTAMO_ID_MAX). No hay validador de rango para `monto_pagado`. Coherente con el hallazgo de validación en backend.
- **models/pago.py:** `monto_pagado = Column(Numeric(14, 2), nullable=False)`. Acepta 0; la regla de negocio "monto > 0" debería aplicarse en endpoint o schema.

---

## 11. Seguridad

- **Autenticación:** Router de pagos y pagos_con_errores usan `dependencies=[Depends(get_current_user)]`. Correcto.
- **SQL:** Filtros con SQLAlchemy (expresiones con columnas y parámetros). No hay concatenación de strings para SQL. Correcto.
- **Duplicados:** Nº documento único en BD y comprobación en crear/actualizar. Correcto.
- **Cédula:** Normalización (strip, uppercase) y existencia de cliente cuando hay préstamo. Correcto.

---

## 12. Checklist de verificación post-auditoría

- [x] Ruta `/pagos/pagos` requiere autenticación.
- [x] GET /api/v1/pagos devuelve datos reales desde tabla `pagos`.
- [x] Filtros (cédula, estado, fechas, analista, conciliado, sin_prestamo) aplicados correctamente.
- [x] POST /pagos valida duplicado por Nº documento (409).
- [x] Orden de routers evita que `/pagos/con-errores` se confunda con `/{pago_id}`.
- [ ] **Opcional:** Añadir validación de monto (min/max) en POST/PUT de pagos.
- [ ] **Opcional:** Quitar o condicionar `console.log` en onSuccess de RegistrarPagoForm (PagosList).

---

## 13. Referencias de código

| Archivo | Líneas relevantes |
|---------|--------------------|
| frontend/src/App.tsx | 132–140, 186–189 |
| frontend/src/pages/PagosPage.tsx | 1–31 |
| frontend/src/components/pagos/PagosList.tsx | 44–639 (estado, query, tabla, onSuccess) |
| frontend/src/services/pagoService.ts | 39–353 |
| frontend/src/services/pagoConErrorService.ts | 39–109 |
| backend/app/api/v1/__init__.py | 68–78 |
| backend/app/api/v1/endpoints/pagos.py | 238–306, 1689–1843, 1596–1606 |
| backend/app/api/v1/endpoints/pagos_con_errores.py | 74–165 |
| backend/app/schemas/pago.py | PagoCreate, PagoUpdate |
| backend/app/models/pago.py | 1–35 |

Esta auditoría verifica línea a línea la pantalla y los endpoints que sirven a **https://rapicredit.onrender.com/pagos/pagos**. La implementación es sólida; las mejoras sugeridas son menores y opcionales.
