# Reporte Conciliación - Documentación Completa

## 📋 Descripción General

Reporte de conciliación financiera que permite cargar datos desde Excel (cédula, total financiamiento, total abonos) y descargue un reporte detallado con:
- Información de clientes y créditos
- Datos de pagos realizados
- Cuotas pagadas vs pendientes
- Integración automática con datos cargados

---

## 🗄️ Tabla: `conciliacion_temporal`

**Ubicación SQL:** `sql/conciliacion_temporal.sql`

```sql
CREATE TABLE conciliacion_temporal (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    total_financiamiento NUMERIC(14, 2) NOT NULL,
    total_abonos NUMERIC(14, 2) NOT NULL,
    columna_e VARCHAR(255) NULL,
    columna_f VARCHAR(255) NULL,
    creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_conciliacion_temporal_cedula ON conciliacion_temporal (cedula);
```

**Propósito:** Almacenar temporalmente los datos cargados desde Excel. Se eliminan automáticamente al descargar el reporte.

---

## 🔌 Backend

### Modelo ORM: `backend/app/models/conciliacion_temporal.py`

```python
class ConciliacionTemporal(Base):
    __tablename__ = "conciliacion_temporal"
    
    id: INT (PK)
    cedula: VARCHAR(20) - índice
    total_financiamiento: NUMERIC(14,2)
    total_abonos: NUMERIC(14,2)
    columna_e: VARCHAR(255) - opcional
    columna_f: VARCHAR(255) - opcional
    creado_en: TIMESTAMP
```

### Endpoints: `backend/app/api/v1/endpoints/reportes/reportes_conciliacion.py`

#### 1. POST `/api/v1/reportes/conciliacion/cargar`

**Descripción:** Carga y valida filas de conciliación desde el frontend.

**Body:**
```json
[
  {
    "cedula": "V12345678",
    "total_financiamiento": 10000.00,
    "total_abonos": 5000.00,
    "columna_e": "dato_opcional",
    "columna_f": "dato_opcional"
  }
]
```

**Validación:**
- Cédula: regex `[A-Za-z0-9\-]{5,20}`
- total_financiamiento y total_abonos: números >= 0

**Respuesta (200 OK):**
```json
{
  "ok": true,
  "filas_guardadas": 15
}
```

**Error (422):**
```json
{
  "detail": {
    "errores": ["Fila 1: cédula inválida", "Fila 2: total financiamiento debe ser un número >= 0"],
    "mensaje": "Corrija los errores antes de guardar"
  }
}
```

**Lógica:**
1. Valida todas las filas
2. Si hay errores → retorna 422 con detalles
3. Si OK → borra registros previos y inserta nuevos
4. Usa transacción: `db.commit()`

---

#### 2. GET `/api/v1/reportes/exportar/conciliacion`

**Descripción:** Genera Excel de conciliación con 12 columnas (A-L) y elimina los datos temporales.

**Parámetros:** Ninguno (usa los datos guardados en `conciliacion_temporal`)

**Respuesta:** 
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Filename: `reporte_conciliacion_YYYY-MM-DD.xlsx`

**Columnas del Excel:**

| Pos | Letra | Encabezado | Fuente |
|-----|-------|-----------|--------|
| 1 | A | Nombre | `cliente.nombres` o "no existe" |
| 2 | B | Cedula | `cliente.cedula` o "no existe" |
| 3 | C | Numero de credito | `prestamo.id` |
| 4 | D | Total financiamiento | `prestamo.total_financiamiento` |
| 5 | E | Columna E | `conciliacion_temporal.columna_e` |
| 6 | F | Columna F | `conciliacion_temporal.columna_f` |
| 7 | G | Total pagos realizados | `SUM(pagos.monto_pagado)` |
| 8 | H | Total cuotas | `COUNT(cuotas)` (acordadas) |
| 9 | I | Cuotas pagadas (num) | `COUNT(cuotas WHERE estado='PAGADO')` |
| 10 | J | Cuotas pagadas ($) | `SUM(cuotas.monto WHERE estado='PAGADO')` |
| 11 | K | Cuotas pendientes (num) | `COUNT(cuotas WHERE estado!='PAGADO')` |
| 12 | L | Cuotas pendientes ($) | `SUM(cuotas.monto WHERE estado!='PAGADO')` |

