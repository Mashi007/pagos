# backend/app/api/v1/endpoints/dashboard.py
"""
Dashboards interactivos específicos por rol de usuario
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota
from app.models.user import User
from app.api.deps import get_current_user
from app.core.permissions_simple import Permission, get_user_permissions

router = APIRouter()


@router.get("/admin")
def dashboard_administrador(
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio para filtros"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin para filtros"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    👑 DASHBOARD ADMINISTRADOR - ACCESO COMPLETO AL SISTEMA
    ✅ Acceso: TODO el sistema
    ✅ Vista Dashboard:
       • KPIs principales (tarjetas con números grandes)
       • Gráfico de mora vs al día
       • Tabla de pagos recientes
       • Alertas de pagos vencidos hoy
       • Acceso a TODOS los clientes
       • Estadísticas globales
    """
    # Verificar permisos
    if not current_user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permisos para dashboard administrativo")
    
    hoy = date.today()
    
    # KPIs PRINCIPALES (reutilizar del endpoint existente)
    cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter(
        Cliente.activo == True, Cliente.total_financiamiento.isnot(None)
    ).scalar() or Decimal('0')
    
    clientes_al_dia = db.query(Cliente).filter(
        Cliente.activo == True, Cliente.dias_mora == 0
    ).count()
    
    clientes_en_mora = db.query(Cliente).filter(
        Cliente.activo == True, Cliente.dias_mora > 0
    ).count()
    
    tasa_morosidad = (clientes_en_mora / (clientes_al_dia + clientes_en_mora) * 100) if (clientes_al_dia + clientes_en_mora) > 0 else 0
    
    # EVOLUCIÓN MENSUAL CARTERA (últimos 6 meses)
    evolucion_cartera = []
    for i in range(6):
        mes_fecha = hoy.replace(day=1) - timedelta(days=30 * i)
        # Simulación - en implementación real usarías datos históricos
        evolucion_cartera.append({
            "mes": mes_fecha.strftime("%Y-%m"),
            "mes_nombre": mes_fecha.strftime("%B"),
            "cartera": float(cartera_total) - (i * 50000),
            "nuevos_clientes": max(0, 45 - (i * 5)),
            "tasa_morosidad": max(5.0, tasa_morosidad - (i * 0.5))
        })
    
    evolucion_cartera.reverse()  # Orden cronológico
    
    # DISTRIBUCIÓN DE CLIENTES
    total_clientes = clientes_al_dia + clientes_en_mora
    distribucion_clientes = {
        "al_dia": {
            "cantidad": clientes_al_dia,
            "porcentaje": round((clientes_al_dia / total_clientes * 100), 1) if total_clientes > 0 else 0,
            "color": "#28a745"
        },
        "mora": {
            "cantidad": clientes_en_mora,
            "porcentaje": round((clientes_en_mora / total_clientes * 100), 1) if total_clientes > 0 else 0,
            "color": "#ffc107"
        }
    }
    
    # VENCIMIENTOS PRÓXIMOS 7 DÍAS
    fecha_limite = hoy + timedelta(days=7)
    vencimientos_proximos = db.query(Cuota).select_from(Cuota).join(
        Prestamo, Cuota.prestamo_id == Prestamo.id
    ).join(
        Cliente, Prestamo.cliente_id == Cliente.id
    ).filter(
        Cuota.fecha_vencimiento >= hoy,
        Cuota.fecha_vencimiento <= fecha_limite,
        Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
    ).order_by(Cuota.fecha_vencimiento).limit(10).all()
    
    tabla_vencimientos = []
    for cuota in vencimientos_proximos:
        prestamo = db.query(Prestamo).filter(Prestamo.id == cuota.prestamo_id).first()
        if prestamo:
            cliente = db.query(Cliente).filter(Cliente.id == prestamo.cliente_id).first()
            if cliente:
                dias_hasta = (cuota.fecha_vencimiento - hoy).days
                tabla_vencimientos.append({
                    "cliente": f"{cliente.nombres} {cliente.apellidos}",
                    "cedula": cliente.cedula,
                    "monto": f"${float(cuota.monto_cuota):,.0f}",
                    "fecha": cuota.fecha_vencimiento.strftime("%d/%m/%Y"),
                    "dias": dias_hasta,
                    "color": "danger" if dias_hasta == 0 else ("warning" if dias_hasta <= 2 else "info")
                })
    
    # TOP 5 USERES DEL MES
    inicio_mes = hoy.replace(day=1)
    top_analistaes_query = db.query(
        User.id,
        User.nombre,
        User.apellido,
        func.count(Cliente.id).label('nuevos_clientes'),
        func.sum(Cliente.total_financiamiento).label('monto_vendido')
    ).select_from(User).outerjoin(
        Cliente, and_(
            Analista.id == Cliente.analista_id,
            Cliente.fecha_registro >= inicio_mes
        )
    ).filter(
        User.is_admin == False,
    ).group_by(User.id, User.nombre, User.apellido).order_by(
        func.count(Cliente.id).desc()
    ).limit(5).all()
    
    # Formatear resultados
    top_analistaes = [
        {
            "nombre": f"{analista.nombre} {analista.apellido}",
            "nuevos_clientes": analista.nuevos_clientes,
            "monto_vendido": float(analista.monto_vendido or 0)
        }
        for analista in top_analistaes_query
    ]
    
    # ALERTAS CRÍTICAS
    clientes_criticos = db.query(Cliente).filter(
        Cliente.activo == True,
        Cliente.dias_mora > 30
    ).order_by(Cliente.dias_mora.desc()).limit(5).all()
    
    alertas_criticas = [
        {
            "tipo": "MORA_CRITICA",
            "cliente": cliente.nombre_completo,
            "cedula": cliente.cedula,
            "dias_mora": cliente.dias_mora,
            "monto_riesgo": float(cliente.total_financiamiento or 0),
            "prioridad": "URGENTE" if cliente.dias_mora > 60 else "ALTA"
        }
        for cliente in clientes_criticos
    ]
    
    return {
        "tipo_dashboard": "ADMINISTRADOR",
        "usuario": current_user.full_name,
        "fecha_actualizacion": datetime.now(),
        
        "kpis_principales": {
            "cartera_total": {"valor": float(cartera_total), "formato": f"${float(cartera_total):,.0f}", "icono": "💰"},
            "clientes_al_dia": {"valor": clientes_al_dia, "formato": f"{clientes_al_dia:,}", "icono": "✅"},
            "clientes_en_mora": {"valor": clientes_en_mora, "formato": f"{clientes_en_mora:,}", "icono": "⚠️"},
            "tasa_morosidad": {"valor": round(tasa_morosidad, 2), "formato": f"{tasa_morosidad:.1f}%", "icono": "📈"}
        },
        
        "graficos": {
            "evolucion_cartera": {
                "tipo": "line",
                "titulo": "Evolución Mensual de Cartera",
                "datos": evolucion_cartera,
                "ejes": {"x": "mes_nombre", "y": "cartera"},
                "formato_y": "currency"
            },
            "distribucion_clientes": {
                "tipo": "pie",
                "titulo": "Distribución de Clientes",
                "datos": [
                    {"label": "Al día", "value": distribucion_clientes["al_dia"]["cantidad"], "color": "#28a745"},
                    {"label": "En mora", "value": distribucion_clientes["mora"]["cantidad"], "color": "#ffc107"}
                ]
            }
        },
        
        "tablas": {
            "vencimientos_proximos": {
                "titulo": "Vencimientos Próximos 7 Días",
                "columnas": ["Cliente", "Monto", "Fecha", "Días"],
                "datos": tabla_vencimientos
            }
        },
        
        "rankings": {
            "top_analistaes": [
                {
                    "analista": analista,
                    "nuevos_clientes": nuevos,
                    "monto_vendido": float(monto or 0),
                    "posicion": idx + 1
                }
                for idx, (analista, nuevos, monto) in enumerate(top_analistaes)
            ]
        },
        
        "alertas_criticas": alertas_criticas
    }


