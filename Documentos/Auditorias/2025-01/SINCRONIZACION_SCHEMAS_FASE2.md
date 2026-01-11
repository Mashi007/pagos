====================================================================================================
REPORTE: SINCRONIZACIÓN SCHEMAS PYDANTIC CON MODELOS ORM
====================================================================================================

Fecha: 2026-01-11 11:39:26

RESUMEN EJECUTIVO
----------------------------------------------------------------------------------------------------
Campos faltantes en schemas: 32
Campos calculados documentados: 14
Schemas sin archivo: 0

CAMPOS FALTANTES EN SCHEMAS (Agregar)
----------------------------------------------------------------------------------------------------
  Modelo: cliente (tabla: clientes)
  Campos a agregar (2):
    - id
    - usuario_registro

  Modelo: amortizacion (tabla: cuotas)
  Campos a agregar (8):
    - capital_pendiente
    - dias_mora
    - estado
    - id
    - interes_pendiente
    - monto_mora
    - observaciones
    - total_pagado

  Modelo: pago (tabla: pagos)
  Campos a agregar (9):
    - activo
    - conciliado
    - documento_nombre
    - documento_ruta
    - documento_tipo
    - fecha_actualizacion
    - fecha_conciliacion
    - fecha_registro
    - verificado_concordancia

  Modelo: prestamo (tabla: prestamos)
  Campos a agregar (10):
    - cliente_id
    - cuota_periodo
    - fecha_aprobacion
    - fecha_base_calculo
    - fecha_requerimiento
    - nombres
    - numero_cuotas
    - observaciones
    - tasa_interes
    - usuario_aprobador

  Modelo: user (tabla: users)
  Campos a agregar (2):
    - hashed_password
    - id

  Modelo: notificacion (tabla: notificaciones)
  Campos a agregar (1):
    - id

CAMPOS CALCULADOS (OK - Mantener solo en schemas)
----------------------------------------------------------------------------------------------------
  Modelo: amortizacion
  Campos calculados (13):
    - cuotas
    - cuotas_actualizadas
    - cuotas_afectadas
    - cuotas_pagadas
    - fecha_calculo
    - fecha_inicio
    - monto_financiado
    - monto_pago
    - numero_cuotas
    - resumen
    - tasa_interes
    - tasa_mora_diaria
    - tipo_amortizacion

  Modelo: user
  Campos calculados (1):
    - items

====================================================================================================
RECOMENDACIONES
====================================================================================================

1. Agregar campos faltantes a schemas Response
2. Documentar campos calculados en comentarios
3. Verificar tipos de datos coinciden
