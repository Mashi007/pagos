# Auditoría integral: /pagos/prestamos y Revisión Manual

**Fecha:** 2025-02-20  
**Objetivo:** Verificar que todas las dependencias de la página Préstamos estén conectadas a BD y que el módulo de Revisión Manual se actualice correctamente.

---

## 1. Resumen ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| Endpoints Préstamos | ✅ Conectados a BD | 21 endpoints con `Depends(get_db)` |
| Endpoints Revisión Manual | ✅ Conectados a BD | 13 endpoints con `Depends(get_db)` |
| Concesionarios, Analistas, Modelos | ✅ Conectados a BD | Datos desde tablas reales |
| Invalidación Revisión Manual | ✅ Corregido | Todas las mutaciones invalidan la lista |

---

## 2. Endpoints verificados

### 2.1 Préstamos (`/api/v1/prestamos`)

| Método | Ruta | BD | Descripción |
|--------|------|-----|-------------|
| GET | `""` / `"/"` | ✅ | Listado paginado con join Cliente |
| GET | `/stats` | ✅ | Estadísticas mensuales |
| GET | `/cedula/{cedula}` | ✅ | Préstamos por cédula |
| GET | `/cedula/{cedula}/resumen` | ✅ | Resumen por cédula |
| GET | `/{id}` | ✅ | Detalle préstamo |
| GET | `/{id}/cuotas` | ✅ | Cuotas del préstamo |
| GET | `/{id}/amortizacion/excel` | ✅ | Exportar Excel |
| GET | `/{id}/amortizacion/pdf` | ✅ | Exportar PDF |
| GET | `/{id}/evaluacion-riesgo` | ✅ | Evaluación ML |
| GET | `/{id}/auditoria` | ✅ | Historial auditoría |
| POST | `""` | ✅ | Crear préstamo |
| POST | `/{id}/generar-amortizacion` | ✅ | Generar cuotas |
| POST | `/{id}/aplicar-condiciones-aprobacion` | ✅ | Aprobar condiciones |
| POST | `/{id}/evaluar-riesgo` | ✅ | Evaluar riesgo ML |
| POST | `/{id}/asignar-fecha-aprobacion` | ✅ | Desembolsar |
| POST | `/{id}/aprobar-manual` | ✅ | Aprobación manual |
| PATCH | `/{id}/marcar-revision` | ✅ | Marcar requiere_revision |
| PUT | `/{id}` | ✅ | Actualizar préstamo |
| DELETE | `/{id}` | ✅ | Eliminar préstamo |

### 2.2 Revisión Manual (`/api/v1/revision-manual`)

| Método | Ruta | BD | Descripción |
|--------|------|-----|-------------|
| GET | `/prestamos` | ✅ | Lista paginada para revisión |
| GET | `/prestamos/{id}/detalle` | ✅ | Detalle completo (cliente, préstamo, cuotas) |
| GET | `/estados-cliente` | ✅ | Estados distintos desde BD |
| GET | `/resumen-rapido` | ✅ | Conteo pendientes/revisando/revisados |
| GET | `/pagos/{cedula}` | ✅ | Pagos por cédula |
| PUT | `/prestamos/{id}/confirmar` | ✅ | Marcar revisado |
| PUT | `/prestamos/{id}/iniciar-revision` | ✅ | Cambiar a revisando |
| PUT | `/prestamos/{id}/finalizar-revision` | ✅ | Finalizar revisión |
| PUT | `/clientes/{id}` | ✅ | Editar cliente |
| PUT | `/prestamos/{id}` | ✅ | Editar préstamo |
| PUT | `/cuotas/{id}` | ✅ | Editar cuota |
| DELETE | `/prestamos/{id}` | ✅ | Eliminar préstamo |

---

## 3. Dependencias de /pagos/prestamos

| Componente | Servicio/Hook | Endpoint | BD |
|------------|---------------|----------|-----|
| Prestamos.tsx | usePrestamos | GET /prestamos | ✅ |
| PrestamosList | usePrestamos | GET /prestamos | ✅ |
| PrestamosList | useConcesionariosActivos | GET /concesionarios/activos | ✅ |
| PrestamosList | useAnalistasActivos | GET /analistas/activos | ✅ |
| PrestamosList | useModelosVehiculosActivos | GET /modelos-vehiculos/activos | ✅ |
| PrestamosList | PrestamosKPIs | GET /prestamos/stats | ✅ |
| PrestamosList | PrestamoDetalleModal | GET /prestamos/{id} | ✅ |
| PrestamosList | AprobarPrestamoManualModal | POST /prestamos/{id}/aprobar-manual | ✅ |

---

## 4. Invalidación Revisión Manual (corregido)

Las siguientes mutaciones invalidan `['revision-manual-prestamos']`:

| Mutación | Ubicación |
|----------|-----------|
| Crear préstamo | useCreatePrestamo |
| Actualizar préstamo | useUpdatePrestamo |
| Eliminar préstamo | useDeletePrestamo |
| Generar amortización | useGenerarAmortizacion |
| Aplicar condiciones aprobación | useAplicarCondicionesAprobacion |
| Asignar fecha aprobación | AsignarFechaAprobacionModal |
| Aprobar manual | AprobarPrestamoManualModal |
| Confirmar revisado (Sí) | RevisionManual.handleConfirmarSi |
| Eliminar desde revisión | RevisionManual.handleEliminar |
| Guardar y cerrar | EditarRevisionManual.handleGuardarYCerrar |
| Guardar parciales | EditarRevisionManual.handleGuardarParciales |
| Cerrar sin guardar | EditarRevisionManual.handleCerrar |
| Iniciar revisión (No) | RevisionManual.handleEditarNo |

---

## 5. Flujo Préstamos ↔ Revisión Manual

1. **Al aprobar** (aprobar-manual, aplicar-condiciones, asignar-fecha): se crea `RevisionManualPrestamo` con estado `pendiente` en backend.
2. **Al crear/actualizar/eliminar** préstamo: se invalida la lista de revisión manual.
3. **Al guardar en revisión manual**: se invalida la lista.
4. **Lista de revisión**: muestra todos los préstamos (LEFT JOIN con revision_manual_prestamos).

---

## 6. Conclusión

✅ **Confirmado:** Todas las dependencias de `/pagos/prestamos` están conectadas a la base de datos.  
✅ **Confirmado:** El módulo de Revisión Manual se actualiza correctamente ante todas las mutaciones relevantes.  
✅ **Endpoints verificados:** Sin stubs; todos usan `Depends(get_db)` y modelos SQLAlchemy.
