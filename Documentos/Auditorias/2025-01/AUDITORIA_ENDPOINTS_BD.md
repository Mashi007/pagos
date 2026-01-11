================================================================================
AUDITORÍA DE ENDPOINTS QUE DEPENDEN DE BASE DE DATOS
================================================================================

Fecha: 2026-01-11 11:27:31

ESTADISTICAS GENERALES
--------------------------------------------------------------------------------
Total de archivos analizados: 34
Archivos con endpoints: 22
Total de endpoints con DB: 213

MODELOS MAS USADOS
--------------------------------------------------------------------------------
  Prestamo: 8 archivo(s)
  Cliente: 5 archivo(s)
  Cuota: 3 archivo(s)
  Pago: 3 archivo(s)
  PrestamoAuditoria: 2 archivo(s)
  PagoAuditoria: 2 archivo(s)
  Auditoria: 2 archivo(s)
  User: 2 archivo(s)
  ModeloVehiculo: 2 archivo(s)
  Notificacion: 2 archivo(s)
  Aprobacion: 2 archivo(s)
  Analista: 1 archivo(s)
  ModeloImpagoCuotas: 1 archivo(s)
  Concesionario: 1 archivo(s)
  AIPromptVariable: 1 archivo(s)
  DocumentoAI: 1 archivo(s)
  ConfiguracionSistema: 1 archivo(s)
  DashboardMorosidadMensual: 1 archivo(s)
  NotificacionPlantilla: 1 archivo(s)
  NotificacionVariable: 1 archivo(s)

COLUMNAS SINCRONIZADAS EN USO
--------------------------------------------------------------------------------
Columnas Pago usadas: 1 de 21
  monto

Columnas Cuota usadas: 0 de 2
  [ADVERTENCIA] Ninguna columna sincronizada esta siendo usada

Columnas Prestamo ML usadas: 6 de 6
  ml_impago_calculado_en, ml_impago_modelo_id, ml_impago_nivel_riesgo_calculado, ml_impago_nivel_riesgo_manual, ml_impago_probabilidad_calculada, ml_impago_probabilidad_manual

[ADVERTENCIA] COLUMNAS SINCRONIZADAS NO USADAS
--------------------------------------------------------------------------------
Columnas Pago no usadas (20):
  banco, codigo_pago, comprobante, creado_en, descuento, dias_mora, documento, fecha_vencimiento, hora_pago, metodo_pago, monto_capital, monto_cuota_programado, monto_interes, monto_mora, monto_total, numero_operacion, observaciones, referencia_pago, tasa_mora, tipo_pago

Columnas Cuota no usadas (2):
  actualizado_en, creado_en

Columnas Prestamo ML no usadas (0):
  ✅ Todas las columnas están en uso

DETALLE POR ARCHIVO
================================================================================

