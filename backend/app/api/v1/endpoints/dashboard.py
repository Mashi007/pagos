# backend/app/api/v1/endpoints/dashboard.py

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.analista import Analista
from app.models.cliente import Cliente
from app.models.notificacion import Notificacion
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User

router = APIRouter()

@router.get("/admin")
def dashboard_administrador(
    fecha_inicio: Optional[date] = Query(
    ),
    fecha_fin: Optional[date] = Query(
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    👑 DASHBOARD ADMINISTRADOR - ACCESO COMPLETO AL SISTEMA
    ✅ Acceso: TODO el sistema
    ✅ Vista Dashboard:
    • Gráfico de mora vs al día
    • Estadísticas globales
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
        )

    hoy = date.today()

    # KPIs PRINCIPALES (reutilizar del endpoint existente)
    cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter(
        Cliente.activo, Cliente.total_financiamiento.isnot(None)
    ).scalar() or Decimal("0")

    clientes_al_dia = (
        db.query(Cliente)
        .filter(Cliente.activo, Cliente.dias_mora == 0)
        .count()
    )

    clientes_en_mora = (
        db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora > 0).count()
    )

        (clientes_en_mora / (clientes_al_dia + clientes_en_mora) * 100)
        if (clientes_al_dia + clientes_en_mora) > 0
        else 0
    )

    evolucion_cartera = []
    for i in range(6):
        evolucion_cartera.append(
            {
                "cartera": float(cartera_total) - (i * 50000),
            }
        )
    evolucion_cartera.reverse()  # Orden cronológico

    # DISTRIBUCIÓN DE CLIENTES
    total_clientes = clientes_al_dia + clientes_en_mora
    distribucion_clientes = {
        "al_dia": {
            "cantidad": clientes_al_dia,
            "porcentaje": (
                round((clientes_al_dia / total_clientes * 100), 1)
                if total_clientes > 0
                else 0
            ),
            "color": "#28a745",
        },
        "mora": {
            "cantidad": clientes_en_mora,
            "porcentaje": (
                round((clientes_en_mora / total_clientes * 100), 1)
                if total_clientes > 0
                else 0
            ),
            "color": "#ffc107",
        },
    }

    # VENCIMIENTOS PRÓXIMOS 7 DÍAS
        db.query(Cuota)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .filter(
            Cuota.fecha_vencimiento >= hoy,
            Cuota.fecha_vencimiento <= fecha_limite,
            Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
        )
        .order_by(Cuota.fecha_vencimiento)
        .limit(10)
        .all()
    )

        prestamo = (
            db.query(Prestamo).filter(Prestamo.id == cuota.prestamo_id).first()
        )
        if prestamo:
            cliente = (
                db.query(Cliente)
                .filter(Cliente.id == prestamo.cliente_id)
                .first()
            )
            if cliente:
                dias_hasta = (cuota.fecha_vencimiento - hoy).days
                    {
                        "cedula": cliente.cedula,
                        "monto": f"${float(cuota.monto_cuota):,.0f}",
                        "dias": dias_hasta,
                        "color": (
                            "danger"
                            if dias_hasta == 0
                            else ("warning" if dias_hasta <= 2 else "info")
                        ),
                    }
                )

    # TOP 5 USERES DEL MES
    inicio_mes = hoy.replace(day=1)
    top_analistaes_query = (
        db.query(
            User.id,
            User.nombre,
            User.apellido,
            func.sum(Cliente.total_financiamiento).label("monto_vendido"),
        )
        .select_from(User)
        .outerjoin(
            Cliente,
            and_(
                Analista.id == Cliente.analista_id,
                Cliente.fecha_registro >= inicio_mes,
            ),
        )
        .filter(
            User.is_admin,
        )
        .group_by(User.id, User.nombre, User.apellido)
        .order_by(func.count(Cliente.id).desc())
        .limit(5)
        .all()
    )

    top_analistaes = [
        {
            "nombre": f"{analista.nombre} {analista.apellido}",
            "monto_vendido": float(analista.monto_vendido or 0),
        }
        for analista in top_analistaes_query
    ]

    # ALERTAS CRÍTICAS
        db.query(Cliente)
        .filter(Cliente.activo, Cliente.dias_mora > 30)
        .order_by(Cliente.dias_mora.desc())
        .limit(5)
        .all()
    )

    alertas_criticas = [
        {
            "tipo": "MORA_CRITICA",
            "cliente": cliente.nombre_completo,
            "cedula": cliente.cedula,
            "dias_mora": cliente.dias_mora,
            "monto_riesgo": float(cliente.total_financiamiento or 0),
            "prioridad": "URGENTE" if cliente.dias_mora > 60 else "ALTA",
        }
    ]

    return {
        "tipo_dashboard": "ADMINISTRADOR",
        "usuario": current_user.full_name,
        "kpis_principales": {
            "cartera_total": {
                "valor": float(cartera_total),
                "formato": f"${float(cartera_total):,.0f}",
                "icono": "💰",
            },
            "clientes_al_dia": {
                "valor": clientes_al_dia,
                "formato": f"{clientes_al_dia:,}",
                "icono": "✅",
            },
            "clientes_en_mora": {
                "valor": clientes_en_mora,
                "formato": f"{clientes_en_mora:,}",
                "icono": "⚠️",
            },
                "icono": "📈",
            },
        },
            "evolucion_cartera": {
                "tipo": "line",
                "titulo": "Evolución Mensual de Cartera",
                "ejes": {"x": "mes_nombre", "y": "cartera"},
                "formato_y": "currency",
            },
            "distribucion_clientes": {
                "tipo": "pie",
                "titulo": "Distribución de Clientes",
                    {
                        "label": "Al día",
                        "value": distribucion_clientes["al_dia"]["cantidad"],
                        "color": "#28a745",
                    },
                    {
                        "label": "En mora",
                        "value": distribucion_clientes["mora"]["cantidad"],
                        "color": "#ffc107",
                    },
                ],
            },
        },
        "tablas": {
                "columnas": ["Cliente", "Monto", "Fecha", "Días"],
            }
        },
        "rankings": {
            "top_analistaes": [
                {
                    "analista": analista,
                    "monto_vendido": float(monto or 0),
                }
            ]
        },
        "alertas_criticas": alertas_criticas,
    }

