# Importar reportados aprobados (Cobros) – Diálogo y descarga Excel

## Backend (implementado)

- **Tabla** `datos_importados_conerrores`: registros que no cumplen validadores al importar. Se acumulan hasta que se descarga el Excel; al descargar se vacía.
- **POST** `/api/v1/pagos/importar-desde-cobros`: igual que antes, pero los fallos se insertan en `datos_importados_conerrores` (no en `pagos_con_errores`). La respuesta incluye:
  - `total_datos_revisar`: número de filas en `datos_importados_conerrores` después del import (para mostrar el diálogo).
- **GET** `/api/v1/pagos/importar-desde-cobros/datos-revisar`: `{ "tiene_datos": boolean, "total": number }`.
- **GET** `/api/v1/pagos/importar-desde-cobros/descargar-excel-errores`: devuelve un Excel con los registros de la tabla y luego **vacía** la tabla.

## Migración

Ejecutar (donde tengas `alembic.ini`):

```bash
alembic upgrade head
```

O aplicar a mano el SQL de `backend/alembic/versions/017_datos_importados_conerrores.py` (crear tabla `datos_importados_conerrores`).

---

## Frontend (a implementar)

### Flujo al hacer clic en "Importar reportados aprobados (Cobros)"

1. Llamar **POST** `/api/v1/pagos/importar-desde-cobros`.
2. Según la respuesta:
   - Si **`total_datos_revisar > 0`**: mostrar diálogo:
     - Texto: **"Hay datos que revisar, ¿quieres descargar Excel?"**
     - Botones: **"Descargar Excel"** y **"No"** (o "Cerrar").
     - **"Descargar Excel"**: abrir en nueva pestaña o descargar con:
       - `GET /api/v1/pagos/importar-desde-cobros/descargar-excel-errores`
       - (El backend ya vacía la tabla al generar el Excel.)
     - **"No"**: cerrar el diálogo; los datos siguen en la tabla hasta una futura descarga.
   - Si **`total_datos_revisar === 0`**: mostrar mensaje (toast o alert):
     - **"Datos importados, no hay datos que revisar"**
     - No descargar nada.

### Ejemplo de uso (pseudocódigo)

```ts
// Tras POST importar-desde-cobros
const res = await api.post('/pagos/importar-desde-cobros');
const total = res.data?.total_datos_revisar ?? 0;

if (total > 0) {
  // Mostrar diálogo: "Hay datos que revisar, ¿quieres descargar Excel?"
  setDialogOpen(true);
  setOnConfirmDownload(() => () => {
    const url = `${API_BASE}/pagos/importar-desde-cobros/descargar-excel-errores`;
    // Usar token si la API requiere auth
    window.open(url, '_blank'); // o fetch + blob + download
    setDialogOpen(false);
  });
} else {
  toast.info('Datos importados, no hay datos que revisar');
}
```

### Descarga del Excel con auth

Si los endpoints requieren token, no sirve un `window.open(url)`. Hacer:

```ts
const response = await fetch(`${API_BASE}/pagos/importar-desde-cobros/descargar-excel-errores`, {
  headers: { Authorization: `Bearer ${token}` },
});
const blob = await response.blob();
// Crear enlace de descarga con blob y nombre sugerido (ej. datos_importados_con_errores_YYYYMMDD_HHMM.xlsx)
```

Nombre del archivo: el backend envía `Content-Disposition: attachment; filename=datos_importados_con_errores_YYYYMMDD_HHMM.xlsx` (se puede usar el de la cabecera o uno fijo).
