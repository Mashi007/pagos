import logging
import re
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, nullslast, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate

# Endpoints de gestion de clientes - VERSION CON AUDITORIA AUTOMATICA
# Sistema completo de gestion de clientes con validaciones y auditoria
# Datos del dashboard ahora son calculados desde la base de datos en tiempo real


router = APIRouter()
logger = logging.getLogger(__name__)


def _aplicar_filtro_busqueda(query, search: Optional[str]):
    """Aplica filtro de búsqueda general"""
    if not search:
        return query
    search_pattern = f"%{search}%"
    return query.filter(
        or_(
            Cliente.nombres.ilike(search_pattern),
            Cliente.cedula.ilike(search_pattern),
            Cliente.telefono.ilike(search_pattern),
        )
    )


def _aplicar_filtros_especificos(
    query,
    estado: Optional[str],
    cedula: Optional[str],
    email: Optional[str],
    telefono: Optional[str],
    ocupacion: Optional[str],
    usuario_registro: Optional[str],
):
    """Aplica filtros específicos a la query"""
    if estado:
        query = query.filter(Cliente.estado == estado)
    if cedula:
        query = query.filter(Cliente.cedula.ilike(f"%{cedula}%"))
    if email:
        query = query.filter(Cliente.email.ilike(f"%{email}%"))
    if telefono:
        query = query.filter(Cliente.telefono.ilike(f"%{telefono}%"))
    if ocupacion:
        query = query.filter(Cliente.ocupacion.ilike(f"%{ocupacion}%"))
    if usuario_registro:
        query = query.filter(Cliente.usuario_registro.ilike(f"%{usuario_registro}%"))
    return query


def _aplicar_filtros_fecha(query, fecha_desde: Optional[str], fecha_hasta: Optional[str]):
    """Aplica filtros de fecha de registro"""
    if fecha_desde:
        try:
            fecha_desde_obj = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
            query = query.filter(func.date(Cliente.fecha_registro) >= fecha_desde_obj)
        except ValueError:
            logger.warning(f"Fecha desde inválida: {fecha_desde}")
    if fecha_hasta:
        try:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
            fecha_hasta_obj = fecha_hasta_obj + timedelta(days=1)
            query = query.filter(func.date(Cliente.fecha_registro) < fecha_hasta_obj)
        except ValueError:
            logger.warning(f"Fecha hasta inválida: {fecha_hasta}")
    return query


def _serializar_clientes(clientes):
    """Serializa una lista de clientes de forma segura"""
    clientes_dict = []
    total_clientes = len(clientes)
    errores_serializacion = 0

    logger.info(f"📋 [serializar_clientes] Iniciando serialización de {total_clientes} clientes")

    for cliente in clientes:
        try:
            cliente_data = ClienteResponse.model_validate(cliente).model_dump()
            clientes_dict.append(cliente_data)
        except Exception as e:
            errores_serializacion += 1
            logger.error(f"❌ Error serializando cliente {getattr(cliente, 'id', 'N/A')}: {e}", exc_info=True)
            # ✅ DEBUG: Log detallado del cliente que falló
            logger.error(f"   Cliente ID: {getattr(cliente, 'id', 'N/A')}")
            logger.error(f"   Cliente tipo: {type(cliente)}")
            logger.error(f"   Cliente atributos: {dir(cliente)[:20]}")
            continue

    logger.info(
        f"✅ [serializar_clientes] Serialización completada: {len(clientes_dict)}/{total_clientes} exitosos, {errores_serializacion} errores"
    )

    if errores_serializacion > 0 and len(clientes_dict) == 0:
        logger.warning(
            f"⚠️ [serializar_clientes] TODOS los clientes fallaron al serializarse. Esto puede indicar un problema con el schema ClienteResponse"
        )

    return clientes_dict


