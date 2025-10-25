from datetime import date
# backend/app/services/amortizacion_service.py"""Servicio de AmortizaciónLógica de negocio para generación y gestión de
# Optionalfrom sqlalchemy import and_from sqlalchemy.orm import Sessionfrom app.models.amortizacion import Cuotafrom
# app.schemas.amortizacion import ( CuotaDetalle, TablaAmortizacionRequest, TablaAmortizacionResponse,)from
# app.utils.date_helpers import calculate_payment_datesclass AmortizacionService: """Servicio para gestión de amortización"""
# @staticmethod def generar_tabla_amortizacion( request: TablaAmortizacionRequest, ) -> TablaAmortizacionResponse: """ Genera
# TablaAmortizacionResponse: Tabla de amortización completa """ if request.sistema_amortizacion == "FRANCES": return
# AmortizacionService._generar_frances(request) elif request.sistema_amortizacion == "ALEMAN": return
# AmortizacionService._generar_aleman(request) elif request.sistema_amortizacion == "AMERICANO": return
# AmortizacionService._generar_americano(request) else: raise ValueError
# {request. \ sistema_amortizacion}" ) @staticmethod def _generar_frances( request: TablaAmortizacionRequest, ) ->
# TablaAmortizacionResponse: """ Sistema Francés: Cuota fija Fórmula: C = P * [i(1+i)^n] / [(1+i)^n - 1] """ monto =
# request.monto_financiado tasa_anual = request.tasa_interes_anual / Decimal("100") n_cuotas = request.numero_cuotas #
# Calcular tasa por período según modalidad if request.modalidad == "SEMANAL": tasa_periodo = tasa_anual / Decimal("52") elif
# request.modalidad == "QUINCENAL": tasa_periodo = tasa_anual / Decimal("24") elif request.modalidad == "MENSUAL":
# tasa_periodo = tasa_anual / Decimal("12") elif request.modalidad == "BIMENSUAL": tasa_periodo = tasa_anual / Decimal("6")
# elif request.modalidad == "TRIMESTRAL": tasa_periodo = tasa_anual / Decimal("4") else: tasa_periodo = tasa_anual /
# Decimal("12") # Calcular cuota fija (si tasa > 0) if tasa_periodo > 0: factor = (tasa_periodo * (1 + tasa_periodo) **
# n_cuotas) / ( (1 + tasa_periodo) ** n_cuotas - 1 ) cuota_fija = monto * factor else: # Sin interés, solo dividir el monto
# cuota_fija = monto / Decimal(n_cuotas) cuota_fija = cuota_fija.quantize( Decimal("0.01"), rounding=ROUND_HALF_UP ) #
# Generar fechas de vencimiento fechas = calculate_payment_dates
# request.modalidad ) # Generar cuotas cuotas = [] saldo = monto total_capital = Decimal("0.00") total_interes =
# Decimal("0.00") for i in range(n_cuotas): # Calcular interés del período interes = (saldo * tasa_periodo).quantize
# Decimal("0.01"), rounding=ROUND_HALF_UP ) # Calcular capital (cuota - interés) capital = cuota_fija - interes # Ajuste en
# saldo - capital cuota = CuotaDetalle
# capital=capital, interes=interes, cuota=cuota_fija, saldo_final=nuevo_saldo, ) cuotas.append(cuota) # Actualizar para
# siguiente iteración saldo = nuevo_saldo total_capital += capital total_interes += interes # Preparar resumen resumen = 
# request.modalidad, "sistema": "FRANCES", } return TablaAmortizacionResponse
# Saldo * Tasa """ monto = request.monto_financiado tasa_anual = request.tasa_interes_anual / Decimal("100") n_cuotas =
# request.numero_cuotas # Calcular tasa por período if request.modalidad == "MENSUAL": tasa_periodo = tasa_anual /
# Decimal("12") else: tasa_periodo = tasa_anual / Decimal("12") # Capital fijo por cuota capital_fijo = 
# Decimal(n_cuotas)).quantize( Decimal("0.01"), rounding=ROUND_HALF_UP ) # Generar fechas fechas = calculate_payment_dates
# request.fecha_primer_vencimiento, n_cuotas, request.modalidad ) # Generar cuotas cuotas = [] saldo = monto total_capital =
# Decimal("0.00") total_interes = Decimal("0.00") for i in range(n_cuotas): # Interés sobre saldo interes = 
# tasa_periodo).quantize( Decimal("0.01"), rounding=ROUND_HALF_UP ) # Capital fijo (ajuste en última cuota) if i == n_cuotas
# - 1: capital = saldo else: capital = capital_fijo # Cuota total cuota_total = capital + interes # Nuevo saldo nuevo_saldo =
# saldo - capital cuota = CuotaDetalle
# capital=capital, interes=interes, cuota=cuota_total, saldo_final=nuevo_saldo, ) cuotas.append(cuota) saldo = nuevo_saldo
# total_capital += capital total_interes += interes resumen = 
# request.tasa_interes_anual, "numero_cuotas": n_cuotas, "modalidad": request.modalidad, "sistema": "ALEMAN", } return
# request: TablaAmortizacionRequest, ) -> TablaAmortizacionResponse: """ Sistema Americano: Solo interés en cuotas, capital
# al final """ monto = request.monto_financiado tasa_anual = request.tasa_interes_anual / Decimal("100") n_cuotas =
# request.numero_cuotas # Tasa por período tasa_periodo = tasa_anual / Decimal("12") # Interés fijo por período interes_fijo
# = (monto * tasa_periodo).quantize( Decimal("0.01"), rounding=ROUND_HALF_UP ) # Generar fechas fechas =
# calculate_payment_dates( request.fecha_primer_vencimiento, n_cuotas, request.modalidad ) # Generar cuotas cuotas = []
# total_interes = Decimal("0.00") for i in range(n_cuotas): if i == n_cuotas - 1: # Última cuota: capital + interés capital =
# monto interes = interes_fijo cuota_total = capital + interes saldo_final = Decimal("0.00") else: # Cuotas intermedias: solo
# interés capital = Decimal("0.00") interes = interes_fijo cuota_total = interes saldo_final = monto cuota = CuotaDetalle
# saldo_final=saldo_final, ) cuotas.append(cuota) total_interes += interes resumen = 
# "numero_cuotas": n_cuotas, "modalidad": request.modalidad, "sistema": "AMERICANO", } return TablaAmortizacionResponse
# int, tabla: TablaAmortizacionResponse ) -> List[Cuota]: """ Crea las cuotas en la BD para un préstamo Args: db: Sesión de
# cuotas_creadas = [] for cuota_detalle in tabla.cuotas: cuota = Cuota
# capital_pendiente=cuota_detalle.capital, interes_pendiente=cuota_detalle.interes, estado="PENDIENTE", ) db.add(cuota)
# cuotas_creadas.append(cuota) db.commit() return cuotas_creadas @staticmethod def obtener_cuotas_prestamo
# prestamo_id: int, estado: Optional[str] = None ) -> List[Cuota]: """Obtiene las cuotas de un préstamo""" query =
# db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id) if estado: query = query.filter(Cuota.estado == estado) return
# query.order_by(Cuota.numero_cuota).all() @staticmethod def recalcular_mora
# tasa_mora_diaria: Decimal, fecha_calculo: Optional[date] = None, ) -> dict: """ Recalcula la mora de todas las cuotas
# diaria (%) fecha_calculo: Fecha para el cálculo Returns: dict: Resumen del recálculo """ if fecha_calculo is None:
# fecha_calculo = date.today() # Obtener cuotas vencidas cuotas = ( db.query(Cuota) .filter
# prestamo_id, Cuota.estado.in_(["VENCIDA", "PARCIAL"]), Cuota.fecha_vencimiento < fecha_calculo, ) ) .all() )
# total_mora_anterior = Decimal("0.00") total_mora_nueva = Decimal("0.00") cuotas_actualizadas = 0 for cuota in cuotas:
# total_mora_anterior += cuota.monto_mora # Calcular nueva mora nueva_mora = cuota.calcular_mora(tasa_mora_diaria) #
# Actualizar cuota.monto_mora = nueva_mora cuota.dias_mora = (fecha_calculo - cuota.fecha_vencimiento).days cuota.tasa_mora =
# tasa_mora_diaria total_mora_nueva += nueva_mora cuotas_actualizadas += 1 db.commit() return 
# total_mora_nueva - total_mora_anterior, }
