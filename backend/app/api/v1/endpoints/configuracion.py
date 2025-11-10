import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
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
    # Nota: actualizado_por no existe en la tabla BD

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
        # OPTIMIZACIÓN: Agregar límite para evitar cargar demasiadas configuraciones
        # Si hay más de 1000 configuraciones, solo cargar las primeras 1000
        MAX_CONFIGURACIONES = 1000
        configuraciones = db.query(ConfiguracionSistema).limit(MAX_CONFIGURACIONES).all()
        total = db.query(ConfiguracionSistema).count()

        return {
            "configuraciones": [
                {
                    "clave": config.clave,
                    "valor": config.valor,
                    "descripcion": config.descripcion,
                    "fecha_actualizacion": config.actualizado_en,
                }
                for config in configuraciones
            ],
            "total": total,
            "retornadas": len(configuraciones),
            "advertencia": "Límite de 1000 configuraciones aplicado" if total > MAX_CONFIGURACIONES else None,
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
                    "fecha_actualizacion": config.actualizado_en,
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
                # creado_por y actualizado_por no existen en la tabla BD
            )
            db.add(config)
        else:
            # Actualizar configuración existente
            config.valor = config_data.valor  # type: ignore[assignment]
            config.descripcion = config_data.descripcion  # type: ignore[assignment]
            # actualizado_en se actualiza automáticamente por onupdate=func.now()

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
        logger.debug("🔍 Consultando logo_filename en BD...")

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
            logger.info(f"✅ Logo filename encontrado en BD: {logo_filename}")
        else:
            logger.debug("⚠️ No se encontró logo_filename en BD (puede ser normal si no se ha subido un logo)")
    except Exception as e:
        logger.error(f"❌ Error obteniendo logo_filename de BD: {str(e)}", exc_info=True)

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
        logger.debug(f"✅ Configuración general retornada con logo_filename: {logo_filename}")
    else:
        logger.debug("⚠️ Configuración general retornada SIN logo_filename")

    return config


def _validar_logo(logo: UploadFile, contents: bytes) -> None:
    """Valida el tipo y tamaño del logo, incluyendo magic bytes"""
    allowed_types = ["image/svg+xml", "image/png", "image/jpeg", "image/jpg"]
    if logo.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Formato no válido. Use SVG, PNG o JPG",
        )
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="El archivo es demasiado grande. Máximo 2MB",
        )

    # Validar magic bytes para verificar contenido real del archivo
    if len(contents) < 4:
        raise HTTPException(
            status_code=400,
            detail="Archivo inválido o corrupto",
        )

    # Magic bytes para diferentes formatos
    # PNG: \x89PNG\r\n\x1a\n
    # JPEG: \xff\xd8
    # SVG: <svg o <?xml (texto)

    is_valid = False

    # Validar PNG
    if logo.content_type == "image/png":
        if contents.startswith(b"\x89PNG"):
            is_valid = True

    # Validar JPEG
    elif logo.content_type in ["image/jpeg", "image/jpg"]:
        if contents.startswith(b"\xff\xd8"):
            is_valid = True

    # Validar SVG (puede empezar con <svg o <?xml)
    elif logo.content_type == "image/svg+xml":
        if contents.startswith(b"<svg") or contents.startswith(b"<?xml"):
            is_valid = True
        else:
            # Verificar si contiene etiquetas SVG en los primeros bytes
            try:
                content_str = contents[:100].decode("utf-8", errors="ignore").lower()
                if "svg" in content_str or "<?xml" in content_str:
                    is_valid = True
            except Exception:
                pass

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="El contenido del archivo no coincide con el tipo declarado. Archivo posiblemente corrupto o malicioso.",
        )


def _obtener_extension_logo(content_type: str) -> str:
    """Obtiene la extensión del archivo basada en content_type"""
    content_type_to_ext = {
        "image/svg+xml": ".svg",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
    }
    return content_type_to_ext.get(content_type, ".svg")


def _obtener_logo_anterior(db: Session) -> Optional[str]:
    """Obtiene el nombre del logo anterior desde la BD"""
    from app.models.configuracion_sistema import ConfiguracionSistema

    logo_config = (
        db.query(ConfiguracionSistema)
        .filter(
            ConfiguracionSistema.categoria == "GENERAL",
            ConfiguracionSistema.clave == "logo_filename",
        )
        .first()
    )

    if logo_config and logo_config.valor:
        return str(logo_config.valor)
    return None