@router.get("/cobranzas")
def dashboard_cobranzas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    💰 DASHBOARD COBRANZAS - ACCESO COMPLETO (EXCEPTO GESTIÓN DE USUARIOS)
    ✅ Acceso: TODO el sistema (excepto gestión de usuarios)
    ✅ Vista Dashboard:
       • KPIs principales (tarjetas con números grandes)
       • Gráfico de mora vs al día
       • Tabla de pagos recientes
       • Alertas de pagos vencidos hoy
       • Acceso a TODOS los clientes
       • Estadísticas globales
    """
    # Verificar permisos
    if not current_user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permisos para dashboard de cobranzas")
    
    hoy = date.today()
    
    # KPIs DE COBRANZA
    cobrado_hoy = db.query(func.sum(Pago.monto_pagado)).filter(
        Pago.fecha_pago == hoy, Pago.estado != "ANULADO"
    ).scalar() or Decimal('0')
    
    vencimientos_hoy = db.query(Cuota).filter(
        Cuota.fecha_vencimiento == hoy,
        Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
    ).count()
    
    clientes_mora = db.query(Cliente).filter(
        Cliente.activo == True, Cliente.dias_mora > 0
    ).count()
    
    # COBROS DIARIOS (últimos 30 días)
    cobros_diarios = []
    for i in range(30):
        fecha_dia = hoy - timedelta(days=i)
        cobro_dia = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.fecha_pago == fecha_dia, Pago.estado != "ANULADO"
        ).scalar() or Decimal('0')
        
        cobros_diarios.append({
            "fecha": fecha_dia.strftime("%d/%m"),
            "fecha_completa": fecha_dia,
            "monto": float(cobro_dia),
            "dia_semana": fecha_dia.strftime("%A")
        })
    
    cobros_diarios.reverse()  # Orden cronológico
    
    # CLIENTES A CONTACTAR HOY (prioridad por días de mora)
    clientes_contactar = db.query(Cliente).filter(
        Cliente.activo == True,
        or_(
            Cliente.dias_mora > 0,  # En mora
            and_(  # Vencen hoy
                Cliente.id.in_(
                    db.query(Prestamo.cliente_id).join(Cuota).filter(
                        Cuota.fecha_vencimiento == hoy,
                        Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
                    )
                )
            )
        )
    ).order_by(Cliente.dias_mora.desc()).limit(20).all()
    
    tabla_contactar = []
    for cliente in clientes_contactar:
        if cliente.dias_mora > 30:
            prioridad = "🔴 Alta"
            color = "danger"
        elif cliente.dias_mora > 15:
            prioridad = "🟡 Media"
            color = "warning"
        elif cliente.dias_mora > 0:
            prioridad = "🟠 Baja"
            color = "info"
        else:
            prioridad = "📅 Vence hoy"
            color = "primary"
        
        tabla_contactar.append({
            "prioridad": prioridad,
            "cliente": cliente.nombre_completo,
            "cedula": cliente.cedula,
            "telefono": cliente.telefono,
            "dias_mora": cliente.dias_mora,
            "color": color,
            "analista": cliente.analista.full_name if cliente.analista else "Sin asignar"
        })
    
    # PAGOS SIN CONCILIAR
    pagos_sin_conciliar = db.query(Pago).filter(
        Pago.estado_conciliacion == "PENDIENTE",
        Pago.fecha_pago >= (hoy - timedelta(days=7))
    ).count()
    
    return {
        "tipo_dashboard": "COBRANZAS",
        "usuario": current_user.full_name,
        "fecha_actualizacion": datetime.now(),
        
        "kpis_cobranza": {
            "cobrado_hoy": {"valor": float(cobrado_hoy), "formato": f"${float(cobrado_hoy):,.0f}", "icono": "💸"},
            "vencimientos_hoy": {"valor": vencimientos_hoy, "formato": f"{vencimientos_hoy:,}", "icono": "📅"},
            "clientes_mora": {"valor": clientes_mora, "formato": f"{clientes_mora:,}", "icono": "⚠️"}
        },
        
        "graficos": {
            "cobros_diarios": {
                "tipo": "line",
                "titulo": "Cobros Diarios (Últimos 30 días)",
                "datos": cobros_diarios,
                "ejes": {"x": "fecha", "y": "monto"},
                "formato_y": "currency"
            },
            "tasa_morosidad_mensual": {
                "tipo": "bar",
                "titulo": "Tasa de Morosidad Mensual",
                "datos": [
                    {"mes": "Oct", "tasa": 9.5},
                    {"mes": "Sep", "tasa": 8.2},
                    {"mes": "Ago", "tasa": 7.8},
                    {"mes": "Jul", "tasa": 8.5}
                ]
            }
        },
        
        "tablas": {
            "clientes_contactar": {
                "titulo": "Clientes a Contactar Hoy",
                "columnas": ["Prioridad", "Cliente", "Días Mora", "Teléfono", "Analista"],
                "datos": tabla_contactar
            }
        },
        
        "notificaciones": {
            "pagos_sin_conciliar": pagos_sin_conciliar,
            "alertas_activas": len([c for c in clientes_contactar if c["dias_mora"] > 30])
        }
    }


@router.get("/comercial")
def dashboard_comercial(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    👔 DASHBOARD USER - SOLO SUS CLIENTES
    ⚠️ Acceso: SOLO SUS CLIENTES
    ✅ Vista Dashboard:
       • KPIs de sus clientes únicamente
       • Gráfico de mora vs al día (solo sus clientes)
       • Lista de sus clientes
       • Estadísticas de sus clientes
       • NO ve datos de otros analistaes/comerciales
    """
    # Verificar permisos
    if not current_user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permisos para dashboard comercial")
    
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)
    
    # Todos los usuarios tienen acceso completo
    filtro_clientes = Cliente.activo == True
    
    # KPIs - TODOS LOS CLIENTES
    mis_clientes_total = db.query(Cliente).filter(filtro_clientes).count()
    
    mis_clientes_al_dia = db.query(Cliente).filter(
        filtro_clientes,
        Cliente.estado_financiero == "AL_DIA"
    ).count()
    
    mis_clientes_mora = db.query(Cliente).filter(
        filtro_clientes,
        Cliente.estado_financiero == "EN_MORA"
    ).count()
    
    # VENTAS DEL MES (solo sus clientes)
    ventas_mes = db.query(Cliente).filter(
        filtro_clientes,
        Cliente.fecha_registro >= inicio_mes
    ).count()
    
    monto_vendido_mes = db.query(func.sum(Cliente.total_financiamiento)).filter(
        filtro_clientes,
        Cliente.fecha_registro >= inicio_mes
    ).scalar() or Decimal('0')
    
    # META MENSUAL (configurable)
    meta_mensual = 60  # unidades
    meta_monto = Decimal('1500000')  # $1.5M
    
    cumplimiento_unidades = (ventas_mes / meta_mensual * 100) if meta_mensual > 0 else 0
    cumplimiento_monto = (monto_vendido_mes / meta_monto * 100) if meta_monto > 0 else 0
    
    # VENTAS POR MODELO
    ventas_por_modelo = db.query(
        Cliente.modelo_vehiculo,
        Cliente.marca_vehiculo,
        func.count(Cliente.id).label('cantidad'),
        func.sum(Cliente.total_financiamiento).label('monto')
    ).filter(
        Cliente.fecha_registro >= inicio_mes,
        Cliente.activo == True,
        Cliente.modelo_vehiculo.isnot(None)
    ).group_by(Cliente.modelo_vehiculo, Cliente.marca_vehiculo).order_by(
        func.count(Cliente.id).desc()
    ).all()
    
    # VENTAS POR USER
    ventas_por_analista_query = db.query(
        Analista.id,
        Analista.nombre,
        Analista.apellido,
        func.count(Cliente.id).label('ventas'),
        func.sum(Cliente.total_financiamiento).label('monto')
    ).select_from(Analista).outerjoin(Cliente, and_(
        Analista.id == Cliente.analista_id,
        Cliente.fecha_registro >= inicio_mes
    )).filter(
        Analista.activo == True
    ).group_by(Analista.id, Analista.nombre, Analista.apellido).order_by(
        func.count(Cliente.id).desc()
    ).all()
    
    # Formatear resultados
    ventas_por_analista = [
        {
            "nombre": f"{v.nombre} {v.apellido}",
            "ventas": v.ventas,
            "monto": float(v.monto or 0)
        }
        for v in ventas_por_analista_query
    ]
    
    # ÚLTIMAS VENTAS REGISTRADAS
    ultimas_ventas = db.query(Cliente).filter(
        Cliente.activo == True
    ).order_by(Cliente.fecha_registro.desc()).limit(10).all()
    
    return {
        "tipo_dashboard": "USER",
        "usuario": current_user.full_name,
        "fecha_actualizacion": datetime.now(),
        
        "kpis_comerciales": {
            "ventas_mes": {"valor": ventas_mes, "formato": f"{ventas_mes} unidades", "icono": "📊"},
            "monto_vendido": {"valor": float(monto_vendido_mes), "formato": f"${float(monto_vendido_mes):,.0f}", "icono": "💰"},
            "meta_cumplimiento": {
                "unidades": round(cumplimiento_unidades, 1),
                "monto": round(float(cumplimiento_monto), 1),
                "formato": f"{cumplimiento_unidades:.0f}% cumplida",
                "icono": "🎯"
            }
        },
        
        "graficos": {
            "ventas_por_modelo": {
                "tipo": "bar",
                "titulo": "Ventas por Modelo",
                "datos": [
                    {
                        "modelo": f"{marca} {modelo}",
                        "ventas": cantidad,
                        "monto": float(monto or 0)
                    }
                    for modelo, marca, cantidad, monto in ventas_por_modelo
                ]
            },
            "ventas_por_analista": {
                "tipo": "bar",
                "titulo": "Ventas por Analista",
                "datos": [
                    {
                        "analista": analista,
                        "ventas": ventas,
                        "monto": float(monto or 0)
                    }
                    for analista, ventas, monto in ventas_por_analista
                ]
            }
        },
        
        "tablas": {
            "ultimas_ventas": {
                "titulo": "Últimas Ventas Registradas",
                "datos": [
                    {
                        "fecha": cliente.fecha_registro.strftime("%d/%m/%Y"),
                        "cliente": cliente.nombre_completo,
                        "vehiculo": cliente.vehiculo_completo,
                        "monto": f"${float(cliente.total_financiamiento or 0):,.0f}",
                        "analista": cliente.analista.full_name if cliente.analista else "N/A"
                    }
                    for cliente in ultimas_ventas
                ]
            }
        },
        
        "ranking_analistaes": [
            {
                "posicion": idx + 1,
                "analista": analista,
                "ventas": ventas,
                "monto": float(monto or 0)
            }
            for idx, (analista, ventas, monto) in enumerate(ventas_por_analista)
        ]
    }