**Lógica:**
1. Obtiene todos los préstamos APROBADOS
2. Para cada préstamo:
   - Busca cliente por ID
   - Si no hay cliente → nombres y cedula = "no existe"
   - Obtiene totales de pagos por `prestamo_id`
   - Obtiene conteos y sumas de cuotas (pagadas vs pendientes)
   - Busca datos en `conciliacion_temporal` por cédula
3. Genera Excel con `openpyxl`
4. **Borra todos los registros de `conciliacion_temporal`**
5. `db.commit()` y retorna blob

---

### Registro de Routers

**`backend/app/api/v1/endpoints/reportes/__init__.py`**
```python
from app.api.v1.endpoints.reportes.reportes_conciliacion import router as router_conciliacion
# ...
router.include_router(router_conciliacion, tags=["reportes"])
```

**`backend/app/models/__init__.py`**
```python
from app.models.conciliacion_temporal import ConciliacionTemporal
# En __all__:
"ConciliacionTemporal",
```

---

## 🎨 Frontend

### Componente: `frontend/src/components/reportes/DialogConciliacion.tsx`

**Props:**
```typescript
interface DialogConciliacionProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onGuardar?: () => void
}
```

**Funcionalidades:**

1. **Cargar Excel**
   - Input file (`.xlsx`)
   - Lee con `xlsx` library
   - Mapea columnas: A→cedula, B→total_financiamiento, C→total_abonos
   - Columnas 5-6 → columna_e, columna_f (opcionales)
   - Muestra tabla con filas cargadas

2. **Validación en Tabla**
   - Cédula: regex match en tiempo real
   - Cantidades: número positivo
   - Errores listados en rojo debajo de tabla
   - Solo habilita "Guardar" si no hay errores

3. **Guardar e Integrar**
   - POST → `reporteService.cargarConciliacion(filas)`
   - Si error: muestra en toast + lista de errores
   - Si OK: cierra diálogo + clearFilas

4. **Descargar Reporte**
   - GET → `reporteService.exportarReporteConciliacion()`
   - Descarga automático del Blob
   - Cierra diálogo
   - Toast de confirmación

### Página: `frontend/src/pages/Reportes.tsx`

**Cambios:**
1. Import icono `Scale` de lucide-react
2. Import `DialogConciliacion`
3. Agregar reporte en array `tiposReporte`:
   ```typescript
   { value: 'CONCILIACION', label: 'Conciliación', icon: Scale }
   ```
4. Condición en `abrirDialogoReporte()`:
   ```typescript
   if (tipo === 'CONCILIACION') {
     setReporteSeleccionado(tipo)
     setDialogAbierto(true)
     return
   }
   ```
5. Incluir en `isDisponible`: `'CONCILIACION'`
6. Renderizar `<DialogConciliacion />`:
   ```tsx
   <DialogConciliacion
     open={dialogAbierto && reporteSeleccionado === 'CONCILIACION'}
     onOpenChange={setDialogAbierto}
     onGuardar={() => {
       queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })
       queryClient.invalidateQueries({ queryKey: ['kpis'] })
     }}
   />
   ```

### Servicio: `frontend/src/services/reporteService.ts`

```typescript
class ReporteService {
  /**
   * Envía filas de conciliación para guardar en BD temporal.
   */
  async cargarConciliacion(filas: Array<{
    cedula: string
    total_financiamiento: number
    total_abonos: number
    columna_e?: string
    columna_f?: string
  }>): Promise<{ ok: boolean; filas_guardadas: number }> {
    return await apiClient.post(`${this.baseUrl}/conciliacion/cargar`, filas)
  }

  /**
   * Exporta reporte Conciliación en Excel.
   * Al descargar se eliminan automáticamente los datos temporales.
   */
  async exportarReporteConciliacion(): Promise<Blob> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(
      `${this.baseUrl}/exportar/conciliacion`,
      { responseType: 'blob', timeout: 180000 }
    )
    return response.data as Blob
  }
}
```

---

## 🔄 Flujo Completo

1. **Usuario hace clic en "Conciliación"**
   - Icono con label "Conciliación" en grid de reportes
   - Abre `DialogConciliacion`