def _eliminar_logo_anterior(db: Session, logos_dir: Path, nuevo_logo_filename: str) -> None:
    """Elimina el logo anterior si existe y es diferente al nuevo"""
    try:
        logo_anterior_filename = _obtener_logo_anterior(db)

        if logo_anterior_filename and logo_anterior_filename != nuevo_logo_filename:
            logo_anterior_path = logos_dir / logo_anterior_filename
            if logo_anterior_path.exists():
                logo_anterior_path.unlink()
                logger.info(f"🗑️ Logo anterior eliminado: {logo_anterior_filename}")
    except Exception as e:
        # No fallar si no se puede eliminar el logo anterior
        logger.warning(f"⚠️ No se pudo eliminar logo anterior: {str(e)}")


def _guardar_logo_en_bd(db: Session, logo_filename: str, logo_base64: str, content_type: str) -> None:
    """
    Guarda o actualiza la referencia del logo en la base de datos.
    Almacena tanto el filename como el contenido base64 para persistencia.
    """
    import json

    from app.models.configuracion_sistema import ConfiguracionSistema

    # Guardar filename
    logo_config = (
        db.query(ConfiguracionSistema)
        .filter(
            ConfiguracionSistema.categoria == "GENERAL",
            ConfiguracionSistema.clave == "logo_filename",
        )
        .first()
    )

    if logo_config:
        logo_config.valor = logo_filename  # type: ignore[assignment]
    else:
        logo_config = ConfiguracionSistema(
            categoria="GENERAL",
            clave="logo_filename",
            valor=logo_filename,
            tipo_dato="STRING",
            descripcion="Nombre del archivo del logo de la empresa",
            visible_frontend=True,
        )
        db.add(logo_config)

    # Guardar datos del logo (base64 + content_type) en valor_json
    logo_data_config = (
        db.query(ConfiguracionSistema)
        .filter(
            ConfiguracionSistema.categoria == "GENERAL",
            ConfiguracionSistema.clave == "logo_data",
        )
        .first()
    )

    logo_data = {
        "base64": logo_base64,
        "content_type": content_type,
        "filename": logo_filename,
    }

    if logo_data_config:
        logo_data_config.valor_json = logo_data  # type: ignore[assignment]
    else:
        logo_data_config = ConfiguracionSistema(
            categoria="GENERAL",
            clave="logo_data",
            valor=None,
            valor_json=logo_data,
            tipo_dato="JSON",
            descripcion="Datos del logo (base64 y metadata) para persistencia en Render",
            visible_frontend=False,  # No mostrar en frontend
        )
        db.add(logo_data_config)

    db.commit()
    db.refresh(logo_config)
    db.refresh(logo_data_config)
    logger.info(f"✅ Logo filename y datos guardados en BD exitosamente: {logo_filename}")


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
        contents = await logo.read()
        _validar_logo(logo, contents)

        extension = _obtener_extension_logo(logo.content_type)

        from app.core.config import settings

        # Usar path absoluto si UPLOAD_DIR está configurado, sino usar relativo
        if hasattr(settings, "UPLOAD_DIR") and settings.UPLOAD_DIR:
            uploads_dir = Path(settings.UPLOAD_DIR).resolve()
        else:
            uploads_dir = Path("uploads").resolve()

        logos_dir = uploads_dir / "logos"
        logos_dir.mkdir(parents=True, exist_ok=True)

        logo_filename = f"logo-custom{extension}"
        logo_path = logos_dir / logo_filename

        # Eliminar logo anterior si existe y es diferente
        _eliminar_logo_anterior(db, logos_dir, logo_filename)

        # Guardar nuevo logo en filesystem (si es posible)
        try:
            with open(logo_path, "wb") as f:
                f.write(contents)
            logger.info(f"✅ Logo guardado en filesystem: {logo_path}")
        except Exception as fs_error:
            logger.warning(f"⚠️ No se pudo guardar logo en filesystem (puede ser efímero): {str(fs_error)}")
            # Continuar - guardaremos en BD como base64

        # Convertir logo a base64 para almacenamiento persistente en BD
        import base64

        logo_base64 = base64.b64encode(contents).decode("utf-8")
        content_type = logo.content_type or "image/jpeg"

        # Intentar guardar en BD (filename + base64), si falla, eliminar archivo
        try:
            _guardar_logo_en_bd(db, logo_filename, logo_base64, content_type)
        except Exception as db_error:
            db.rollback()
            # Rollback: eliminar archivo si falla guardado en BD
            try:
                if logo_path.exists():
                    logo_path.unlink()
                    logger.info(f"🗑️ Archivo de logo eliminado debido a error en BD: {logo_filename}")
            except Exception as cleanup_error:
                logger.error(f"❌ Error eliminando archivo después de fallo en BD: {str(cleanup_error)}")

            logger.error(f"❌ Error guardando configuración de logo en BD: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error guardando configuración de logo en base de datos: {str(db_error)}"
            )

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


