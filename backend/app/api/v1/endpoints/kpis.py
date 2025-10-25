# Decimal\nfrom typing \nimport Optional\nfrom fastapi \nimport APIRouter, Depends, Query\nfrom sqlalchemy \nimport case,
# func, or_\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user, get_db\nfrom
# app.models.amortizacion \nimport Cuota\nfrom app.models.analista \nimport Analista\nfrom app.models.cliente \nimport
# Cliente\nfrom app.models.pago \nimport Pago\nfrom app.models.user \nimport Userlogger = logging.getLogger(__name__)router =
# APIRouter()@router.get("/dashboard")\ndef dashboard_kpis_principales( fecha_corte:\n Optional[date] = Query( None,
# description="Fecha de corte (default:\n hoy)" ), db:\n Session = Depends(get_db), current_user:\n User =
# = date.today() # 💰 CARTERA TOTAL cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter( Cliente.activo,
# Cliente.total_financiamiento.isnot(None) ).scalar() or Decimal("0") # ✅ CLIENTES AL DÍA clientes_al_dia = (
# db.query(Cliente) .filter( Cliente.activo, or_(Cliente.estado_financiero == "AL_DIA", Cliente.dias_mora == 0), ) .count() )
# # ⚠️ CLIENTES EN MORA clientes_en_mora = ( db.query(Cliente) .filter( Cliente.activo, Cliente.estado_financiero == "MORA",
# Cliente.dias_mora > 0, ) .count() ) # 📈 TASA DE MOROSIDAD total_clientes = clientes_al_dia + clientes_en_mora
# db.query(func.sum(Pago.monto_pagado)).filter( Pago.fecha_pago == fecha_corte, Pago.estado != "ANULADO" ).scalar() or
# Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), ) .count() ) return { "fecha_corte":\n fecha_corte, "kpis_principales":\n {
# "cartera_total":\n { "valor":\n float(cartera_total), "formato":\n f"${float(cartera_total):\n,.0f}", "icono":\n "💰",
# "color":\n "primary", }, "clientes_al_dia":\n { "valor":\n clientes_al_dia, "formato":\n f"{clientes_al_dia:\n,}",
# "icono":\n "✅", "color":\n "success", }, "clientes_en_mora":\n { "valor":\n clientes_en_mora, "formato":\n
# "cobrado_hoy":\n { "valor":\n float(cobrado_hoy), "formato":\n f"${float(cobrado_hoy):\n,.0f}", "icono":\n "💸", "color":\n
# "color":\n "info", }, }, "resumen":\n { "total_clientes":\n total_clientes, "porcentaje_al_dia":\n ( round((clientes_al_dia
# fecha_inicio:\n Optional[date] = Query(None), fecha_fin:\n Optional[date] = Query(None), db:\n Session = Depends(get_db),
# fechas según período hoy = date.today() if not fecha_inicio or not fecha_fin:\n if periodo == "dia":\n fecha_inicio =
# func.sum(Cliente.total_financiamiento - Cliente.cuota_inicial) ).filter( Cliente.activo,
# Cliente.total_financiamiento.isnot(None) ).scalar() or Decimal( "0" ) # Total cobrado en el período total_cobrado =
# db.query(func.sum(Pago.monto_pagado)).filter( Pago.fecha_pago >= fecha_inicio, Pago.fecha_pago <= fecha_fin, Pago.estado !=
# flujo_proyectado = db.query(func.sum(Cuota.monto_cuota)).filter( Cuota.fecha_vencimiento >= hoy, Cuota.fecha_vencimiento <=
# db.query(func.sum(Pago.monto_mora)).filter( Pago.fecha_pago >= fecha_inicio, Pago.fecha_pago <= fecha_fin ).scalar() or
# Decimal("0") # Tasa de recuperación total_vencido = db.query(func.sum(Cuota.monto_cuota)).filter( Cuota.fecha_vencimiento
# <= hoy, Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]), ).scalar() or Decimal("0") tasa_recuperacion = (
# (total_cobrado / total_vencido * 100) if total_vencido > 0 else 100 ) # Rentabilidad por modalidad rentabilidad_modalidad =
# ( db.query( Cliente.modalidad_pago, func.count(Cliente.id).label("clientes"),
# func.sum(Cliente.total_financiamiento).label("monto_total"),
# func.avg(Cliente.total_financiamiento).label("ticket_promedio"), ) .filter(Cliente.activo,
# Cliente.modalidad_pago.isnot(None)) .group_by(Cliente.modalidad_pago) .all() ) return { "periodo":\n { "tipo":\n periodo,
# float(cartera_total), "total_cobrado_periodo":\n float(total_cobrado), "proyeccion_30_dias":\n float(flujo_proyectado),
# round(float(tasa_recuperacion), 2), "rentabilidad_por_modalidad":\n [ { "modalidad":\n modalidad, "clientes":\n clientes,
# "monto_total":\n float(monto), "ticket_promedio":\n float(ticket), } for modalidad, clientes, monto, ticket in
# rentabilidadmodalidad ], }, }@router.get("/cobranza")\ndef kpis_cobranza( db:\n Session = Depends(get_db), current_user:\n
# db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora > 0).count() ) clientes_al_dia = ( db.query(Cliente)
# func.count(Cliente.id).label("total_clientes"), func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label( "clientes_mora"
# ), ) .outerjoin(Cliente, Analista.id == Cliente.analista_id) .filter(Analista.activo, Cliente.activo) .group_by(User.id,
# User.full_name) .all() ) # Promedio de días de retraso promedio_dias_mora = ( db.query(func.avg(Cliente.dias_mora))
# tiempo) cuotas_vencidas = ( db.query(Cuota).filter(Cuota.fecha_vencimiento <= date.today()).count() ) cuotas_pagadas_tiempo
# = ( db.query(Cuota) .filter( Cuota.estado == "PAGADA", Cuota.fecha_pago <= Cuota.fecha_vencimiento, ) .count() )
# porcentaje_cumplimiento = ( (cuotas_pagadas_tiempo / cuotas_vencidas * 100) if cuotas_vencidas > 0 else 0 ) # Top 10
# Cliente.dias_mora, Cliente.total_financiamiento, ) .filter(Cliente.activo, Cliente.dias_mora > 0)
# round(float(promedio_dias_mora), 1), "porcentaje_cumplimiento":\n round(porcentaje_cumplimiento, 2),
# "clientes_al_dia_vs_mora":\n { "al_dia":\n clientes_al_dia, "en_mora":\n clientes_mora, "total":\n total_clientes, }, },
# "cedula":\n cedula, "dias_mora":\n dias_mora, "monto_financiamiento":\n float(monto or 0), } for cliente_id, nombres,
# }@router.get("/analistaes")\ndef kpis_analistaes( db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🏆 KPIs de Analistaes - Ranking de ventas - Gestión de cobranza - Comparativa entre
# analistaes """ # Ranking de ventas ventas_por_analista = ( db.query( User.id, User.full_name,
# func.count(Cliente.id).label("total_ventas"), func.sum(Cliente.total_financiamiento).label("monto_vendido"),
# func.avg(Cliente.total_financiamiento).label("ticket_promedio"), ) .outerjoin(Cliente, Analista.id == Cliente.analista_id)
# .filter(Analista.activo, Cliente.activo) .group_by(User.id, User.full_name)
# .order_by(func.sum(Cliente.total_financiamiento).desc()) .all() ) # Gestión de cobranza por analista cobranza_por_analista
# = ( db.query( User.id, User.full_name, func.count(Cliente.id).label("total_clientes"), func.sum(case((Cliente.dias_mora ==
# 0, 1), else_=0)).label( "clientes_al_dia" ), func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label( "clientes_mora" ),
# ) .outerjoin(Cliente, Analista.id == Cliente.analista_id) .filter(Analista.activo, Cliente.activo) .group_by(User.id,
# ventas, monto, ticket in ventas_por_analista:\n ranking_ventas.append( { "analista_id":\n analista_id, "nombre":\n nombre,
# "total_ventas":\n ventas or 0, "monto_vendido":\n float(monto or 0), "ticket_promedio":\n float(ticket or 0), } ) for
# analista_id, nombre, total, al_dia, mora in cobranza_por_analista:\n tasa_cobro = (al_dia / total * 100) if total > 0 else
# 0 ranking_cobranza.append( { "analista_id":\n analista_id, "nombre":\n nombre, "total_clientes":\n total or 0,
# "clientes_al_dia":\n al_dia or 0, "clientes_mora":\n mora or 0, "tasa_cobro":\n round(tasa_cobro, 2), } ) # Identificar
# mejores y peores mejor_vendedor = ( max(ranking_ventas, key=lambda x:\n x["total_ventas"]) if ranking_ventas else None )
# mayor_monto = ( max(ranking_ventas, key=lambda x:\n x["monto_vendido"]) if ranking_ventas else None ) menor_ventas = (
# min(ranking_ventas, key=lambda x:\n x["total_ventas"]) if ranking_ventas else None ) mejor_cobrador = (
# max(ranking_cobranza, key=lambda x:\n x["tasa_cobro"]) if ranking_cobranza else None ) peor_cobrador = (
# min(ranking_cobranza, key=lambda x:\n x["tasa_cobro"]) if ranking_cobranza else None ) return { "ranking_ventas":\n {
# "mejor_vendedor_unidades":\n mejor_vendedor, "mayor_monto_vendido":\n mayor_monto, "menor_ventas":\n menor_ventas,
# "promedio_ventas":\n ( sum(r["total_ventas"] for r in ranking_ventas) / len(ranking_ventas) if ranking_ventas else 0 ),
# "promedio_tasa_cobro":\n ( sum(r["tasa_cobro"] for r in ranking_cobranza) / len(ranking_cobranza) if ranking_cobranza else
# modelo - Mora por modelo """ # Ventas por modelo ventas_por_modelo = ( db.query( Cliente.modelo_vehiculo,
# Cliente.marca_vehiculo, func.count(Cliente.id).label("total_ventas"),
# func.sum(Cliente.total_financiamiento).label("monto_total"),
# func.avg(Cliente.total_financiamiento).label("ticket_promedio"), ) .filter(Cliente.activo,
# Cliente.modelo_vehiculo.isnot(None)) .group_by(Cliente.modelo_vehiculo, Cliente.marca_vehiculo) .all() ) # Mora por modelo
# mora_por_modelo = ( db.query( Cliente.modelo_vehiculo, func.count(Cliente.id).label("total_clientes"),
# func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label( "clientes_mora" ), ) .filter(Cliente.activo,
# for m in mora_por_modelo if m[0] == modelo), (modelo, 0, 0) ) tasa_mora_modelo = ( (mora_data[2] / mora_data[1] * 100) if
# "monto_total":\n float(monto), "ticket_promedio":\n float(ticket), "clientes_mora":\n mora_data[2], "tasa_mora":\n
# Depends(get_current_user),):\n """ 🏢 KPIs de Concesionario - Ventas por concesionario - Mora por concesionario -
# Cliente.concesionario, func.count(Cliente.id).label("total_ventas"),
# func.sum(Cliente.total_financiamiento).label("monto_total"),
# func.avg(Cliente.total_financiamiento).label("ticket_promedio"), ) .filter(Cliente.activo,
# Cliente.concesionario.isnot(None)) .group_by(Cliente.concesionario) .all() ) # Mora por concesionario
# mora_por_concesionario = ( db.query( Cliente.concesionario, func.count(Cliente.id).label("total_clientes"),
# func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label( "clientes_mora" ),
# func.avg(Cliente.dias_mora).label("promedio_dias_mora"), ) .filter(Cliente.activo, Cliente.concesionario.isnot(None))
# == concesionario), (concesionario, 0, 0, 0), ) tasa_mora = ( (mora_data[2] / mora_data[1] * 100) if mora_data[1] > 0 else 0
# "ticket_promedio":\n float(ticket), "clientes_mora":\n mora_data[2], "tasa_mora":\n round(tasa_mora, 2),
# "promedio_dias_mora":\n round(float(mora_data[3] or 0), 1), } ) # Ordenar por monto total