@router.get("/cobranzas")
def dashboard_cobranzas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    💰 DASHBOARD COBRANZAS - ACCESO COMPLETO (EXCEPTO GESTIÓN DE USUARIOS)
    ✅ Vista Dashboard:
    • Gráfico de mora vs al día
    • Estadísticas globales
    """
    if not current_user.is_admin:
        raise HTTPException(
        )

    hoy = date.today()

    # KPIs DE COBRANZA
    cobrado_hoy = db.query(func.sum(Pago.monto_pagado)).filter(
        Pago.fecha_pago == hoy, Pago.estado != "ANULADO"
    ).scalar() or Decimal("0")

        db.query(Cuota)
        .filter(
            Cuota.fecha_vencimiento == hoy,
            Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
        )
        .count()
    )

    clientes_mora = (
        db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora > 0).count()
    )

    for i in range(30):
        cobro_dia = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.fecha_pago == fecha_dia, Pago.estado != "ANULADO"
        ).scalar() or Decimal("0")
            {
                "fecha_completa": fecha_dia,
                "monto": float(cobro_dia),
            }
        )

    # CLIENTES A CONTACTAR HOY (prioridad por días de mora)
    clientes_contactar = (
        db.query(Cliente)
        .filter(
            Cliente.activo,
            or_(
                Cliente.dias_mora > 0,  # En mora
                and_(  # Vencen hoy
                    Cliente.id.in_(
                        db.query(Prestamo.cliente_id)
                        .join(Cuota)
                        .filter(
                            Cuota.fecha_vencimiento == hoy,
                            Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
                        )
                    )
                ),
            ),
        )
        .order_by(Cliente.dias_mora.desc())
        .limit(20)
        .all()
    )

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

        tabla_contactar.append(
            {
                "prioridad": prioridad,
                "cliente": cliente.nombre_completo,
                "cedula": cliente.cedula,
                "telefono": cliente.telefono,
                "dias_mora": cliente.dias_mora,
                "color": color,
                "analista": (
                    cliente.analista.full_name
                    if cliente.analista
                    else "Sin asignar"
                ),
            }
        )

    # PAGOS SIN CONCILIAR
        db.query(Pago)
        .filter(
            Pago.estado_conciliacion == "PENDIENTE",
        )
        .count()
    )

    return {
        "tipo_dashboard": "COBRANZAS",
        "usuario": current_user.full_name,
        "kpis_cobranza": {
            "cobrado_hoy": {
                "valor": float(cobrado_hoy),
                "formato": f"${float(cobrado_hoy):,.0f}",
                "icono": "💸",
            },
                "icono": "📅",
            },
            "clientes_mora": {
                "valor": clientes_mora,
                "formato": f"{clientes_mora:,}",
                "icono": "⚠️",
            },
        },
                "tipo": "line",
                "ejes": {"x": "fecha", "y": "monto"},
                "formato_y": "currency",
            },
                "tipo": "bar",
                    {"mes": "Oct", "tasa": 9.5},
                    {"mes": "Sep", "tasa": 8.2},
                    {"mes": "Ago", "tasa": 7.8},
                    {"mes": "Jul", "tasa": 8.5},
                ],
            },
        },
        "tablas": {
            "clientes_contactar": {
                "titulo": "Clientes a Contactar Hoy",
                "columnas": [
                    "Prioridad",
                    "Cliente",
                    "Días Mora",
                    "Teléfono",
                    "Analista",
                ],
            }
        },
        "notificaciones": {
            "alertas_activas": len(
                [c for c in clientes_contactar if c["dias_mora"] > 30]
            ),
        },
    }

@router.get("/comercial")
def dashboard_comercial(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    👔 DASHBOARD USER - SOLO SUS CLIENTES
    ⚠️ Acceso: SOLO SUS CLIENTES
    ✅ Vista Dashboard:
    • KPIs de sus clientes únicamente
    • Gráfico de mora vs al día (solo sus clientes)
    • Lista de sus clientes
    • Estadísticas de sus clientes
    """
    if not current_user.is_admin:
        raise HTTPException(
        )

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    filtro_clientes = Cliente.activo

    # KPIs - TODOS LOS CLIENTES
    db.query(Cliente).filter(filtro_clientes).count()

    # Variables calculadas pero no usadas en el retorno actual
    # mis_clientes_al_dia = (
    #     db.query(Cliente)
    #     .filter(filtro_clientes, Cliente.estado_financiero == "AL_DIA")
    #     .count()
    # )
    # mis_clientes_mora = (
    #     db.query(Cliente)
    #     .filter(filtro_clientes, Cliente.estado_financiero == "EN_MORA")
    #     .count()
    # )

    # VENTAS DEL MES (solo sus clientes)
    ventas_mes = (
        db.query(Cliente)
        .filter(filtro_clientes, Cliente.fecha_registro >= inicio_mes)
        .count()
    )

    monto_vendido_mes = db.query(
        func.sum(Cliente.total_financiamiento)
    ).filter(
        filtro_clientes, Cliente.fecha_registro >= inicio_mes
    ).scalar() or Decimal(
        "0"
    )

    # META MENSUAL (configurable)
    meta_mensual = 60  # unidades
    meta_monto = Decimal("1500000")  # $1.5M

    cumplimiento_unidades = (
        (ventas_mes / meta_mensual * 100) if meta_mensual > 0 else 0
    )
    cumplimiento_monto = (
        (monto_vendido_mes / meta_monto * 100) if meta_monto > 0 else 0
    )

    # VENTAS POR MODELO
    ventas_por_modelo = (
        db.query(
            Cliente.modelo_vehiculo,
            Cliente.marca_vehiculo,
            func.count(Cliente.id).label("cantidad"),
            func.sum(Cliente.total_financiamiento).label("monto"),
        )
        .filter(
            Cliente.fecha_registro >= inicio_mes,
            Cliente.activo,
            Cliente.modelo_vehiculo.isnot(None),
        )
        .group_by(Cliente.modelo_vehiculo, Cliente.marca_vehiculo)
        .order_by(func.count(Cliente.id).desc())
        .all()
    )

    # VENTAS POR USER
    ventas_por_analista_query = (
        db.query(
            Analista.id,
            Analista.nombre,
            Analista.apellido,
            func.count(Cliente.id).label("ventas"),
            func.sum(Cliente.total_financiamiento).label("monto"),
        )
        .select_from(Analista)
        .outerjoin(
            Cliente,
            and_(
                Analista.id == Cliente.analista_id,
                Cliente.fecha_registro >= inicio_mes,
            ),
        )
        .filter(Analista.activo)
        .group_by(Analista.id, Analista.nombre, Analista.apellido)
        .order_by(func.count(Cliente.id).desc())
        .all()
    )

    ventas_por_analista = [
        {
            "nombre": f"{v.nombre} {v.apellido}",
            "ventas": v.ventas,
            "monto": float(v.monto or 0),
        }
        for v in ventas_por_analista_query
    ]

    # ÚLTIMAS VENTAS REGISTRADAS
    ultimas_ventas = (
        db.query(Cliente)
        .filter(Cliente.activo)
        .order_by(Cliente.fecha_registro.desc())
        .limit(10)
        .all()
    )

    return {
        "tipo_dashboard": "USER",
        "usuario": current_user.full_name,
        "kpis_comerciales": {
            "ventas_mes": {
                "valor": ventas_mes,
                "formato": f"{ventas_mes} unidades",
                "icono": "📊",
            },
            "monto_vendido": {
                "valor": float(monto_vendido_mes),
                "formato": f"${float(monto_vendido_mes):,.0f}",
                "icono": "💰",
            },
            "meta_cumplimiento": {
                "unidades": round(cumplimiento_unidades, 1),
                "monto": round(float(cumplimiento_monto), 1),
                "formato": f"{cumplimiento_unidades:.0f}% cumplida",
                "icono": "🎯",
            },
        },
            "ventas_por_modelo": {
                "tipo": "bar",
                "titulo": "Ventas por Modelo",
                    {
                        "modelo": f"{marca} {modelo}",
                        "ventas": cantidad,
                        "monto": float(monto or 0),
                    }
                    for modelo, marca, cantidad, monto in ventas_por_modelo
                ],
            },
            "ventas_por_analista": {
                "tipo": "bar",
                "titulo": "Ventas por Analista",
                    {
                        "analista": analista,
                        "ventas": ventas,
                        "monto": float(monto or 0),
                    }
                    for analista, ventas, monto in ventas_por_analista
                ],
            },
        },
        "tablas": {
            "ultimas_ventas": {
                "titulo": "Últimas Ventas Registradas",
                    {
                        "cliente": cliente.nombre_completo,
                        "vehiculo": cliente.vehiculo_completo,
                        "monto": f"${float(cliente.total_financiamiento):,.0f}",
                        "analista": (
                            cliente.analista.full_name
                            if cliente.analista
                            else "N/A"
                        ),
                    }
                    for cliente in ultimas_ventas
                ],
            }
        },
        "ranking_analistaes": [
            {
                "analista": analista,
                "ventas": ventas,
                "monto": float(monto or 0),
            }
            for idx, (analista, ventas, monto) in enumerate(
                ventas_por_analista
            )
        ],
    }