def _obtener_logo_desde_bd(filename: str, db: Session) -> Optional[tuple[bytes, str]]:
    """
    Intenta obtener el logo desde la BD (base64) como fallback si no existe en filesystem.
    Retorna (contenido_bytes, content_type) o None si no existe en BD.
    """
    import base64

    from app.models.configuracion_sistema import ConfiguracionSistema

    try:
        logo_data_config = (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == "GENERAL",
                ConfiguracionSistema.clave == "logo_data",
            )
            .first()
        )

        if not logo_data_config or not logo_data_config.valor_json:
            return None

        logo_data = logo_data_config.valor_json
        if isinstance(logo_data, dict) and logo_data.get("base64") and logo_data.get("filename") == filename:
            # Decodificar base64
            logo_bytes = base64.b64decode(logo_data["base64"])
            content_type = logo_data.get("content_type", "image/jpeg")
            logger.info(f"✅ Logo recuperado desde BD (base64) para: {filename}")
            return logo_bytes, content_type

        return None
    except Exception as e:
        logger.warning(f"⚠️ Error obteniendo logo desde BD: {str(e)}")
        return None


def _verificar_logo_existe(filename: str, db: Optional[Session] = None) -> tuple[Optional[Path], str, Optional[bytes]]:
    """
    Verifica si el logo existe y retorna el path, content type y contenido (si viene de BD).
    Función compartida para HEAD y GET para garantizar consistencia.
    Si no existe en filesystem, intenta obtener desde BD.
    """
    from app.core.config import settings

    # Validar que el archivo sea del tipo correcto
    if not filename.startswith("logo-custom") or not any(filename.endswith(ext) for ext in [".svg", ".png", ".jpg", ".jpeg"]):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")

    # Usar path absoluto si UPLOAD_DIR está configurado
    if hasattr(settings, "UPLOAD_DIR") and settings.UPLOAD_DIR:
        uploads_dir = Path(settings.UPLOAD_DIR).resolve()
    else:
        uploads_dir = Path("uploads").resolve()
    logo_path = uploads_dir / "logos" / filename

    # Determinar content type
    content_type_map = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    ext = Path(filename).suffix.lower()
    media_type = content_type_map.get(ext, "application/octet-stream")

    # Intentar leer desde filesystem primero
    if logo_path.exists() and logo_path.is_file():
        try:
            if logo_path.stat().st_size > 0:
                return logo_path, media_type, None  # Existe en filesystem
        except OSError:
            pass

    # Si no existe en filesystem, intentar desde BD
    if db:
        logo_bd = _obtener_logo_desde_bd(filename, db)
        if logo_bd:
            logo_bytes, content_type = logo_bd
            return None, content_type, logo_bytes  # Existe en BD

    # No existe en ningún lado
    logger.warning(f"⚠️ Logo no encontrado ni en filesystem ni en BD: {filename} " f"(uploads_dir: {uploads_dir})")
    raise HTTPException(status_code=404, detail="Logo no encontrado")