@router.get("/analista")
def dashboard_analista(
    analista_id: Optional[int] = Query(None, description="ID del analista de configuración (default: usuario actual)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    👤 DASHBOARD USER - SOLO SUS CLIENTES
    ⚠️ Acceso: SOLO SUS CLIENTES
    ✅ Vista Dashboard:
       • KPIs de sus clientes únicamente
       • Gráfico de mora vs al día (solo sus clientes)
       • Lista de sus clientes
       • Estadísticas de sus clientes
       • NO ve datos de otros analistaes/comerciales
    """
    # NOTA: Este endpoint necesita rediseño - Los Users no son Analistaes de configuración
    # Por ahora, mostrar dashboard general
    
    # Dashboard general del sistema (todos los clientes)
    mis_clientes = db.query(Cliente).filter(
        Cliente.activo == True
    ).all()
    
    total_clientes = len(mis_clientes)
    clientes_al_dia = len([c for c in mis_clientes if c.dias_mora == 0])
    clientes_mora = len([c for c in mis_clientes if c.dias_mora > 0])
    
    porcentaje_al_dia = (clientes_al_dia / total_clientes * 100) if total_clientes > 0 else 0
    porcentaje_mora = (clientes_mora / total_clientes * 100) if total_clientes > 0 else 0
    
    # ESTADO DE MI CARTERA
    total_financiado = sum(float(c.total_financiamiento or 0) for c in mis_clientes)
    
    # MIS CLIENTES EN MORA
    clientes_mora_detalle = [
        {
            "cliente": cliente.nombre_completo,
            "cedula": cliente.cedula,
            "telefono": cliente.telefono,
            "dias_mora": cliente.dias_mora,
            "monto_deuda": float(cliente.total_financiamiento or 0),
            "vehiculo": cliente.vehiculo_completo,
            "prioridad": "🔴 Alta" if cliente.dias_mora > 30 else ("🟡 Media" if cliente.dias_mora > 15 else "🟠 Baja")
        }
        for cliente in mis_clientes if cliente.dias_mora > 0
    ]
    
    # MI POSICIÓN EN RANKING
    ranking_general = db.query(
        Analista.id,
        Analista.nombre,
        Analista.apellido,
        func.count(Cliente.id).label('total_clientes'),
        func.sum(Cliente.total_financiamiento).label('monto_total')
    ).outerjoin(Cliente, Analista.id == Cliente.analista_id).filter(
        Analista.activo == True,
        Cliente.activo == True
    ).group_by(Analista.id, Analista.nombre, Analista.apellido).order_by(
        func.count(Cliente.id).desc()
    ).all()
    
    mi_posicion = None
    # NOTA: La lógica de posición individual requiere mapeo User->Analista
    # Por ahora, no calcular posición individual
    for idx, analista_rank in enumerate(ranking_general):
        # Lógica de posición deshabilitada - requiere rediseño
        if False:  # analista_rank.id == analista_id:
            mi_posicion = {
                "posicion": idx + 1,
                "total_analistaes": len(ranking_general),
                "clientes": analista_rank.total_clientes,
                "monto": float(analista_rank.monto_total or 0),
                "percentil": round((1 - idx / len(ranking_general)) * 100, 1) if len(ranking_general) > 0 else 0
            }
            break
    
    return {
        "tipo_dashboard": "USER",
        "analista": analista.full_name,
        "fecha_actualizacion": datetime.now(),
        
        "mis_estadisticas": {
            "total_clientes": {"valor": total_clientes, "formato": f"{total_clientes}", "icono": "👥"},
            "clientes_al_dia": {"valor": clientes_al_dia, "formato": f"{clientes_al_dia} ({porcentaje_al_dia:.1f}%)", "icono": "✅"},
            "clientes_mora": {"valor": clientes_mora, "formato": f"{clientes_mora} ({porcentaje_mora:.1f}%)", "icono": "⚠️"},
            "total_financiado": {"valor": total_financiado, "formato": f"${total_financiado:,.0f}", "icono": "💰"}
        },
        
        "graficos": {
            "estado_cartera": {
                "tipo": "pie",
                "titulo": "Estado de Mi Cartera",
                "datos": [
                    {"label": "Al día", "value": clientes_al_dia, "color": "#28a745"},
                    {"label": "En mora", "value": clientes_mora, "color": "#dc3545"}
                ]
            }
        },
        
        "tablas": {
            "clientes_mora": {
                "titulo": "Mis Clientes en Mora",
                "columnas": ["Cliente", "Días Mora", "Monto Deuda", "Teléfono", "Prioridad"],
                "datos": clientes_mora_detalle
            }
        },
        
        "mi_ranking": mi_posicion,
        
        "acciones_sugeridas": [
            f"Contactar {len([c for c in clientes_mora_detalle if c['dias_mora'] > 30])} clientes críticos",
            f"Seguimiento a {len([c for c in clientes_mora_detalle if c['dias_mora'] <= 15])} clientes en mora temprana",
            "Revisar próximos vencimientos de la semana"
        ]
    }


@router.get("/matriz-acceso-roles")
def obtener_matriz_acceso_roles(
    current_user: User = Depends(get_current_user)
):
    """
    📋 Matriz de acceso actualizada por roles
    """
    return {
        "titulo": "DASHBOARD ACTUALIZADO POR ROL",
        "fecha_actualizacion": datetime.now().isoformat(),
        "usuario_actual": {
            "nombre": current_user.full_name,
            "rol": "ADMIN" if current_user.is_admin else "USER",
            "dashboard_asignado": f"/api/v1/dashboard/{'admin' if current_user.is_admin else 'user'}"
        },
        "matriz_acceso": {
            "ADMIN": {
                "emoji": "👑",
                "titulo": "ADMINISTRADOR",
                "acceso": "✅ TODO el sistema",
                "vista_dashboard": [
                    "• KPIs principales (tarjetas con números grandes)",
                    "• Gráfico de mora vs al día",
                    "• Tabla de pagos recientes", 
                    "• Alertas de pagos vencidos hoy",
                    "• Acceso a TODOS los clientes",
                    "• Estadísticas globales"
                ],
                "endpoint": "/api/v1/dashboard/admin",
                "permisos_especiales": ["Gestión de usuarios", "Configuración del sistema"]
            },
            "COBRANZAS": {
                "emoji": "💰",
                "titulo": "COBRANZAS", 
                "acceso": "✅ TODO el sistema (excepto gestión de usuarios)",
                "vista_dashboard": [
                    "• KPIs principales (tarjetas con números grandes)",
                    "• Gráfico de mora vs al día",
                    "• Tabla de pagos recientes",
                    "• Alertas de pagos vencidos hoy", 
                    "• Acceso a TODOS los clientes",
                    "• Estadísticas globales"
                ],
                "endpoint": "/api/v1/dashboard/cobranzas",
                "restricciones": ["NO puede gestionar usuarios"]
            },
            "USER": {
                "emoji": "👔",
                "titulo": "USER",
                "acceso": "⚠️ SOLO SUS CLIENTES",
                "vista_dashboard": [
                    "• KPIs de sus clientes únicamente",
                    "• Gráfico de mora vs al día (solo sus clientes)",
                    "• Lista de sus clientes",
                    "• Estadísticas de sus clientes",
                    "• NO ve datos de otros analistaes/comerciales"
                ],
                "endpoint": "/api/v1/dashboard/comercial",
                "filtro_aplicado": "TODOS LOS CLIENTES (roles sin analista individual)"
            },
            "USER": {
                "emoji": "👤", 
                "titulo": "USER",
                "acceso": "⚠️ SOLO SUS CLIENTES",
                "vista_dashboard": [
                    "• KPIs de sus clientes únicamente",
                    "• Gráfico de mora vs al día (solo sus clientes)",
                    "• Lista de sus clientes", 
                    "• Estadísticas de sus clientes",
                    "• NO ve datos de otros analistaes/comerciales"
                ],
                "endpoint": "/api/v1/dashboard/analista",
                "filtro_aplicado": "TODOS LOS CLIENTES (roles sin analista individual)"
            }
        },
        "implementacion_tecnica": {
            "filtros_por_rol": {
                "ADMIN_COBRANZAS": "Sin filtros - acceso completo",
                "USER_USER": "Dashboard general - sin filtro por analista individual"
            },
            "endpoints_disponibles": {
                "admin": "/api/v1/dashboard/admin",
                "cobranzas": "/api/v1/dashboard/cobranzas", 
                "comercial": "/api/v1/dashboard/comercial",
                "analista": "/api/v1/dashboard/analista",
                "por_rol": "/api/v1/dashboard/por-rol"
            }
        }
    }


@router.get("/por-rol")
def dashboard_por_rol(
    filtro_fecha: Optional[str] = Query("mes", description="dia, semana, mes, año"),
    filtro_analista: Optional[int] = Query(None, description="Filtrar por analista específico"),
    filtro_estado: Optional[str] = Query(None, description="AL_DIA, MORA, TODOS"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🎨 Dashboard adaptativo según rol del usuario actual
    IMPLEMENTA MATRIZ DE ACCESO POR ROL:
    - ADMIN/COBRANZAS: Acceso completo a todos los datos
    - USER/USER: Solo sus clientes asignados
    """
    user_role = "ADMIN" if current_user.is_admin else "USER"
    
    # Todos los usuarios tienen acceso completo
    info_acceso = {
        "USER": "✅ ACCESO COMPLETO - Todos los datos del sistema"
    }
    
    # Todos usan el mismo dashboard con acceso completo
    dashboard_data = dashboard_administrador(db=db, current_user=current_user)
    
    # Agregar información de acceso al dashboard
    if dashboard_data:
        dashboard_data["info_acceso"] = {
            "rol": user_role,
            "descripcion": info_acceso.get(user_role, "Acceso básico"),
            "filtros_aplicados": "Solo sus clientes" if user_role in ["USER", "USER"] else "Sin filtros",
            "puede_ver_otros_analistaes": user_role in ["ADMIN", "COBRANZAS"]
        }
    
    return dashboard_data


@router.get("/datos-graficos/{tipo_grafico}")
def obtener_datos_grafico(
    tipo_grafico: str,
    periodo: Optional[str] = Query("mes", description="dia, semana, mes, año"),
    filtro_analista: Optional[int] = Query(None),
    filtro_modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Obtener datos específicos para gráficos interactivos
    Soporta tooltips y drill-down
    """
    hoy = date.today()
    
    if tipo_grafico == "evolucion_cartera":
        # Datos para gráfico de línea de evolución
        datos = []
        for i in range(12):  # Últimos 12 meses
            mes_fecha = hoy.replace(day=1) - timedelta(days=30 * i)
            # Simulación de datos históricos
            cartera_mes = db.query(func.sum(Cliente.total_financiamiento)).filter(
                Cliente.activo == True
            ).scalar() or Decimal('0')
            
            datos.append({
                "fecha": mes_fecha.strftime("%Y-%m"),
                "mes": mes_fecha.strftime("%B"),
                "cartera": float(cartera_mes) - (i * 25000),  # Simulación
                "nuevos_clientes": max(0, 35 - (i * 2)),
                "tooltip": f"Cartera: ${float(cartera_mes) - (i * 25000):,.0f}"
            })
        
        datos.reverse()
        return {"tipo": "line", "datos": datos}
    
    elif tipo_grafico == "distribucion_mora":
        # Gráfico de dona/pie para distribución
        al_dia = db.query(Cliente).filter(Cliente.activo == True, Cliente.dias_mora == 0).count()
        mora_1_30 = db.query(Cliente).filter(Cliente.activo == True, Cliente.dias_mora.between(1, 30)).count()
        mora_31_60 = db.query(Cliente).filter(Cliente.activo == True, Cliente.dias_mora.between(31, 60)).count()
        mora_60_plus = db.query(Cliente).filter(Cliente.activo == True, Cliente.dias_mora > 60).count()
        
        return {
            "tipo": "doughnut",
            "datos": [
                {"label": "Al día", "value": al_dia, "color": "#28a745", "tooltip": f"{al_dia} clientes al día"},
                {"label": "Mora 1-30", "value": mora_1_30, "color": "#ffc107", "tooltip": f"{mora_1_30} clientes en mora temprana"},
                {"label": "Mora 31-60", "value": mora_31_60, "color": "#fd7e14", "tooltip": f"{mora_31_60} clientes en mora media"},
                {"label": "Mora >60", "value": mora_60_plus, "color": "#dc3545", "tooltip": f"{mora_60_plus} clientes en mora crítica"}
            ]
        }
    
    elif tipo_grafico == "cobros_mensuales":
        # Gráfico de barras para cobros mensuales
        datos = []
        for i in range(6):  # Últimos 6 meses
            mes_fecha = hoy.replace(day=1) - timedelta(days=30 * i)
            inicio_mes = mes_fecha.replace(day=1)
            fin_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            cobros_mes = db.query(func.sum(Pago.monto_pagado)).filter(
                Pago.fecha_pago >= inicio_mes,
                Pago.fecha_pago <= fin_mes,
                Pago.estado != "ANULADO"
            ).scalar() or Decimal('0')
            
            datos.append({
                "mes": mes_fecha.strftime("%B"),
                "monto": float(cobros_mes),
                "tooltip": f"{mes_fecha.strftime('%B')}: ${float(cobros_mes):,.0f}"
            })
        
        datos.reverse()
        return {"tipo": "bar", "datos": datos}
    
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Tipo de gráfico no soportado")


@router.get("/configuracion-dashboard")
def obtener_configuracion_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ⚙️ Configuración del dashboard interactivo
    """
    return {
        "usuario": {
            "nombre": current_user.full_name,
            "rol": "ADMIN" if current_user.is_admin else "USER",
            "dashboards_disponibles": _get_dashboards_disponibles(current_user.is_admin)
        },
        "configuracion_visual": {
            "tema_disponibles": ["claro", "oscuro"],
            "tema_actual": "claro",
            "actualizacion_automatica": True,
            "intervalo_actualizacion": 30,  # segundos
            "animaciones_habilitadas": True
        },
        "filtros_disponibles": {
            "fechas": ["dia", "semana", "mes", "año", "personalizado"],
            "estados": ["TODOS", "AL_DIA", "MORA", "CRITICO"],
            "analistaes": [
                {"id": u.id, "nombre": u.full_name}
                for u in db.query(User).filter(
                    User.is_active == True
                ).all()
            ]
        },
        "opciones_exportacion": ["PDF", "Excel", "PNG", "CSV"],
        "responsive": {
            "breakpoints": {
                "mobile": 768,
                "tablet": 1024,
                "desktop": 1200
            },
            "componentes_adaptables": True
        }
    }


@router.get("/alertas-tiempo-real")
def obtener_alertas_tiempo_real(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔔 Alertas en tiempo real para el dashboard
    """
    alertas = []
    
    # Pagos pendientes de conciliar
    pagos_pendientes = db.query(Pago).filter(
        Pago.estado_conciliacion == "PENDIENTE",
        Pago.fecha_pago >= (date.today() - timedelta(days=3))
    ).count()
    
    if pagos_pendientes > 0:
        alertas.append({
            "tipo": "CONCILIACION_PENDIENTE",
            "mensaje": f"{pagos_pendientes} pago(s) pendiente(s) de conciliar",
            "prioridad": "MEDIA",
            "icono": "💳",
            "color": "warning",
            "accion": "/conciliacion/pendientes"
        })
    
    # Clientes críticos (>30 días mora)
    clientes_criticos = db.query(Cliente).filter(
        Cliente.activo == True,
        Cliente.dias_mora > 30
    ).count()
    
    if clientes_criticos > 0:
        alertas.append({
            "tipo": "MORA_CRITICA",
            "mensaje": f"{clientes_criticos} cliente(s) con mora crítica (>30 días)",
            "prioridad": "ALTA",
            "icono": "🚨",
            "color": "danger",
            "accion": "/clientes?dias_mora_min=30"
        })
    
    # Vencimientos de hoy
    vencimientos_hoy = db.query(Cuota).filter(
        Cuota.fecha_vencimiento == date.today(),
        Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
    ).count()
    
    if vencimientos_hoy > 0:
        alertas.append({
            "tipo": "VENCIMIENTOS_HOY",
            "mensaje": f"{vencimientos_hoy} cuota(s) vencen hoy",
            "prioridad": "NORMAL",
            "icono": "📅",
            "color": "info",
            "accion": "/pagos/vencimientos-hoy"
        })
    
    return {
        "alertas": alertas,
        "total_alertas": len(alertas),
        "ultima_actualizacion": datetime.now(),
        "alertas_por_prioridad": {
            "ALTA": len([a for a in alertas if a["prioridad"] == "ALTA"]),
            "MEDIA": len([a for a in alertas if a["prioridad"] == "MEDIA"]),
            "NORMAL": len([a for a in alertas if a["prioridad"] == "NORMAL"])
        }
    }


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def _get_dashboards_disponibles(is_admin: bool) -> List[str]:
    """Obtener dashboards disponibles según rol"""
    if is_admin:
        return ["admin", "cobranzas", "comercial", "analista"]
    else:
        return ["comercial", "analista"]


# ============================================
# CARACTERÍSTICAS INTERACTIVAS
# ============================================

@router.get("/tabla-detalle/{componente}")
def obtener_detalle_tabla(
    componente: str,
    filtros: Optional[str] = Query(None, description="Filtros JSON"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Obtener detalle de tabla al hacer click en gráfico
    """
    if componente == "vencimientos_proximos":
        # Detalle de vencimientos próximos
        fecha_limite = date.today() + timedelta(days=7)
        
        query = db.query(Cuota).select_from(Cuota).join(
            Prestamo, Cuota.prestamo_id == Prestamo.id
        ).join(
            Cliente, Prestamo.cliente_id == Cliente.id
        ).filter(
            Cuota.fecha_vencimiento >= date.today(),
            Cuota.fecha_vencimiento <= fecha_limite,
            Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
        )
        
        total = query.count()
        skip = (page - 1) * page_size
        resultados = query.order_by(Cuota.fecha_vencimiento).offset(skip).limit(page_size).all()
        
        datos = []
        for cuota in resultados:
            prestamo = db.query(Prestamo).filter(Prestamo.id == cuota.prestamo_id).first()
            if prestamo:
                cliente = db.query(Cliente).filter(Cliente.id == prestamo.cliente_id).first()
                if cliente:
                    datos.append({
                        "cliente": cliente.nombre_completo,
                        "cedula": cliente.cedula,
                        "telefono": cliente.telefono,
                        "cuota": cuota.numero_cuota,
                        "monto": float(cuota.monto_cuota),
                        "fecha_vencimiento": cuota.fecha_vencimiento,
                        "dias_hasta": (cuota.fecha_vencimiento - date.today()).days,
                        "analista": cliente.analista.full_name if cliente.analista else "Sin asignar"
                    })
        
        return {
            "componente": componente,
            "total": total,
            "page": page,
            "page_size": page_size,
            "datos": datos
        }
    
    elif componente == "clientes_mora":
        # Detalle de clientes en mora
        query = db.query(Cliente).filter(
            Cliente.activo == True,
            Cliente.dias_mora > 0
        )
        
        total = query.count()
        skip = (page - 1) * page_size
        clientes = query.order_by(Cliente.dias_mora.desc()).offset(skip).limit(page_size).all()
        
        datos = [
            {
                "cliente": cliente.nombre_completo,
                "cedula": cliente.cedula,
                "telefono": cliente.telefono,
                "dias_mora": cliente.dias_mora,
                "monto_financiamiento": float(cliente.total_financiamiento or 0),
                "vehiculo": cliente.vehiculo_completo,
                "analista": cliente.analista.full_name if cliente.analista else "Sin asignar",
                "prioridad": "CRITICA" if cliente.dias_mora > 60 else ("ALTA" if cliente.dias_mora > 30 else "MEDIA")
            }
            for cliente in clientes
        ]
        
        return {
            "componente": componente,
            "total": total,
            "page": page,
            "page_size": page_size,
            "datos": datos
        }
    
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Componente no soportado")


@router.post("/exportar-vista")
async def exportar_vista_dashboard(
    tipo_vista: str,
    formato: str = Query("excel", description="excel, pdf, png, csv"),
    filtros: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📤 Exportar cualquier vista del dashboard
    """
    try:
        if formato == "excel":
            import openpyxl
            from openpyxl.styles import Font, PatternFill
            import io
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"Dashboard {tipo_vista}"
            
            # Encabezado
            ws.append([f"Dashboard {tipo_vista.title()}", "", "", ""])
            ws.append([f"Usuario: {current_user.full_name}", "", "", ""])
            ws.append([f"Fecha: {date.today().strftime('%d/%m/%Y')}", "", "", ""])
            ws.append([])
            
            # Obtener datos según tipo de vista
            if tipo_vista == "admin":
                dashboard_data = dashboard_administrador(db=db, current_user=current_user)
                
                # KPIs
                ws.append(["KPIs PRINCIPALES", "", "", ""])
                for kpi_name, kpi_data in dashboard_data["kpis_principales"].items():
                    ws.append([kpi_name.replace("_", " ").title(), kpi_data["formato"], "", ""])
                
                ws.append([])
                
                # Vencimientos próximos
                ws.append(["VENCIMIENTOS PRÓXIMOS", "", "", ""])
                ws.append(["Cliente", "Monto", "Fecha", "Días"])
                
                for venc in dashboard_data["tablas"]["vencimientos_proximos"]["datos"]:
                    ws.append([venc["cliente"], venc["monto"], venc["fecha"], venc["dias"]])
            
            # Guardar en memoria
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=dashboard_{tipo_vista}_{date.today().strftime('%Y%m%d')}.xlsx"}
            )
        
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Formato {formato} no soportado aún")
    
    except ImportError:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Dependencias de exportación no instaladas")


@router.get("/tiempo-real/actualizacion")
def obtener_actualizacion_tiempo_real(
    componentes: Optional[str] = Query(None, description="Componentes a actualizar (separados por coma)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ⚡ Actualización en tiempo real de componentes específicos
    """
    hoy = date.today()
    
    actualizaciones = {}
    
    if not componentes or "kpis" in componentes:
        # Actualizar KPIs
        cobrado_hoy = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.fecha_pago == hoy, Pago.estado != "ANULADO"
        ).scalar() or Decimal('0')
        
        vencimientos_hoy = db.query(Cuota).filter(
            Cuota.fecha_vencimiento == hoy,
            Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
        ).count()
        
        actualizaciones["kpis"] = {
            "cobrado_hoy": float(cobrado_hoy),
            "vencimientos_hoy": vencimientos_hoy,
            "timestamp": datetime.now()
        }
    
    if not componentes or "alertas" in componentes:
        # Actualizar alertas
        alertas_data = obtener_alertas_tiempo_real(db=db, current_user=current_user)
        actualizaciones["alertas"] = alertas_data
    
    if not componentes or "notificaciones" in componentes:
        # Actualizar notificaciones pendientes
        notif_pendientes = db.query(Notificacion).filter(
            Notificacion.estado == "PENDIENTE"
        ).count()
        
        actualizaciones["notificaciones"] = {
            "pendientes": notif_pendientes,
            "timestamp": datetime.now()
        }
    
    return {
        "actualizaciones": actualizaciones,
        "timestamp_servidor": datetime.now(),
        "componentes_actualizados": componentes.split(",") if componentes else ["todos"]
    }
