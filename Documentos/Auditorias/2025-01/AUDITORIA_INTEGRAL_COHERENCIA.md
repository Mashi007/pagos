====================================================================================================
AUDITORÍA INTEGRAL: COHERENCIA BD - BACKEND - FRONTEND
====================================================================================================

Fecha: 2026-01-11 11:28:51

RESUMEN EJECUTIVO
----------------------------------------------------------------------------------------------------
Modelos ORM analizados: 29
Schemas analizados: 16
Modelos en frontend: 0
Discrepancias encontradas: 246

DISCREPANCIAS POR SEVERIDAD
----------------------------------------------------------------------------------------------------
ALTA (Críticas): 109
MEDIA (Importantes): 137
BAJA (Advertencias): 0

DETALLE DE DISCREPANCIAS
====================================================================================================

[ALTA] 109 discrepancias
----------------------------------------------------------------------------------------------------
  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: total_mora
  Descripción: Campo total_mora existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: monto_pago
  Descripción: Campo monto_pago existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: tipo_amortizacion
  Descripción: Campo tipo_amortizacion existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: numero_cuotas
  Descripción: Campo numero_cuotas existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: tasa_mora_diaria
  Descripción: Campo tasa_mora_diaria existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: cuotas
  Descripción: Campo cuotas existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: monto_financiado
  Descripción: Campo monto_financiado existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: fecha_calculo
  Descripción: Campo fecha_calculo existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: fecha_inicio
  Descripción: Campo fecha_inicio existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: mensaje
  Descripción: Campo mensaje existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: cuotas_pagadas
  Descripción: Campo cuotas_pagadas existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: tasa_interes
  Descripción: Campo tasa_interes existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: cuotas_afectadas
  Descripción: Campo cuotas_afectadas existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: cuotas_vencidas
  Descripción: Campo cuotas_vencidas existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: nuevo_saldo_pendiente
  Descripción: Campo nuevo_saldo_pendiente existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: resumen
  Descripción: Campo resumen existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: cuotas_actualizadas
  Descripción: Campo cuotas_actualizadas existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: total_mora_calculada
  Descripción: Campo total_mora_calculada existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: proximas_cuotas
  Descripción: Campo proximas_cuotas existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: amortizacion
  Campo: cuotas_pendientes
  Descripción: Campo cuotas_pendientes existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: analista
  Campo: items
  Descripción: Campo items existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: analista
  Campo: pages
  Descripción: Campo pages existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: analista
  Campo: size
  Descripción: Campo size existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: analista
  Campo: page
  Descripción: Campo page existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: analista
  Campo: total
  Descripción: Campo total existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: aprobacion
  Campo: datos_adicionales
  Descripción: Campo datos_adicionales existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: aprobacion
  Campo: tipo
  Descripción: Campo tipo existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: aprobacion
  Campo: monto
  Descripción: Campo monto existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: aprobacion
  Campo: descripcion
  Descripción: Campo descripcion existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: total_acciones
  Descripción: Campo total_acciones existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: registro_id
  Descripción: Campo registro_id existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: total_pages
  Descripción: Campo total_pages existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: campo
  Descripción: Campo campo existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: acciones_hoy
  Descripción: Campo acciones_hoy existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: descripcion
  Descripción: Campo descripcion existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: resultado
  Descripción: Campo resultado existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: acciones_por_usuario
  Descripción: Campo acciones_por_usuario existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: total
  Descripción: Campo total existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: modulo
  Descripción: Campo modulo existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: items
  Descripción: Campo items existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: acciones_este_mes
  Descripción: Campo acciones_este_mes existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: page_size
  Descripción: Campo page_size existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: acciones_por_modulo
  Descripción: Campo acciones_por_modulo existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: usuario_email
  Descripción: Campo usuario_email existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: page
  Descripción: Campo page existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: tabla
  Descripción: Campo tabla existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: auditoria
  Campo: acciones_esta_semana
  Descripción: Campo acciones_esta_semana existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: fecha_registro_hasta
  Descripción: Campo fecha_registro_hasta existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: order_direction
  Descripción: Campo order_direction existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: total_pages
  Descripción: Campo total_pages existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: puede_reasignar_analista
  Descripción: Campo puede_reasignar_analista existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: confirmacion
  Descripción: Campo confirmacion existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: comentarios
  Descripción: Campo comentarios existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: search_text
  Descripción: Campo search_text existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: puede_registrar_pago
  Descripción: Campo puede_registrar_pago existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: puede_generar_estado_cuenta
  Descripción: Campo puede_generar_estado_cuenta existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: puede_enviar_recordatorio
  Descripción: Campo puede_enviar_recordatorio existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: cliente_data
  Descripción: Campo cliente_data existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: items
  Descripción: Campo items existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: page_size
  Descripción: Campo page_size existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: puede_modificar_financiamiento
  Descripción: Campo puede_modificar_financiamiento existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: order_by
  Descripción: Campo order_by existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: page
  Descripción: Campo page existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: fecha_registro_desde
  Descripción: Campo fecha_registro_desde existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: cliente
  Campo: total
  Descripción: Campo total existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: concesionario
  Campo: items
  Descripción: Campo items existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: concesionario
  Campo: pages
  Descripción: Campo pages existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: concesionario
  Campo: size
  Descripción: Campo size existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: concesionario
  Campo: page
  Descripción: Campo page existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: concesionario
  Campo: total
  Descripción: Campo total existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: modelo_vehiculo
  Campo: total_pages
  Descripción: Campo total_pages existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: modelo_vehiculo
  Campo: items
  Descripción: Campo items existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: modelo_vehiculo
  Campo: page_size
  Descripción: Campo page_size existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: modelo_vehiculo
  Campo: page
  Descripción: Campo page existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: modelo_vehiculo
  Campo: total
  Descripción: Campo total existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion
  Campo: activa
  Descripción: Campo activa existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion
  Campo: template_id
  Descripción: Campo template_id existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion
  Campo: variables_disponibles
  Descripción: Campo variables_disponibles existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion
  Campo: descripcion
  Descripción: Campo descripcion existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion
  Campo: variables
  Descripción: Campo variables existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion
  Campo: zona_horaria
  Descripción: Campo zona_horaria existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion
  Campo: cuerpo
  Descripción: Campo cuerpo existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion
  Campo: nombre
  Descripción: Campo nombre existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion_plantilla
  Campo: cliente_id
  Descripción: Campo cliente_id existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion_plantilla
  Campo: template_id
  Descripción: Campo template_id existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: notificacion_plantilla
  Campo: variables
  Descripción: Campo variables existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: pago
  Campo: monto_cuota
  Descripción: Campo monto_cuota existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: pago
  Campo: total_pagado
  Descripción: Campo total_pagado existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: campo_modificado
  Descripción: Campo campo_modificado existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: valor_nuevo
  Descripción: Campo valor_nuevo existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: usuario
  Descripción: Campo usuario existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: accion
  Descripción: Campo accion existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: fecha_cambio
  Descripción: Campo fecha_cambio existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: valor_anterior
  Descripción: Campo valor_anterior existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: estado_anterior
  Descripción: Campo estado_anterior existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: estado_nuevo
  Descripción: Campo estado_nuevo existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: prestamo
  Campo: prestamo_id
  Descripción: Campo prestamo_id existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: token_type
  Descripción: Campo token_type existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: sub
  Descripción: Campo sub existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: user
  Descripción: Campo user existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: access_token
  Descripción: Campo access_token existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: remember_me
  Descripción: Campo remember_me existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: iat
  Descripción: Campo iat existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: total
  Descripción: Campo total existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: items
  Descripción: Campo items existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: page_size
  Descripción: Campo page_size existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: exp
  Descripción: Campo exp existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: page
  Descripción: Campo page existe en schema pero no en modelo ORM

  Tipo: SCHEMA_SIN_ORM
  Tabla/Modelo: user
  Campo: password
  Descripción: Campo password existe en schema pero no en modelo ORM