[ARCHIVO] api\v1\endpoints\configuracion.py
--------------------------------------------------------------------------------
  Endpoints con DB: 36
  Modelos usados: AIPromptVariable, ConfiguracionSistema, DocumentoAI, Prestamo, User
  Endpoints:
    - GET /sistema/completa (obtener_configuracion_completa)
      Modelos: ConfiguracionSistema
    - GET /sistema/{clave} (obtener_configuracion_por_clave)
      Modelos: ConfiguracionSistema
    - GET /sistema/categoria/{categoria} (obtener_configuracion_por_categoria)
      Modelos: ConfiguracionSistema
    - PUT /sistema/{clave} (actualizar_configuracion)
      Modelos: ConfiguracionSistema
    - DELETE /sistema/{clave} (eliminar_configuracion)
      Modelos: ConfiguracionSistema
    - GET /general (obtener_configuracion_general)
      Modelos: ConfiguracionSistema
    - GET /email/configuracion (obtener_configuracion_email)
    - PUT /email/configuracion (actualizar_configuracion_email)
      Modelos: ConfiguracionSistema
    - GET /notificaciones/envios (obtener_configuracion_envios)
      Modelos: ConfiguracionSistema
    - PUT /notificaciones/envios (actualizar_configuracion_envios)
      Modelos: ConfiguracionSistema
    - GET /email/estado (verificar_estado_configuracion_email)
      Modelos: ConfiguracionSistema
    - POST /email/probar (probar_configuracion_email)
      Modelos: ConfiguracionSistema
    - PUT /general (actualizar_configuracion_general)
    - GET /whatsapp/configuracion (obtener_configuracion_whatsapp)
    - PUT /whatsapp/configuracion (actualizar_configuracion_whatsapp)
      Modelos: ConfiguracionSistema
    - POST /validadores/probar (probar_validadores)
    - GET /prestamos/parametros (obtener_parametros_prestamos)
      Modelos: ConfiguracionSistema
    - GET /sistema/estadisticas (obtener_estadisticas_sistema)
      Modelos: ConfiguracionSistema, Prestamo, User
    - GET /ai/configuracion (obtener_configuracion_ai)
    - PUT /ai/configuracion (actualizar_configuracion_ai)
      Modelos: ConfiguracionSistema
    - GET /ai/documentos (listar_documentos_ai)
      Modelos: DocumentoAI
    - POST /ai/documentos/{documento_id}/procesar (procesar_documento_ai)
      Modelos: DocumentoAI
    - DELETE /ai/documentos/{documento_id} (eliminar_documento_ai)
      Modelos: DocumentoAI
    - GET /ai/documentos/{documento_id} (obtener_documento_ai)
      Modelos: DocumentoAI
    - PUT /ai/documentos/{documento_id} (actualizar_documento_ai)
      Modelos: DocumentoAI
    - PATCH /ai/documentos/{documento_id}/activar (activar_desactivar_documento_ai)
      Modelos: DocumentoAI
    - GET /ai/prompt/variables (listar_variables_prompt_ai)
      Modelos: AIPromptVariable
    - POST /ai/prompt/variables (crear_variable_prompt_ai)
      Modelos: AIPromptVariable
    - PUT /ai/prompt/variables/{variable_id} (actualizar_variable_prompt_ai)
      Modelos: AIPromptVariable
    - DELETE /ai/prompt/variables/{variable_id} (eliminar_variable_prompt_ai)
      Modelos: AIPromptVariable
    - GET /ai/prompt (obtener_prompt_ai)
      Modelos: AIPromptVariable, ConfiguracionSistema
    - PUT /ai/prompt (actualizar_prompt_ai)
      Modelos: ConfiguracionSistema
    - GET /ai/prompt/default (obtener_prompt_default_ai)
    - GET /ai/metricas (obtener_metricas_ai)
      Modelos: DocumentoAI
    - GET /ai/metricas/chat (obtener_metricas_chat_ai)
    - GET /ai/tablas-campos (obtener_tablas_campos)