def _identificar_problemas_validacion(cliente) -> dict:
    """
    Identifica problemas de validación en un cliente sin intentar serializarlo.
    Retorna un dict con los problemas encontrados.
    """
    problemas = []

    # Verificar teléfono
    telefono = getattr(cliente, "telefono", None)
    if telefono:
        telefono_str = str(telefono).strip()
        if not telefono_str.startswith("+58"):
            problemas.append(
                {
                    "campo": "telefono",
                    "valor_actual": telefono_str,
                    "error": f"Teléfono debe empezar por '+58'. Recibido: '{telefono_str}'",
                    "requisito": "Formato: +58 seguido de 10 dígitos, primero NO puede ser 0",
                }
            )
        elif len(telefono_str) != 13:
            problemas.append(
                {
                    "campo": "telefono",
                    "valor_actual": telefono_str,
                    "error": f"Teléfono debe tener exactamente 13 caracteres. Recibido: {len(telefono_str)}",
                    "requisito": "Formato: +58XXXXXXXXXX (13 caracteres)",
                }
            )
        elif len(telefono_str) == 13:
            # Verificar que después de +58 tenga 10 dígitos
            digitos = telefono_str[3:]
            if not re.match(r"^[0-9]{10}$", digitos):
                problemas.append(
                    {
                        "campo": "telefono",
                        "valor_actual": telefono_str,
                        "error": f"Después de '+58' deben ir exactamente 10 dígitos. Recibido: '{digitos}'",
                        "requisito": "Formato: +58 seguido de 10 dígitos numéricos",
                    }
                )
            elif digitos[0] == "0":
                problemas.append(
                    {
                        "campo": "telefono",
                        "valor_actual": telefono_str,
                        "error": "El primer dígito después de '+58' NO puede ser 0",
                        "requisito": "El número debe empezar por 1-9 después de +58",
                    }
                )
    elif not telefono:
        problemas.append(
            {"campo": "telefono", "valor_actual": None, "error": "Teléfono requerido", "requisito": "Teléfono es obligatorio"}
        )

    # Verificar nombres
    nombres = getattr(cliente, "nombres", None)
    if nombres:
        nombres_str = str(nombres).strip()
        palabras = [p for p in nombres_str.split() if p]
        if len(palabras) < 2:
            problemas.append(
                {
                    "campo": "nombres",
                    "valor_actual": nombres_str,
                    "error": f"Mínimo 2 palabras requeridas. Recibido: {len(palabras)}",
                    "requisito": "Nombre + apellido (mínimo 2 palabras)",
                }
            )
        elif len(palabras) > 7:
            problemas.append(
                {
                    "campo": "nombres",
                    "valor_actual": nombres_str,
                    "error": f"Máximo 7 palabras permitidas. Recibido: {len(palabras)}",
                    "requisito": "Máximo 7 palabras",
                }
            )
    elif not nombres:
        problemas.append(
            {"campo": "nombres", "valor_actual": None, "error": "Nombres requeridos", "requisito": "Nombres es obligatorio"}
        )

    # Verificar email (solo formato básico, no validación estricta)
    email = getattr(cliente, "email", None)
    if email:
        email_str = str(email).strip()
        if "@" not in email_str:
            problemas.append(
                {
                    "campo": "email",
                    "valor_actual": email_str,
                    "error": "Email debe contener '@'",
                    "requisito": "Formato válido de email",
                }
            )

    # Verificar cédula
    cedula = getattr(cliente, "cedula", None)
    if cedula:
        cedula_str = str(cedula).strip()
        if len(cedula_str) < 6 or len(cedula_str) > 13:
            problemas.append(
                {
                    "campo": "cedula",
                    "valor_actual": cedula_str,
                    "error": f"Cédula debe tener entre 6 y 13 caracteres. Recibido: {len(cedula_str)}",
                    "requisito": "Entre 6 y 13 caracteres",
                }
            )
    elif not cedula:
        problemas.append(
            {"campo": "cedula", "valor_actual": None, "error": "Cédula requerida", "requisito": "Cédula es obligatoria"}
        )

    return {
        "cliente_id": getattr(cliente, "id", None),
        "cedula": getattr(cliente, "cedula", None),
        "nombres": getattr(cliente, "nombres", None),
        "problemas": problemas,
        "tiene_problemas": len(problemas) > 0,
    }