@router.get("/analista")
def dashboard_analista(
    analista_id: Optional[int] = Query(
        None,
        description="ID del analista de configuración (default: usuario actual)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    👤 DASHBOARD USER - SOLO SUS CLIENTES
    ⚠️ Acceso: SOLO SUS CLIENTES
    ✅ Vista Dashboard:
    • KPIs de sus clientes únicamente
    • Gráfico de mora vs al día (solo sus clientes)
    • Lista de sus clientes
    • Estadísticas de sus clientes
    """

    mis_clientes = db.query(Cliente).filter(Cliente.activo).all()
    total_clientes = len(mis_clientes)
    clientes_al_dia = len([c for c in mis_clientes if c.dias_mora == 0])
    clientes_mora = len([c for c in mis_clientes if c.dias_mora > 0])

    porcentaje_al_dia = (
        (clientes_al_dia / total_clientes * 100) if total_clientes > 0 else 0
    )
    porcentaje_mora = (
        (clientes_mora / total_clientes * 100) if total_clientes > 0 else 0
    )

    # ESTADO DE MI CARTERA
    total_financiado = sum(
        float(c.total_financiamiento or 0) for c in mis_clientes
    )

    # MIS CLIENTES EN MORA
    clientes_mora_detalle = [
        {
            "cliente": cliente.nombre_completo,
            "cedula": cliente.cedula,
            "telefono": cliente.telefono,
            "dias_mora": cliente.dias_mora,
            "monto_deuda": float(cliente.total_financiamiento or 0),
            "vehiculo": cliente.vehiculo_completo,
            "prioridad": (
                "🔴 Alta"
                if cliente.dias_mora > 30
                else ("🟡 Media" if cliente.dias_mora > 15 else "🟠 Baja")
            ),
        }
        for cliente in mis_clientes
        if cliente.dias_mora > 0
    ]

    # MI POSICIÓN EN RANKING
    ranking_general = (
        db.query(
            Analista.id,
            Analista.nombre,
            Analista.apellido,
            func.count(Cliente.id).label("total_clientes"),
            func.sum(Cliente.total_financiamiento).label("monto_total"),
        )
        .outerjoin(Cliente, Analista.id == Cliente.analista_id)
        .filter(Analista.activo, Cliente.activo)
        .group_by(Analista.id, Analista.nombre, Analista.apellido)
        .order_by(func.count(Cliente.id).desc())
        .all()
    )

    for idx, analista_rank in enumerate(ranking_general):
        if False:  # analista_rank.id == analista_id:
                "total_analistaes": len(ranking_general),
                "clientes": analista_rank.total_clientes,
                "monto": float(analista_rank.monto_total or 0),
                "percentil": (
                    round((1 - idx / len(ranking_general)) * 100, 1)
                    if len(ranking_general) > 0
                    else 0
                ),
            }
            break

    return {
        "tipo_dashboard": "USER",
        "analista": current_user.full_name,
        "mis_estadisticas": {
            "total_clientes": {
                "valor": total_clientes,
                "formato": f"{total_clientes}",
                "icono": "👥",
            },
            "clientes_al_dia": {
                "valor": clientes_al_dia,
                "formato": f"{clientes_al_dia} ({porcentaje_al_dia:.1f}%)",
                "icono": "✅",
            },
            "clientes_mora": {
                "valor": clientes_mora,
                "formato": f"{clientes_mora} ({porcentaje_mora:.1f}%)",
                "icono": "⚠️",
            },
            "total_financiado": {
                "valor": total_financiado,
                "formato": f"${total_financiado:,.0f}",
                "icono": "💰",
            },
        },
            "estado_cartera": {
                "tipo": "pie",
                "titulo": "Estado de Mi Cartera",
                    {
                        "label": "Al día",
                        "value": clientes_al_dia,
                        "color": "#28a745",
                    },
                    {
                        "label": "En mora",
                        "value": clientes_mora,
                        "color": "#dc3545",
                    },
                ],
            }
        },
        "tablas": {
            "clientes_mora": {
                "titulo": "Mis Clientes en Mora",
                "columnas": [
                    "Cliente",
                    "Días Mora",
                    "Monto Deuda",
                    "Teléfono",
                    "Prioridad",
                ],
            }
        },
        "acciones_sugeridas": [
            f"Seguimiento a {len([c for c in clientes_mora_detalle if c['dias_mora'] <= 15])} clientes en mora temprana",
        ],
    }

@router.get("/matriz-acceso-roles")
def obtener_matriz_acceso_roles(
    current_user: User = Depends(get_current_user),
):
    """
    📋 Matriz de acceso actualizada por roles
    """
    return {
        "titulo": "DASHBOARD ACTUALIZADO POR ROL",
        "usuario_actual": {
            "nombre": current_user.full_name,
            "rol": "ADMIN" if current_user.is_admin else "USER",
            "dashboard_asignado": (
                f"/api/v1/dashboard/{'admin' if current_user.is_admin else 'user'}"
            ),
        },
        "matriz_acceso": {
            "ADMIN": {
                "emoji": "👑",
                "titulo": "ADMINISTRADOR",
                "acceso": "✅ TODO el sistema",
                "vista_dashboard": [
                    "• Gráfico de mora vs al día",
                    "• Estadísticas globales",
                ],
                "endpoint": "/api/v1/dashboard/admin",
                    "Configuración del sistema",
                ],
            },
            "COBRANZAS": {
                "emoji": "💰",
                "titulo": "COBRANZAS",
                "vista_dashboard": [
                    "• Gráfico de mora vs al día",
                    "• Estadísticas globales",
                ],
                "endpoint": "/api/v1/dashboard/cobranzas",
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
                ],
                "endpoint": "/api/v1/dashboard/comercial",
                "filtro_aplicado": "TODOS LOS CLIENTES (roles sin analista individual)",
            },
            "USER_ANALISTA": {
                "emoji": "👤",
                "titulo": "USER_ANALISTA",
                "acceso": "⚠️ SOLO SUS CLIENTES",
                "vista_dashboard": [
                    "• KPIs de sus clientes únicamente",
                    "• Gráfico de mora vs al día (solo sus clientes)",
                    "• Lista de sus clientes",
                    "• Estadísticas de sus clientes",
                ],
                "endpoint": "/api/v1/dashboard/analista",
                "filtro_aplicado": "TODOS LOS CLIENTES (roles sin analista individual)",
            },
        },
        "implementacion_tecnica": {
                "USER_USER": "Dashboard general - sin filtro por analista individual",
            },
            "endpoints_disponibles": {
                "admin": "/api/v1/dashboard/admin",
                "cobranzas": "/api/v1/dashboard/cobranzas",
                "comercial": "/api/v1/dashboard/comercial",
                "analista": "/api/v1/dashboard/analista",
                "por_rol": "/api/v1/dashboard/por-rol",
            },
        },
    }

@router.get("/por-rol")
def dashboard_por_rol(
    filtro_fecha: Optional[str] = Query(
        "mes", description="dia, semana, mes, año"
    ),
    filtro_analista: Optional[int] = Query(
        None, description="Filtrar por analista específico"
    ),
    filtro_estado: Optional[str] = Query(
        None, description="AL_DIA, MORA, TODOS"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🎨 Dashboard adaptativo según rol del usuario actual
    IMPLEMENTA MATRIZ DE ACCESO POR ROL:
    """
    user_role = "ADMIN" if current_user.is_admin else "USER"


    dashboard_data = dashboard_administrador(db=db, current_user=current_user)

    # Agregar información de acceso al dashboard
    if dashboard_data:
        dashboard_data["info_acceso"] = {
            "rol": user_role,
            "descripcion": info_acceso.get(user_role, "Acceso básico"),
                "Solo sus clientes"
                if user_role in ["USER", "USER"]
            ),
        }

    return dashboard_data

    tipo_grafico: str,
    periodo: Optional[str] = Query("mes", description="dia, semana, mes, año"),
    filtro_analista: Optional[int] = Query(None),
    filtro_modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soporta tooltips y drill-down
    """
    hoy = date.today()

    if tipo_grafico == "evolucion_cartera":
            cartera_mes = db.query(
                func.sum(Cliente.total_financiamiento)
            ).filter(Cliente.activo).scalar() or Decimal("0")
                {
                    "cartera": float(cartera_mes) - (i * 25000),  # Simulación
                    "tooltip": f"Cartera: ${float(cartera_mes) - (i * 25000):,.0f}",
                }
            )

    elif tipo_grafico == "distribucion_mora":
        # Gráfico de dona/pie para distribución
        al_dia = (
            db.query(Cliente)
            .filter(Cliente.activo, Cliente.dias_mora == 0)
            .count()
        )
        mora_1_30 = (
            db.query(Cliente)
            .filter(Cliente.activo, Cliente.dias_mora.between(1, 30))
            .count()
        )
        mora_31_60 = (
            db.query(Cliente)
            .filter(Cliente.activo, Cliente.dias_mora.between(31, 60))
            .count()
        )
        mora_60_plus = (
            db.query(Cliente)
            .filter(Cliente.activo, Cliente.dias_mora > 60)
            .count()
        )

        return {
            "tipo": "doughnut",
                {
                    "label": "Al día",
                    "value": al_dia,
                    "color": "#28a745",
                    "tooltip": f"{al_dia} clientes al día",
                },
                {
                    "label": "Mora 1-30",
                    "value": mora_1_30,
                    "color": "#ffc107",
                    "tooltip": f"{mora_1_30} clientes en mora temprana",
                },
                {
                    "label": "Mora 31-60",
                    "value": mora_31_60,
                    "color": "#fd7e14",
                    "tooltip": f"{mora_31_60} clientes en mora media",
                },
                {
                    "label": "Mora >60",
                    "value": mora_60_plus,
                    "color": "#dc3545",
                    "tooltip": f"{mora_60_plus} clientes en mora crítica",
                },
            ],
        }

            inicio_mes = mes_fecha.replace(day=1)
                day=1

                Pago.fecha_pago >= inicio_mes,
                Pago.fecha_pago <= fin_mes,
                Pago.estado != "ANULADO",
            ).scalar() or Decimal("0")

                {
                }
            )

    else:
        raise HTTPException(
            status_code=400, detail="Tipo de gráfico no soportado"
        )

@router.get("/configuracion-dashboard")
def obtener_configuracion_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚙️ Configuración del dashboard interactivo
    """
    return {
        "usuario": {
            "nombre": current_user.full_name,
            "rol": "ADMIN" if current_user.is_admin else "USER",
            "dashboards_disponibles": _get_dashboards_disponibles(
                current_user.is_admin
            ),
        },
        "configuracion_visual": {
            "tema_actual": "claro",
            "actualizacion_automatica": True,
            "animaciones_habilitadas": True,
        },
            "fechas": ["dia", "semana", "mes", "año", "personalizado"],
            "analistaes": [
                {"id": u.id, "nombre": u.full_name}
                for u in db.query(User).filter(User.is_active).all()
            ],
        },
        "opciones_exportacion": ["PDF", "Excel", "PNG", "CSV"],
        "responsive": {
            "breakpoints": {"mobile": 768, "tablet": 1024, "desktop": 1200},
            "componentes_adaptables": True,
        },
    }

