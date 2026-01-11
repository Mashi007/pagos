# 🔍 AUDITORÍA INTEGRAL DEL ENDPOINT /pagos

**Fecha:** 2026-01-10 20:55:52
**Endpoint:** https://rapicredit.onrender.com/pagos
**Endpoint API:** https://rapicredit.onrender.com/api/v1/pagos

## 📊 RESUMEN EJECUTIVO

**Verificaciones exitosas:** 4/8

## 📋 DETALLES DE VERIFICACIONES

### ✅ Conexion Bd

**Estado:** exitoso

**Mensaje:** Conexión establecida correctamente

### ✅ Estructura Tabla

**Estado:** exitoso

### ✅ Datos Bd

**Estado:** exitoso

### ⚠️ Endpoint Backend

**Estado:** parcial

### ❌ Rendimiento

**Estado:** error

**Mensaje:** (psycopg2.errors.UndefinedColumn) column prestamos_1.valor_activo does not exist
LINE 1: ...dula, prestamos_1.nombres AS prestamos_1_nombres, prestamos_...
                                                             ^

[SQL: SELECT pagos.id AS pagos_id, pagos.cedula AS pagos_cedula, pagos.cliente_id AS pagos_cliente_id, pagos.prestamo_id AS pagos_prestamo_id, pagos.numero_cuota AS pagos_numero_cuota, pagos.fecha_pago AS pagos_fecha_pago, pagos.fecha_registro AS pagos_fecha_registro, pagos.monto_pagado AS pagos_monto_pagado, pagos.numero_documento AS pagos_numero_documento, pagos.institucion_bancaria AS pagos_institucion_bancaria, pagos.documento_nombre AS pagos_documento_nombre, pagos.documento_tipo AS pagos_documento_tipo, pagos."documento_tamaño" AS "pagos_documento_tamaño", pagos.documento_ruta AS pagos_documento_ruta, pagos.conciliado AS pagos_conciliado, pagos.fecha_conciliacion AS pagos_fecha_conciliacion, pagos.estado AS pagos_estado, pagos.activo AS pagos_activo, pagos.notas AS pagos_notas, pagos.usuario_registro AS pagos_usuario_registro, pagos.fecha_actualizacion AS pagos_fecha_actualizacion, pagos.verificado_concordancia AS pagos_verificado_concordancia, clientes_1.id AS clientes_1_id, clientes_1.cedula AS clientes_1_cedula, clientes_1.nombres AS clientes_1_nombres, clientes_1.telefono AS clientes_1_telefono, clientes_1.email AS clientes_1_email, clientes_1.direccion AS clientes_1_direccion, clientes_1.fecha_nacimiento AS clientes_1_fecha_nacimiento, clientes_1.ocupacion AS clientes_1_ocupacion, clientes_1.estado AS clientes_1_estado, clientes_1.activo AS clientes_1_activo, clientes_1.fecha_registro AS clientes_1_fecha_registro, clientes_1.fecha_actualizacion AS clientes_1_fecha_actualizacion, clientes_1.usuario_registro AS clientes_1_usuario_registro, clientes_1.notas AS clientes_1_notas, prestamos_1.id AS prestamos_1_id, prestamos_1.cliente_id AS prestamos_1_cliente_id, prestamos_1.cedula AS prestamos_1_cedula, prestamos_1.nombres AS prestamos_1_nombres, prestamos_1.valor_activo AS prestamos_1_valor_activo, prestamos_1.total_financiamiento AS prestamos_1_total_financiamiento, prestamos_1.fecha_requerimiento AS prestamos_1_fecha_requerimiento, prestamos_1.modalidad_pago AS prestamos_1_modalidad_pago, prestamos_1.numero_cuotas AS prestamos_1_numero_cuotas, prestamos_1.cuota_periodo AS prestamos_1_cuota_periodo, prestamos_1.tasa_interes AS prestamos_1_tasa_interes, prestamos_1.fecha_base_calculo AS prestamos_1_fecha_base_calculo, prestamos_1.producto AS prestamos_1_producto, prestamos_1.producto_financiero AS prestamos_1_producto_financiero, prestamos_1.concesionario AS prestamos_1_concesionario, prestamos_1.analista AS prestamos_1_analista, prestamos_1.modelo_vehiculo AS prestamos_1_modelo_vehiculo, prestamos_1.concesionario_id AS prestamos_1_concesionario_id, prestamos_1.analista_id AS prestamos_1_analista_id, prestamos_1.modelo_vehiculo_id AS prestamos_1_modelo_vehiculo_id, prestamos_1.estado AS prestamos_1_estado, prestamos_1.usuario_proponente AS prestamos_1_usuario_proponente, prestamos_1.usuario_aprobador AS prestamos_1_usuario_aprobador, prestamos_1.usuario_autoriza AS prestamos_1_usuario_autoriza, prestamos_1.observaciones AS prestamos_1_observaciones, prestamos_1.fecha_registro AS prestamos_1_fecha_registro, prestamos_1.fecha_aprobacion AS prestamos_1_fecha_aprobacion, prestamos_1.informacion_desplegable AS prestamos_1_informacion_desplegable, prestamos_1.ml_impago_nivel_riesgo_manual AS prestamos_1_ml_impago_nivel_riesgo_manual, prestamos_1.ml_impago_probabilidad_manual AS prestamos_1_ml_impago_probabilidad_manual, prestamos_1.ml_impago_nivel_riesgo_calculado AS prestamos_1_ml_impago_nivel_riesgo_calculado, prestamos_1.ml_impago_probabilidad_calculada AS prestamos_1_ml_impago_probabilidad_calculada, prestamos_1.ml_impago_calculado_en AS prestamos_1_ml_impago_calculado_en, prestamos_1.ml_impago_modelo_id AS prestamos_1_ml_impago_modelo_id, prestamos_1.fecha_actualizacion AS prestamos_1_fecha_actualizacion 
FROM pagos LEFT OUTER JOIN clientes AS clientes_1 ON clientes_1.id = pagos.cliente_id LEFT OUTER JOIN prestamos AS prestamos_1 ON prestamos_1.id = pagos.prestamo_id 
 LIMIT %(param_1)s]
[parameters: {'param_1': 10}]
(Background on this error at: https://sqlalche.me/e/20/f405)

### ⚠️ Indices

**Estado:** advertencia

### ✅ Validaciones

**Estado:** exitoso

### ⚠️ Conectividad Produccion

**Estado:** parcial

## ⚠️ ADVERTENCIAS

- Índices faltantes: ix_pagos_fecha_registro

