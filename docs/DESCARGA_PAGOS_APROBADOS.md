## Descarga de Pagos Aprobados desde Tabla Temporal

> **Histórico:** el endpoint `GET /api/v1/cobros/descargar-pagos-aprobados-excel` y la función `descargarPagosAprobadosExcel` del frontend **se eliminaron**. Use el Excel de administración **`GET /api/v1/cobros/pagos-reportados/exportar-aprobados-excel`** (fallas de validadores / carga masiva) y el flujo actual de Cobros en la app.

### Funcionalidad Implementada

Se ha desarrollado un sistema completo para:
1. **Almacenar pagos aprobados** en una tabla temporal (`pagos_pendiente_descargar`)
2. **Descargar en Excel** solo los pagos que están en estado "aprobados"
3. **Vaciar la tabla automáticamente** después de cada descarga

---

## Arquitectura Backend

### 1. Modelo de Datos
**Archivo:** `backend/app/models/pago_pendiente_descargar.py`

```python
class PagoPendienteDescargar(Base):
    __tablename__ = "pagos_pendiente_descargar"
    id: Integer (PK)
    pago_reportado_id: Integer (FK → pagos_reportados.id, cascade delete)
    created_at: DateTime
```

### 2. Migración Alembic
**Archivo:** `backend/alembic/versions/021_pagos_pendiente_descargar.py`

- Crea tabla `pagos_pendiente_descargar`
- Establece FK con cascade delete
- Crea índices para búsquedas rápidas

### 3. Servicio
**Archivo:** `backend/app/services/cobros/pagos_pendiente_descargar_service.py`

Funciones:
- `obtener_pagos_aprobados_pendientes(db)`: Retorna pagos de la tabla temporal
- `agregar_a_pendiente_descargar(db, pago_id)`: Inserta pago al aprobar
- `vaciar_tabla_pendiente_descargar(db)`: Elimina todos los registros
- `obtener_datos_excel(db, pagos)`: Formatea datos para Excel (incluye tasa Bs/USD del día `fecha_pago` y equivalente USD)

### 4. Endpoint Backend (histórico)
**Archivo:** `backend/app/api/v1/endpoints/cobros/routes.py`

El endpoint dedicado de descarga desde cola temporal fue **retirado**. La cola `pagos_pendiente_descargar` sigue usándose al aprobar y al exportar (se limpia por IDs al marcar exportados; ver `_persist_marcar_exportados_y_cola`).

Para exportar hoy: **`GET /api/v1/cobros/pagos-reportados/exportar-aprobados-excel`** (parámetros opcionales `cedula`, `institucion`).

#### Integración con Aprobación
Se agregó lógica en dos puntos:
1. **Endpoint `/aprobar`** (aprobación directa)
2. **Endpoint `/cambiar-estado`** (cambio de estado)

Ambos llaman a `agregar_a_pendiente_descargar(db, pago.id)` al aprobar.

---

## Arquitectura Frontend

### 1. Función de servicio (actual)
**Archivo:** `frontend/src/services/cobrosService.ts`

Use la función que llama a **`GET /api/v1/cobros/pagos-reportados/exportar-aprobados-excel`** (exportar Excel de filas que no validan para carga masiva), no la descarga antigua desde cola temporal.

### 2. Página de Cobros
**Archivo:** `frontend/src/pages/CobrosPagosReportadosPage.tsx`

#### Estado
```typescript
const [descargandoTabla, setDescargandoTabla] = useState(false)
```

#### Handler
```typescript
const handleDescargarPagosTablaTemporalExcel = async () => {
  // Descarga Excel
  // Muestra toast de éxito/error
  // Recarga la tabla
}
```

#### Botón UI
- Ubicado junto al botón "Descargar Excel Aprobados"
- Texto: "Descargar de Tabla Temporal"
- Ícono: FileText (lucide-react)
- Estado de carga: Muestra spinner mientras descarga
- Deshabilitado durante la descarga