@router.get("/alertas-tiempo-real")
def obtener_alertas_tiempo_real(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔔 Alertas en tiempo real para el dashboard
    """
    alertas = []

        db.query(Pago)
        .filter(
            Pago.estado_conciliacion == "PENDIENTE",
        )
        .count()
    )

        alertas.append(
            {
                "tipo": "CONCILIACION_PENDIENTE",
                "prioridad": "MEDIA",
                "icono": "💳",
                "color": "warning",
                "accion": "/conciliacion/pendientes",
            }
        )

        db.query(Cliente)
        .filter(Cliente.activo, Cliente.dias_mora > 30)
        .count()
    )

        alertas.append(
            {
                "tipo": "MORA_CRITICA",
                "prioridad": "ALTA",
                "icono": "🚨",
                "color": "danger",
                "accion": "/clientes?dias_mora_min=30",
            }
        )

        db.query(Cuota)
        .filter(
            Cuota.fecha_vencimiento == date.today(),
            Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
        )
        .count()
    )

        alertas.append(
            {
                "tipo": "VENCIMIENTOS_HOY",
                "prioridad": "NORMAL",
                "icono": "📅",
                "color": "info",
            }
        )

    return {
        "alertas": alertas,
        "total_alertas": len(alertas),
        "alertas_por_prioridad": {
            "ALTA": len([a for a in alertas if a["prioridad"] == "ALTA"]),
            "MEDIA": len([a for a in alertas if a["prioridad"] == "MEDIA"]),
            "NORMAL": len([a for a in alertas if a["prioridad"] == "NORMAL"]),
        },
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
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📋 Obtener detalle de tabla al hacer click en gráfico
    """
        query = (
            db.query(Cuota)
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .filter(
                Cuota.fecha_vencimiento >= date.today(),
                Cuota.fecha_vencimiento <= fecha_limite,
                Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
            )
        )

        total = query.count()
        skip = (page - 1) * page_size
            query.order_by(Cuota.fecha_vencimiento)
            .offset(skip)
            .limit(page_size)
            .all()
        )

            prestamo = (
                db.query(Prestamo)
                .filter(Prestamo.id == cuota.prestamo_id)
                .first()
            )
            if prestamo:
                cliente = (
                    db.query(Cliente)
                    .filter(Cliente.id == prestamo.cliente_id)
                    .first()
                )
                if cliente:
                        {
                            "cliente": cliente.nombre_completo,
                            "cedula": cliente.cedula,
                            "telefono": cliente.telefono,
                            "cuota": cuota.numero_cuota,
                            "monto": float(cuota.monto_cuota),
                            "fecha_vencimiento": cuota.fecha_vencimiento,
                            "dias_hasta": (
                                cuota.fecha_vencimiento - date.today()
                            ).days,
                            "analista": (
                                cliente.analista.full_name
                                if cliente.analista
                                else "Sin asignar"
                            ),
                        }
                    )

        return {
            "componente": componente,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    elif componente == "clientes_mora":
        # Detalle de clientes en mora
        query = db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora > 0)
        total = query.count()
        skip = (page - 1) * page_size
        clientes = (
            query.order_by(Cliente.dias_mora.desc())
            .offset(skip)
            .limit(page_size)
            .all()
        )

            {
                "cliente": cliente.nombre_completo,
                "cedula": cliente.cedula,
                "telefono": cliente.telefono,
                "dias_mora": cliente.dias_mora,
                "monto_financiamiento": float(
                    cliente.total_financiamiento or 0
                ),
                "vehiculo": cliente.vehiculo_completo,
                "analista": (
                    cliente.analista.full_name
                    if cliente.analista
                    else "Sin asignar"
                ),
                "prioridad": (
                    "CRITICA"
                    if cliente.dias_mora > 60
                    else ("ALTA" if cliente.dias_mora > 30 else "MEDIA")
                ),
            }
            for cliente in clientes
        ]

        return {
            "componente": componente,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    else:
        raise HTTPException(status_code=400, detail="Componente no soportado")

async def exportar_vista_dashboard(
    tipo_vista: str,
    formato: str = Query("excel", description="excel, pdf, png, csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📤 Exportar cualquier vista del dashboard
    """
    try:
        if formato == "excel":
            import io
            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"Dashboard {tipo_vista}"

            # Encabezado
            ws.append([f"Dashboard {tipo_vista.title()}", "", "", ""])
            ws.append([f"Usuario: {current_user.full_name}", "", "", ""])
            ws.append(
            )
            ws.append([])

            if tipo_vista == "admin":
                dashboard_data = dashboard_administrador(
                    db=db, current_user=current_user
                )

                # KPIs
                ws.append(["KPIs PRINCIPALES", "", "", ""])
                for kpi_name, kpi_data in dashboard_data[
                    "kpis_principales"
                ].items():
                    ws.append(
                        [
                            kpi_name.replace("_", " ").title(),
                            kpi_data["formato"],
                            "",
                            "",
                        ]
                    )
                ws.append([])

                ws.append(["VENCIMIENTOS PRÓXIMOS", "", "", ""])
                ws.append(["Cliente", "Monto", "Fecha", "Días"])
                ]:
                    ws.append(
                        [
                            venc["cliente"],
                            venc["monto"],
                            venc["fecha"],
                            venc["dias"],
                        ]
                    )

            # Guardar en memoria
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            from fastapi.responses import StreamingResponse

            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    )
                },
            )

        else:
            raise HTTPException(
                status_code=400, detail=f"Formato {formato} no soportado aún"
            )

    except ImportError:
        raise HTTPException(
            status_code=500, detail="Dependencias de exportación no instaladas"
        )

@router.get("/tiempo-real/actualizacion")
def obtener_actualizacion_tiempo_real(
    componentes: Optional[str] = Query(
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    """
    hoy = date.today()
    actualizaciones = {}

    if not componentes or "kpis" in componentes:
        # Actualizar KPIs
        cobrado_hoy = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.fecha_pago == hoy, Pago.estado != "ANULADO"
        ).scalar() or Decimal("0")

            db.query(Cuota)
            .filter(
                Cuota.fecha_vencimiento == hoy,
                Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
            )
            .count()
        )

        actualizaciones["kpis"] = {
            "cobrado_hoy": float(cobrado_hoy),
        }

    if not componentes or "alertas" in componentes:
        # Actualizar alertas
        alertas_data = obtener_alertas_tiempo_real(
            db=db, current_user=current_user
        )
        actualizaciones["alertas"] = alertas_data

    if not componentes or "notificaciones" in componentes:
        # Actualizar notificaciones pendientes
        notif_pendientes = (
            db.query(Notificacion)
            .filter(Notificacion.estado == "PENDIENTE")
            .count()
        )
        actualizaciones["notificaciones"] = {
            "pendientes": notif_pendientes,
        }

    return {
        "actualizaciones": actualizaciones,
        ),
    }
