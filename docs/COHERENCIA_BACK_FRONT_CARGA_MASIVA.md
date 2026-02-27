# Coherencia Back–Front: carga masiva de pagos

**Fecha:** 2026-02-25  
**Ámbito:** Batch préstamos por cédulas, creación de pago (POST), rutas y cuerpos de petición/respuesta.

---

## Rutas

| Uso | Backend | Frontend | ¿Coincide? |
|-----|---------|----------|------------|
| Prefijo API | `API_V1_STR = "/api/v1"` en `main.py` → `api_router` | `apiClient` con base según `API_URL` (vacío en prod → rutas relativas) | Sí |
| Préstamos | Router en `api/v1/__init__.py` con `prefix="/prestamos"` | `prestamoService.baseUrl = '/api/v1/prestamos'` | Sí |
| Batch por cédulas | `POST /api/v1/prestamos/cedula/batch` (prestamos.py) | `POST ${baseUrl}/cedula/batch` → `/api/v1/prestamos/cedula/batch` | Sí |
| Crear pago | `POST /api/v1/pagos/` (pagos.py) | `pagoService.createPago` → `POST /api/v1/pagos/` | Sí |

---

## Batch préstamos por cédulas

- **Request:** Backend espera `PrestamosPorCedulasBatchBody` con `cedulas: list[str]`. Frontend envía `{ cedulas: cedulasNorm }` (array de cédulas únicas, longitud ≥ 5). Coincide.
- **Response:** Backend devuelve `{"prestamos": resultado}` donde `resultado` es un dict con claves = cédulas enviadas (tras strip, sin duplicados). Frontend usa `(response)?.prestamos || {}` y construye el mapa por cédula; las claves son las mismas que las enviadas. Coincide.

---

## Crear pago (POST /api/v1/pagos/)

- **Body:** Backend `PagoCreate`: `cedula_cliente`, `prestamo_id`, `fecha_pago`, `monto_pagado`, `numero_documento`, `institucion_bancaria`, `notas`, `conciliado`. Frontend envía exactamente esos campos. Coincide.
- **Nº documento:** Backend no elimina símbolos (€, $, Bs, etc.); solo normaliza notación científica. Frontend tampoco los quita; el valor del Excel se envía tal cual. Coincide.
- **Duplicados:** Backend devuelve **409** si ya existe un pago con el mismo `numero_documento`. Frontend trata 409 mostrando mensaje de documento duplicado y ofreciendo "Revisar Pagos". Coincide.

---

## Resumen

- Rutas de batch y de creación de pago están alineadas entre backend y frontend.
- Formato de request/response del batch y del POST de pago es coherente.
- Comportamiento de documento (conservar símbolos) y de duplicados (409 + flujo Revisar Pagos) es coherente.
