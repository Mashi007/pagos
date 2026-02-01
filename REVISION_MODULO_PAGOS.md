# Revisión módulo Pagos

**Fecha:** 2026-02-01  
**Alcance:** Endpoints, conexión a base de datos y caracteres especiales (encoding) en frontend.

---

## 1. Resumen ejecutivo

| Área | Estado | Nota |
|------|--------|------|
| Endpoints backend `/api/v1/pagos` | Parcial | Solo existen GET `/kpis` y GET `/stats` (stubs). Faltan CRUD, upload, conciliación, etc. |
| Conexión a base de datos | No implementada | Los endpoints son stubs; no hay sesión ni consultas a BD. |
| Estructura de respuesta `/stats` | Corregido | El stub ahora devuelve `cuotas_pagadas`, `cuotas_pendientes`, `cuotas_atrasadas`, `pagos_hoy` que espera el frontend. |
| Caracteres especiales en frontend | Parcial | Corregidos mojibake en DashboardPagos y PagosList (✓, ←). Emoji 🔍 en una línea puede requerir reemplazo manual por `<Search />` si persiste. |

---

## 2. Endpoints del módulo Pagos

### 2.1 Lo que existe en backend (`backend/app/api/v1/endpoints/pagos.py`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/pagos/kpis` | KPIs (stub: ceros). Parámetros: `fecha_inicio`, `fecha_fin`. |
| GET | `/pagos/stats` | Estadísticas (stub). Parámetros: `fecha_inicio`, `fecha_fin`, `analista`, `concesionario`, `modelo`. |

**Cambio aplicado:** El stub de `/stats` ahora devuelve la estructura que espera el frontend:

- `total_pagos`, `total_pagado`, `pagos_por_estado` (lista)
- `cuotas_pagadas`, `cuotas_pendientes`, `cuotas_atrasadas`, `pagos_hoy`

Así el Dashboard de Pagos puede mostrar números coherentes (aunque en cero hasta tener BD).

### 2.2 Lo que usa el frontend y no existe en backend

El servicio `frontend/src/services/pagoService.ts` y las pantallas llaman a:

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/pagos/` | Lista paginada de pagos (PagosList). **404** si no existe. |
| POST | `/pagos/` | Crear pago. **404** |
| GET | `/pagos/{id}` | Detalle. **404** |
| PUT | `/pagos/{id}` | Actualizar. **404** |
| DELETE | `/pagos/{id}` | Eliminar. **404** |
| POST | `/pagos/{id}/aplicar-cuotas` | Aplicar pago a cuotas. **404** |
| POST | `/pagos/upload` | Carga masiva Excel. **404** |
| POST | `/pagos/conciliacion/upload` | Excel de conciliación. **404** |
| GET | `/pagos/ultimos` | Últimos pagos por cédula. **404** |
| GET | `/pagos/exportar/errores` | Descargar Excel de errores. **404** |

Además, `descargarPDFPendientes` llama a `/api/v1/reportes/cliente/{cedula}/pendientes.pdf`, que tampoco está implementado.

---

## 3. Conexión a base de datos

- **Frontend → API:** Correcta. El frontend usa `apiClient` y `pagoService` con la URL base configurada (`env.API_URL`).
- **API → Base de datos:** No hay conexión. Los endpoints de pagos no usan `get_db`, sesión ni modelos. El backend tiene `DATABASE_URL` en `config.py` pero la capa de datos no está implementada en el módulo pagos (igual que en dashboard y otros módulos).

Para tener datos reales habría que:

1. Implementar en backend la capa de datos (engine, sesión, modelos para pagos/cuotas).
2. Añadir dependencia `get_db` en los endpoints de pagos.
3. Implementar los endpoints CRUD y de upload/conciliación que hoy devuelven 404.

---

## 4. Caracteres especiales (encoding) en frontend

### 4.1 Problema

Varios archivos tenían **mojibake**: texto UTF-8 interpretado como Latin-1, por ejemplo:

- `âœ…` en lugar de ✓  
- `â†'` en lugar de ←  
- `ðŸ"` en lugar del emoji 🔍  
- `Ãš` en lugar de Ú (ej. "Últimos")

### 4.2 Cambios aplicados en el módulo pagos

- **DashboardPagos.tsx:** Comentarios con `âœ…` sustituidos por `✓`. Botón "Menú" con `â†'` sustituido por `←`. Import de `Search` desde `lucide-react` añadido para poder sustituir el emoji por el icono si hace falta.
- **PagosList.tsx:** Comentario con `âœ…` sustituido por `✓`.

### 4.3 Script existente

El proyecto incluye `frontend/fix-encoding.ps1` para restaurar UTF-8 en `frontend/src` (reemplazos de mojibake por caracteres correctos). Si quedan más archivos afectados, ejecutar:

```powershell
cd frontend
.\fix-encoding.ps1
```

### 4.4 Recomendación

- Guardar siempre los fuentes en **UTF-8 sin BOM**.
- En el editor/IDE, configurar encoding por defecto a UTF-8.
- Para nuevos textos con tildes o símbolos, usar UTF-8 de forma consistente para evitar nuevos mojibake.

---

## 5. Parámetros de query y encoding

En `pagoService.getKPIs()` se envían `mes` y `año` en la query. Usar `año` en la URL puede dar problemas en algunos clientes/servidores. Recomendación: en la API usar el nombre de parámetro `anio` (sin tilde) y documentar que es el año; en el frontend enviar `anio` en lugar de `año` en la query string.

---

## 6. Archivos clave

| Archivo | Rol |
|---------|-----|
| `backend/app/api/v1/endpoints/pagos.py` | Endpoints de pagos (stubs). |
| `backend/app/api/v1/__init__.py` | Registro del router `pagos` con prefijo `/pagos`. |
| `frontend/src/services/pagoService.ts` | Cliente de API de pagos. |
| `frontend/src/pages/DashboardPagos.tsx` | Dashboard de pagos. |
| `frontend/src/components/pagos/PagosList.tsx` | Lista y gestión de pagos. |
| `frontend/fix-encoding.ps1` | Script para corregir mojibake en `src`. |

---

## 7. Referencias

- **Auditoría de endpoints:** `AUDITORIA_ENDPOINTS.md`
- **Conexión dashboard y BD:** `REVISION_CONEXION_DASHBOARD_BD.md`
