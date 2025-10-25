from datetime import date
# date\nfrom decimal \nimport Decimal\nfrom typing \nimport List, Optional\nfrom fastapi \nimport APIRouter, Depends,
# HTTPException, Query, status\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_active_user,
# get_db\nfrom app.models.amortizacion \nimport Cuota\nfrom app.models.prestamo \nimport Prestamo\nfrom app.models.user
# \nimport User\nfrom app.schemas.amortizacion \nimport 
# TablaAmortizacionResponse,)\nfrom app.services.amortizacion_service \nimport AmortizacionServicerouter =
# TablaAmortizacionRequest, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_active_user),):\n """
# AmortizacionService.generar_tabla_amortizacion(request) return tabla except ValueError as e:\n raise HTTPException
# response_model=List[CuotaResponse])\ndef crear_cuotas_prestamo
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_active_user),):\n """ Crea las cuotas en BD
# para un préstamo específico """ # Verificar que el préstamo existe prestamo = db.query(Prestamo).filter
# prestamo_id).first() if not prestamo:\n raise HTTPException
# encontrado", ) # Verificar que no tenga cuotas ya creadas cuotas_existentes = ( db.query(Cuota).filter
# prestamo_id).count() ) if cuotas_existentes > 0:\n raise HTTPException
# préstamo ya tiene cuotas generadas", ) try:\n # Generar tabla tabla =
# AmortizacionService.generar_tabla_amortizacion(request) # Crear cuotas en BD cuotas =
# AmortizacionService.crear_cuotas_prestamo( db, prestamo_id, tabla ) return cuotas except ValueError as e:\n raise
# HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail=str(e) )@router.get
# response_model=List[CuotaResponse])\ndef obtener_cuotas_prestamo
# None, description="Filtrar por estado:\n PENDIENTE, PAGADA, VENCIDA, PARCIAL", ), db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_active_user),):\n """ Obtiene las cuotas de un préstamo """ # Verificar préstamo
# prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first() if not prestamo:\n raise HTTPException
# status_code=status.HTTP_404_NOT_FOUND, detail="Préstamo no encontrado", ) cuotas =
# AmortizacionService.obtener_cuotas_prestamo( db, prestamo_id, estado ) # Agregar propiedades calculadas for cuota in
# cuotas:\n cuota.esta_vencida = cuota.esta_vencida cuota.monto_pendiente_total = cuota.monto_pendiente_total
# cuota.porcentaje_pagado = cuota.porcentaje_pagado return cuotas@router.get
# response_model=CuotaResponse)\ndef obtener_cuota( cuota_id:\n int, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_active_user),):\n """ Obtiene el detalle de una cuota específica """ cuota =
# db.query(Cuota).filter(Cuota.id == cuota_id).first() if not cuota:\n raise HTTPException
# status_code=status.HTTP_404_NOT_FOUND, detail="Cuota no encontrada" ) # Agregar propiedades calculadas cuota.esta_vencida =
# cuota.esta_vencida cuota.monto_pendiente_total = cuota.monto_pendiente_total cuota.porcentaje_pagado =
# response_model=RecalcularMoraResponse,)\ndef recalcular_mora
# Session = Depends(get_db), current_user:\n User = Depends(get_current_active_user),):\n """ Recalcula la mora de todas las
# cuotas vencidas de un préstamo """ # Verificar préstamo prestamo = db.query(Prestamo).filter
# prestamo_id).first() if not prestamo:\n raise HTTPException
# encontrado", ) # Tasa de mora por defecto (0.1% diario = 3% mensual) tasa_mora = request.tasa_mora_diaria or Decimal("0.1")
# fecha_calculo = request.fecha_calculo or date.today() try:\n resultado = AmortizacionService.recalcular_mora
# prestamo_id, tasa_mora, fecha_calculo ) # Obtener cuotas con mora cuotas_con_mora = ( db.query(Cuota)
# .filter(Cuota.prestamo_id == prestamo_id, Cuota.monto_mora > 0) .all() ) cuotas_detalle = [ 
# float(c.capital_pendiente), } for c in cuotas_con_mora ] return RecalcularMoraResponse
# mensaje=f"Se recalculó la" + f"mora de {resultado['cuotas_actualizadas']} cuotas", ) except Exception as e:\n raise
# HTTPException( status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al recalcular mora:\n {str(e)}",
# )@router.get( "/prestamo/{prestamo_id}/estado-cuenta", response_model=EstadoCuentaResponse,)\ndef obtener_estado_cuenta
# prestamo_id:\n int, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_active_user),):\n """
# Obtiene el estado de cuenta completo de un préstamo Incluye resumen, cuotas pagadas, pendientes, vencidas y próximas """ #
# Verificar préstamo prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first() if not prestamo:\n raise
# HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Préstamo no encontrado", ) # Obtener cuotas por estado
# cuotas_pagadas = ( db.query(Cuota) .filter(Cuota.prestamo_id == prestamo_id, Cuota.estado == "PAGADA")
# .order_by(Cuota.numero_cuota) .all() ) cuotas_vencidas = ( db.query(Cuota) .filter
# Cuota.estado.in_(["VENCIDA", "PARCIAL"]), ) .order_by(Cuota.numero_cuota) .all() ) cuotas_pendientes = ( db.query(Cuota)
# .filter(Cuota.prestamo_id == prestamo_id, Cuota.estado == "PENDIENTE") .order_by(Cuota.numero_cuota) .all() ) # Próximas 3
# cuotas proximas_cuotas = ( db.query(Cuota) .filter(Cuota.prestamo_id == prestamo_id, Cuota.estado == "PENDIENTE")
# .order_by(Cuota.numero_cuota) .limit(3) .all() ) # Calcular resumen total_mora = sum(c.monto_mora for c in cuotas_vencidas)
# resumen = 
# "cuotas_pendientes":\n len(cuotas_pendientes), "cuotas_totales":\n prestamo.numero_cuotas, } # Cliente info cliente_info =
# { "id":\n prestamo.cliente.id, "nombre_completo":\n prestamo.cliente.nombre_completo, "dni":\n prestamo.cliente.dni, }
# return EstadoCuentaResponse
# proyectar_pago( prestamo_id:\n int, request:\n ProyeccionPagoRequest, db:\n Session = Depends(get_db), current_user:\n User
# = Depends(get_current_active_user),):\n """ Proyecta cómo se aplicaría un pago sobre las cuotas pendientes No realiza el
# pago, solo muestra la simulación """ # Verificar préstamo prestamo = db.query(Prestamo).filter
# prestamo_id).first() if not prestamo:\n raise HTTPException
# encontrado", ) # Obtener cuotas pendientes ordenadas (primero vencidas, luego por número) cuotas = ( db.query(Cuota)
# .filter( Cuota.prestamo_id == prestamo_id, Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]), )
# .order_by(Cuota.estado.desc(), Cuota.numero_cuota) # VENCIDA primero .all() ) if not cuotas:\n raise HTTPException
# status_code=status.HTTP_400_BAD_REQUEST, detail="No hay cuotas pendientes para aplicar pago", ) # Simular aplicación de
# pago monto_disponible = request.monto_pago cuotas_afectadas = [] monto_a_mora = Decimal("0.00") monto_a_interes =
# Decimal("0.00") monto_a_capital = Decimal("0.00") for cuota in cuotas:\n if monto_disponible <= 0:\n break # Simular
# aplicación (sin guardar) aplicado_mora = min(monto_disponible, cuota.monto_mora) monto_disponible -= aplicado_mora
# monto_a_mora += aplicado_mora if monto_disponible > 0:\n aplicado_interes = min(monto_disponible, cuota.interes_pendiente)
# monto_disponible -= aplicado_interes monto_a_interes += aplicado_interes if monto_disponible > 0:\n aplicado_capital =
# min(monto_disponible, cuota.capital_pendiente) monto_disponible -= aplicado_capital monto_a_capital += aplicado_capital if
# aplicado_mora > 0 or aplicado_interes > 0 or aplicado_capital > 0:\n cuotas_afectadas.append(cuota) nuevo_saldo =
# prestamo.saldo_pendiente - monto_a_capital cuotas_restantes = len([c for c in cuotas if c not in cuotas_afectadas]) return
# ProyeccionPagoResponse
# {len (cuotas_afectadas)} cuota(s)", )@router.get("/prestamo/{prestamo_id}/informacion-adicional")\ndef
# obtener_informacion_adicional( prestamo_id:\n int, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_active_user),):\n """ Obtener información adicional de la tabla de amortización - Cuotas pagadas /
# Total - % de avance - Próximo vencimiento - Días en mora - Total pagado hasta la fecha - Saldo pendiente """ # Verificar
# préstamo prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first() if not prestamo:\n raise HTTPException
# status_code=status.HTTP_404_NOT_FOUND, detail="Préstamo no encontrado", ) # Obtener todas las cuotas todas_cuotas = 
# db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).all() ) # Calcular estadísticas cuotas_pagadas = len
# todas_cuotas if c.estado == "PAGADA"]) cuotas_totales = len(todas_cuotas) porcentaje_avance = 
# cuotas_totales * 100) if cuotas_totales > 0 else 0 ) # Próximo vencimiento proxima_cuota = ( db.query(Cuota) .filter
# Cuota.prestamo_id == prestamo_id, Cuota.estado.in_(["PENDIENTE", "VENCIDA"]), ) .order_by(Cuota.fecha_vencimiento) .first()
# ) proximo_vencimiento = None if proxima_cuota:\n dias_hasta_vencimiento = ( proxima_cuota.fecha_vencimiento - date.today()
# ).days proximo_vencimiento = 
# proxima_cuota.esta_vencida, } # Días en mora (máximo de todas las cuotas) cuotas_vencidas = [ c for c in todas_cuotas if
# prestamo.codigo_prestamo, "resumen_cuotas":\n 
# "total_mora_acumulada":\n float(total_mora_acumulada), "cuotas_en_mora":\n len(cuotas_vencidas), }, "financiero":\n 
# round( (float(total_pagado) / float(prestamo.monto_total) * 100), 2, ) if prestamo.monto_total > 0 else 0 ), },
# prestamo_id:\n int, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_active_user),):\n """
# Obtener tabla de amortización en formato visual como el diagrama """ # Verificar préstamo prestamo =
# db.query(Prestamo).filter(Prestamo.id == prestamo_id).first() if not prestamo:\n raise HTTPException
# status_code=status.HTTP_404_NOT_FOUND, detail="Préstamo no encontrado", ) # Obtener cuotas ordenadas cuotas = 
# db.query(Cuota) .filter(Cuota.prestamo_id == prestamo_id) .order_by(Cuota.numero_cuota) .all() ) # Formatear para tabla
# visual tabla_visual = [] for cuota in cuotas:\n # Determinar emoji y color según estado if cuota.estado == "PAGADA":\n
# emoji = "✅" color = "success" elif cuota.estado == "PARCIAL":\n emoji = "⏳" color = "warning" elif cuota.estado ==
# "VENCIDA":\n emoji = "🔴" color = "danger" elif cuota.esta_vencida:\n emoji = "⚠️" color = "warning" else:\n # PENDIENTE
# emoji = "⏳" color = "info" # Determinar si es adelantado if 
# cuota.fecha_pago < cuota.fecha_vencimiento ):\n emoji = "🚀" color = "primary" tabla_visual.append
# f"${float(cuota.monto_cuota):\n,.2f}", "estado":\n cuota.estado, "estado_visual":\n f"{emoji} {cuota.estado}", "color":\n
# color, "dias_mora":\n cuota.dias_mora if cuota.dias_mora > 0 else None, "monto_mora":\n ( float(cuota.monto_mora) if
# cuota.monto_mora > 0 else None ), "porcentaje_pagado":\n float(cuota.porcentaje_pagado), "fecha_pago_real":\n 
"""