[ARCHIVO] api\v1\endpoints\dashboard.py
--------------------------------------------------------------------------------
  Endpoints con DB: 25
  Modelos usados: Cliente, DashboardMorosidadMensual, Pago, Prestamo
  Columnas Pago usadas: monto
  Endpoints:
    - GET /opciones-filtros (obtener_opciones_filtros)
    - GET /cobros-diarios (obtener_cobros_diarios)
    - GET /admin (dashboard_administrador)
      Modelos: Prestamo
    - GET /analista (dashboard_analista)
      Modelos: Cliente
    - GET /resumen (resumen_general)
      Modelos: Cliente, Prestamo
    - GET /kpis-principales (obtener_kpis_principales)
      Modelos: Cliente
    - GET /cobranzas-mensuales (obtener_cobranzas_mensuales)
    - GET /cobranza-por-dia (obtener_cobranza_por_dia)
    - GET /cobranza-fechas-especificas (obtener_cobranza_fechas_especificas)
    - GET /metricas-acumuladas (obtener_metricas_acumuladas)
    - GET /morosidad-por-analista (obtener_morosidad_por_analista)
    - GET /prestamos-por-concesionario (obtener_prestamos_por_concesionario)
      Modelos: Prestamo
    - GET /prestamos-por-modelo (obtener_prestamos_por_modelo)
      Modelos: Prestamo
    - GET /pagos-conciliados (obtener_pagos_conciliados)
      Modelos: Pago
    - GET /financiamiento-por-rangos (obtener_financiamiento_por_rangos)
      Modelos: Prestamo
    - GET /composicion-morosidad (obtener_composicion_morosidad)
    - GET /evolucion-general-mensual (obtener_evolucion_general_mensual)
    - GET /distribucion-prestamos (obtener_distribucion_prestamos)
      Modelos: Prestamo
    - GET /cuentas-cobrar-tendencias (obtener_cuentas_cobrar_tendencias)
    - GET /financiamiento-tendencia-mensual (obtener_financiamiento_tendencia_mensual)
    - GET /cobranzas-semanales (obtener_cobranzas_semanales)
    - GET /cobros-por-analista (obtener_cobros_por_analista)
    - GET /evolucion-morosidad (obtener_evolucion_morosidad)
      Modelos: DashboardMorosidadMensual
    - GET /evolucion-pagos (obtener_evolucion_pagos)
    - GET /resumen-financiamiento-pagado (obtener_resumen_financiamiento_pagado)

[ARCHIVO] api\v1\endpoints\cobranzas.py
--------------------------------------------------------------------------------
  Endpoints con DB: 18
  Modelos usados: Cuota, ModeloImpagoCuotas, Prestamo
  Columnas Prestamo ML usadas: ml_impago_calculado_en, ml_impago_modelo_id, ml_impago_nivel_riesgo_calculado, ml_impago_nivel_riesgo_manual, ml_impago_probabilidad_calculada, ml_impago_probabilidad_manual
  Endpoints:
    - GET /diagnostico-ml (diagnostico_ml_impago)
      Modelos: ModeloImpagoCuotas
    - GET /health (healthcheck_cobranzas)
    - GET /diagnostico (diagnostico_cobranzas)
    - GET /clientes-atrasados (obtener_clientes_atrasados)
      Modelos: Cuota, ModeloImpagoCuotas, Prestamo
      Columnas Prestamo ML: ml_impago_nivel_riesgo_manual, ml_impago_probabilidad_manual
    - GET /clientes-por-cantidad-pagos (obtener_clientes_por_cantidad_pagos_atrasados)
      Modelos: Cuota, ModeloImpagoCuotas, Prestamo
    - GET /por-analista (obtener_cobranzas_por_analista)
    - GET /por-analista/{analista}/clientes (obtener_clientes_por_analista)
      Modelos: Cuota, ModeloImpagoCuotas, Prestamo
    - GET /montos-por-mes (obtener_montos_vencidos_por_mes)
    - GET /resumen (obtener_resumen_cobranzas)
      Modelos: Cuota
    - PUT /prestamos/{prestamo_id}/ml-impago (actualizar_ml_impago)
      Modelos: Prestamo
    - DELETE /prestamos/{prestamo_id}/ml-impago (eliminar_ml_impago_manual)
      Modelos: Prestamo
    - POST /notificaciones/atrasos (disparar_notificaciones_atrasos)
    - GET /informes/clientes-atrasados (informe_clientes_atrasados)
      Modelos: Cuota, ModeloImpagoCuotas, Prestamo
    - GET /informes/rendimiento-analista (informe_rendimiento_analista)
    - GET /informes/montos-vencidos-periodo (informe_montos_vencidos_periodo)
    - GET /informes/por-categoria-dias (informe_por_categoria_dias)
    - GET /informes/antiguedad-saldos (informe_antiguedad_saldos)
    - GET /informes/resumen-ejecutivo (informe_resumen_ejecutivo)