2. **Cargar Excel**
   - Usuario selecciona archivo `.xlsx`
   - Columnas esperadas: A=cedula, B=total_financiamiento, C=total_abonos
   - Validación en cliente (regex cedula + números positivos)
   - Tabla muestra filas con errores en rojo

3. **Guardar e Integrar**
   - Botón solo activo si no hay errores
   - POST `/reportes/conciliacion/cargar` con filas
   - Backend:
     - Valida nuevamente
     - Si error → 422 con lista de errores
     - Si OK → DELETE previos + INSERT nuevos
   - Diálogo se cierra

4. **Descargar Reporte**
   - GET `/reportes/exportar/conciliacion`
   - Backend:
     - Genera Excel (A-L) con JOIN clientes+prestamos+pagos+cuotas+conciliacion_temporal
     - DELETE conciliacion_temporal
   - Frontend: descarga archivo `.xlsx`
   - Toast de confirmación

---

## 🛠️ Cambios Técnicos

| Archivo | Cambios |
|---------|---------|
| `sql/conciliacion_temporal.sql` | Nueva tabla + índice |
| `backend/app/models/conciliacion_temporal.py` | Nuevo modelo ORM |
| `backend/app/models/__init__.py` | +import +__all__ |
| `backend/app/api/v1/endpoints/reportes/reportes_conciliacion.py` | Nuevos endpoints |
| `backend/app/api/v1/endpoints/reportes/__init__.py` | +import +include_router |
| `frontend/src/components/reportes/DialogConciliacion.tsx` | Nuevo componente |
| `frontend/src/pages/Reportes.tsx` | +import +tipo reporte +diálogo |
| `frontend/src/services/reporteService.ts` | +2 métodos |
| `backend/app/api/v1/endpoints/pagos_con_errores.py` | Fix encoding error |

---

## ✅ Estado de Implementación

- ✅ SQL table created
- ✅ Backend model + endpoints
- ✅ Frontend dialog + page integration
- ✅ Validation (cedula + amounts)
- ✅ Excel generation (openpyxl)
- ✅ Auto-delete on download
- ✅ Error handling
- ✅ Service methods
- ✅ Git commit created
- ⏳ Ready for Render deployment

---

## 📝 Notas Importantes

1. **Validación de Cédula:** Regex `^[A-Za-z0-9\-]{5,20}$` - ajustar si necesita otros formatos
2. **Búsqueda por Cédula:** Los datos de `conciliacion_temporal` se buscan por cédula. Si la cédula no coincide exactamente (espacios, mayúsculas), no se concatenarán.
3. **Soft Delete:** Los registros se borran **después** de descargar, no antes. Permite reintento si la descarga falla.
4. **Relación Cliente-Préstamo:** Si un préstamo no tiene `cliente_id` o el cliente no existe, muestra "no existe" en nombre y cédula.
5. **Cuotas no Pagadas:** Incluye cuotas con `estado != 'PAGADO'` (PENDIENTE, VENCIDO, etc.)

---

## 🚀 Deployment Checklist

- [ ] Ejecutar SQL `conciliacion_temporal.sql` en Render PostgreSQL
- [ ] O: Render creará la tabla automáticamente en el startup con `Base.metadata.create_all()`
- [ ] Verificar encoding UTF-8 en archivos Python
- [ ] Frontend build sin errores (✓ completado)
- [ ] Backend imports resueltos (✓ completado)
- [ ] Push a `main` branch
- [ ] Trigger deploy en Render

---

## 📞 Soporte

**Errores comunes:**

1. `SyntaxError: utf-8 codec can't decode byte 0xed`
   - Fix: Remover caracteres especiales mal codificados en docstrings
   - Solución: `set-content -Encoding UTF8`

2. `AttributeError: 'ReporteService' has no attribute 'cargarConciliacion'`
   - Fix: Verificar que se agregó el método en `reporteService.ts`

3. `No such table: conciliacion_temporal`
   - Fix: Ejecutar SQL o aguardar a que se cree con `create_all()`

4. Validación rechaza cédulas válidas
   - Fix: Revisar regex y ajustar en `reportes_conciliacion.py`