[MEDIA] 137 discrepancias
----------------------------------------------------------------------------------------------------
  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: actualizado_en
  Descripción: Columna actualizado_en existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: total_pagado
  Descripción: Columna total_pagado existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: monto_morosidad
  Descripción: Columna monto_morosidad existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: capital_pendiente
  Descripción: Columna capital_pendiente existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: es_cuota_especial
  Descripción: Columna es_cuota_especial existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: creado_en
  Descripción: Columna creado_en existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: dias_mora
  Descripción: Columna dias_mora existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: interes_pendiente
  Descripción: Columna interes_pendiente existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: monto_mora
  Descripción: Columna monto_mora existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: amortizacion
  Campo: dias_morosidad
  Descripción: Columna dias_morosidad existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: analista
  Campo: updated_at
  Descripción: Columna updated_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: analista
  Campo: created_at
  Descripción: Columna created_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: analista
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: entidad_id
  Descripción: Columna entidad_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: created_at
  Descripción: Columna created_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: revisor_id
  Descripción: Columna revisor_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: updated_at
  Descripción: Columna updated_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: notificado_solicitante
  Descripción: Columna notificado_solicitante existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: solicitante_id
  Descripción: Columna solicitante_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: entidad
  Descripción: Columna entidad existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: tamaño_archivo
  Descripción: Columna tamaño_archivo existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: archivo_evidencia
  Descripción: Columna archivo_evidencia existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: fecha_limite
  Descripción: Columna fecha_limite existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: resultado
  Descripción: Columna resultado existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: fecha_aprobacion
  Descripción: Columna fecha_aprobacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: tiempo_respuesta_horas
  Descripción: Columna tiempo_respuesta_horas existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: visto_por_admin
  Descripción: Columna visto_por_admin existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: tipo_archivo
  Descripción: Columna tipo_archivo existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: notificado_admin
  Descripción: Columna notificado_admin existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: estado
  Descripción: Columna estado existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: justificacion
  Descripción: Columna justificacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: fecha_solicitud
  Descripción: Columna fecha_solicitud existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: bloqueado_temporalmente
  Descripción: Columna bloqueado_temporalmente existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: tipo_solicitud
  Descripción: Columna tipo_solicitud existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: aprobacion
  Campo: prioridad
  Descripción: Columna prioridad existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: auditoria
  Campo: entidad_id
  Descripción: Columna entidad_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: auditoria
  Campo: fecha
  Descripción: Columna fecha existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: auditoria
  Campo: detalles
  Descripción: Columna detalles existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: auditoria
  Campo: exito
  Descripción: Columna exito existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: auditoria
  Campo: entidad
  Descripción: Columna entidad existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: auditoria
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: cliente
  Campo: fecha_registro
  Descripción: Columna fecha_registro existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: cliente
  Campo: fecha_actualizacion
  Descripción: Columna fecha_actualizacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: cliente
  Campo: usuario_registro
  Descripción: Columna usuario_registro existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: cliente
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: concesionario
  Campo: updated_at
  Descripción: Columna updated_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: concesionario
  Campo: created_at
  Descripción: Columna created_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: concesionario
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: modelo_vehiculo
  Campo: created_at
  Descripción: Columna created_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: modelo_vehiculo
  Campo: actualizado_por
  Descripción: Columna actualizado_por existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: modelo_vehiculo
  Campo: fecha_actualizacion
  Descripción: Columna fecha_actualizacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: modelo_vehiculo
  Campo: updated_at
  Descripción: Columna updated_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: modelo_vehiculo
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: max_intentos
  Descripción: Columna max_intentos existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: destinatario_email
  Descripción: Columna destinatario_email existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: enviada_en
  Descripción: Columna enviada_en existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: respuesta_servicio
  Descripción: Columna respuesta_servicio existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: mensaje
  Descripción: Columna mensaje existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: user_id
  Descripción: Columna user_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: creado_en
  Descripción: Columna creado_en existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: prioridad
  Descripción: Columna prioridad existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: categoria
  Descripción: Columna categoria existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: destinatario_telefono
  Descripción: Columna destinatario_telefono existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: destinatario_nombre
  Descripción: Columna destinatario_nombre existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: intentos
  Descripción: Columna intentos existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: actualizado_en
  Descripción: Columna actualizado_en existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: extra_data
  Descripción: Columna extra_data existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: estado
  Descripción: Columna estado existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: leida_en
  Descripción: Columna leida_en existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: programada_para
  Descripción: Columna programada_para existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion
  Campo: error_mensaje
  Descripción: Columna error_mensaje existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion_plantilla
  Campo: fecha_actualizacion
  Descripción: Columna fecha_actualizacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion_plantilla
  Campo: fecha_creacion
  Descripción: Columna fecha_creacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion_plantilla
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion_variable
  Campo: fecha_actualizacion
  Descripción: Columna fecha_actualizacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion_variable
  Campo: fecha_creacion
  Descripción: Columna fecha_creacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: notificacion_variable
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: documento_nombre
  Descripción: Columna documento_nombre existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: monto_capital
  Descripción: Columna monto_capital existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: documento
  Descripción: Columna documento existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: banco
  Descripción: Columna banco existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: comprobante
  Descripción: Columna comprobante existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: tipo_pago
  Descripción: Columna tipo_pago existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: observaciones
  Descripción: Columna observaciones existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: monto_total
  Descripción: Columna monto_total existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: verificado_concordancia
  Descripción: Columna verificado_concordancia existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: monto_cuota_programado
  Descripción: Columna monto_cuota_programado existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: documento_tipo
  Descripción: Columna documento_tipo existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: creado_en
  Descripción: Columna creado_en existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: dias_mora
  Descripción: Columna dias_mora existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: hora_pago
  Descripción: Columna hora_pago existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: usuario_registro
  Descripción: Columna usuario_registro existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: fecha_conciliacion
  Descripción: Columna fecha_conciliacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: notas
  Descripción: Columna notas existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: fecha_actualizacion
  Descripción: Columna fecha_actualizacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: codigo_pago
  Descripción: Columna codigo_pago existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: monto_interes
  Descripción: Columna monto_interes existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: metodo_pago
  Descripción: Columna metodo_pago existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: fecha_registro
  Descripción: Columna fecha_registro existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: documento_tamaño
  Descripción: Columna documento_tamaño existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: monto
  Descripción: Columna monto existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: descuento
  Descripción: Columna descuento existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: conciliado
  Descripción: Columna conciliado existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: tasa_mora
  Descripción: Columna tasa_mora existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: cliente_id
  Descripción: Columna cliente_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: numero_operacion
  Descripción: Columna numero_operacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: referencia_pago
  Descripción: Columna referencia_pago existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: documento_ruta
  Descripción: Columna documento_ruta existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: activo
  Descripción: Columna activo existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: monto_mora
  Descripción: Columna monto_mora existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: pago
  Campo: institucion_bancaria
  Descripción: Columna institucion_bancaria existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: modelo_vehiculo_id
  Descripción: Columna modelo_vehiculo_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: nombres
  Descripción: Columna nombres existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: ml_impago_nivel_riesgo_calculado
  Descripción: Columna ml_impago_nivel_riesgo_calculado existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: usuario_autoriza
  Descripción: Columna usuario_autoriza existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: concesionario_id
  Descripción: Columna concesionario_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: usuario_aprobador
  Descripción: Columna usuario_aprobador existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: producto
  Descripción: Columna producto existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: fecha_actualizacion
  Descripción: Columna fecha_actualizacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: analista_id
  Descripción: Columna analista_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: fecha_registro
  Descripción: Columna fecha_registro existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: ml_impago_probabilidad_manual
  Descripción: Columna ml_impago_probabilidad_manual existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: ml_impago_probabilidad_calculada
  Descripción: Columna ml_impago_probabilidad_calculada existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: fecha_aprobacion
  Descripción: Columna fecha_aprobacion existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: ml_impago_nivel_riesgo_manual
  Descripción: Columna ml_impago_nivel_riesgo_manual existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: ml_impago_calculado_en
  Descripción: Columna ml_impago_calculado_en existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: cliente_id
  Descripción: Columna cliente_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: producto_financiero
  Descripción: Columna producto_financiero existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: ml_impago_modelo_id
  Descripción: Columna ml_impago_modelo_id existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: prestamo
  Campo: informacion_desplegable
  Descripción: Columna informacion_desplegable existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: user
  Campo: hashed_password
  Descripción: Columna hashed_password existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: user
  Campo: created_at
  Descripción: Columna created_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: user
  Campo: updated_at
  Descripción: Columna updated_at existe en modelo ORM pero no en schema Pydantic

  Tipo: ORM_SIN_SCHEMA
  Tabla/Modelo: user
  Campo: id
  Descripción: Columna id existe en modelo ORM pero no en schema Pydantic