[ARCHIVO] api\v1\endpoints\notificaciones.py
--------------------------------------------------------------------------------
  Endpoints con DB: 16
  Modelos usados: Notificacion, NotificacionPlantilla, NotificacionVariable
  Endpoints:
    - GET / (listar_notificaciones)
      Modelos: Notificacion
    - GET /estadisticas/resumen (obtener_estadisticas_notificaciones)
    - GET /plantillas (listar_plantillas)
    - GET /plantillas/verificar (verificar_plantillas)
      Modelos: NotificacionPlantilla
    - POST /plantillas (crear_plantilla)
      Modelos: NotificacionPlantilla
    - PUT /plantillas/{plantilla_id} (actualizar_plantilla)
      Modelos: NotificacionPlantilla
    - DELETE /plantillas/{plantilla_id} (eliminar_plantilla)
      Modelos: NotificacionPlantilla
    - GET /plantillas/{plantilla_id} (obtener_plantilla)
      Modelos: NotificacionPlantilla
    - GET /plantillas/{plantilla_id}/export (exportar_plantilla)
      Modelos: NotificacionPlantilla
    - POST /automaticas/procesar (procesar_notificaciones_automaticas)
    - GET /variables (listar_variables)
      Modelos: NotificacionVariable
    - GET /variables/{variable_id} (obtener_variable)
      Modelos: NotificacionVariable
    - POST /variables (crear_variable)
      Modelos: NotificacionVariable
    - PUT /variables/{variable_id} (actualizar_variable)
      Modelos: NotificacionVariable
    - POST /variables/inicializar-precargadas (inicializar_variables_precargadas)
      Modelos: NotificacionVariable
    - DELETE /variables/{variable_id} (eliminar_variable)
      Modelos: NotificacionVariable

[ARCHIVO] api\v1\endpoints\prestamos.py
--------------------------------------------------------------------------------
  Endpoints con DB: 13
  Modelos usados: Cliente, ModeloVehiculo, Prestamo, PrestamoAuditoria
  Endpoints:
    - GET /stats (obtener_estadisticas_prestamos)
      Modelos: Prestamo
    - GET / (listar_prestamos)
    - POST / (crear_prestamo)
      Modelos: Cliente, ModeloVehiculo
    - GET /cedula/{cedula} (buscar_prestamos_por_cedula)
      Modelos: Prestamo
    - GET /cedula/{cedula}/resumen (obtener_resumen_prestamos_cliente)
      Modelos: Prestamo
    - GET /auditoria/{prestamo_id} (obtener_auditoria_prestamo)
      Modelos: PrestamoAuditoria
    - GET /{prestamo_id} (obtener_prestamo)
      Modelos: Prestamo
    - PUT /{prestamo_id} (actualizar_prestamo)
      Modelos: Prestamo
    - DELETE /{prestamo_id} (eliminar_prestamo)
      Modelos: Prestamo, PrestamoAuditoria
    - POST /{prestamo_id}/generar-amortizacion (generar_amortizacion_prestamo)
      Modelos: Prestamo
    - GET /{prestamo_id}/cuotas (obtener_cuotas_prestamo)
      Modelos: Prestamo
    - POST /{prestamo_id}/evaluar-riesgo (evaluar_riesgo_prestamo)
      Modelos: Prestamo
    - POST /{prestamo_id}/aplicar-condiciones-aprobacion (aplicar_condiciones_aprobacion)
      Modelos: Prestamo