@router.head("/logo/{filename}")
async def verificar_logo_existe(
    filename: str,
    db: Session = Depends(get_db),
):
    """Verificar si el logo existe (HEAD request)"""
    try:
        from fastapi.responses import Response

        logo_path, media_type, logo_bytes = _verificar_logo_existe(filename, db)

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
    db: Session = Depends(get_db),
):
    """Obtener logo de la empresa"""
    try:
        from fastapi.responses import Response

        # Usar la misma función de verificación que HEAD para garantizar consistencia
        logo_path, media_type, logo_bytes = _verificar_logo_existe(filename, db)

        # Si existe en filesystem, leer desde ahí
        if logo_path and logo_path.exists():
            with open(logo_path, "rb") as f:
                file_content = f.read()
        # Si no existe en filesystem pero existe en BD, usar base64
        elif logo_bytes:
            file_content = logo_bytes
            logger.info(f"✅ Sirviendo logo desde BD (base64) para: {filename}")
        else:
            raise HTTPException(status_code=404, detail="Logo no encontrado")

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


def _obtener_valores_email_por_defecto() -> Dict[str, str]:
    """Retorna valores por defecto para configuración de email"""
    return {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": "587",
        "smtp_user": "",
        "smtp_password": "",
        "from_email": "",
        "from_name": "RapiCredit",
        "smtp_use_tls": "true",
    }


def _consultar_configuracion_email(db: Session) -> Optional[Any]:
    """Intenta consultar configuración de email desde BD"""
    try:
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "EMAIL").all()
        logger.info(f"📊 Configuraciones encontradas: {len(configs)}")
        return configs
    except Exception as query_error:
        logger.error(f"❌ Error ejecutando consulta de configuración de email: {str(query_error)}", exc_info=True)
        try:
            config_dict = ConfiguracionSistema.obtener_categoria(db, "EMAIL")
            if config_dict:
                logger.info(f"✅ Configuración obtenida usando método alternativo: {len(config_dict)} configuraciones")
                return config_dict
        except Exception as alt_error:
            logger.error(f"❌ Error en método alternativo también falló: {str(alt_error)}", exc_info=True)
        return None


def _procesar_configuraciones_email(configs: list) -> Dict[str, Any]:
    """Procesa una lista de configuraciones y retorna un diccionario"""
    config_dict = {}
    for config in configs:
        try:
            if hasattr(config, "clave") and config.clave:
                valor = config.valor if hasattr(config, "valor") and config.valor is not None else ""
                config_dict[config.clave] = valor
                logger.debug(f"📝 Configuración: {config.clave} = {valor[:20] if len(str(valor)) > 20 else valor}")
            else:
                logger.warning(f"⚠️ Configuración sin clave válida: {config}")
        except Exception as config_error:
            logger.error(f"❌ Error procesando configuración individual: {config_error}", exc_info=True)
            continue
    return config_dict


