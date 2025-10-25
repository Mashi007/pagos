from datetime import date
# Decimal\nfrom typing \nimport Optional\nfrom fastapi \nimport APIRouter, Depends, Query\nfrom sqlalchemy \nimport case,
# func, or_\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user, get_db\nfrom
# app.models.amortizacion \nimport Cuota\nfrom app.models.analista \nimport Analista\nfrom app.models.cliente \nimport
# Cliente\nfrom app.models.pago \nimport Pago\nfrom app.models.user \nimport Userlogger = logging.getLogger(__name__)router =
# APIRouter()@router.get("/dashboard")\ndef dashboard_kpis_principales
# description="Fecha de corte (default:\n hoy)" ), db:\n Session = Depends(get_db), current_user:\n User =
# = date.today() # 💰 CARTERA TOTAL cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter
# Cliente.total_financiamiento.isnot(None) ).scalar() or Decimal("0") # ✅ CLIENTES AL DÍA clientes_al_dia = 
# db.query(Cliente) .filter( Cliente.activo, or_(Cliente.estado_financiero == "AL_DIA", Cliente.dias_mora == 0), ) .count() )
# # ⚠️ CLIENTES EN MORA clientes_en_mora = ( db.query(Cliente) .filter
# Cliente.dias_mora > 0, ) .count() ) # 📈 TASA DE MOROSIDAD total_clientes = clientes_al_dia + clientes_en_mora
# db.query(func.sum(Pago.monto_pagado)).filter( Pago.fecha_pago == fecha_corte, Pago.estado != "ANULADO" ).scalar() or
# Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), ) .count() ) return 
# "cartera_total":\n { "valor":\n float(cartera_total), "formato":\n f"${float(cartera_total):\n,.0f}", "icono":\n "💰",
# "color":\n "primary", }, "clientes_al_dia":\n { "valor":\n clientes_al_dia, "formato":\n f"{clientes_al_dia:\n,}",
# "icono":\n "✅", "color":\n "success", }, "clientes_en_mora":\n 
# "cobrado_hoy":\n { "valor":\n float(cobrado_hoy), "formato":\n f"${float(cobrado_hoy):\n,.0f}", "icono":\n "💸", "color":\n
# "color":\n "info", }, }, "resumen":\n 
# "monto_total":\n float(monto), "ticket_promedio":\n float(ticket), } for modalidad, clientes, monto, ticket in
# rentabilidadmodalidad ], }, }@router.get("/cobranza")\ndef kpis_cobranza( db:\n Session = Depends(get_db), current_user:\n
# db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora > 0).count() ) clientes_al_dia = ( db.query(Cliente)
# func.count(Cliente.id).label("total_clientes"), func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label
# ), ) .outerjoin(Cliente, Analista.id == Cliente.analista_id) .filter(Analista.activo, Cliente.activo) .group_by
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
# analistaes """ # Ranking de ventas ventas_por_analista = 
# func.count(Cliente.id).label("total_ventas"), func.sum(Cliente.total_financiamiento).label("monto_vendido"),
# func.avg(Cliente.total_financiamiento).label("ticket_promedio"), ) .outerjoin(Cliente, Analista.id == Cliente.analista_id)
# .filter(Analista.activo, Cliente.activo) .group_by(User.id, User.full_name)
# .order_by(func.sum(Cliente.total_financiamiento).desc()) .all() ) # Gestión de cobranza por analista cobranza_por_analista
# = ( db.query( User.id, User.full_name, func.count(Cliente.id).label("total_clientes"), func.sum
# 0, 1), else_=0)).label( "clientes_al_dia" ), func.sum(case((Cliente.dias_mora > 0, 1), else_=0)).label( "clientes_mora" ),
# ) .outerjoin(Cliente, Analista.id == Cliente.analista_id) .filter(Analista.activo, Cliente.activo) .group_by
# "total_ventas":\n ventas or 0, "monto_vendido":\n float(monto or 0), "ticket_promedio":\n float(ticket or 0), } ) for
# analista_id, nombre, total, al_dia, mora in cobranza_por_analista:\n tasa_cobro = (al_dia / total * 100) if total > 0 else
# 0 ranking_cobranza.append
# "clientes_al_dia":\n al_dia or 0, "clientes_mora":\n mora or 0, "tasa_cobro":\n round(tasa_cobro, 2), } ) # Identificar
# mejores y peores mejor_vendedor = ( max(ranking_ventas, key=lambda x:\n x["total_ventas"]) if ranking_ventas else None )
# mayor_monto = ( max(ranking_ventas, key=lambda x:\n x["monto_vendido"]) if ranking_ventas else None ) menor_ventas = 
# min(ranking_ventas, key=lambda x:\n x["total_ventas"]) if ranking_ventas else None ) mejor_cobrador = 
# max(ranking_cobranza, key=lambda x:\n x["tasa_cobro"]) if ranking_cobranza else None ) peor_cobrador = 
# min(ranking_cobranza, key=lambda x:\n x["tasa_cobro"]) if ranking_cobranza else None ) return 
# "promedio_dias_mora":\n round(float(mora_data[3] or 0), 1), } ) # Ordenar por monto total