[ARCHIVO] api\v1\endpoints\amortizacion.py
--------------------------------------------------------------------------------
  Endpoints con DB: 12
  Modelos usados: Cuota, Prestamo
  Endpoints:
    - POST /generar-tabla (generar_tabla_amortizacion)
    - POST /prestamo/{prestamo_id}/cuotas (crear_cuotas_prestamo)
      Modelos: Cuota, Prestamo
    - GET /prestamo/{prestamo_id}/cuotas (obtener_cuotas_prestamo)
      Modelos: Prestamo
    - POST /cuotas/multiples (obtener_cuotas_multiples_prestamos)
      Modelos: Cuota
    - GET /cuota/{cuota_id} (obtener_cuota)
      Modelos: Cuota
    - PUT /cuota/{cuota_id} (actualizar_cuota)
      Modelos: Cuota
    - DELETE /cuota/{cuota_id} (eliminar_cuota)
      Modelos: Cuota
    - POST /prestamo/{prestamo_id}/recalcular-mora (recalcular_mora)
      Modelos: Cuota, Prestamo
    - GET /prestamo/{prestamo_id}/estado-cuenta (obtener_estado_cuenta)
      Modelos: Cuota, Prestamo
    - POST /prestamo/{prestamo_id}/proyectar-pago (proyectar_pago)
      Modelos: Cuota, Prestamo
    - GET /prestamo/{prestamo_id}/informacion-adicional (obtener_informacion_adicional)
      Modelos: Cuota, Prestamo
    - GET /prestamo/{prestamo_id}/tabla-visual (obtener_tabla_visual)
      Modelos: Cuota, Prestamo

[ARCHIVO] api\v1\endpoints\pagos.py
--------------------------------------------------------------------------------
  Endpoints con DB: 12
  Modelos usados: Cliente, Cuota, Pago, PagoAuditoria, Prestamo
  Endpoints:
    - GET /health (healthcheck_pagos)
    - GET /diagnostico (diagnostico_pagos)
    - GET / (listar_pagos)
      Modelos: Pago
    - POST / (crear_pago)
      Modelos: Cliente, Prestamo
    - POST /{pago_id}/aplicar-cuotas (aplicar_pago_manualmente)
      Modelos: Pago
    - PUT /{pago_id} (actualizar_pago)
      Modelos: Pago
    - DELETE /{pago_id} (eliminar_pago)
      Modelos: Pago
    - GET /ultimos (listar_ultimos_pagos)
      Modelos: Pago
    - GET /kpis (obtener_kpis_pagos)
    - GET /stats (obtener_estadisticas_pagos)
      Modelos: Cuota, Pago
    - GET /auditoria/{pago_id} (obtener_auditoria_pago)
      Modelos: PagoAuditoria
    - GET /exportar/errores (exportar_pagos_con_errores)

[ARCHIVO] api\v1\endpoints\clientes.py
--------------------------------------------------------------------------------
  Endpoints con DB: 11
  Modelos usados: Cliente
  Endpoints:
    - GET / (listar_clientes)
      Modelos: Cliente
    - GET /stats (obtener_estadisticas_clientes)
      Modelos: Cliente
    - GET /embudo/estadisticas (obtener_estadisticas_embudo)
      Modelos: Cliente
    - GET /{cliente_id} (obtener_cliente)
      Modelos: Cliente
    - POST / (crear_cliente)
      Modelos: Cliente
    - PUT /{cliente_id} (actualizar_cliente)
      Modelos: Cliente
    - DELETE /{cliente_id} (eliminar_cliente)
      Modelos: Cliente
    - GET /con-problemas-validacion (listar_clientes_con_problemas_validacion)
      Modelos: Cliente
    - GET /valores-por-defecto (listar_clientes_valores_por_defecto)
      Modelos: Cliente
    - GET /valores-por-defecto/exportar (exportar_clientes_valores_por_defecto)
      Modelos: Cliente
    - POST /actualizar-lote (actualizar_clientes_lote)
      Modelos: Cliente

[ARCHIVO] api\v1\endpoints\reportes.py
--------------------------------------------------------------------------------
  Endpoints con DB: 10
  Modelos usados: Cliente, Pago, Prestamo
  Endpoints:
    - GET /health (healthcheck_reportes)
    - GET /cartera (reporte_cartera)
      Modelos: Prestamo
    - GET /pagos (reporte_pagos)
      Modelos: Pago
    - GET /morosidad (reporte_morosidad)
    - GET /financiero (reporte_financiero)
    - GET /asesores (reporte_asesores)
    - GET /productos (reporte_productos)
    - GET /exportar/cartera (exportar_reporte_cartera)
      Modelos: Prestamo
    - GET /dashboard/resumen (resumen_dashboard)
      Modelos: Cliente, Pago
    - GET /cliente/{cedula}/pendientes.pdf (generar_pdf_pendientes_cliente)