====================================================================================================
RECOMENDACIONES PARA CORRECCIÓN
====================================================================================================

[ORM_SIN_SCHEMA] 137 casos
----------------------------------------------------------------------------------------------------
  ACCIÓN: Agregar campos faltantes a los schemas Pydantic
  IMPACTO: Los endpoints no pueden recibir/enviar estos campos
  EJEMPLO:
    - Agregar campo 'actualizado_en' al schema amortizacion
    - Agregar campo 'total_pagado' al schema amortizacion
    - Agregar campo 'monto_morosidad' al schema amortizacion

[SCHEMA_SIN_ORM] 109 casos
----------------------------------------------------------------------------------------------------
  ACCIÓN: Agregar columnas faltantes a los modelos ORM o remover del schema
  IMPACTO: CRÍTICO - Los schemas esperan campos que no existen en BD
  EJEMPLO:
    - Verificar campo 'total_mora' en modelo amortizacion
    - Verificar campo 'monto_pago' en modelo amortizacion
    - Verificar campo 'tipo_amortizacion' en modelo amortizacion

====================================================================================================
SCRIPT SQL PARA VERIFICACIÓN EN BD
====================================================================================================

Ejecutar el siguiente script SQL para obtener estructura real de la BD:


-- ============================================================================
-- Script SQL generado para auditoría de coherencia
-- Ejecutar este script para obtener estructura real de la base de datos
-- ============================================================================

