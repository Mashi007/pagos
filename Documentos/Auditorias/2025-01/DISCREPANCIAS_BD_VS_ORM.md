====================================================================================================
REPORTE DE DISCREPANCIAS: BASE DE DATOS vs MODELOS ORM
====================================================================================================

Fecha: 2026-01-11 11:33:47

RESUMEN EJECUTIVO
----------------------------------------------------------------------------------------------------
Total discrepancias: 45
  - ALTA (Críticas): 4
  - MEDIA (Importantes): 41

DISCREPANCIAS POR TIPO
====================================================================================================

[NULLABLE_DIFERENTE] 41 casos
----------------------------------------------------------------------------------------------------
  Tabla: clientes
  Columna: cedula
  Severidad: MEDIA
  Descripción: Columna cedula: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: clientes
  Columna: nombres
  Severidad: MEDIA
  Descripción: Columna nombres: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: clientes
  Columna: telefono
  Severidad: MEDIA
  Descripción: Columna telefono: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: clientes
  Columna: email
  Severidad: MEDIA
  Descripción: Columna email: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: clientes
  Columna: ocupacion
  Severidad: MEDIA
  Descripción: Columna ocupacion: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: clientes
  Columna: estado
  Severidad: MEDIA
  Descripción: Columna estado: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: clientes
  Columna: usuario_registro
  Severidad: MEDIA
  Descripción: Columna usuario_registro: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: prestamo_id
  Severidad: MEDIA
  Descripción: Columna prestamo_id: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: monto_cuota
  Severidad: MEDIA
  Descripción: Columna monto_cuota: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: monto_capital
  Severidad: MEDIA
  Descripción: Columna monto_capital: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: monto_interes
  Severidad: MEDIA
  Descripción: Columna monto_interes: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: saldo_capital_inicial
  Severidad: MEDIA
  Descripción: Columna saldo_capital_inicial: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: saldo_capital_final
  Severidad: MEDIA
  Descripción: Columna saldo_capital_final: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: capital_pendiente
  Severidad: MEDIA
  Descripción: Columna capital_pendiente: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: interes_pendiente
  Severidad: MEDIA
  Descripción: Columna interes_pendiente: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: cuotas
  Columna: estado
  Severidad: MEDIA
  Descripción: Columna estado: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: pagos
  Columna: monto_pagado
  Severidad: MEDIA
  Descripción: Columna monto_pagado: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: pagos
  Columna: fecha_registro
  Severidad: MEDIA
  Descripción: Columna fecha_registro: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: pagos
  Columna: referencia_pago
  Severidad: MEDIA
  Descripción: Columna referencia_pago: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: pagos
  Columna: verificado_concordancia
  Severidad: MEDIA
  Descripción: Columna verificado_concordancia: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: cliente_id
  Severidad: MEDIA
  Descripción: Columna cliente_id: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: cedula
  Severidad: MEDIA
  Descripción: Columna cedula: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: nombres
  Severidad: MEDIA
  Descripción: Columna nombres: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: total_financiamiento
  Severidad: MEDIA
  Descripción: Columna total_financiamiento: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: modalidad_pago
  Severidad: MEDIA
  Descripción: Columna modalidad_pago: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: cuota_periodo
  Severidad: MEDIA
  Descripción: Columna cuota_periodo: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: tasa_interes
  Severidad: MEDIA
  Descripción: Columna tasa_interes: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: producto
  Severidad: MEDIA
  Descripción: Columna producto: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: producto_financiero
  Severidad: MEDIA
  Descripción: Columna producto_financiero: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: estado
  Severidad: MEDIA
  Descripción: Columna estado: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: prestamos
  Columna: usuario_proponente
  Severidad: MEDIA
  Descripción: Columna usuario_proponente: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: users
  Columna: email
  Severidad: MEDIA
  Descripción: Columna email: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: users
  Columna: nombre
  Severidad: MEDIA
  Descripción: Columna nombre: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: users
  Columna: apellido
  Severidad: MEDIA
  Descripción: Columna apellido: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: users
  Columna: hashed_password
  Severidad: MEDIA
  Descripción: Columna hashed_password: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: users
  Columna: rol
  Severidad: MEDIA
  Descripción: Columna rol: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: users
  Columna: created_at
  Severidad: MEDIA
  Descripción: Columna created_at: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: notificaciones
  Columna: tipo
  Severidad: MEDIA
  Descripción: Columna tipo: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: notificaciones
  Columna: categoria
  Severidad: MEDIA
  Descripción: Columna categoria: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: notificaciones
  Columna: estado
  Severidad: MEDIA
  Descripción: Columna estado: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: notificaciones
  Columna: prioridad
  Severidad: MEDIA
  Descripción: Columna prioridad: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True


[ORM_SIN_BD] 4 casos
----------------------------------------------------------------------------------------------------
  Tabla: prestamos
  Columna: ml_impago_nivel_riesgo_calculado
  Severidad: ALTA
  Descripción: Columna ml_impago_nivel_riesgo_calculado existe en modelo ORM pero no en BD prestamos

  Tabla: prestamos
  Columna: ml_impago_probabilidad_calculada
  Severidad: ALTA
  Descripción: Columna ml_impago_probabilidad_calculada existe en modelo ORM pero no en BD prestamos

  Tabla: prestamos
  Columna: ml_impago_calculado_en
  Severidad: ALTA
  Descripción: Columna ml_impago_calculado_en existe en modelo ORM pero no en BD prestamos

  Tabla: prestamos
  Columna: ml_impago_modelo_id
  Severidad: ALTA
  Descripción: Columna ml_impago_modelo_id existe en modelo ORM pero no en BD prestamos

====================================================================================================
RECOMENDACIONES PARA CORRECCIÓN
====================================================================================================

2. COLUMNAS EN MODELO ORM SIN BD (ALTA PRIORIDAD)
----------------------------------------------------------------------------------------------------
  Estas columnas están en modelos ORM pero no existen en BD.
  ACCIÓN: Verificar si deben agregarse a BD o removerse del modelo.

  - prestamos.ml_impago_nivel_riesgo_calculado
  - prestamos.ml_impago_probabilidad_calculada
  - prestamos.ml_impago_calculado_en
  - prestamos.ml_impago_modelo_id

3. DIFERENCIAS EN NULLABLE (MEDIA PRIORIDAD)
----------------------------------------------------------------------------------------------------
  Estas columnas tienen diferente configuración de nullable.
  ACCIÓN: Sincronizar nullable entre BD y ORM.

  - clientes.cedula: BD=False, ORM=True
  - clientes.nombres: BD=False, ORM=True
  - clientes.telefono: BD=False, ORM=True
  - clientes.email: BD=False, ORM=True
  - clientes.ocupacion: BD=False, ORM=True
  - clientes.estado: BD=False, ORM=True
  - clientes.usuario_registro: BD=False, ORM=True
  - cuotas.prestamo_id: BD=False, ORM=True
  - cuotas.monto_cuota: BD=False, ORM=True
  - cuotas.monto_capital: BD=False, ORM=True

====================================================================================================
PLAN DE ACCIÓN
====================================================================================================

1. PRIORIDAD ALTA - Corregir discrepancias críticas:
   - Agregar columnas faltantes en modelos ORM
   - Verificar columnas en ORM que no existen en BD

2. PRIORIDAD MEDIA - Sincronizar configuración:
   - Corregir diferencias en nullable
   - Corregir diferencias en longitudes

3. VERIFICACIÓN:
   - Ejecutar este script nuevamente después de correcciones
   - Verificar que no haya errores en aplicación

====================================================================================================
FIN DEL REPORTE
====================================================================================================