[ARCHIVO] api\v1\endpoints\concesionarios.py
--------------------------------------------------------------------------------
  Endpoints con DB: 8
  Modelos usados: Concesionario
  Endpoints:
    - GET / (list_concesionarios)
      Modelos: Concesionario
    - GET /activos (list_concesionarios_activos)
      Modelos: Concesionario
    - GET /dropdown (get_concesionarios_dropdown)
      Modelos: Concesionario
    - GET /{concesionario_id} (obtener_concesionario)
      Modelos: Concesionario
    - POST / (crear_concesionario)
    - PUT /{concesionario_id} (actualizar_concesionario)
      Modelos: Concesionario
    - DELETE /{concesionario_id} (eliminar_concesionario)
      Modelos: Concesionario
    - POST /importar (importar_concesionarios)

[ARCHIVO] api\v1\endpoints\users.py
--------------------------------------------------------------------------------
  Endpoints con DB: 8
  Modelos usados: Aprobacion, Auditoria, Notificacion, User
  Endpoints:
    - GET /verificar-admin (verificar_rol_administracion)
      Modelos: User
    - POST / (create_user)
      Modelos: User
    - GET / (list_users)
      Modelos: User
    - GET /{user_id} (get_user)
      Modelos: User
    - PUT /{user_id} (update_user)
      Modelos: User
    - DELETE /{user_id} (delete_user)
      Modelos: Aprobacion, Auditoria, Notificacion, User
    - POST /{user_id}/activate (activate_user)
      Modelos: User
    - POST /{user_id}/deactivate (deactivate_user)
      Modelos: User

[ARCHIVO] api\v1\endpoints\analistas.py
--------------------------------------------------------------------------------
  Endpoints con DB: 7
  Modelos usados: Analista
  Endpoints:
    - GET / (listar_analistas)
      Modelos: Analista
    - GET /activos (listar_analistas_activos)
      Modelos: Analista
    - GET /{analista_id} (obtener_analista)
      Modelos: Analista
    - POST / (crear_analista)
    - PUT /{analista_id} (actualizar_analista)
      Modelos: Analista
    - DELETE /{analista_id} (eliminar_analista)
      Modelos: Analista
    - POST /importar (importar_analistas)

[ARCHIVO] api\v1\endpoints\modelos_vehiculos.py
--------------------------------------------------------------------------------
  Endpoints con DB: 7
  Modelos usados: ModeloVehiculo
  Endpoints:
    - GET / (listar_modelos_vehiculos)
      Modelos: ModeloVehiculo
    - GET /activos (listar_modelos_activos)
      Modelos: ModeloVehiculo
    - GET /{modelo_id} (obtener_modelo_vehiculo)
      Modelos: ModeloVehiculo
    - POST / (crear_modelo_vehiculo)
      Modelos: ModeloVehiculo
    - PUT /{modelo_id} (actualizar_modelo_vehiculo)
      Modelos: ModeloVehiculo
    - DELETE /{modelo_id} (eliminar_modelo_vehiculo)
      Modelos: ModeloVehiculo
    - POST /importar (importar_modelos_vehiculos)

[ARCHIVO] api\v1\endpoints\scheduler_notificaciones.py
--------------------------------------------------------------------------------
  Endpoints con DB: 6
  Modelos usados: Ninguno
  Endpoints:
    - GET /configuracion (obtener_configuracion_scheduler)
    - PUT /configuracion (configurar_scheduler)
    - GET /logs (obtener_logs_scheduler)
    - GET /estado (obtener_estado_scheduler)
    - GET /tareas (obtener_tareas_programadas)
    - GET /verificacion-completa (verificar_sistema_notificaciones_completo)

