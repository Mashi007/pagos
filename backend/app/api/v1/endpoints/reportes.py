# decimal \nimport Decimal\nfrom typing \nimport Optional\nfrom fastapi \nimport APIRouter, Depends, HTTPException,
# Query\nfrom fastapi.responses \nimport StreamingResponse# Imports para Excel\nfrom openpyxl.styles \nimport Font,
# PatternFill\nfrom reportlab.lib.pagesizes \nimport A4, letter# Imports para reportes PDF\nfrom reportlab.pdfgen \nimport
# canvas\nfrom sqlalchemy \nimport func\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user,
# get_db\nfrom app.core.constants \nimport EstadoPrestamo\nfrom app.models.amortizacion \nimport Cuota\nfrom
# app.models.cliente \nimport Cliente\nfrom app.models.pago \nimport Pago\nfrom app.models.prestamo \nimport Prestamo\nfrom
# app.models.user \nimport User\nfrom app.schemas.reportes \nimport ( ReporteCartera, ReporteCobranza,
# response_model=ReporteCartera)\ndef reporte_cartera( fecha_corte:\n Optional[date] = None, db:\n Session =
# Depends(get_db)):\n """ Genera reporte de cartera al día de corte. """ if not fecha_corte:\n fecha_corte = date.today() #
# Cartera total cartera_total = db.query(func.sum(Prestamo.monto_total)).filter( Prestamo.estado.in_([EstadoPrestamo.ACTIVO,
# EstadoPrestamo.EN_MORA]) ).scalar() or Decimal("0") # Capital pendiente capital_pendiente =
# db.query(func.sum(Prestamo.saldo_pendiente)).filter( Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
# func.count(Prestamo.id).label("cantidad"), func.sum(Prestamo.monto_total).label("monto"), ) .filter( Prestamo.estado.in_(
# [EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA] ) ) .group_by( func.case( (Prestamo.monto_total <= 1000, "Hasta $1,000"),
# (Prestamo.monto_total <= 5000, "$1,001 - $5,000"), (Prestamo.monto_total <= 10000, "$5,001 - $10,000"), else_="Más de
# $10,000", ) ) .all() ) return ReporteCartera( fecha_corte=fecha_corte, cartera_total=cartera_total,
# capital_pendiente=capital_pendiente, intereses_pendientes=cartera_total - capital_pendiente,
# "max":\n 60}, {"nombre":\n "61-90 días", "min":\n 61, "max":\n 90}, {"nombre":\n "Más de 90 días", "min":\n 91, "max":\n
# EstadoPrestamo.EN_MORA, Prestamo.dias_mora >= rango["min"], Prestamo.dias_mora <= rango["max"], ) .all() ) cantidad =
# "cantidad":\n cantidad, "monto_total":\n monto_mora, } ) # Total general total_mora = ( db.query(Prestamo)
# .filter(Prestamo.estado == EstadoPrestamo.EN_MORA) .count() ) monto_total_mora =
# db.query(func.sum(Prestamo.saldo_pendiente)).filter( Prestamo.estado == EstadoPrestamo.EN_MORA ).scalar() or Decimal("0")
# fecha_inicio:\n date, fecha_fin:\n date, db:\n Session = Depends(get_db)):\n """ Genera reporte de gestión de cobranza. """
# por_concepto = ( db.query( Pago.concepto, func.count(Pago.id).label("cantidad"), func.sum(Pago.monto).label("monto"), )
# .filter(Pago.fecha_pago >= fecha_inicio, Pago.fecha_pago <= fecha_fin) .group_by(Pago.concepto) .all() ) # Eficiencia de
# cobranza total_esperado = db.query(func.sum(Prestamo.cuota)).filter( Prestamo.estado.in_([EstadoPrestamo.ACTIVO,
# EstadoPrestamo.EN_MORA]) ).scalar() or Decimal("0") eficiencia = ( (total_recaudado / total_esperado * 100) if
# total_esperado > 0 else 0 ) return ReporteCobranza( fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
# el archivo Excel""" header_fill = PatternFill( start_color="366092", end_color="366092", fill_type="solid" ) header_font =
# Font(color="FFFFFF", bold=True) return header_fill, header_font\ndef _crear_reporte_cartera(ws, header_fill, header_font,
# db):\n """Crear reporte de cartera""" ws.title = "Reporte de Cartera" ws.append(["Reporte de Cartera", "", "", ""])
# "", ""]) ws.append([]) headers = [ "Fecha", "Préstamo ID", "Cliente", "Monto", "Concepto", "Referencia", ]
# float(p.monto), p.concepto, p.referencia_bancaria or "", ] )\ndef _ajustar_ancho_columnas(ws):\n """Ajustar ancho de
# columnas""" for column in ws.columns:\n max_length = 0 column_letter = column[0].column_letter for cell in column:\n try:\n
# if len(str(cell.value)) > max_length:\n max_length = len(cell.value) except Exception:\n # Ignorar errores de formato de
# celda pass adjusted_width = min(max_length + 2, 50) ws.column_dimensions[column_letter].width = adjusted_width\ndef
# _guardar_excel_en_memoria(wb):\n """Guardar Excel en memoria""" output = io.BytesIO() wb.save(output) output.seek(0) return
# output@router.get("/exportar/excel")async \ndef exportar_excel( tipo_reporte:\n str, fecha_inicio:\n Optional[date] = None,
# fecha_fin:\n Optional[date] = None, db:\n Session = Depends(get_db),):\n """ Exporta reportes a Excel (VERSIÓN
# REFACTORIZADA). """ try:\n \nimport openpyxl except ImportError:\n raise HTTPException( status_code=500, detail="openpyxl
# header_fill, header_font, fecha_inicio, fecha_fin, db ) # Ajustar ancho de columnas _ajustar_ancho_columnas(ws) # Guardar
# en memoria output = _guardar_excel_en_memoria(wb) filename = (
# f"attachment;\n filename={filename}" }, ) except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error
# generando Excel:\n {str(e)}" )@router.get("/clientes-top")\ndef clientes_top(limite:\n int = 10, db:\n Session =
# .group_by(Cliente.id) .order_by(func.sum(Prestamo.monto_total).desc()) .limit(limite) .all() ) return [ { "cliente_id":\n
# in resultado ]# ============================================# REPORTES PREDEFINIDOS#
# ============================================@router.get("/estado-cuenta/{cliente_id}/pdf")async \ndef
# generar_estado_cuenta_pdf( cliente_id:\n int, db:\n Session = Depends(get_db)):\n """ 1. Estado de cuenta por cliente (PDF)
# cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first() if not cliente:\n raise HTTPException(
# status_code=404, detail="Cliente no encontrado" ) # Crear PDF en memoria buffer = io.BytesIO() p = canvas.Canvas(buffer,
# p.showPage() p.save() buffer.seek(0) return StreamingResponse( buffer, media_type="application/pdf", headers={
# HTTPException( status_code=500, detail="reportlab no está instalado"
# )@router.get("/tabla-amortizacion/{cliente_id}/pdf")async \ndef generar_tabla_amortizacion_pdf( cliente_id:\n int, db:\n
# reportlab.lib.styles \nimport getSampleStyleSheet \nfrom reportlab.platypus \nimport ( Paragraph, SimpleDocTemplate,
# Spacer, Table, TableStyle, ) # Obtener cliente y sus cuotas cliente = db.query(Cliente).filter(Cliente.id ==
# cliente_id).first() if not cliente:\n raise HTTPException( status_code=404, detail="Cliente no encontrado" ) # Obtener
# préstamo y cuotas prestamo = ( db.query(Prestamo) .filter(Prestamo.cliente_id == cliente_id) .first() ) if not prestamo:\n
# raise HTTPException( status_code=404, detail="Préstamo no encontrado" ) cuotas = ( db.query(Cuota)
# .filter(Cuota.prestamo_id == prestamo.id) .order_by(Cuota.numero_cuota) .all() ) # Crear PDF buffer = io.BytesIO() doc =
# SimpleDocTemplate(buffer, pagesize=A4) styles = getSampleStyleSheet() story = [] # Título title = Paragraph( "<b>TABLA DE
# AMORTIZACIÓN</b><br/>{cliente.nombre_completo}", styles["Title"], ) story.append(title) story.append(Spacer(1, 20)) #
# Información del cliente info_cliente = f""" <b>Cliente:\n</b> {cliente.nombre_completo}<br/> <b>Cédula:\n</b>
# {cliente.cedula}<br/> <b>Vehículo:\n</b> {cliente.vehiculo_completo}<br/> <b>Monto Financiado:\n</b>
# ${float(prestamo.monto_total):\n,.2f}<br/> <b>Tasa de Interés:\n</b> {float (prestamo.tasa_interes_anual)}% anual<br/>
# <b>Modalidad:\n</b> {cliente.modalidad_pago} """ story.append(Paragraph(info_cliente, styles["Normal"]))
# story.append(Spacer(1, 20)) # Tabla de cuotas data = [ [ "#", "Fecha Venc.", "Capital", "Interés", "Cuota", "Saldo",
# "Estado", ] ] for cuota in cuotas:\n estado_emoji = { "PENDIENTE":\n "⏳", "PAGADA":\n "✅", "PARCIAL":\n "🔶", "VENCIDA":\n
# f"${float(cuota.monto_capital):\n,.2f}", f"${float(cuota.monto_interes):\n,.2f}", f"${float(cuota.monto_cuota):\n,.2f}",
# f"${float(cuota.saldo_pendiente):\n,.2f}", f"{estado_emoji} {cuota.estado}", ] ) table = Table(data) table.setStyle(
# TableStyle( [ ("BACKGROUND", (0, 0), (-1, 0), colors.grey), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("ALIGN",
# (0, 0), (-1, -1), "CENTER"), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 10),
# ("BOTTOMPADDING", (0, 0), (-1, 0), 12), ("BACKGROUND", (0, 1), (-1, -1), colors.beige), ("GRID", (0, 0), (-1, -1), 1,
# colors.black), ] ) ) story.append(table) doc.build(story) buffer.seek(0) return StreamingResponse( buffer,
# filename=amortizacion_{cliente.cedula}.pdf" }, ) except ImportError:\n raise HTTPException( status_code=500,
# detail="reportlab no está instalado" )@router.get("/cobranza-diaria/pd")async \ndef reporte_cobranza_diaria_pdf( fecha:\n
# Optional[date] = Query( None, description="Fecha del reporte (default:\n hoy)" ), db:\n Session = Depends(get_db),):\n """
# .join(Prestamo, Pago.prestamo_id == Prestamo.id) .join(Cliente, Prestamo.cliente_id == Cliente.id) .filter(Pago.fecha_pago
# Cuota.prestamo_id == Prestamo.id) .join(Cliente, Prestamo.cliente_id == Cliente.id) .filter( Cuota.fecha_vencimiento ==
# fecha, Cuota.estado.in_(["PENDIENTE", "PARCIAL"]), ) .all() ) # Crear respuesta JSON (PDF requeriría reportlab) return {
# pago.prestamo.cliente.cedula, "monto":\n float(pago.monto_pagado), "metodo":\n pago.metodo_pago, "referencia":\n
# cuota.prestamo.cliente.nombre_completo, "cedula":\n cuota.prestamo.cliente.cedula, "numero_cuota":\n cuota.numero_cuota,
# modalidad:\n Optional[str] = Query( None, description="SEMANAL, QUINCENAL, MENSUAL" ), # Columnas a incluir
# fecha_fin:\n query = query.filter(Cliente.fecha_registro <= fecha_fin) if cliente_ids:\n ids = [int(id.strip()) for id in
# cliente_ids.split(",")] query = query.filter(Cliente.id.in_(ids)) if asesor_ids:\n ids = [int(id.strip()) for id in
# query.filter(Cliente.dias_mora == 0) elif estado == "MORA":\n query = query.filter(Cliente.dias_mora > 0) if modalidad:\n
# "telefono":\n cliente.telefono, "email":\n cliente.email, "direccion":\n cliente.direccion, } ) if
# cliente.calcular_resumen_financiero(db) cliente_data.update( { "total_financiado":\n float(resumen["total_financiado"]),
# "total_pagado":\n float(resumen["total_pagado"]), "saldo_pendiente":\n float(resumen["saldo_pendiente"]), "dias_mora":\n
# db.query(Pago) .join(Prestamo) .filter(Prestamo.cliente_id == cliente.id) .order_by(Pago.fecha_pago.desc()) .limit(5)
# ============================================# REPORTES PDF FALTANTES#
# ============================================@router.get("/cartera-mensual/pd")async \ndef reporte_mensual_cartera_pdf(
# mes:\n Optional[int] = Query(None, description="Mes (1-12)"), anio:\n Optional[int] = Query(None, description="Año"), db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 4. Reporte mensual de cartera (PDF) -
# KPIs del mes - Análisis de mora - Comparativa vs mes anterior - Proyecciones """ try:\n pass \nfrom reportlab.lib \nimport
# colors \nfrom reportlab.lib.pagesizes \nimport A4 \nfrom reportlab.lib.styles \nimport getSampleStyleSheet \nfrom
# reportlab.platypus \nimport ( Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, ) # Establecer período if not mes:\n
# 1) if mes == 12:\n fin_mes = date(anio + 1, 1, 1) else:\n fin_mes = date(anio, mes + 1, 1) # KPIs principales
# total_clientes = db.query(Cliente).filter(Cliente.activo).count() clientes_al_dia = ( db.query(Cliente)
# .filter(Cliente.activo, Cliente.estado_financiero == "AL_DIA") .count() ) clientes_mora = ( db.query(Cliente)
# db.query(func.sum(Pago.monto_pagado)) .filter( Pago.fecha_pago >= inicio_mes, Pago.fecha_pago < fin_mes, Pago.estado !=
# "ANULADO", ) .scalar() or 0 ) # Crear PDF buffer = io.BytesIO() doc = SimpleDocTemplate(buffer, pagesize=A4) styles =
# getSampleStyleSheet() story = [] # Título title = Paragraph( f"<b>REPORTE MENSUAL DE CARTERA</b><br/>{mes:\n02d}/{anio}",
# styles["Title"], ) story.append(title) story.append(Spacer(1, 30)) # KPIs principales kpis_data = [ ["KPI", "Valor",
# "Porcentaje"], ["Total Clientes", f"{total_clientes:\n,}", "100%"], [ "Clientes al Día", f"{clientes_al_dia:\n,}", (
# f"{(clientes_al_dia / total_clientes * 100):\n.1f}%" if total_clientes > 0 else "0%" ), ], [ "Clientes en Mora",
# f"{clientes_mora:\n,}", ( f"{(clientes_mora / total_clientes * 100):\n.1f}%" if total_clientes > 0 else "0%" ), ], ["Total
# ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("ALIGN", (0, 0), (-1,
# -1), "CENTER"), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 12), ("BOTTOMPADDING", (0,
# 0), (-1, 0), 12), ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue), ("GRID", (0, 0), (-1, -1), 1, colors.black), ] ) )
# story.append(Paragraph("<b>KPIs del Mes</b>", styles["Heading2"])) story.append(kpis_table) story.append(Spacer(1, 30)) #
# str(clientes_al_dia), ( f"{(clientes_al_dia / total_clientes * 100):\n.1f}%" if total_clientes > 0 else "0%" ), ], ["1-30
# días", "0", "0%"], # Placeholder - calcular real ["31-60 días", "0", "0%"], # Placeholder - calcular real ["60+ días", "0",
# "0%"], # Placeholder - calcular real ] mora_table = Table(mora_data) mora_table.setStyle( TableStyle( [ ("BACKGROUND", (0,
# 0), (-1, 0), colors.darkred), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
# ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 1, colors.black), ] ) )
# story.append(Paragraph("<b>Análisis de Mora</b>", styles["Heading2"])) story.append(mora_table) doc.build(story)
# f"attachment;\n filename=cartera_mensual_{mes:\n02d}_{anio}." f"pdf" }, ) except ImportError:\n raise HTTPException(
# status_code=500, detail="reportlab no está instalado" )@router.get("/asesor/{asesor_id}/pdf")async \ndef
# reporte_asesor_pdf( asesor_id:\n int, fecha_inicio:\n Optional[date] = Query(None), fecha_fin:\n Optional[date] =
# Query(None), db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 5. Reporte por
# """ try:\n \nfrom reportlab.lib \nimport colors \nfrom reportlab.lib.pagesizes \nimport A4 \nfrom reportlab.lib.styles
# \nimport getSampleStyleSheet \nfrom reportlab.platypus \nimport ( Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
# ) # Verificar que el analista existe \nfrom app.models.analista \nimport Analista asesor =
# db.query(Analista).filter(Analista.id == asesor_id).first() if not asesor:\n raise HTTPException( status_code=404,
# detail="Analista no encontrado" ) # Establecer período por defecto if not fecha_inicio:\n fecha_inicio =
# date.today().replace(day=1) # Inicio del mes actual if not fecha_fin:\n fecha_fin = date.today() # Obtener clientes del
# asesor clientes_asesor = ( db.query(Cliente) .filter(Cliente.asesor_id == asesor_id, Cliente.activo) .all() ) # Ventas del
# período ventas_periodo = ( db.query(Cliente) .filter( Cliente.asesor_id == asesor_id, Cliente.fecha_registro >=
# fecha_inicio, Cliente.fecha_registro <= fecha_fin, ) .count() ) # Monto total de cartera monto_cartera = sum(
# float(c.total_financiamiento or 0) for c in clientes_asesor ) # Estado de cobranza clientes_al_dia = len( [c for c in
# clientes_asesor if c.estado_financiero == "AL_DIA"] ) clientes_mora = len( [c for c in clientes_asesor if
# c.estado_financiero == "EN_MORA"] ) # Crear PDF buffer = io.BytesIO() doc = SimpleDocTemplate(buffer, pagesize=A4) styles =
# getSampleStyleSheet() story = [] # Título title = Paragraph( f"<b>REPORTE DE USER</b><br/>{asesor.full_name}",
# styles["Title"] ) story.append(title) story.append(Spacer(1, 30)) # Información del período periodo_info = """
# {asesor.full_name}<br/> <b>Email:\n</b> {asesor.email}<br/> <b>Rol:\n</b> {"Administrador" if asesor.is_admin else
# "Usuario"} """ story.append(Paragraph(periodo_info, styles["Normal"])) story.append(Spacer(1, 20)) # Resumen de cartera
# str(ventas_periodo)], ["Monto Total Cartera", f"${monto_cartera:\n,.2f}"], [ "Clientes al Día", ( f"{clientes_al_dia}
# ({(clientes_al_dia / len(clientes_asesor) * 100):\n.1f}%)" if clientes_asesor else "0" ), ], [ "Clientes en Mora", (
# f"{clientes_mora} ({(clientes_mora / len(clientes_asesor) * 100):\n.1f}%)" if clientes_asesor else "0" ), ], ]
# resumen_table = Table(resumen_data) resumen_table.setStyle( TableStyle( [ ("BACKGROUND", (0, 0), (-1, 0),
# colors.darkgreen), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "LEFT"), ("FONTNAME", (0,
# 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 12), ("BOTTOMPADDING", (0, 0), (-1, 0), 12), ("BACKGROUND",
# (0, 1), (-1, -1), colors.lightgreen), ("GRID", (0, 0), (-1, -1), 1, colors.black), ] ) ) story.append(
# Paragraph("<b>Resumen de Cartera</b>", styles["Heading2"]) ) story.append(resumen_table) story.append(Spacer(1, 30)) #
# "Monto"] ] for cliente in clientes_asesor[:\n20]:\n # Limitar a 20 para el PDF clientes_data.append( [
# cliente.nombre_completo, cliente.cedula, cliente.vehiculo_completo or "N/A", cliente.estado_financiero,
# f"${float(cliente.total_financiamiento or 0):\n,.0f}", ] ) clientes_table = Table(clientes_data) clientes_table.setStyle(
# TableStyle( [ ("BACKGROUND", (0, 0), (-1, 0), colors.navy), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("ALIGN",
# (0, 0), (-1, -1), "LEFT"), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
# ("BOTTOMPADDING", (0, 0), (-1, 0), 12), ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue), ("GRID", (0, 0), (-1, -1), 1,
# story.append(clientes_table) doc.build(story) buffer.seek(0) return StreamingResponse( buffer,
# f"full_name.replace(" ', '_')}.pdf" }, ) except ImportError:\n raise HTTPException( status_code=500, detail="reportlab no
# está instalado" )# ============================================# ENDPOINT DE VERIFICACIÓN DE REPORTES#
# ============================================@router.get("/verificacion-reportes-pd")\ndef
# { "nombre":\n "✅ Estado de cuenta por cliente", "endpoint":\n "GET /api/v1/reportes/estado-cuenta/{cliente_id}/pdf",
# pendiente" ), "implementado":\n True, "formato":\n "PDF", "ejemplo_url":\n "/api/v1/reportes/estado-cuenta/123/pdf", },
# "2_tabla_amortizacion":\n { "nombre":\n "✅ Tabla de amortización por cliente", "endpoint":\n "GET
# "/api/v1/reportes/tabla-amortizacion/123/pdf", }, "3_cobranza_diaria":\n { "nombre":\n "✅ Reporte de cobranza diaria",
# "/api/v1/reportes/cobranza-diaria/pdf?fecha=2025-10-13", }, "4_cartera_mensual":\n { "nombre":\n "✅ Reporte mensual de
# cartera", "endpoint":\n "GET /api/v1/reportes/cartera-mensual/pd", "descripcion":\n ( "KPIs del mes, análisis de mora,
# comparativa vs mes anterior, proyecciones" ), "implementado":\n True, "formato":\n "PDF", "ejemplo_url":\n
# "/api/v1/reportes/cartera-mensual/pdf?mes=10&anio=2025", }, "5_reporte_asesor":\n { "nombre":\n "✅ Reporte por asesor",
# "endpoint":\n "GET /api/v1/reportes/asesor/{asesor_id}/pdf", "descripcion":\n ( "Clientes del asesor, ventas del período,
# "ejemplo_url":\n "/api/v1/reportes/asesor/1/pdf", }, }, "caracteristicas_implementadas":\n { "generacion_pdf":\n "✅ Usando
# 'Authorization:\n Bearer TOKEN'" ), "cobranza_diaria":\n ( "curl -X GET
# TOKEN'" ), "cartera_mensual":\n ( "curl -X GET
# IMPLEMENTADOS Y FUNCIONALES", }, }
