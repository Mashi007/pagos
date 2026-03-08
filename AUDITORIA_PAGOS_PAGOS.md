# Auditoria integral: /pagos/pagos (RapiCredit)
Alcance: https://rapicredit.onrender.com/pagos/pagos
Fecha: 2025-03-08

## 1. Resumen
- Conexion BD: Todos los endpoints usan Depends(get_db). OK.
- Tablas: Pago, Prestamo, Cliente, Cuota, CuotaPago, RevisarPago, PagoConError. OK.
- Datos reales: Sin stubs. OK.
- Health: Incluir tablas pagos, pagos_con_errores, revisar_pagos, cuota_pagos en GET /health/db.

## 2. Endpoints pagos (backend)
GET /api/v1/pagos - listado (Pago, RevisarPago, Prestamo)
GET /api/v1/pagos/ultimos - Pago, Prestamo, Cliente, Cuota
POST /api/v1/pagos/upload - Pago, PagoConError, Cliente, Prestamo
POST /api/v1/pagos/validar-filas-batch - Pago, Cliente, Prestamo
POST /api/v1/pagos/guardar-fila-editable - Cliente, Prestamo, Pago
POST /api/v1/pagos/conciliacion/upload - Pago, Cliente, Prestamo
GET /api/v1/pagos/kpis - Cuota, Prestamo, Cliente
GET /api/v1/pagos/stats - Cuota, Prestamo, Cliente
POST /api/v1/pagos/revisar-pagos/mover - RevisarPago, Pago
GET /api/v1/pagos/{id} - Pago
POST /api/v1/pagos - Cliente, Pago
PUT /api/v1/pagos/{id} - Pago
DELETE /api/v1/pagos/{id} - Pago
POST /api/v1/pagos/{id}/aplicar-cuotas - Pago, Cuota, CuotaPago

## 3. Tablas dependientes
pagos -> prestamos (prestamo_id), clientes (cedula_cliente)
prestamos -> clientes (cliente_id)
cuotas -> prestamos (prestamo_id)
cuota_pagos -> pagos, cuotas
revisar_pagos -> pagos
pagos_con_errores: tabla independiente (errores carga masiva)

## 4. Recomendacion health
En backend/app/api/v1/endpoints/health.py anadir a CRITICAL_TABLES:
"pagos", "pagos_con_errores", "revisar_pagos", "cuota_pagos"