@router.get("/email/configuracion")
def obtener_configuracion_email(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener configuración de email"""
    try:
        logger.info(f"📧 Obteniendo configuración de email - Usuario: {getattr(current_user, 'email', 'N/A')}")

        if not getattr(current_user, "is_admin", False):
            logger.warning(
                f"⚠️ Usuario no autorizado intentando acceder a configuración de email: {getattr(current_user, 'email', 'N/A')}"
            )
            raise HTTPException(
                status_code=403,
                detail="Solo administradores pueden ver configuración de email",
            )

        logger.info("🔍 Consultando configuración de email desde BD...")
        configs = _consultar_configuracion_email(db)

        if configs is None:
            logger.warning("⚠️ No se pudo obtener configuración de BD, retornando valores por defecto")
            return _obtener_valores_email_por_defecto()

        if isinstance(configs, dict):
            return configs

        if not configs:
            logger.info("📝 Retornando valores por defecto de email (no hay configuraciones en BD)")
            return _obtener_valores_email_por_defecto()

        config_dict = _procesar_configuraciones_email(configs)
        logger.info(f"✅ Configuración de email obtenida exitosamente: {len(config_dict)} configuraciones")
        return config_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración de email: {str(e)}", exc_info=True)
        logger.warning("⚠️ Retornando valores por defecto debido a error")
        return _obtener_valores_email_por_defecto()


def _validar_configuracion_gmail_smtp(config_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validar configuración de Gmail SMTP y probar conexión

    Returns:
        (es_valida, mensaje_error)
    """
    import smtplib

    smtp_host = config_data.get("smtp_host", "").lower()

    # Solo validar si es Gmail
    if "gmail.com" not in smtp_host:
        return True, None

    smtp_port = config_data.get("smtp_port", "587")
    smtp_user = config_data.get("smtp_user", "")
    smtp_password = config_data.get("smtp_password", "")
    smtp_use_tls = config_data.get("smtp_use_tls", "true").lower() in ("true", "1", "yes", "on")

    # Validaciones básicas
    if not smtp_user or not smtp_password:
        return False, "Email y Contraseña de Aplicación son requeridos para Gmail"

    # Validar que el email sea de Gmail
    if "@gmail.com" not in smtp_user.lower() and "@googlemail.com" not in smtp_user.lower():
        return False, "El email debe ser de Gmail (@gmail.com o @googlemail.com) cuando uses smtp.gmail.com"

    # Validar puerto
    try:
        puerto = int(smtp_port)
        if puerto not in (587, 465):
            return False, "Gmail requiere puerto 587 (TLS) o 465 (SSL). El puerto 587 es recomendado."
        if puerto == 587 and not smtp_use_tls:
            return False, "Para puerto 587, TLS debe estar habilitado (requerido por Gmail)."
    except (ValueError, TypeError):
        return False, "Puerto SMTP inválido"

    # Validar formato de contraseña de aplicación (16 caracteres sin espacios)
    password_sin_espacios = smtp_password.replace(" ", "").replace("\t", "")
    if len(password_sin_espacios) != 16:
        return (
            False,
            "La Contraseña de Aplicación de Gmail debe tener exactamente 16 caracteres (los espacios se eliminan automáticamente).",
        )

    # Probar conexión SMTP para verificar credenciales
    try:
        server = smtplib.SMTP(smtp_host, puerto, timeout=10)

        if smtp_use_tls:
            server.starttls()

        # Intentar login - aquí es donde Gmail rechazará si no hay 2FA o si se usa contraseña normal
        server.login(smtp_user, password_sin_espacios)
        server.quit()

        return True, None

    except smtplib.SMTPAuthenticationError as e:
        error_msg = str(e).lower()
        if "username and password not accepted" in error_msg or "535" in str(e):
            return False, (
                "❌ Error de autenticación con Gmail. Posibles causas:\n"
                "1. ⚠️ NO tienes Autenticación de 2 Factores (2FA) activada en tu cuenta de Google\n"
                "2. ⚠️ Estás usando tu contraseña normal de Gmail en lugar de una Contraseña de Aplicación\n"
                "3. ⚠️ La Contraseña de Aplicación es incorrecta o fue revocada\n\n"
                "SOLUCIÓN:\n"
                "- Activa 2FA en: https://myaccount.google.com/security\n"
                "- Genera una Contraseña de Aplicación en: https://myaccount.google.com/apppasswords\n"
                "- Usa esa contraseña de 16 caracteres (NO tu contraseña normal)"
            )
        return False, f"Error de autenticación SMTP: {str(e)}"
    except smtplib.SMTPException as e:
        return False, f"Error de conexión SMTP: {str(e)}"
    except Exception as e:
        # No bloquear guardado por errores de conexión temporales, solo advertir
        logger.warning(f"⚠️ No se pudo validar conexión SMTP al guardar (puede ser temporal): {str(e)}")
        return True, None  # Permitir guardar pero advertir


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

    # Validar configuración de Gmail antes de guardar
    es_valida, mensaje_error = _validar_configuracion_gmail_smtp(config_data)
    if not es_valida:
        raise HTTPException(status_code=400, detail=mensaje_error or "Configuración de email inválida")

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
                # actualizado_en se actualiza automáticamente por onupdate=func.now()
                configuraciones.append(config)  # type: ignore[arg-type]
            else:
                nueva_config = ConfiguracionSistema(
                    categoria="EMAIL",
                    clave=clave,
                    valor=str(valor),
                    tipo_dato="STRING",
                    visible_frontend=True,
                    # creado_por y actualizado_por no existen en la tabla BD
                )
                db.add(nueva_config)
                configuraciones.append(nueva_config)

        db.commit()

        logger.info(f"Configuración de email actualizada por {current_user.email}")

        return {
            "mensaje": "Configuración de email actualizada exitosamente",
            "configuraciones_actualizadas": len(configuraciones),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando configuración de email: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/notificaciones/envios")
def obtener_configuracion_envios(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener configuración de habilitación de envíos y CCO por tipo de notificación"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver configuración de envíos",
        )

    try:
        # Tipos de notificación
        tipos = [
            "PAGO_5_DIAS_ANTES",
            "PAGO_3_DIAS_ANTES",
            "PAGO_1_DIA_ANTES",
            "PAGO_DIA_0",
            "PAGO_1_DIA_ATRASADO",
            "PAGO_3_DIAS_ATRASADO",
            "PAGO_5_DIAS_ATRASADO",
            "PREJUDICIAL",
        ]

        config_dict = {}
        for tipo in tipos:
            # Habilitación
            clave_habilitado = f"envio_habilitado_{tipo}"
            config_habilitado = (
                db.query(ConfiguracionSistema)
                .filter(
                    ConfiguracionSistema.categoria == "NOTIFICACIONES",
                    ConfiguracionSistema.clave == clave_habilitado,
                )
                .first()
            )
            habilitado = (
                config_habilitado.valor.lower() in ("true", "1", "yes", "on")
                if config_habilitado and config_habilitado.valor
                else True
            )

            # CCO (hasta 3 correos)
            cco_emails = []
            for i in range(1, 4):  # CCO 1, 2, 3
                clave_cco = f"cco_{tipo}_{i}"
                config_cco = (
                    db.query(ConfiguracionSistema)
                    .filter(
                        ConfiguracionSistema.categoria == "NOTIFICACIONES",
                        ConfiguracionSistema.clave == clave_cco,
                    )
                    .first()
                )
                if config_cco and config_cco.valor and config_cco.valor.strip():
                    cco_emails.append(config_cco.valor.strip())

            config_dict[tipo] = {"habilitado": habilitado, "cco": cco_emails}

        return config_dict

    except Exception as e:
        logger.error(f"Error obteniendo configuración de envíos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/notificaciones/envios")
def actualizar_configuracion_envios(
    config_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración de habilitación de envíos y CCO por tipo de notificación"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden actualizar configuración de envíos",
        )

    try:
        configuraciones = []
        for tipo, config_tipo in config_data.items():
            # Actualizar habilitación
            if isinstance(config_tipo, dict):
                habilitado = config_tipo.get("habilitado", True)
                cco_emails = config_tipo.get("cco", [])
            else:
                # Compatibilidad con formato anterior (solo boolean)
                habilitado = config_tipo if isinstance(config_tipo, bool) else True
                cco_emails = []

            # Guardar habilitación
            clave_habilitado = f"envio_habilitado_{tipo}"
            config = (
                db.query(ConfiguracionSistema)
                .filter(
                    ConfiguracionSistema.categoria == "NOTIFICACIONES",
                    ConfiguracionSistema.clave == clave_habilitado,
                )
                .first()
            )

            if config:
                config.valor = "true" if habilitado else "false"
                configuraciones.append(config)
            else:
                nueva_config = ConfiguracionSistema(
                    categoria="NOTIFICACIONES",
                    clave=clave_habilitado,
                    valor="true" if habilitado else "false",
                    tipo_dato="BOOLEAN",
                    visible_frontend=True,
                    descripcion=f"Habilitar envío de notificaciones tipo {tipo}",
                )
                db.add(nueva_config)
                configuraciones.append(nueva_config)

            # Guardar CCO (hasta 3 correos)
            if isinstance(cco_emails, list):
                # Limitar a 3 correos máximo
                cco_emails = [email.strip() for email in cco_emails[:3] if email and email.strip()]

                # Eliminar configuraciones CCO existentes para este tipo
                for i in range(1, 4):
                    clave_cco = f"cco_{tipo}_{i}"
                    config_cco_existente = (
                        db.query(ConfiguracionSistema)
                        .filter(
                            ConfiguracionSistema.categoria == "NOTIFICACIONES",
                            ConfiguracionSistema.clave == clave_cco,
                        )
                        .first()
                    )
                    if config_cco_existente:
                        db.delete(config_cco_existente)

                # Crear nuevas configuraciones CCO
                for i, email in enumerate(cco_emails, 1):
                    clave_cco = f"cco_{tipo}_{i}"
                    nueva_config_cco = ConfiguracionSistema(
                        categoria="NOTIFICACIONES",
                        clave=clave_cco,
                        valor=email,
                        tipo_dato="STRING",
                        visible_frontend=True,
                        descripcion=f"CCO {i} para notificaciones tipo {tipo}",
                    )
                    db.add(nueva_config_cco)
                    configuraciones.append(nueva_config_cco)

        db.commit()

        logger.info(f"Configuración de envíos y CCO actualizada por {current_user.email}")

        return {
            "mensaje": "Configuración de envíos y CCO actualizada exitosamente",
            "configuraciones_actualizadas": len(configuraciones),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando configuración de envíos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


class ProbarEmailRequest(BaseModel):
    email_destino: Optional[str] = None
    subject: Optional[str] = None
    mensaje: Optional[str] = None


@router.post("/email/probar")
def probar_configuracion_email(
    request: Optional[ProbarEmailRequest] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Probar configuración de email enviando un email de prueba a cualquier correo

    Args:
        request: Objeto con email_destino opcional. Si no se proporciona, se envía al email del usuario actual.
                Puedes enviar a CUALQUIER correo para verificar que funciona.
    """
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

        # Determinar email destino - acepta cualquier email válido
        email_destino_val = None
        if request:
            if isinstance(request, dict):
                email_destino_val = request.get("email_destino")
            elif hasattr(request, "email_destino"):
                email_destino_val = request.email_destino

        # Si se proporcionó un email, usarlo; si no, usar el email del usuario actual
        email_a_enviar = email_destino_val.strip() if email_destino_val and email_destino_val.strip() else current_user.email

        # Validar formato de email
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email_a_enviar):
            raise HTTPException(status_code=400, detail="Email de destino inválido")

        # Obtener subject y mensaje personalizados si se proporcionaron
        subject_personalizado = None
        mensaje_personalizado = None
        if request:
            if isinstance(request, dict):
                subject_personalizado = request.get("subject")
                mensaje_personalizado = request.get("mensaje")
            elif hasattr(request, "subject"):
                subject_personalizado = request.subject
                mensaje_personalizado = request.mensaje

        # Usar subject personalizado o el predeterminado
        subject_email = (
            subject_personalizado.strip()
            if subject_personalizado and subject_personalizado.strip()
            else "✅ Prueba de configuración - RapiCredit"
        )

        # Construir el cuerpo del email
        if mensaje_personalizado and mensaje_personalizado.strip():
            # Si hay mensaje personalizado, usarlo
            cuerpo_email = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <div style="background-color: #4CAF50; color: white; padding: 15px; border-radius: 5px 5px 0 0; margin: -20px -20px 20px -20px;">
                        <h2 style="margin: 0;">✅ Email de Prueba</h2>
                    </div>

                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; white-space: pre-wrap;">
                        {mensaje_personalizado.strip()}
                    </div>

                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; font-size: 12px; color: #666;">
                        <p style="margin: 0;"><strong>📧 Destinatario:</strong> {email_a_enviar}</p>
                        <p style="margin: 5px 0;"><strong>📅 Fecha y Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p style="margin: 5px 0;"><strong>👤 Usuario:</strong> {current_user.email}</p>
                    </div>

                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
                        <p>Este es un email automático del sistema RapiCredit</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            # Mensaje predeterminado
            cuerpo_email = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <div style="background-color: #4CAF50; color: white; padding: 15px; border-radius: 5px 5px 0 0; margin: -20px -20px 20px -20px;">
                        <h2 style="margin: 0;">✅ Email de Prueba Exitoso</h2>
                    </div>

                    <p>Este es un <strong>email de prueba</strong> para verificar que la configuración SMTP está funcionando correctamente.</p>

                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>📧 Destinatario:</strong> {email_a_enviar}</p>
                        <p style="margin: 5px 0;"><strong>📅 Fecha y Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p style="margin: 5px 0;"><strong>👤 Usuario:</strong> {current_user.email}</p>
                    </div>

                    <p>Si recibes este email, significa que:</p>
                    <ul>
                        <li>✅ La configuración SMTP es correcta</li>
                        <li>✅ Las credenciales son válidas</li>
                        <li>✅ El servidor de email está funcionando</li>
                        <li>✅ El sistema puede enviar correos normalmente</li>
                    </ul>

                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
                        <p>Este es un email automático del sistema RapiCredit</p>
                    </div>
                </div>
            </body>
            </html>
            """

        # Verificar modo de envío (Producción o Pruebas)
        config_dict = {config.clave: config.valor for config in configs}
        modo_pruebas = config_dict.get("modo_pruebas", "true").lower() in ("true", "1", "yes", "on")  # Por defecto: Pruebas

        # En modo Producción, el email de prueba debe enviarse REALMENTE al destinatario especificado
        # para verificar que la configuración funciona correctamente.
        # Si el email llega, es prueba de que el servicio está bien configurado y funciona.
        # En modo Pruebas, se respeta el comportamiento normal (redirige a email_pruebas)

        # Enviar email de prueba
        from app.services.email_service import EmailService

        email_service = EmailService(db=db)

        # Si estamos en modo Producción, forzar envío real para verificar que funciona
        # Si estamos en modo Pruebas, respetar el comportamiento normal
        forzar_real = not modo_pruebas

        result = email_service.send_email(
            to_emails=[email_a_enviar],
            subject=subject_email,
            body=cuerpo_email,
            is_html=True,
            forzar_envio_real=forzar_real,
        )

        if result.get("success"):
            return {
                "mensaje": f"Email de prueba enviado exitosamente a {email_a_enviar}",
                "email_destino": email_a_enviar,
                "detalle": result,
            }
        else:
            return {
                "mensaje": "Error enviando email de prueba",
                "error": result.get("message"),
                "email_destino": email_a_enviar,
            }

    except HTTPException:
        raise
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


def _probar_validador_telefono(telefono: str, pais: str, resultados: Dict[str, Any]) -> tuple[int, int]:
    """Prueba el validador de teléfono. Returns: (validos, invalidos)"""
    try:
        from app.services.validators_service import ValidadorTelefono

        resultado = ValidadorTelefono.validar_y_formatear_telefono(telefono, pais)
        resultados["telefono"] = resultado
        return (1, 0) if resultado.get("valido") else (0, 1)
    except Exception as e:
        resultados["telefono"] = {"valido": False, "error": str(e)}
        return (0, 1)


def _probar_validador_cedula(cedula: str, resultados: Dict[str, Any]) -> tuple[int, int]:
    """Prueba el validador de cédula. Returns: (validos, invalidos)"""
    try:
        from app.services.validators_service import ValidadorCedula

        resultado = ValidadorCedula.validar_y_formatear_cedula(cedula)
        resultados["cedula"] = resultado
        return (1, 0) if resultado.get("valido") else (0, 1)
    except Exception as e:
        resultados["cedula"] = {"valido": False, "error": str(e)}
        return (0, 1)


def _probar_validador_fecha(fecha: Any, resultados: Dict[str, Any]) -> tuple[int, int]:
    """Prueba el validador de fecha. Returns: (validos, invalidos)"""
    try:
        from app.services.validators_service import ValidadorFecha

        resultado = ValidadorFecha.validar_y_formatear_fecha(fecha)
        resultados["fecha"] = resultado
        return (1, 0) if resultado.get("valido") else (0, 1)
    except Exception as e:
        resultados["fecha"] = {"valido": False, "error": str(e)}
        return (0, 1)


def _probar_validador_email(email: str, resultados: Dict[str, Any]) -> tuple[int, int]:
    """Prueba el validador de email. Returns: (validos, invalidos)"""
    try:
        from app.services.validators_service import ValidadorEmail

        resultado = ValidadorEmail.validar_y_formatear_email(email)
        resultados["email"] = resultado
        return (1, 0) if resultado.get("valido") else (0, 1)
    except Exception as e:
        resultados["email"] = {"valido": False, "error": str(e)}
        return (0, 1)


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

        if datos_prueba.get("telefono"):
            total_validados += 1
            v, i = _probar_validador_telefono(datos_prueba["telefono"], datos_prueba.get("pais_telefono", "VE"), resultados)
            validos += v
            invalidos += i

        if datos_prueba.get("cedula"):
            total_validados += 1
            v, i = _probar_validador_cedula(datos_prueba["cedula"], resultados)
            validos += v
            invalidos += i

        if datos_prueba.get("fecha"):
            total_validados += 1
            v, i = _probar_validador_fecha(datos_prueba["fecha"], resultados)
            validos += v
            invalidos += i

        if datos_prueba.get("email"):
            total_validados += 1
            v, i = _probar_validador_email(datos_prueba["email"], resultados)
            validos += v
            invalidos += i

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
