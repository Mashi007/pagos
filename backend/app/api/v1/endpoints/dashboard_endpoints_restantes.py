# Archivo temporal con los endpoints restantes - Copiar al final de dashboard.py


@router.get("/morosidad-por-analista")
def obtener_morosidad_por_analista(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 3: Morosidad por Analista
    Todos los clientes que tienen morosidad desde 1 día
    """
    try:
        hoy = date.today()

        # Obtener morosidad por analista (morosidad = cuotas vencidas no pagadas)
        query = (
            db.query(
                func.coalesce(Prestamo.analista, Prestamo.producto_financiero, "Sin Analista").label("analista"),
                func.sum(Cuota.monto_cuota).label("total_morosidad"),
                func.count(func.distinct(Prestamo.cedula)).label("cantidad_clientes"),
                func.count(Cuota.id).label("cantidad_cuotas_atrasadas"),
            )
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
            )
            .group_by("analista")
        )

        # Aplicar filtros (excepto analista que ya estamos agrupando)
        if concesionario:
            query = query.filter(Prestamo.concesionario == concesionario)
        if modelo:
            query = query.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))

        resultados = query.all()

        analistas_data = []
        for row in resultados:
            total_morosidad = float(row.total_morosidad or Decimal("0"))
            cantidad_clientes = row.cantidad_clientes or 0
            cantidad_cuotas = row.cantidad_cuotas_atrasadas or 0

            promedio_por_cliente = total_morosidad / cantidad_clientes if cantidad_clientes > 0 else 0

            analistas_data.append(
                {
                    "analista": row.analista or "Sin Analista",
                    "total_morosidad": total_morosidad,
                    "cantidad_clientes": cantidad_clientes,
                    "cantidad_cuotas_atrasadas": cantidad_cuotas,
                    "promedio_morosidad_por_cliente": promedio_por_cliente,
                }
            )

        return {"analistas": analistas_data}

    except Exception as e:
        logger.error(f"Error obteniendo morosidad por analista: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/prestamos-por-concesionario")
def obtener_prestamos_por_concesionario(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 4: Préstamos por Concesionario (expresado en porcentaje)
    """
    try:
        # Obtener total general de préstamos
        query_base = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
        query_base = FiltrosDashboard.aplicar_filtros_prestamo(
            query_base, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

        total_general = float(query_base.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0"))

        # Agrupar por concesionario
        query_concesionarios = (
            db.query(
                func.coalesce(Prestamo.concesionario, "Sin Concesionario").label("concesionario"),
                func.sum(Prestamo.total_financiamiento).label("total_prestamos"),
                func.count(Prestamo.id).label("cantidad_prestamos"),
            )
            .filter(Prestamo.estado == "APROBADO")
            .group_by("concesionario")
        )

        # Aplicar filtros
        if analista:
            query_concesionarios = query_concesionarios.filter(
                or_(Prestamo.analista == analista, Prestamo.producto_financiero == analista)
            )
        if modelo:
            query_concesionarios = query_concesionarios.filter(
                or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo)
            )
        if fecha_inicio:
            query_concesionarios = query_concesionarios.filter(Prestamo.fecha_registro >= fecha_inicio)
        if fecha_fin:
            query_concesionarios = query_concesionarios.filter(Prestamo.fecha_registro <= fecha_fin)

        resultados = query_concesionarios.all()

        concesionarios_data = []
        for row in resultados:
            total_prestamos = float(row.total_prestamos or Decimal("0"))
            porcentaje = (total_prestamos / total_general * 100) if total_general > 0 else 0

            concesionarios_data.append(
                {
                    "concesionario": row.concesionario or "Sin Concesionario",
                    "total_prestamos": total_prestamos,
                    "cantidad_prestamos": row.cantidad_prestamos or 0,
                    "porcentaje": round(porcentaje, 2),
                }
            )

        return {
            "concesionarios": concesionarios_data,
            "total_general": total_general,
        }

    except Exception as e:
        logger.error(f"Error obteniendo préstamos por concesionario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/distribucion-prestamos")
def obtener_distribucion_prestamos(
    tipo: str = Query("rango_monto", description="Tipo de distribución: rango_monto, plazo, rango_monto_plazo, estado"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 5: Distribución de Préstamos
    """
    try:
        query_base = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
        query_base = FiltrosDashboard.aplicar_filtros_prestamo(
            query_base, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

        total_prestamos = query_base.count()
        total_monto = float(query_base.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0"))

        distribucion_data = []

        if tipo == "rango_monto":
            # Rangos: 0-5000, 5000-10000, 10000-20000, 20000-50000, 50000+
            rangos = [
                (0, 5000, "0 - $5,000"),
                (5000, 10000, "$5,000 - $10,000"),
                (10000, 20000, "$10,000 - $20,000"),
                (20000, 50000, "$20,000 - $50,000"),
                (50000, None, "$50,000+"),
            ]

            for min_val, max_val, categoria in rangos:
                query_rango = query_base.filter(Prestamo.total_financiamiento >= Decimal(str(min_val)))
                if max_val:
                    query_rango = query_rango.filter(Prestamo.total_financiamiento < Decimal(str(max_val)))

                cantidad = query_rango.count()
                monto_total = float(
                    query_rango.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0")
                )
                porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
                porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0

                distribucion_data.append(
                    {
                        "categoria": categoria,
                        "cantidad_prestamos": cantidad,
                        "monto_total": monto_total,
                        "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                        "porcentaje_monto": round(porcentaje_monto, 2),
                    }
                )

        elif tipo == "plazo":
            # Agrupar por numero_cuotas (plazo)
            query_plazo = (
                query_base.with_entities(
                    Prestamo.numero_cuotas.label("plazo"),
                    func.count(Prestamo.id).label("cantidad"),
                    func.sum(Prestamo.total_financiamiento).label("monto_total"),
                )
                .group_by(Prestamo.numero_cuotas)
                .order_by(Prestamo.numero_cuotas)
            )

            resultados = query_plazo.all()
            for row in resultados:
                cantidad = row.cantidad or 0
                monto_total = float(row.monto_total or Decimal("0"))
                porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
                porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0

                distribucion_data.append(
                    {
                        "categoria": f"{row.plazo} cuotas",
                        "cantidad_prestamos": cantidad,
                        "monto_total": monto_total,
                        "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                        "porcentaje_monto": round(porcentaje_monto, 2),
                    }
                )

        elif tipo == "estado":
            # Agrupar por estado (aunque todos deberían ser APROBADO)
            query_estado = query_base.with_entities(
                Prestamo.estado.label("estado"),
                func.count(Prestamo.id).label("cantidad"),
                func.sum(Prestamo.total_financiamiento).label("monto_total"),
            ).group_by(Prestamo.estado)

            resultados = query_estado.all()
            for row in resultados:
                cantidad = row.cantidad or 0
                monto_total = float(row.monto_total or Decimal("0"))
                porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
                porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0

                distribucion_data.append(
                    {
                        "categoria": row.estado or "Sin Estado",
                        "cantidad_prestamos": cantidad,
                        "monto_total": monto_total,
                        "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                        "porcentaje_monto": round(porcentaje_monto, 2),
                    }
                )

        elif tipo == "rango_monto_plazo":
            # Combinación: rango de monto + plazo
            rangos_monto = [
                (0, 10000, "Pequeño"),
                (10000, 30000, "Mediano"),
                (30000, None, "Grande"),
            ]
            rangos_plazo = [
                (0, 12, "Corto"),
                (12, 36, "Medio"),
                (36, None, "Largo"),
            ]

            for min_monto, max_monto, cat_monto in rangos_monto:
                for min_plazo, max_plazo, cat_plazo in rangos_plazo:
                    query_combinado = query_base.filter(Prestamo.total_financiamiento >= Decimal(str(min_monto)))
                    if max_monto:
                        query_combinado = query_combinado.filter(Prestamo.total_financiamiento < Decimal(str(max_monto)))

                    query_combinado = query_combinado.filter(Prestamo.numero_cuotas >= min_plazo)
                    if max_plazo:
                        query_combinado = query_combinado.filter(Prestamo.numero_cuotas < max_plazo)

                    cantidad = query_combinado.count()
                    if cantidad > 0:
                        monto_total = float(
                            query_combinado.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0")
                        )
                        porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
                        porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0

                        distribucion_data.append(
                            {
                                "categoria": f"{cat_monto} - {cat_plazo}",
                                "cantidad_prestamos": cantidad,
                                "monto_total": monto_total,
                                "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                                "porcentaje_monto": round(porcentaje_monto, 2),
                            }
                        )

        return {
            "distribucion": distribucion_data,
            "tipo": tipo,
            "total_prestamos": total_prestamos,
            "total_monto": total_monto,
        }

    except Exception as e:
        logger.error(f"Error obteniendo distribución de préstamos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/cuentas-cobrar-tendencias")
def obtener_cuentas_cobrar_tendencias(
    meses_proyeccion: int = Query(6, description="Meses de proyección adelante"),
    granularidad: str = Query(
        "mes_actual", description="Granularidad: mes_actual, proximos_n_dias, hasta_fin_anio, personalizado"
    ),
    dias: Optional[int] = Query(None, description="Días para granularidad 'proximos_n_dias'"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 6: Tendencias de Cuentas por Cobrar y Cuotas en Días
    """
    try:
        hoy = date.today()

        # Determinar rango de fechas según granularidad
        if granularidad == "mes_actual":
            fecha_inicio_query = date(hoy.year, hoy.month, 1)
            if hoy.month == 12:
                fecha_fin_query = date(hoy.year + 1, 1, 1)
            else:
                fecha_fin_query = date(hoy.year, hoy.month + 1, 1)
        elif granularidad == "proximos_n_dias":
            fecha_inicio_query = hoy
            fecha_fin_query = hoy + timedelta(days=dias or 30)
        elif granularidad == "hasta_fin_anio":
            fecha_inicio_query = hoy
            fecha_fin_query = date(hoy.year, 12, 31)
        else:  # personalizado
            fecha_inicio_query = fecha_inicio or hoy
            fecha_fin_query = fecha_fin or (hoy + timedelta(days=30))

        # Extender hasta incluir proyección
        fecha_fin_proyeccion = fecha_fin_query + timedelta(days=meses_proyeccion * 30)

        # Generar lista de fechas (diaria)
        datos = []
        current_date = fecha_inicio_query
        fecha_division = fecha_fin_query  # Separación entre datos reales y proyección

        while current_date <= fecha_fin_proyeccion:
            es_proyeccion = current_date > fecha_division

            # CUENTAS POR COBRAR: Suma de monto_cuota de cuotas pendientes hasta esa fecha
            if not es_proyeccion:
                query_cuentas = (
                    db.query(func.sum(Cuota.monto_cuota))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_vencimiento <= current_date,
                        Cuota.estado != "PAGADO",
                    )
                )
                query_cuentas = FiltrosDashboard.aplicar_filtros_cuota(
                    query_cuentas, analista, concesionario, modelo, fecha_inicio, fecha_fin
                )
                cuentas_por_cobrar = float(query_cuentas.scalar() or Decimal("0"))
            else:
                # Proyección: usar promedio de últimos 30 días
                query_promedio = (
                    db.query(func.avg(Cuota.monto_cuota))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_vencimiento >= fecha_inicio_query - timedelta(days=30),
                        Cuota.fecha_vencimiento < fecha_inicio_query,
                        Cuota.estado != "PAGADO",
                    )
                )
                query_promedio = FiltrosDashboard.aplicar_filtros_cuota(
                    query_promedio, analista, concesionario, modelo, fecha_inicio, fecha_fin
                )
                promedio_diario = float(query_promedio.scalar() or Decimal("0"))
                # Proyección simple: último valor conocido * factor de crecimiento estimado
                ultimo_valor = datos[-1]["cuentas_por_cobrar"] if datos else 0
                cuentas_por_cobrar = ultimo_valor * 1.02 if ultimo_valor > 0 else 0  # Crecimiento del 2%

            # CUOTAS EN DÍAS: Contar cuotas que se deben pagar por día (fecha_vencimiento = current_date)
            query_cuotas_dia = (
                db.query(func.count(Cuota.id))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento == current_date,
                    Cuota.estado != "PAGADO",
                )
            )
            query_cuotas_dia = FiltrosDashboard.aplicar_filtros_cuota(
                query_cuotas_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            cuotas_en_dias = query_cuotas_dia.scalar() or 0

            # Proyección de cuotas en días
            if es_proyeccion:
                # Proyección simple basada en promedio histórico
                query_promedio_cuotas = (
                    db.query(func.avg(func.count(Cuota.id)))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_vencimiento >= fecha_inicio_query - timedelta(days=30),
                        Cuota.fecha_vencimiento < fecha_inicio_query,
                        Cuota.estado != "PAGADO",
                    )
                    .group_by(Cuota.fecha_vencimiento)
                )
                promedio_cuotas = db.query(func.avg(query_promedio_cuotas.scalar())).scalar() or 0
                cuotas_en_dias = int(promedio_cuotas)

            datos.append(
                {
                    "fecha": current_date.isoformat(),
                    "fecha_formateada": current_date.strftime("%d/%m/%Y"),
                    "cuentas_por_cobrar": cuentas_por_cobrar if not es_proyeccion else None,
                    "cuentas_por_cobrar_proyectado": cuentas_por_cobrar if es_proyeccion else None,
                    "cuotas_en_dias": cuotas_en_dias if not es_proyeccion else None,
                    "cuotas_en_dias_proyectado": cuotas_en_dias if es_proyeccion else None,
                    "es_proyeccion": es_proyeccion,
                }
            )

            current_date += timedelta(days=1)

        return {
            "datos": datos,
            "fecha_inicio": fecha_inicio_query.isoformat(),
            "fecha_fin": fecha_fin_proyeccion.isoformat(),
            "meses_proyeccion": meses_proyeccion,
            "ultima_actualizacion": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo tendencias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
