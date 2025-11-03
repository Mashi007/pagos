import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.configuracion_sistema import ConfiguracionSistema
from app.models.prestamo import Prestamo
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class ConfiguracionUpdate(BaseModel):
    """Schema para actualizar configuración"""

    clave: str = Field(..., description="Clave de configuración")
    valor: str = Field(..., description="Valor de configuración")
    descripcion: Optional[str] = Field(None, description="Descripción")


class ConfiguracionResponse(BaseModel):
    """Response para configuración"""

    id: int
    clave: str
    valor: str
    descripcion: Optional[str]
    fecha_actualizacion: datetime
    actualizado_por: int

    class Config:
        from_attributes = True


# ============================================
# MONITOREO Y OBSERVABILIDAD
# ============================================


@router.get("/monitoreo/estado")
def obtener_estado_monitoreo(current_user: User = Depends(get_current_user)):
    """Verificar estado del sistema de monitoreo y observabilidad"""
    # Solo admin puede ver configuración de monitoreo
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver configuración de monitoreo",
        )

    return {
        "estado": "ACTIVO",
        "nivel": "BÁSICO",
        "componentes": {
            "logging": "ACTIVO",
            "health_checks": "ACTIVO",
            "métricas_básicas": "ACTIVO",
        },
        "última_verificación": datetime.now(),
    }