-- Obtener todas las columnas de las tablas principales
SELECT 
    table_name AS tabla,
    column_name AS columna,
    data_type AS tipo_dato,
    character_maximum_length AS longitud_maxima,
    numeric_precision AS precision_numerica,
    numeric_scale AS escala_numerica,
    is_nullable AS nullable,
    column_default AS valor_por_defecto
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN ('pagos', 'cuotas', 'prestamos', 'clientes', 'amortizacion', 'notificaciones', 'users')
ORDER BY table_name, ordinal_position;


====================================================================================================
PLAN DE ACCIÓN RECOMENDADO
====================================================================================================

1. PRIORIDAD ALTA - Corregir discrepancias críticas:
   - Verificar campos en schemas que no existen en ORM
   - Verificar campos en frontend que no existen en ORM
   - Ejecutar script SQL para comparar con BD real

2. PRIORIDAD MEDIA - Sincronizar schemas con ORM:
   - Agregar campos faltantes a schemas
   - Verificar tipos de datos coinciden

3. PRIORIDAD BAJA - Optimizar uso de campos:
   - Evaluar si campos no usados deben usarse
   - Documentar campos disponibles pero no usados

4. VERIFICACIÓN FINAL:
   - Ejecutar este script nuevamente después de correcciones
   - Comparar resultados con estructura real de BD
   - Documentar decisiones sobre campos no usados

====================================================================================================
FIN DEL REPORTE
====================================================================================================