---

## Flujo de Datos

### Aprobación de Pago
```
1. Usuario aprueba pago reportado
2. Backend:
   - Cambia estado a "aprobado"
   - Crea registro en tabla pagos
   - Genera recibo PDF
   - Envía correo al cliente
   - ✨ INSERTA en pagos_pendiente_descargar
```

### Exportación (flujo actual)
El botón o acción de la UI debe usar **`exportar-aprobados-excel`** (servicio TypeScript que ya consume ese `GET`). La cola temporal se actualiza al aprobar y al marcar exportados según la lógica vigente en `cobros/routes.py`.
```
1. Usuario exporta Excel de administración (fallas validadores / pendientes de exportar)
2. Frontend: GET /api/v1/cobros/pagos-reportados/exportar-aprobados-excel
3. Backend: genera .xlsx, marca exportados y limpia filas de cola asociadas a esos IDs
```

---

## Especificaciones del Excel

### Columnas (Orden exacto del usuario)
| Columna A | Columna B | Columna C | Columna D |
|-----------|----------|----------|----------|
| Cédula | Fecha | Comentario | Número de Documento |

### Formato
- **Cédula**: `{tipo_cedula}{numero_cedula}` (ej: V20149164)
- **Fecha**: `DD/MM/YYYY` (ej: 20/03/2026)
- **Comentario**: Campo `observacion` del pago
- **Número de Documento**: Campo `numero_operacion` del pago

### Nombre del Archivo
`pagos_aprobados_YYYYMMDD.xlsx`

---

## Validaciones

### Backend
- ✓ Solo pagos en estado "aprobado" se descargan
- ✓ Si no hay pagos pendientes → Retorna 204 No Content
- ✓ Índices para búsquedas rápidas
- ✓ Cascade delete: Si se elimina un pago reportado, se elimina automáticamente de la tabla

### Frontend
- ✓ Botón deshabilitado durante descarga
- ✓ Toast de error si falla la descarga
- ✓ Recarga automática después de descargar
- ✓ Validación de permisos (requiere autenticación)

---

## Cambios de Archivos

### Backend
- `backend/app/models/pago_pendiente_descargar.py` (nuevo)
- `backend/alembic/versions/021_pagos_pendiente_descargar.py` (nueva migración)
- `backend/app/services/cobros/pagos_pendiente_descargar_service.py` (nuevo)
- `backend/app/api/v1/endpoints/cobros.py` (modificado)
- `backend/app/models/__init__.py` (modificado)

### Frontend
- `frontend/src/pages/CobrosPagosReportadosPage.tsx` (modificado)
- `frontend/src/services/cobrosService.ts` (modificado)

---

## Pruebas Manuales

1. **Crear pago reportado** y llevarlo a estado "aprobado"
2. Verificar que aparezca en `pagos_pendiente_descargar`
3. Click en "Descargar de Tabla Temporal"
4. Verificar que:
   - Se descarga el Excel
   - La tabla se vacía (no hay más pagos)
   - El Excel contiene los datos correctos (cédula, fecha, comentario, número doc)
5. Aprobar otro pago y repetir

---

## Notas Técnicas

- **Tabla Temporal**: No persiste pagos exportados (se vacía en cada descarga)
- **Idempotencia**: Un mismo pago no se puede agregar dos veces a la tabla
- **Base de Datos**: Usa PostgreSQL con operadores nativos
- **Seguridad**: Requiere autenticación mediante `get_current_user`
- **Performance**: Índices en `pago_reportado_id` y `id` para búsquedas O(1)

---

## Próximos Pasos (Opcional)

- Agregar auditoría de descargas (tabla `descargas_pagos_reportados`)
- Permitir filtros antes de descargar
- Agregar columnas adicionales configurable
- Comprimir múltiples descargas en ZIP
- Enviar Excel por email automaticamente