[ARCHIVO] api\v1\endpoints\solicitudes.py
--------------------------------------------------------------------------------
  Endpoints con DB: 5
  Modelos usados: Aprobacion
  Endpoints:
    - GET / (listar_solicitudes)
      Modelos: Aprobacion
    - GET /{solicitud_id} (obtener_solicitud)
      Modelos: Aprobacion
    - PUT /{solicitud_id}/aprobar (aprobar_solicitud)
      Modelos: Aprobacion
    - PUT /{solicitud_id}/rechazar (rechazar_solicitud)
      Modelos: Aprobacion
    - GET /pendientes/count (contar_solicitudes_pendientes)
      Modelos: Aprobacion

[ARCHIVO] api\v1\endpoints\auditoria.py
--------------------------------------------------------------------------------
  Endpoints con DB: 4
  Modelos usados: Auditoria, PagoAuditoria, PrestamoAuditoria
  Endpoints:
    - GET /auditoria (listar_auditoria)
      Modelos: Auditoria, PagoAuditoria, PrestamoAuditoria
    - GET /auditoria/exportar (exportar_auditoria)
      Modelos: Auditoria, PagoAuditoria, PrestamoAuditoria
    - GET /auditoria/stats (estadisticas_auditoria)
    - POST /auditoria/registrar (registrar_evento_auditoria)

[ARCHIVO] api\v1\endpoints\kpis.py
--------------------------------------------------------------------------------
  Endpoints con DB: 4
  Modelos usados: Prestamo
  Endpoints:
    - GET /dashboard (dashboard_kpis_principales)
    - GET /analistas (kpis_analistas)
    - GET /cartera (kpis_cartera)
    - GET /prestamos (kpis_prestamos)
      Modelos: Prestamo

[ARCHIVO] api\v1\endpoints\validadores.py
--------------------------------------------------------------------------------
  Endpoints con DB: 3
  Modelos usados: Ninguno
  Endpoints:
    - GET /configuracion-validadores (obtener_configuracion_validadores)
    - POST /probar-validador (probar_validador)
    - POST /validar-campo (validar_campo)

[ARCHIVO] api\v1\endpoints\notificaciones_dia_pago.py
--------------------------------------------------------------------------------
  Endpoints con DB: 2
  Modelos usados: Ninguno
  Endpoints:
    - GET / (listar_notificaciones_dia_pago)
    - POST /calcular (calcular_notificaciones_dia_pago)

[ARCHIVO] api\v1\endpoints\notificaciones_prejudicial.py
--------------------------------------------------------------------------------
  Endpoints con DB: 2
  Modelos usados: Ninguno
  Endpoints:
    - GET / (listar_notificaciones_prejudiciales)
    - POST /calcular (calcular_notificaciones_prejudiciales)

[ARCHIVO] api\v1\endpoints\notificaciones_previas.py
--------------------------------------------------------------------------------
  Endpoints con DB: 2
  Modelos usados: Ninguno
  Endpoints:
    - GET / (listar_notificaciones_previas)
    - POST /calcular (calcular_notificaciones_previas)

[ARCHIVO] api\v1\endpoints\notificaciones_retrasadas.py
--------------------------------------------------------------------------------
  Endpoints con DB: 2
  Modelos usados: Ninguno
  Endpoints:
    - GET / (listar_notificaciones_retrasadas)
    - POST /calcular (calcular_notificaciones_retrasadas)

================================================================================
RECOMENDACIONES
================================================================================

[INFO] Columnas de Pago disponibles pero no usadas:
   Considera usar estas columnas para mejorar funcionalidades:
   - banco
   - codigo_pago
   - comprobante
   - creado_en
   - descuento
   - dias_mora
   - documento
   - fecha_vencimiento
   - hora_pago
   - metodo_pago
   - monto_capital
   - monto_cuota_programado
   - monto_interes
   - monto_mora
   - monto_total
   - numero_operacion
   - observaciones
   - referencia_pago
   - tasa_mora
   - tipo_pago

[INFO] Columnas de Cuota disponibles pero no usadas:
   - actualizado_en
   - creado_en

================================================================================
FIN DEL REPORTE
================================================================================