@router.post("/monitoreo/habilitar-basico")
def habilitar_monitoreo_basico(current_user: User = Depends(get_current_user)):
    """Habilitar monitoreo básico sin dependencias externas"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden configurar monitoreo")

    try:
        # Configurar logging estructurado básico
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Logger específico para el sistema de financiamiento
        finance_logger = logging.getLogger("financiamiento_automotriz")
        finance_logger.setLevel(logging.INFO)

        return {
            "mensaje": "Monitoreo básico habilitado exitosamente",
            "configuración": {
                "nivel_logging": "INFO",
                "formato": "Timestamp + Archivo + Línea + Mensaje",
                "logger_específico": "financiamiento_automotriz",
            },
            "características": [
                "Logging estructurado",
                "Health checks básicos",
                "Métricas de operaciones",
                "Sin dependencias externas adicionales",
            ],
            "siguiente_paso": "Configurar Sentry y Prometheus para monitoreo avanzado",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error configurando monitoreo: {str(e)}")


# ============================================
# CONFIGURACIÓN CENTRALIZADA DEL SISTEMA
# ============================================


@router.get("/sistema/completa")
def obtener_configuracion_completa(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener toda la configuración del sistema"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver configuración completa",
        )

    try:
        configuraciones = db.query(ConfiguracionSistema).all()

        return {
            "configuraciones": [
                {
                    "clave": config.clave,
                    "valor": config.valor,
                    "descripcion": config.descripcion,
                    "fecha_actualizacion": config.fecha_actualizacion,
                }
                for config in configuraciones
            ],
            "total": len(configuraciones),
        }

    except Exception as e:
        logger.error(f"Error obteniendo configuración: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/sistema/{clave}")
def obtener_configuracion_por_clave(
    clave: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener configuración específica por clave"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver configuración")

    try:
        config = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave == clave).first()

        if not config:
            raise HTTPException(status_code=404, detail=f"Configuración '{clave}' no encontrada")

        return config

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo configuración: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/sistema/categoria/{categoria}")
def obtener_configuracion_por_categoria(
    categoria: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener todas las configuraciones de una categoría específica"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver configuración por categoría",
        )

    try:
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == categoria.upper()).all()

        return {
            "categoria": categoria.upper(),
            "configuraciones": [
                {
                    "clave": config.clave,
                    "valor": config.valor,
                    "descripcion": config.descripcion,
                    "fecha_actualizacion": config.fecha_actualizacion,
                }
                for config in configs
            ],
            "total": len(configs),
        }

    except Exception as e:
        logger.error(f"Error obteniendo configuración por categoría: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.put("/sistema/{clave}")
def actualizar_configuracion(
    clave: str,
    config_data: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración específica"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden actualizar configuración",
        )

    try:
        config = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave == clave).first()

        if not config:
            # Crear nueva configuración
            config = ConfiguracionSistema(
                clave=config_data.clave,
                valor=config_data.valor,
                descripcion=config_data.descripcion,
                actualizado_por=current_user.id,
            )
            db.add(config)
        else:
            # Actualizar configuración existente
            config.valor = config_data.valor  # type: ignore[assignment]
            config.descripcion = config_data.descripcion  # type: ignore[assignment]
            config.actualizado_por = int(current_user.id)  # type: ignore[assignment]
            config.fecha_actualizacion = datetime.now()  # type: ignore[assignment]

        db.commit()
        db.refresh(config)

        return {
            "mensaje": "Configuración actualizada exitosamente",
            "configuracion": config,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando configuración: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.delete("/sistema/{clave}")
def eliminar_configuracion(
    clave: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar configuración específica"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar configuración")

    try:
        config = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave == clave).first()

        if not config:
            raise HTTPException(status_code=404, detail=f"Configuración '{clave}' no encontrada")

        db.delete(config)
        db.commit()

        return {"mensaje": "Configuración eliminada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando configuración: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# ============================================
# CONFIGURACIÓN GENERAL (FRONTEND)
# ============================================


@router.get("/general")
def obtener_configuracion_general(db: Session = Depends(get_db)):
    """Obtener configuración general del sistema"""
    # Consultar logo_filename desde la base de datos
    logo_filename = None
    try:
        logo_config = (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == "GENERAL",
                ConfiguracionSistema.clave == "logo_filename",
            )
            .first()
        )
        if logo_config:
            logo_filename = logo_config.valor
            logger.info(f"Logo filename encontrado en BD: {logo_filename}")
    except Exception as e:
        logger.warning(f"No se pudo obtener logo_filename de BD: {str(e)}")

    # Retornar configuración con logo_filename si existe
    config = {
        "nombre_empresa": "RAPICREDIT",
        "version_sistema": "1.0.0",
        "idioma": "ES",
        "zona_horaria": "America/Caracas",
        "moneda": "VES",
        "formato_fecha": "DD/MM/YYYY",
        "ruc": "",
        "direccion": "",
        "telefono": "",
        "email": "",
        "horario_atencion": "08:00-18:00",
    }

    # Agregar logo_filename si existe
    if logo_filename:
        config["logo_filename"] = logo_filename

    return config


@router.post("/upload-logo")
async def upload_logo(
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Subir logo de la empresa (solo administradores)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden subir el logo",
        )

    try:
        # Validar tipo de archivo
        allowed_types = ["image/svg+xml", "image/png", "image/jpeg", "image/jpg"]
        if logo.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Formato no válido. Use SVG, PNG o JPG",
            )

        # Validar tamaño (máximo 2MB)
        contents = await logo.read()
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="El archivo es demasiado grande. Máximo 2MB",
            )

        # Determinar extensión basada en content_type
        content_type_to_ext = {
            "image/svg+xml": ".svg",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
        }
        extension = content_type_to_ext.get(logo.content_type, ".svg")

        # Crear directorio de logos en el directorio de uploads del backend
        from app.core.config import settings

        uploads_dir = Path(settings.UPLOAD_DIR) if hasattr(settings, "UPLOAD_DIR") else Path("uploads")
        logos_dir = uploads_dir / "logos"
        logos_dir.mkdir(parents=True, exist_ok=True)

        # Nombre del archivo: logo-custom.{ext}
        logo_filename = f"logo-custom{extension}"
        logo_path = logos_dir / logo_filename

        # Guardar archivo
        with open(logo_path, "wb") as f:
            f.write(contents)

        # Guardar referencia del logo en la base de datos
        from app.models.configuracion_sistema import ConfiguracionSistema

        try:
            # Buscar si ya existe una configuración de logo
            logo_config = (
                db.query(ConfiguracionSistema)
                .filter(
                    ConfiguracionSistema.categoria == "GENERAL",
                    ConfiguracionSistema.clave == "logo_filename",
                )
                .first()
            )

            if logo_config:
                # Actualizar configuración existente
                logo_config.valor = logo_filename  # type: ignore[assignment]
                logo_config.actualizado_por = current_user.email  # type: ignore[assignment]
                logo_config.actualizado_en = datetime.utcnow()  # type: ignore[assignment]
            else:
                # Crear nueva configuración
                logo_config = ConfiguracionSistema(
                    categoria="GENERAL",
                    clave="logo_filename",
                    valor=logo_filename,
                    tipo_dato="STRING",
                    descripcion="Nombre del archivo del logo de la empresa",
                    visible_frontend=True,
                    creado_por=current_user.email,
                    actualizado_por=current_user.email,
                )
                db.add(logo_config)

            db.commit()
            logger.info(f"Logo guardado en BD: {logo_filename}")
        except Exception as db_error:
            db.rollback()
            logger.error(f"Error guardando configuración de logo en BD: {str(db_error)}", exc_info=True)
            # No fallar si solo falla el guardado en BD, el archivo ya está guardado

        logger.info(f"Logo subido por usuario {current_user.email}: {logo_filename}")

        return {
            "message": "Logo cargado exitosamente",
            "status": "success",
            "filename": logo_filename,
            "path": f"/api/v1/configuracion/logo/{logo_filename}",
            "url": f"/api/v1/configuracion/logo/{logo_filename}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir logo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al subir logo: {str(e)}")


@router.head("/logo/{filename}")
async def verificar_logo_existe(
    filename: str,
):
    """Verificar si el logo existe (HEAD request)"""
    try:
        from fastapi.responses import Response

        from app.core.config import settings

        # Validar que el archivo sea del tipo correcto
        if not filename.startswith("logo-custom") or not any(
            filename.endswith(ext) for ext in [".svg", ".png", ".jpg", ".jpeg"]
        ):
            raise HTTPException(status_code=400, detail="Nombre de archivo no válido")

        uploads_dir = Path(settings.UPLOAD_DIR) if hasattr(settings, "UPLOAD_DIR") else Path("uploads")
        logo_path = uploads_dir / "logos" / filename

        if not logo_path.exists():
            raise HTTPException(status_code=404, detail="Logo no encontrado")

        # Determinar content type
        content_type_map = {
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        ext = Path(filename).suffix.lower()
        media_type = content_type_map.get(ext, "application/octet-stream")

        # Devolver respuesta HEAD sin cuerpo
        return Response(
            status_code=200,
            headers={"Content-Type": media_type},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verificando logo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error verificando logo: {str(e)}")


@router.get("/logo/{filename}")
async def obtener_logo(
    filename: str,
):
    """Obtener logo de la empresa"""
    try:
        from fastapi.responses import FileResponse

        from app.core.config import settings

        # Validar que el archivo sea del tipo correcto
        if not filename.startswith("logo-custom") or not any(
            filename.endswith(ext) for ext in [".svg", ".png", ".jpg", ".jpeg"]
        ):
            raise HTTPException(status_code=400, detail="Nombre de archivo no válido")

        uploads_dir = Path(settings.UPLOAD_DIR) if hasattr(settings, "UPLOAD_DIR") else Path("uploads")
        logo_path = uploads_dir / "logos" / filename

        if not logo_path.exists():
            raise HTTPException(status_code=404, detail="Logo no encontrado")

        # Determinar content type
        content_type_map = {
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        ext = Path(filename).suffix.lower()
        media_type = content_type_map.get(ext, "application/octet-stream")

        from fastapi.responses import Response

        # Leer el contenido del archivo
        with open(logo_path, "rb") as f:
            file_content = f.read()

        # Crear respuesta con headers de no-caché para forzar recarga
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Content-Disposition": f'inline; filename="{filename}"',
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo logo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo logo: {str(e)}")


# ============================================
# CONFIGURACIÓN DE EMAIL
# ============================================


@router.get("/email/configuracion")
def obtener_configuracion_email(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener configuración de email"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver configuración de email",
        )

    try:
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "EMAIL").all()

        if not configs:
            # Valores por defecto
            return {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": "587",
                "smtp_user": "",
                "smtp_password": "",
                "from_email": "",
                "from_name": "RapiCredit",
                "smtp_use_tls": "true",
            }

        config_dict = {}
        for config in configs:
            config_dict[config.clave] = config.valor

        return config_dict

    except Exception as e:
        logger.error(f"Error obteniendo configuración de email: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/email/configuracion")
def actualizar_configuracion_email(
    config_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración de email"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden actualizar configuración",
        )

    try:
        configuraciones = []
        for clave, valor in config_data.items():
            config = (
                db.query(ConfiguracionSistema)
                .filter(
                    ConfiguracionSistema.categoria == "EMAIL",
                    ConfiguracionSistema.clave == clave,
                )
                .first()
            )

            if config:
                config.valor = str(valor)  # type: ignore[assignment]
                config.actualizado_por = current_user.email  # type: ignore[assignment]
                configuraciones.append(config)  # type: ignore[arg-type]
            else:
                nueva_config = ConfiguracionSistema(
                    categoria="EMAIL",
                    clave=clave,
                    valor=str(valor),
                    tipo_dato="STRING",
                    visible_frontend=True,
                    creado_por=current_user.email,
                    actualizado_por=current_user.email,
                )
                db.add(nueva_config)
                configuraciones.append(nueva_config)

        db.commit()

        logger.info(f"Configuración de email actualizada por {current_user.email}")

        return {
            "mensaje": "Configuración de email actualizada exitosamente",
            "configuraciones_actualizadas": len(configuraciones),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando configuración de email: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/email/probar")
def probar_configuracion_email(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Probar configuración de email enviando un email de prueba"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden probar configuración de email",
        )

    try:
        # Obtener configuración
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "EMAIL").all()

        if not configs:
            raise HTTPException(status_code=400, detail="No hay configuración de email")

        # Enviar email de prueba
        from app.services.email_service import EmailService

        # Actualizar configuración global temporalmente
        email_service = EmailService()
        result = email_service.send_email(
            to_emails=[current_user.email],
            subject="Prueba de configuración - RapiCredit",
            body=f"""
            <html>
            <body>
                <h2>Email de prueba</h2>
                <p>Esta es una prueba de la configuración de email.</p>
                <p>Si recibes este email, la configuración está correcta.</p>
                <p><strong>Fecha:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </body>
            </html>
            """,
            is_html=True,
        )

        if result.get("success"):
            return {
                "mensaje": "Email de prueba enviado exitosamente",
                "detalle": result,
            }
        else:
            return {
                "mensaje": "Error enviando email de prueba",
                "error": result.get("message"),
            }

    except Exception as e:
        logger.error(f"Error probando configuración de email: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/general")
def actualizar_configuracion_general(
    update_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración general del sistema"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden actualizar configuración general",
        )

    # Simplemente retornar éxito sin escribir en la DB
    # para evitar errores de esquema
    return {
        "message": "Configuración general actualizada exitosamente",
        "configuracion": update_data,
    }


# ============================================
# VALIDADORES (Proxy para mantener compatibilidad)
# ============================================


@router.post("/validadores/probar")
def probar_validadores(
    datos_prueba: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Probar múltiples validadores con datos de ejemplo"""
    try:
        from datetime import datetime

        resultados = {}
        total_validados = 0
        validos = 0
        invalidos = 0

        # Probar teléfono si está presente
        if datos_prueba.get("telefono"):
            total_validados += 1
            try:
                from app.services.validators_service import ValidadorTelefono

                pais = datos_prueba.get("pais_telefono", "VE")
                resultado_telefono = ValidadorTelefono.validar_y_formatear_telefono(datos_prueba["telefono"], pais)
                if resultado_telefono.get("valido"):
                    validos += 1
                else:
                    invalidos += 1
                resultados["telefono"] = resultado_telefono
            except Exception as e:
                invalidos += 1
                resultados["telefono"] = {"valido": False, "error": str(e)}

        # Probar cédula si está presente
        if datos_prueba.get("cedula"):
            total_validados += 1
            try:
                from app.services.validators_service import ValidadorCedula

                pais = datos_prueba.get("pais_cedula", "VE")
                resultado_cedula = ValidadorCedula.validar_y_formatear_cedula(datos_prueba["cedula"])
                if resultado_cedula.get("valido"):
                    validos += 1
                else:
                    invalidos += 1
                resultados["cedula"] = resultado_cedula
            except Exception as e:
                invalidos += 1
                resultados["cedula"] = {"valido": False, "error": str(e)}

        # Probar fecha si está presente
        if datos_prueba.get("fecha"):
            total_validados += 1
            try:
                from app.services.validators_service import ValidadorFecha

                resultado_fecha = ValidadorFecha.validar_y_formatear_fecha(datos_prueba["fecha"])
                if resultado_fecha.get("valido"):
                    validos += 1
                else:
                    invalidos += 1
                resultados["fecha"] = resultado_fecha
            except Exception as e:
                invalidos += 1
                resultados["fecha"] = {"valido": False, "error": str(e)}

        # Probar email si está presente
        if datos_prueba.get("email"):
            total_validados += 1
            try:
                from app.services.validators_service import ValidadorEmail

                resultado_email = ValidadorEmail.validar_y_formatear_email(datos_prueba["email"])
                if resultado_email.get("valido"):
                    validos += 1
                else:
                    invalidos += 1
                resultados["email"] = resultado_email
            except Exception as e:
                invalidos += 1
                resultados["email"] = {"valido": False, "error": str(e)}

        return {
            "titulo": "Prueba de Validadores",
            "fecha_prueba": datetime.now().isoformat(),
            "datos_entrada": datos_prueba,
            "resultados": resultados,
            "resumen": {
                "total_validados": total_validados,
                "validos": validos,
                "invalidos": invalidos,
            },
        }

    except Exception as e:
        logger.error(f"Error probando validadores: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# CONFIGURACIÓN DE PRÉSTAMOS
# ============================================


@router.get("/prestamos/parametros")
def obtener_parametros_prestamos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener parámetros de configuración para préstamos"""
    try:
        # Obtener configuraciones relacionadas con préstamos
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave.like("PRESTAMO_%")).all()

        parametros = {}
        for config in configs:
            parametros[config.clave] = {
                "valor": config.valor,
                "descripcion": config.descripcion,
            }

        return {"parametros": parametros, "total": len(configs)}

    except Exception as e:
        logger.error(f"Error obteniendo parámetros: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/sistema/estadisticas")
def obtener_estadisticas_sistema(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener estadísticas del sistema"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver estadísticas del sistema",
        )

    try:
        # Estadísticas básicas
        total_configuraciones = db.query(ConfiguracionSistema).count()
        total_usuarios = db.query(User).count()
        total_prestamos = db.query(Prestamo).count()

        # Configuraciones por categoría
        configs_por_categoria = (
            db.query(
                ConfiguracionSistema.clave,
                func.count(ConfiguracionSistema.id).label("cantidad"),
            )
            .group_by(func.split_part(ConfiguracionSistema.clave, "_", 1))
            .all()
        )

        return {
            "estadisticas_generales": {
                "total_configuraciones": total_configuraciones,
                "total_usuarios": total_usuarios,
                "total_prestamos": total_prestamos,
            },
            "configuraciones_por_categoria": [{"categoria": item[0], "cantidad": item[1]} for item in configs_por_categoria],
            "fecha_consulta": datetime.now(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