@router.get("", response_model=dict)
def listar_clientes(
    page: int = Query(1, ge=1, description="Numero de pagina"),
    per_page: int = Query(20, ge=1, le=5000, description="Tamano de pagina"),
    # Busqueda de texto
    search: Optional[str] = Query(None, description="Buscar por nombre, cedula o telefono"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    cedula: Optional[str] = Query(None, description="Filtrar por cédula exacta"),
    email: Optional[str] = Query(None, description="Filtrar por email"),
    telefono: Optional[str] = Query(None, description="Filtrar por teléfono"),
    ocupacion: Optional[str] = Query(None, description="Filtrar por ocupación"),
    usuario_registro: Optional[str] = Query(None, description="Filtrar por usuario que registró"),
    fecha_desde: Optional[str] = Query(None, description="Fecha de registro desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha de registro hasta (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar clientes con paginacion y filtros
    import time

    start_time = time.time()
    try:
        logger.info(f"Listar clientes - Usuario: {current_user.email}, page={page}, per_page={per_page}")

        # Query base
        query = db.query(Cliente)

        # Aplicar filtros
        query = _aplicar_filtro_busqueda(query, search)
        query = _aplicar_filtros_especificos(query, estado, cedula, email, telefono, ocupacion, usuario_registro)
        query = _aplicar_filtros_fecha(query, fecha_desde, fecha_hasta)

        # Ordenamiento por fecha de registro descendente (más recientes primero)
        # ✅ CORRECCIÓN: Usar nullslast para manejar registros sin fecha_registro
        query = query.order_by(nullslast(Cliente.fecha_registro.desc()), Cliente.id.desc())

        # ✅ OPTIMIZACIÓN: Solo contar si realmente se necesita (primera página o cuando hay pocos resultados)
        # Para páginas grandes (per_page > 500), usar estimación rápida
        if per_page > 500:
            # Para páginas muy grandes, hacer count solo si es página 1
            if page == 1:
                start_count = time.time()
                total = query.count()
                count_time = int((time.time() - start_count) * 1000)
                logger.info(f"📊 [clientes] Count completado en {count_time}ms: {total} total")
            else:
                # Para páginas > 1, estimar total basado en resultados previos
                # Esto evita hacer count() en cada página
                total = None  # No calculamos total para páginas grandes
        else:
            # Para páginas normales, hacer count siempre
            start_count = time.time()
            total = query.count()
            count_time = int((time.time() - start_count) * 1000)
            logger.info(f"📊 [clientes] Count completado en {count_time}ms: {total} total")

        # Paginacion
        offset = (page - 1) * per_page
        start_query = time.time()
        clientes = query.offset(offset).limit(per_page).all()
        query_time = int((time.time() - start_query) * 1000)
        logger.info(f"📊 [clientes] Query completada en {query_time}ms: {len(clientes)} registros")

        # ✅ DEBUG: Log detallado de la query
        if len(clientes) == 0:
            logger.warning(f"⚠️ [clientes] Query retornó 0 registros pero total={total}. Verificando query...")
            logger.info(f"   Offset: {offset}, Limit: {per_page}, Page: {page}")
            # Verificar si hay registros sin paginación
            total_sin_paginar = query.limit(100).all()
            logger.info(f"   Registros sin paginación (limit 100): {len(total_sin_paginar)}")
            if len(total_sin_paginar) > 0:
                logger.info(f"   Primer cliente ID: {total_sin_paginar[0].id}")
        else:
            logger.info(f"✅ [clientes] Primer cliente ID: {clientes[0].id}, Último cliente ID: {clientes[-1].id}")

        # Serializacion segura
        start_serialize = time.time()
        clientes_dict = _serializar_clientes(clientes)
        serialize_time = int((time.time() - start_serialize) * 1000)
        logger.info(
            f"📊 [clientes] Serialización completada en {serialize_time}ms: {len(clientes_dict)} clientes serializados"
        )

        # Calcular paginas
        if total is not None:
            total_pages = (total + per_page - 1) // per_page
        else:
            # Si no tenemos total, estimar basado en si hay más resultados
            total_pages = page + 1 if len(clientes) == per_page else page

        total_time = int((time.time() - start_time) * 1000)
        count_time_str = f"{count_time}ms" if total is not None else "N/A"
        logger.info(
            f"⏱️ [clientes] Tiempo total: {total_time}ms (count: {count_time_str}, query: {query_time}ms, serialize: {serialize_time}ms)"
        )

        return {
            "clientes": clientes_dict,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Error en listar_clientes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/stats")
def obtener_estadisticas_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener estadísticas de clientes directamente desde la BD
    import time
    start_time = time.time()
    
    try:
        logger.info(f"📊 [stats] Obteniendo estadísticas de clientes - Usuario: {current_user.email}")

        # Contar total de clientes
        total = db.query(Cliente).count()
        logger.debug(f"📊 [stats] Total clientes: {total}")

        # Contar por estado
        activos = db.query(Cliente).filter(Cliente.estado == "ACTIVO").count()
        logger.debug(f"📊 [stats] Clientes activos: {activos}")

        inactivos = db.query(Cliente).filter(Cliente.estado == "INACTIVO").count()
        logger.debug(f"📊 [stats] Clientes inactivos: {inactivos}")

        finalizados = db.query(Cliente).filter(Cliente.estado == "FINALIZADO").count()
        logger.debug(f"📊 [stats] Clientes finalizados: {finalizados}")

        # Verificar consistencia de datos
        suma_estados = activos + inactivos + finalizados
        if suma_estados != total:
            logger.warning(
                f"⚠️ [stats] Inconsistencia detectada: Total={total}, Suma estados={suma_estados} "
                f"(Activos={activos}, Inactivos={inactivos}, Finalizados={finalizados})"
            )

        tiempo_total = int((time.time() - start_time) * 1000)
        logger.info(
            f"✅ [stats] Estadísticas obtenidas en {tiempo_total}ms: "
            f"Total={total}, Activos={activos}, Inactivos={inactivos}, Finalizados={finalizados}"
        )

        return {
            "total": total,
            "activos": activos,
            "inactivos": inactivos,
            "finalizados": finalizados,
        }

    except Exception as e:
        tiempo_total = int((time.time() - start_time) * 1000)
        logger.error(f"❌ [stats] Error en obtener_estadisticas_clientes después de {tiempo_total}ms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/embudo/estadisticas")
def obtener_estadisticas_embudo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas del embudo de clientes basadas en estados de préstamos"""
    try:
        logger.info(f"Obteniendo estadísticas del embudo - Usuario: {current_user.email}")

        # Total de clientes
        total = db.query(Cliente).count()

        # Clientes con préstamos RECHAZADOS
        clientes_rechazados = (
            db.query(func.count(func.distinct(Prestamo.cliente_id))).filter(Prestamo.estado == "RECHAZADO").scalar() or 0
        )

        # Clientes con préstamos APROBADOS
        clientes_aprobados = (
            db.query(func.count(func.distinct(Prestamo.cliente_id))).filter(Prestamo.estado == "APROBADO").scalar() or 0
        )

        # Clientes con préstamos en evaluación (EN_REVISION o DRAFT)
        clientes_evaluacion = (
            db.query(func.count(func.distinct(Prestamo.cliente_id)))
            .filter(Prestamo.estado.in_(["EN_REVISION", "DRAFT"]))
            .scalar()
            or 0
        )

        # Prospectos: todos los clientes que no están en los otros estados
        # Es decir, clientes que no tienen préstamos o tienen préstamos en otros estados
        clientes_con_prestamos = (
            db.query(func.count(func.distinct(Prestamo.cliente_id)))
            .filter(Prestamo.estado.in_(["RECHAZADO", "APROBADO", "EN_REVISION", "DRAFT"]))
            .scalar()
            or 0
        )
        prospectos = total - clientes_con_prestamos

        return {
            "total": total,
            "prospectos": max(0, prospectos),  # Asegurar que no sea negativo
            "evaluacion": clientes_evaluacion,
            "aprobados": clientes_aprobados,
            "rechazados": clientes_rechazados,
        }

    except Exception as e:
        logger.error(f"Error en obtener_estadisticas_embudo: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener cliente por ID
    try:
        logger.info(f"Obteniendo cliente {cliente_id}")
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return ClienteResponse.model_validate(cliente)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_cliente: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("", response_model=None)
def crear_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear nuevo cliente
    try:
        logger.info(f"Crear cliente - Usuario: {current_user.email}")

        # ✅ Validar: NO permitir crear si existe:
        # - Misma cédula Y mismo nombre (ambos deben coincidir)
        # - O mismo email
        # NOTA: El teléfono NO se valida como duplicado
        nombres_normalizados = (cliente_data.nombres or "").strip().lower()
        email_normalizado = (cliente_data.email or "").lower().strip() if cliente_data.email else None

        # 1) Bloquear por cédula Y nombre duplicados (ambos deben coincidir)
        if nombres_normalizados:
            existente_cedula_nombre = (
                db.query(Cliente)
                .filter(
                    Cliente.cedula == cliente_data.cedula,
                    func.lower(Cliente.nombres) == nombres_normalizados
                )
                .first()
            )
            if existente_cedula_nombre:
                logger.warning(
                    f"❌ Intento de crear cliente con cédula y nombre ya registrados: "
                    f"cédula={cliente_data.cedula}, nombre={cliente_data.nombres} "
                    f"(ID existente: {existente_cedula_nombre.id})"
                )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No se puede crear un cliente con la misma cédula ({cliente_data.cedula}) "
                        f"y el mismo nombre completo ({cliente_data.nombres}). "
                        f"Ya existe un cliente (ID: {existente_cedula_nombre.id}) con esos datos."
                    ),
                )

        # 2) Bloquear por email duplicado (case-insensitive)
        if email_normalizado:
            existente_email = db.query(Cliente).filter(func.lower(Cliente.email) == email_normalizado).first()
            if existente_email:
                logger.warning(
                    f"❌ Intento de crear cliente con email ya registrado: {email_normalizado} "
                    f"(ID existente: {existente_email.id})"
                )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No se puede crear un cliente con el mismo email ({cliente_data.email}). "
                        f"Ya existe un cliente (ID: {existente_email.id}) con ese email."
                    ),
                )

        # Preparar datos
        cliente_dict = cliente_data.model_dump()

        # ✅ REGLA DE NEGOCIO ACTUALIZADA: Por defecto ACTIVO (todos los clientes nuevos)
        # INACTIVO: Automático cuando tiene 4 o más cuotas sin pagar
        # ACTIVO: Si está al día o termina de pagar todas las cuotas (siempre permanece ACTIVO)
        if not cliente_dict.get("estado"):
            cliente_dict["estado"] = "ACTIVO"

        # Usuario que registra el cliente
        cliente_dict["usuario_registro"] = current_user.email

        # Asegurar normalización (aunque el trigger de BD también lo hará)
        if "email" in cliente_dict and cliente_dict["email"]:
            cliente_dict["email"] = cliente_dict["email"].lower().strip()
        if "cedula" in cliente_dict and cliente_dict["cedula"]:
            cliente_dict["cedula"] = re.sub(r"[-\s]", "", cliente_dict["cedula"].strip())

        # Crear nuevo cliente
        nuevo_cliente = Cliente(**cliente_dict)

        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)

        return ClienteResponse.model_validate(nuevo_cliente)

    except Exception as e:
        import traceback

        error_detail = f"{str(e)}: {traceback.format_exc()}"
        logger.error(f"Error en crear_cliente: {error_detail}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


def _validar_duplicados_actualizacion(db: Session, cliente_id: int, update_data: dict, cliente: Cliente):
    """Valida que no haya duplicados al actualizar: misma cédula Y nombre, o mismo email"""
    # Solo validar si se actualiza cédula, nombres o email (teléfono no se valida)
    if not any(key in update_data for key in ["cedula", "nombres", "email"]):
        return

    nueva_cedula = update_data.get("cedula", cliente.cedula)
    nuevos_nombres = update_data.get("nombres", cliente.nombres)
    nuevo_email = update_data.get("email", cliente.email)

    # Validar cédula Y nombre duplicados (ambos deben coincidir)
    if ("cedula" in update_data or "nombres" in update_data) and nuevos_nombres:
        nuevos_nombres_normalizados = nuevos_nombres.strip().lower()
        otro_con_misma_cedula_nombre = (
            db.query(Cliente)
            .filter(
                Cliente.cedula == nueva_cedula,
                func.lower(Cliente.nombres) == nuevos_nombres_normalizados,
                Cliente.id != cliente_id,
            )
            .first()
        )
        if otro_con_misma_cedula_nombre:
            logger.warning(
                f"❌ Intento de actualizar cliente {cliente_id} a cédula y nombre duplicados: "
                f"cédula={nueva_cedula}, nombre={nuevos_nombres} "
                f"(ya existe ID: {otro_con_misma_cedula_nombre.id})"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No se puede actualizar el cliente para tener la misma cédula ({nueva_cedula}) "
                    f"y el mismo nombre completo ({nuevos_nombres}) que otro cliente existente "
                    f"(ID: {otro_con_misma_cedula_nombre.id})."
                ),
            )

    # Validar email duplicado (case-insensitive)
    if "email" in update_data and nuevo_email:
        nuevo_email_normalizado = nuevo_email.lower().strip()
        otro_con_mismo_email = (
            db.query(Cliente)
            .filter(func.lower(Cliente.email) == nuevo_email_normalizado, Cliente.id != cliente_id)
            .first()
        )
        if otro_con_mismo_email:
            logger.warning(
                f"❌ Intento de actualizar cliente {cliente_id} a email duplicado: {nuevo_email} "
                f"(ya existe ID: {otro_con_mismo_email.id})"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No se puede actualizar el cliente para tener el mismo email "
                    f"({nuevo_email}) que otro cliente existente (ID: {otro_con_mismo_email.id})."
                ),
            )


@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    cliente_data: ClienteUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar cliente
    try:
        logger.info(f"Actualizando cliente {cliente_id}")

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        update_data = cliente_data.model_dump(exclude_unset=True)

        # Validar duplicados
        _validar_duplicados_actualizacion(db, cliente_id, update_data, cliente)

        # Nota: Ya no hay campo 'activo', solo se maneja 'estado'

        # Aplicar actualizaciones
        nombres_actualizados = False
        for field, value in update_data.items():
            if hasattr(cliente, field):
                setattr(cliente, field, value)
                # Detectar si se actualizó el nombre
                if field == 'nombres':
                    nombres_actualizados = True

        # Actualizar fecha_actualizacion manualmente
        cliente.fecha_actualizacion = datetime.utcnow()

        # Si se actualizó el nombre, sincronizar con préstamos relacionados
        if nombres_actualizados and cliente.nombres:
            prestamos_relacionados = db.query(Prestamo).filter(
                Prestamo.cliente_id == cliente_id
            ).all()
            
            if prestamos_relacionados:
                for prestamo in prestamos_relacionados:
                    prestamo.nombres = cliente.nombres  # type: ignore[assignment]
                logger.info(
                    f"✅ Actualizados {len(prestamos_relacionados)} préstamos con nuevo nombre del cliente: {cliente.nombres}"
                )

        db.commit()
        db.refresh(cliente)

        return ClienteResponse.model_validate(cliente)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualizar_cliente: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/{cliente_id}")
def eliminar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar cliente (hard delete)
    try:
        logger.info(f"Eliminando cliente {cliente_id}")

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Hard delete - eliminar fisicamente de la BD
        db.delete(cliente)
        db.commit()

        return {"message": "Cliente eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en eliminar_cliente: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# =====================================================
# ENDPOINTS PARA VALORES POR DEFECTO
# =====================================================


@router.get("/con-problemas-validacion", response_model=dict)
def listar_clientes_con_problemas_validacion(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista clientes que tienen problemas de validación que deben ser corregidos.
    Estos son clientes que no pueden ser serializados correctamente debido a validaciones estrictas.
    """
    try:
        import time

        start_time = time.time()

        # Obtener todos los clientes (sin paginación inicial para identificar problemas)
        # Para optimizar, primero obtenemos una muestra y luego contamos
        todos_clientes = db.query(Cliente).all()

        # Identificar clientes con problemas
        clientes_con_problemas_completos = []
        for cliente in todos_clientes:
            try:
                # Intentar validar
                ClienteResponse.model_validate(cliente)
                # Si pasa la validación, no tiene problemas
            except Exception:
                # Si falla, identificar los problemas específicos
                problemas_info = _identificar_problemas_validacion(cliente)
                if problemas_info["tiene_problemas"]:
                    # Agregar información adicional del cliente
                    problemas_info["telefono"] = getattr(cliente, "telefono", None)
                    problemas_info["email"] = getattr(cliente, "email", None)
                    problemas_info["direccion"] = getattr(cliente, "direccion", None)
                    problemas_info["ocupacion"] = getattr(cliente, "ocupacion", None)
                    problemas_info["fecha_registro"] = getattr(cliente, "fecha_registro", None)
                    problemas_info["estado"] = getattr(cliente, "estado", None)
                    problemas_info["activo"] = getattr(cliente, "activo", None)
                    clientes_con_problemas_completos.append(problemas_info)

        total_con_problemas = len(clientes_con_problemas_completos)

        # Aplicar paginación
        offset = (page - 1) * per_page
        clientes_paginados = clientes_con_problemas_completos[offset : offset + per_page]

        total_pages = (total_con_problemas + per_page - 1) // per_page if total_con_problemas > 0 else 1

        tiempo_total = int((time.time() - start_time) * 1000)
        logger.info(f"📊 [clientes-problemas] Encontrados {total_con_problemas} clientes con problemas en {tiempo_total}ms")

        return {
            "clientes": clientes_paginados,
            "total": total_con_problemas,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error(f"Error en listar_clientes_con_problemas_validacion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/valores-por-defecto", response_model=dict)
def listar_clientes_valores_por_defecto(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista clientes que tienen valores por defecto que necesitan ser corregidos.

    Valores por defecto detectados:
    - Email con 'noemail' o '@noemail'
    - Teléfono con '999999999'
    - Dirección con 'Actualizar'
    - Ocupación con 'Actualizar'
    - Notas con 'NA' o 'No hay observacion'
    """
    try:
        # Buscar clientes con valores por defecto
        query = db.query(Cliente).filter(
            or_(
                Cliente.email.ilike("%noemail%"),
                Cliente.email.ilike("%@noemail%"),
                Cliente.telefono.ilike("%999999999%"),
                Cliente.direccion.ilike("%Actualizar%"),
                Cliente.ocupacion.ilike("%Actualizar%"),
                Cliente.notas.in_(["NA", "No hay observacion", "No existe observaciones"]),
            )
        )

        total = query.count()

        # Paginación
        offset = (page - 1) * per_page
        clientes = query.order_by(Cliente.fecha_registro.desc()).offset(offset).limit(per_page).all()

        # Serializar clientes
        clientes_dict = _serializar_clientes(clientes)

        # Calcular total de páginas
        total_pages = (total + per_page - 1) // per_page

        return {
            "items": clientes_dict,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error(f"Error en listar_clientes_valores_por_defecto: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/valores-por-defecto/exportar")
def exportar_clientes_valores_por_defecto(
    formato: str = Query("csv", pattern="^(csv|excel)$", description="Formato de exportación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exporta clientes con valores por defecto en formato CSV o Excel.
    """
    try:
        import csv
        import io
        from datetime import datetime

        # Buscar todos los clientes con valores por defecto
        clientes = (
            db.query(Cliente)
            .filter(
                or_(
                    Cliente.email.ilike("%noemail%"),
                    Cliente.email.ilike("%@noemail%"),
                    Cliente.telefono.ilike("%999999999%"),
                    Cliente.direccion.ilike("%Actualizar%"),
                    Cliente.ocupacion.ilike("%Actualizar%"),
                    Cliente.notas.in_(["NA", "No hay observacion", "No existe observaciones"]),
                )
            )
            .order_by(Cliente.fecha_registro.desc())
            .all()
        )

        if formato == "csv":
            # Generar CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # Encabezados
            writer.writerow(
                ["ID", "Cédula", "Nombres", "Teléfono", "Email", "Dirección", "Ocupación", "Estado", "Fecha Registro", "Notas"]
            )

            # Datos
            for cliente in clientes:
                writer.writerow(
                    [
                        cliente.id,
                        cliente.cedula,
                        cliente.nombres,
                        cliente.telefono,
                        cliente.email,
                        cliente.direccion,
                        cliente.ocupacion,
                        cliente.estado,
                        cliente.fecha_registro.strftime("%Y-%m-%d %H:%M:%S") if cliente.fecha_registro else "",
                        cliente.notas,
                    ]
                )

            from fastapi.responses import Response

            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=clientes_valores_por_defecto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                },
            )

        elif formato == "excel":
            # Generar Excel
            import pandas as pd

            data = []
            for cliente in clientes:
                data.append(
                    {
                        "ID": cliente.id,
                        "Cédula": cliente.cedula,
                        "Nombres": cliente.nombres,
                        "Teléfono": cliente.telefono,
                        "Email": cliente.email,
                        "Dirección": cliente.direccion,
                        "Ocupación": cliente.ocupacion,
                        "Estado": cliente.estado,
                        "Fecha Registro": (
                            cliente.fecha_registro.strftime("%Y-%m-%d %H:%M:%S") if cliente.fecha_registro else ""
                        ),
                        "Notas": cliente.notas,
                    }
                )

            df = pd.DataFrame(data)
            output = io.BytesIO()
            df.to_excel(output, index=False, engine="openpyxl")
            output.seek(0)

            from fastapi.responses import Response

            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=clientes_valores_por_defecto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                },
            )

    except Exception as e:
        logger.error(f"Error en exportar_clientes_valores_por_defecto: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/actualizar-lote", response_model=dict)
def actualizar_clientes_lote(
    actualizaciones: list,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza múltiples clientes en lote.

    Formato esperado:
    [
        {"id": 1, "email": "nuevo@email.com", "telefono": "+581234567890"},
        {"id": 2, "direccion": "Nueva dirección", "ocupacion": "Nueva ocupación"},
    ]
    """
    try:
        actualizados = 0
        errores = []

        for actualizacion in actualizaciones:
            cliente_id = actualizacion.get("id")
            if not cliente_id:
                errores.append({"id": None, "error": "ID de cliente requerido"})
                continue

            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                errores.append({"id": cliente_id, "error": "Cliente no encontrado"})
                continue

            try:
                # Actualizar campos permitidos
                campos_permitidos = ["email", "telefono", "direccion", "ocupacion", "notas", "estado", "activo"]
                for campo, valor in actualizacion.items():
                    if campo != "id" and campo in campos_permitidos and valor is not None:
                        setattr(cliente, campo, valor)

                # Normalizar email y cédula (el trigger de BD también lo hará, pero lo hacemos aquí también)
                if hasattr(cliente, "email") and cliente.email:
                    cliente.email = cliente.email.lower().strip()

                db.commit()
                actualizados += 1

            except Exception as e:
                db.rollback()
                errores.append({"id": cliente_id, "error": str(e)})

        return {
            "actualizados": actualizados,
            "errores": errores,
            "total_procesados": len(actualizaciones),
        }

    except Exception as e:
        logger.error(f"Error en actualizar_clientes_lote: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
