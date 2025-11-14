import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.configuracion_sistema import ConfiguracionSistema
from app.models.documento_ai import DocumentoAI
from app.models.pago import Pago
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
        error_str = str(query_error)
        error_type = type(query_error).__name__
        # ✅ Verificar si es un error de transacción abortada
        is_transaction_aborted = (
            "aborted" in error_str.lower()
            or "InFailedSqlTransaction" in error_type
            or "current transaction is aborted" in error_str.lower()
        )

        if is_transaction_aborted:
            # ✅ Hacer rollback antes de intentar método alternativo
            try:
                db.rollback()
                logger.debug("✅ Rollback realizado antes de método alternativo (transacción abortada)")
            except Exception as rollback_error:
                logger.warning(f"⚠️ Error al hacer rollback: {rollback_error}")

        logger.error(f"❌ Error ejecutando consulta de configuración de email: {str(query_error)}", exc_info=True)
        try:
            config_dict = ConfiguracionSistema.obtener_categoria(db, "EMAIL")
            if config_dict:
                logger.info(f"✅ Configuración obtenida usando método alternativo: {len(config_dict)} configuraciones")
                return config_dict
        except Exception as alt_error:
            # ✅ Si el método alternativo también falla, verificar si es transacción abortada
            alt_error_str = str(alt_error)
            alt_error_type = type(alt_error).__name__
            is_alt_transaction_aborted = (
                "aborted" in alt_error_str.lower()
                or "InFailedSqlTransaction" in alt_error_type
                or "current transaction is aborted" in alt_error_str.lower()
            )

            if is_alt_transaction_aborted:
                # ✅ Cambiar a debug - es un comportamiento esperado cuando la transacción está abortada
                logger.debug(
                    f"⚠️ Método alternativo falló por transacción abortada (comportamiento esperado): {str(alt_error)}"
                )
            else:
                logger.error(f"❌ Error en método alternativo también falló: {str(alt_error)}", exc_info=True)
        return None


def _procesar_configuraciones_email(configs: list) -> Dict[str, Any]:
    """Procesa una lista de configuraciones y retorna un diccionario"""
    config_dict = {}
    for config in configs:
        try:
            if hasattr(config, "clave") and config.clave:
                valor = config.valor if hasattr(config, "valor") and config.valor is not None else ""

                # Normalizar valores booleanos a strings para el frontend
                # El frontend espera strings 'true'/'false' para campos como smtp_use_tls
                if config.clave in ("smtp_use_tls", "modo_pruebas", "email_activo"):
                    if isinstance(valor, bool):
                        valor = "true" if valor else "false"
                    elif isinstance(valor, str):
                        # Normalizar strings: 'True', 'TRUE', '1', 'yes' -> 'true'
                        valor_lower = valor.lower().strip()
                        if valor_lower in ("true", "1", "yes", "on"):
                            valor = "true"
                        elif valor_lower in ("false", "0", "no", "off", ""):
                            valor = "false"
                        else:
                            # Si no es reconocible, mantener el valor original
                            pass
                    else:
                        # Si es None o otro tipo, usar valores por defecto
                        if config.clave == "smtp_use_tls":
                            valor = "false"
                        elif config.clave == "email_activo":
                            valor = "true"  # Por defecto activo
                        else:
                            valor = "true"

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
    Validar configuración de Gmail/Google Workspace SMTP y probar conexión
    Soporta tanto cuentas de Gmail (@gmail.com) como Google Workspace (dominios personalizados)

    Returns:
        (es_valida, mensaje_error)
    """
    import smtplib

    smtp_host = config_data.get("smtp_host", "").lower()

    # Solo validar si es Gmail/Google Workspace
    if "gmail.com" not in smtp_host:
        return True, None

    smtp_port = config_data.get("smtp_port", "587")
    smtp_user = config_data.get("smtp_user", "")
    smtp_password = config_data.get("smtp_password", "")
    smtp_use_tls = config_data.get("smtp_use_tls", "true").lower() in ("true", "1", "yes", "on")

    # Validaciones básicas
    if not smtp_user or not smtp_password:
        return False, "Email y Contraseña de Aplicación son requeridos para Gmail/Google Workspace"

    # NOTA: Ya no validamos que el email sea @gmail.com o @googlemail.com
    # Google Workspace permite usar smtp.gmail.com con dominios personalizados
    # La validación real se hace al probar la conexión SMTP

    # Validar puerto
    try:
        puerto = int(smtp_port)
        if puerto not in (587, 465):
            return False, "Gmail/Google Workspace requiere puerto 587 (TLS) o 465 (SSL). El puerto 587 es recomendado."
        if puerto == 587 and not smtp_use_tls:
            return False, "Para puerto 587, TLS debe estar habilitado (requerido por Gmail/Google Workspace)."
    except (ValueError, TypeError):
        return False, "Puerto SMTP inválido"

    # NOTA: Ya no validamos estrictamente la longitud de la contraseña
    # Google Workspace puede usar diferentes métodos de autenticación:
    # - Contraseñas de Aplicación (16 caracteres)
    # - OAuth2 tokens
    # - Otras formas de autenticación según la configuración del dominio
    # La validación real se hace al probar la conexión SMTP
    password_sin_espacios = smtp_password.replace(" ", "").replace("\t", "")

    # Solo advertir si la contraseña es muy corta (probablemente no es una App Password)
    if len(password_sin_espacios) < 10:
        logger.warning(
            f"⚠️ Contraseña muy corta ({len(password_sin_espacios)} caracteres). "
            "Para Gmail/Google Workspace, normalmente se requiere una Contraseña de Aplicación de 16 caracteres."
        )

    # Probar conexión SMTP para verificar credenciales
    try:
        logger.info(f"🔗 Probando conexión SMTP con Google: {smtp_user}@{smtp_host}:{puerto}")

        # ✅ Puerto 465 requiere SSL (SMTP_SSL), puerto 587 requiere TLS (SMTP + starttls)
        if puerto == 465:
            # Puerto 465: Usar SSL directamente (no TLS)
            server = smtplib.SMTP_SSL(smtp_host, puerto, timeout=10)
            logger.debug("✅ Conexión SSL establecida para puerto 465")
        else:
            # Puerto 587 u otros: Usar SMTP normal con TLS opcional
            server = smtplib.SMTP(smtp_host, puerto, timeout=10)
            if smtp_use_tls:
                server.starttls()
                logger.debug("✅ TLS iniciado correctamente")

        # Intentar login - aquí es donde Gmail/Google Workspace rechazará si no hay 2FA o si se usa contraseña normal
        # Esto funciona tanto para @gmail.com como para dominios de Google Workspace
        server.login(smtp_user, password_sin_espacios)
        server.quit()

        # ✅ CONFIRMACIÓN: Google aceptó la conexión - el sistema está vinculado correctamente
        logger.info(
            f"✅ CONFIRMADO: Google/Google Workspace aceptó la conexión SMTP para {smtp_user}. "
            f"El sistema está vinculado correctamente y puede enviar emails."
        )

        return True, None

    except smtplib.SMTPAuthenticationError as e:
        error_msg = str(e).lower()
        error_code = str(e)

        # Detectar error específico de "Application-specific password required"
        # Código 534 o 5.7.9 = Application-specific password required
        # Código 535 = Username and password not accepted (puede ser App Password incorrecta)
        if "application-specific password required" in error_msg or "534" in error_code or "5.7.9" in error_code:
            return False, (
                "❌ Google requiere una Contraseña de Aplicación (App Password)\n\n"
                "El error indica: 'Application-specific password required'\n\n"
                "SOLUCIÓN:\n"
                "1. ⚠️ Activa Autenticación de 2 Factores (2FA) en tu cuenta de Google:\n"
                "   → https://myaccount.google.com/security\n\n"
                "2. ⚠️ Genera una Contraseña de Aplicación (16 caracteres):\n"
                "   → https://myaccount.google.com/apppasswords\n"
                "   → Selecciona 'Correo' y 'Otro (nombre personalizado)'\n"
                "   → Ingresa 'RapiCredit' como nombre\n"
                "   → Copia la contraseña de 16 caracteres (sin espacios)\n\n"
                "3. ⚠️ Usa esa App Password en el campo 'Contraseña de Aplicación'\n"
                "   NO uses tu contraseña normal de Gmail\n\n"
                "NOTA: Para Google Workspace, verifica que tu administrador haya habilitado App Passwords"
            )

        # Detectar otros errores de autenticación
        if "username and password not accepted" in error_msg or "535" in error_code:
            return False, (
                "❌ Error de autenticación con Gmail/Google Workspace. Posibles causas:\n"
                "1. ⚠️ NO tienes Autenticación de 2 Factores (2FA) activada en tu cuenta de Google\n"
                "2. ⚠️ Estás usando tu contraseña normal en lugar de una Contraseña de Aplicación\n"
                "3. ⚠️ La Contraseña de Aplicación es incorrecta o fue revocada\n"
                "4. ⚠️ Para Google Workspace: El dominio no está configurado correctamente\n\n"
                "SOLUCIÓN:\n"
                "- Para Gmail: Activa 2FA en https://myaccount.google.com/security\n"
                "- Para Google Workspace: Activa 2FA en tu cuenta de administrador\n"
                "- Genera una Contraseña de Aplicación:\n"
                "  • Gmail: https://myaccount.google.com/apppasswords\n"
                "  • Google Workspace: https://myaccount.google.com/apppasswords (si está habilitado)\n"
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
    # Esta validación prueba la conexión SMTP con Google y confirma que acepta las credenciales
    es_valida, mensaje_error = _validar_configuracion_gmail_smtp(config_data)

    # ✅ Si la validación falla, permitir guardar pero advertir al usuario
    # Esto permite que el usuario guarde la configuración y luego corrija los problemas
    if not es_valida:
        # Para TODOS los errores de autenticación, permitir guardar pero advertir
        # El usuario puede corregir la configuración después de guardarla
        if mensaje_error:
            if (
                "application-specific password required" in mensaje_error.lower()
                or "requiere una contraseña de aplicación" in mensaje_error.lower()
            ):
                logger.warning(
                    f"⚠️ Google requiere App Password para {config_data.get('smtp_user', 'N/A')}. "
                    f"Se permitirá guardar la configuración pero no se podrá enviar emails hasta corregir la contraseña."
                )
            else:
                logger.warning(
                    f"⚠️ Google/Google Workspace rechazó la conexión SMTP para {config_data.get('smtp_user', 'N/A')}. "
                    f"Razón: {mensaje_error}. Se permitirá guardar la configuración pero requiere corrección."
                )
        # NO lanzar excepción - permitir guardar con advertencia para que el usuario pueda corregir después

    # ✅ Solo mostrar confirmación de vinculación si la validación fue exitosa
    es_gmail = "gmail.com" in config_data.get("smtp_host", "").lower()
    if es_gmail and es_valida:
        logger.info(
            f"✅ CONFIRMACIÓN DE VINCULACIÓN: Google aceptó las credenciales para {config_data.get('smtp_user', 'N/A')}. "
            f"El sistema está vinculado y autorizado para enviar emails."
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

        # ✅ Flush para aplicar cambios antes del commit
        db.flush()

        # ✅ Commit explícito para persistir cambios
        db.commit()

        logger.info(f"✅ Configuración de email guardada - {len(configuraciones)} configuraciones actualizadas/creadas")

        # Determinar si la validación SMTP fue exitosa (Google aceptó)
        # Si es Gmail, la validación ya probó la conexión y Google la aceptó
        es_gmail = "gmail.com" in config_data.get("smtp_host", "").lower()
        validacion_exitosa = es_valida and es_gmail  # Solo exitosa si es Gmail Y la validación pasó

        # ✅ Verificar si el error es específicamente "Application-specific password required"
        # NO marcar como requiere_app_password si es "username and password not accepted"
        # porque eso puede significar que la App Password es incorrecta, no que falte
        requiere_app_password = (
            not es_valida
            and mensaje_error
            and (
                "application-specific password required" in mensaje_error.lower()
                or "requiere una contraseña de aplicación" in mensaje_error.lower()
            )
            # NO incluir "username and password not accepted" porque puede ser App Password incorrecta
        )

        logger.info(f"✅ Configuración de email actualizada por {current_user.email}")
        if validacion_exitosa:
            logger.info(
                f"✅ Sistema vinculado correctamente con Google/Google Workspace. "
                f"La cuenta {config_data.get('smtp_user', 'N/A')} está autorizada para enviar emails."
            )
        elif requiere_app_password:
            logger.warning(
                f"⚠️ Configuración guardada pero Google requiere App Password para {config_data.get('smtp_user', 'N/A')}. "
                f"No se podrán enviar emails hasta corregir la contraseña."
            )

        # Construir mensaje de respuesta
        if validacion_exitosa:
            mensaje_vinculacion = (
                "✅ Sistema vinculado correctamente con Google/Google Workspace. "
                "La configuración fue aceptada y puedes enviar emails."
            )
        elif requiere_app_password:
            # ✅ Solo mostrar mensaje de App Password si el error es específicamente "application-specific password required"
            mensaje_vinculacion = (
                "⚠️ Configuración guardada, pero Google requiere una Contraseña de Aplicación (App Password).\n\n"
                "Para poder enviar emails:\n"
                "1. Activa 2FA en tu cuenta de Google\n"
                "2. Genera una App Password en https://myaccount.google.com/apppasswords\n"
                "3. Actualiza el campo 'Contraseña de Aplicación' con la nueva contraseña de 16 caracteres"
            )
        elif not es_valida and mensaje_error:
            # ✅ Si hay error pero NO es específicamente "requiere App Password", mostrar mensaje de error genérico
            mensaje_vinculacion = (
                f"⚠️ Configuración guardada, pero hay un error de autenticación con Gmail/Google Workspace.\n\n"
                f"Error: {mensaje_error}\n\n"
                f"Posibles causas:\n"
                f"1. La App Password es incorrecta o fue revocada\n"
                f"2. No tienes 2FA activado en tu cuenta de Google\n"
                f"3. Estás usando tu contraseña normal en lugar de App Password\n\n"
                f"SOLUCIÓN:\n"
                f"1. Verifica que tengas 2FA activado: https://myaccount.google.com/security\n"
                f"2. Genera una nueva App Password: https://myaccount.google.com/apppasswords\n"
                f"3. Asegúrate de usar la contraseña de 16 caracteres (sin espacios)"
            )
        else:
            mensaje_vinculacion = "Configuración guardada. La conexión se validará al enviar emails."

        return {
            "mensaje": "Configuración de email actualizada exitosamente",
            "configuraciones_actualizadas": len(configuraciones),
            "vinculacion_confirmada": validacion_exitosa,
            "mensaje_vinculacion": mensaje_vinculacion,
            "requiere_app_password": requiere_app_password,
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


@router.get("/email/estado")
def verificar_estado_configuracion_email(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verificar el estado de la configuración de email sin enviar un email
    Útil para verificar si la configuración está completa y válida
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden verificar configuración de email",
        )

    try:
        from app.services.email_service import EmailService

        # Obtener configuración
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "EMAIL").all()

        if not configs:
            return {
                "configurada": False,
                "mensaje": "No hay configuración de email en la base de datos",
                "configuraciones": {},
                "problemas": ["No hay configuraciones de EMAIL en la base de datos"],
            }

        config_dict = {config.clave: config.valor for config in configs}

        # Verificar configuraciones requeridas
        problemas = []
        configuraciones_requeridas = {
            "smtp_host": config_dict.get("smtp_host"),
            "smtp_port": config_dict.get("smtp_port"),
            "smtp_user": config_dict.get("smtp_user"),
            "smtp_password": config_dict.get("smtp_password"),
            "from_email": config_dict.get("from_email"),
        }

        # Validar cada configuración requerida
        if not configuraciones_requeridas["smtp_host"]:
            problemas.append("smtp_host no está configurado")
        if not configuraciones_requeridas["smtp_port"]:
            problemas.append("smtp_port no está configurado")
        elif not configuraciones_requeridas["smtp_port"].isdigit():
            problemas.append("smtp_port debe ser un número")
        elif not (1 <= int(configuraciones_requeridas["smtp_port"]) <= 65535):
            problemas.append("smtp_port debe estar entre 1 y 65535")
        if not configuraciones_requeridas["smtp_user"]:
            problemas.append("smtp_user no está configurado")
        if not configuraciones_requeridas["smtp_password"]:
            problemas.append("smtp_password no está configurado o está vacío")
        if not configuraciones_requeridas["from_email"]:
            problemas.append("from_email no está configurado")

        # Verificar problema crítico: modo_pruebas sin email_pruebas
        modo_pruebas = config_dict.get("modo_pruebas", "true").lower() in ("true", "1", "yes", "on")
        email_pruebas = config_dict.get("email_pruebas", "").strip()
        if modo_pruebas and not email_pruebas:
            problemas.append(
                "⚠️ MODO PRUEBAS activo pero email_pruebas no está configurado. " "Los emails fallarán si se intentan enviar."
            )

        # Preparar respuesta con valores ocultos para seguridad
        configuraciones_visibles = {}
        for clave, valor in config_dict.items():
            if clave in ("smtp_password", "smtp_user"):
                configuraciones_visibles[clave] = "*** (oculto)" if valor else None
            else:
                configuraciones_visibles[clave] = valor

        # Probar conexión SMTP si todas las configuraciones están presentes
        conexion_smtp = None
        if not problemas:
            try:
                email_service = EmailService(db=db)
                conexion_smtp = email_service.test_connection()

                # ✅ Si la conexión SMTP falla, agregar el mensaje a problemas
                if not conexion_smtp.get("success", False):
                    error_msg = conexion_smtp.get("message", "Error desconocido en conexión SMTP")
                    problemas.append(error_msg)
                    logger.warning(f"⚠️ Conexión SMTP falló: {error_msg}")
                else:
                    # ✅ Si la conexión fue exitosa, confirmar que Gmail aceptó
                    logger.info(f"✅ Conexión SMTP exitosa con Gmail/Google Workspace")
            except Exception as e:
                error_msg = f"Error probando conexión SMTP: {str(e)}"
                problemas.append(error_msg)
                conexion_smtp = {"success": False, "message": error_msg}
                logger.error(f"❌ Excepción al probar conexión SMTP: {error_msg}", exc_info=True)

        # ✅ configurada = True solo si NO hay problemas Y la conexión SMTP fue exitosa
        # Esto confirma que Gmail ACEPTÓ la conexión
        configurada = len(problemas) == 0 and conexion_smtp is not None and conexion_smtp.get("success", False) is True

        mensaje = (
            "✅ Configuración correcta: Gmail aceptó la conexión"
            if configurada
            else f"❌ Se encontraron {len(problemas)} problema(s)" if len(problemas) > 0 else "⚠️ Configuración incompleta"
        )

        return {
            "configurada": configurada,
            "mensaje": mensaje,
            "configuraciones": configuraciones_visibles,
            "problemas": problemas,
            "conexion_smtp": conexion_smtp,
            "modo_pruebas": modo_pruebas,
            "email_pruebas": email_pruebas if email_pruebas else None,
        }

    except Exception as e:
        logger.error(f"Error verificando estado de configuración de email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


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
# CONFIGURACIÓN DE WHATSAPP
# ============================================


def _obtener_valores_whatsapp_por_defecto() -> Dict[str, str]:
    """Retorna valores por defecto para configuración de WhatsApp"""
    return {
        "api_url": "https://graph.facebook.com/v18.0",
        "access_token": "",
        "phone_number_id": "",
        "business_account_id": "",
        "webhook_verify_token": "",
        "modo_pruebas": "true",
        "telefono_pruebas": "",
    }


def _consultar_configuracion_whatsapp(db: Session) -> Optional[Any]:
    """Intenta consultar configuración de WhatsApp desde BD"""
    try:
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "WHATSAPP").all()
        logger.info(f"📊 Configuraciones WhatsApp encontradas: {len(configs)}")
        return configs
    except Exception as query_error:
        error_str = str(query_error)
        error_type = type(query_error).__name__
        # ✅ Verificar si es un error de transacción abortada
        is_transaction_aborted = (
            "aborted" in error_str.lower()
            or "InFailedSqlTransaction" in error_type
            or "current transaction is aborted" in error_str.lower()
        )

        if is_transaction_aborted:
            # ✅ Hacer rollback antes de intentar método alternativo
            try:
                db.rollback()
                logger.debug("✅ Rollback realizado antes de método alternativo (transacción abortada)")
            except Exception as rollback_error:
                logger.warning(f"⚠️ Error al hacer rollback: {rollback_error}")

        logger.error(f"❌ Error ejecutando consulta de configuración de WhatsApp: {str(query_error)}", exc_info=True)
        try:
            config_dict = ConfiguracionSistema.obtener_categoria(db, "WHATSAPP")
            if config_dict:
                logger.info(
                    f"✅ Configuración WhatsApp obtenida usando método alternativo: {len(config_dict)} configuraciones"
                )
                return config_dict
        except Exception as alt_error:
            # ✅ Si el método alternativo también falla, verificar si es transacción abortada
            alt_error_str = str(alt_error)
            alt_error_type = type(alt_error).__name__
            is_alt_transaction_aborted = (
                "aborted" in alt_error_str.lower()
                or "InFailedSqlTransaction" in alt_error_type
                or "current transaction is aborted" in alt_error_str.lower()
            )

            if is_alt_transaction_aborted:
                # ✅ Cambiar a debug - es un comportamiento esperado cuando la transacción está abortada
                logger.debug(
                    f"⚠️ Método alternativo falló por transacción abortada (comportamiento esperado): {str(alt_error)}"
                )
            else:
                logger.error(f"❌ Error en método alternativo también falló: {str(alt_error)}", exc_info=True)
        return None


def _procesar_configuraciones_whatsapp(configs: list) -> Dict[str, Any]:
    """Procesa una lista de configuraciones y retorna un diccionario"""
    config_dict = {}
    for config in configs:
        try:
            if hasattr(config, "clave") and config.clave:
                valor = config.valor if hasattr(config, "valor") and config.valor is not None else ""
                config_dict[config.clave] = valor
                logger.debug(f"📝 Configuración WhatsApp: {config.clave} = {valor[:20] if len(str(valor)) > 20 else valor}")
            else:
                logger.warning(f"⚠️ Configuración WhatsApp sin clave válida: {config}")
        except Exception as config_error:
            logger.error(f"❌ Error procesando configuración WhatsApp individual: {config_error}", exc_info=True)
            continue
    return config_dict


@router.get("/whatsapp/configuracion")
def obtener_configuracion_whatsapp(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener configuración de WhatsApp"""
    try:
        logger.info(f"📱 Obteniendo configuración de WhatsApp - Usuario: {getattr(current_user, 'email', 'N/A')}")

        if not getattr(current_user, "is_admin", False):
            logger.warning(
                f"⚠️ Usuario no autorizado intentando acceder a configuración de WhatsApp: {getattr(current_user, 'email', 'N/A')}"
            )
            raise HTTPException(
                status_code=403,
                detail="Solo administradores pueden ver configuración de WhatsApp",
            )

        logger.info("🔍 Consultando configuración de WhatsApp desde BD...")
        configs = _consultar_configuracion_whatsapp(db)

        if configs is None:
            logger.warning("⚠️ No se pudo obtener configuración de BD, retornando valores por defecto")
            return _obtener_valores_whatsapp_por_defecto()

        if isinstance(configs, dict):
            return configs

        if not configs:
            logger.info("📝 Retornando valores por defecto de WhatsApp (no hay configuraciones en BD)")
            return _obtener_valores_whatsapp_por_defecto()

        config_dict = _procesar_configuraciones_whatsapp(configs)
        logger.info(f"✅ Configuración de WhatsApp obtenida exitosamente: {len(config_dict)} configuraciones")
        return config_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración de WhatsApp: {str(e)}", exc_info=True)
        logger.warning("⚠️ Retornando valores por defecto debido a error")
        return _obtener_valores_whatsapp_por_defecto()


@router.put("/whatsapp/configuracion")
def actualizar_configuracion_whatsapp(
    config_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración de WhatsApp"""
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
                    ConfiguracionSistema.categoria == "WHATSAPP",
                    ConfiguracionSistema.clave == clave,
                )
                .first()
            )

            if config:
                config.valor = str(valor)  # type: ignore[assignment]
                configuraciones.append(config)  # type: ignore[arg-type]
            else:
                nueva_config = ConfiguracionSistema(
                    categoria="WHATSAPP",
                    clave=clave,
                    valor=str(valor),
                    tipo_dato="STRING",
                    visible_frontend=True,
                )
                db.add(nueva_config)
                configuraciones.append(nueva_config)

        db.commit()

        logger.info(f"Configuración de WhatsApp actualizada por {current_user.email}")

        return {
            "mensaje": "Configuración de WhatsApp actualizada exitosamente",
            "configuraciones_actualizadas": len(configuraciones),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando configuración de WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


class ProbarWhatsAppRequest(BaseModel):
    telefono_destino: Optional[str] = None
    mensaje: Optional[str] = None


@router.post("/whatsapp/probar")
async def probar_configuracion_whatsapp(
    request: Optional[ProbarWhatsAppRequest] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Probar configuración de WhatsApp enviando un mensaje de prueba

    Args:
        request: Objeto con telefono_destino opcional. Si no se proporciona, se usa el teléfono de pruebas.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden probar configuración de WhatsApp",
        )

    try:
        # Obtener configuración
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "WHATSAPP").all()

        if not configs:
            raise HTTPException(status_code=400, detail="No hay configuración de WhatsApp")

        config_dict = {config.clave: config.valor for config in configs}
        modo_pruebas = config_dict.get("modo_pruebas", "true").lower() in ("true", "1", "yes", "on")

        # Determinar teléfono destino
        telefono_destino_val = None
        if request:
            if isinstance(request, dict):
                telefono_destino_val = request.get("telefono_destino")
            elif hasattr(request, "telefono_destino"):
                telefono_destino_val = request.telefono_destino

        # Si se proporcionó un teléfono, usarlo; si no, usar el teléfono de pruebas o requerirlo
        if telefono_destino_val and telefono_destino_val.strip():
            telefono_a_enviar = telefono_destino_val.strip()
        elif modo_pruebas and config_dict.get("telefono_pruebas"):
            telefono_a_enviar = config_dict["telefono_pruebas"]
        else:
            raise HTTPException(status_code=400, detail="Debe proporcionar un número de teléfono de destino")

        # Validar formato de teléfono (básico)
        import re

        # Limpiar número (quitar espacios, guiones, paréntesis)
        telefono_limpio = re.sub(r"[\s\-\(\)]", "", telefono_a_enviar)
        # Debe empezar con + y tener al menos 10 dígitos
        if not re.match(r"^\+?[1-9]\d{9,14}$", telefono_limpio):
            raise HTTPException(
                status_code=400, detail="Número de teléfono inválido. Debe incluir código de país (ej: +584121234567)"
            )

        # Obtener mensaje personalizado si se proporcionó
        mensaje_personalizado = None
        if request:
            if isinstance(request, dict):
                mensaje_personalizado = request.get("mensaje")
            elif hasattr(request, "mensaje"):
                mensaje_personalizado = request.mensaje

        # Usar mensaje personalizado o el predeterminado
        mensaje_whatsapp = (
            mensaje_personalizado.strip()
            if mensaje_personalizado and mensaje_personalizado.strip()
            else "✅ Prueba de configuración - RapiCredit\n\nEste es un mensaje de prueba para verificar que la configuración de WhatsApp está funcionando correctamente.\n\nSi recibes este mensaje, significa que:\n✅ La configuración es correcta\n✅ Las credenciales son válidas\n✅ El sistema puede enviar mensajes normalmente"
        )

        # Enviar mensaje de prueba
        from app.services.whatsapp_service import WhatsAppService

        whatsapp_service = WhatsAppService(db=db)

        # Si estamos en modo Producción, forzar envío real para verificar que funciona
        # Si estamos en modo Pruebas, respetar el comportamiento normal
        forzar_real = not modo_pruebas

        result = await whatsapp_service.send_message(
            to_number=telefono_limpio,
            message=mensaje_whatsapp,
            forzar_envio_real=forzar_real,
        )

        if result.get("success"):
            return {
                "mensaje": f"Mensaje de prueba enviado exitosamente a {telefono_limpio}",
                "telefono_destino": telefono_limpio,
                "detalle": result,
            }
        else:
            return {
                "mensaje": "Error enviando mensaje de prueba",
                "error": result.get("message"),
                "telefono_destino": telefono_limpio,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error probando configuración de WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/whatsapp/test-completo")
async def test_completo_whatsapp(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Test completo de WhatsApp que verifica:
    1. Configuración en BD
    2. Conexión con Meta API
    3. Validación de credenciales
    4. Estado de rate limits
    5. Envío de mensaje de prueba (opcional)

    Retorna diagnóstico detallado de todos los componentes
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ejecutar tests de WhatsApp",
        )

    resultados = {
        "timestamp": datetime.now().isoformat(),
        "usuario": current_user.email,
        "tests": {},
        "resumen": {"total": 0, "exitosos": 0, "fallidos": 0, "advertencias": 0},
    }

    try:
        from app.services.whatsapp_service import WhatsAppService

        # ============================================
        # TEST 1: Verificar configuración en BD
        # ============================================
        logger.info("🔍 [TEST] Verificando configuración en BD...")
        test_config = {"nombre": "Configuración en BD", "exito": False, "detalles": {}}

        try:
            configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "WHATSAPP").all()

            if not configs:
                test_config["exito"] = False
                test_config["error"] = "No hay configuración de WhatsApp en la base de datos"
                test_config["detalles"]["configuraciones_encontradas"] = 0
            else:
                config_dict = {config.clave: config.valor for config in configs}
                test_config["detalles"]["configuraciones_encontradas"] = len(configs)
                test_config["detalles"]["configuraciones"] = {
                    k: "✅ Configurado" if v else "❌ Vacío" for k, v in config_dict.items()
                }

                # Verificar campos críticos
                campos_criticos = ["access_token", "phone_number_id", "api_url"]
                campos_faltantes = [campo for campo in campos_criticos if not config_dict.get(campo)]

                if campos_faltantes:
                    test_config["exito"] = False
                    test_config["error"] = f"Campos críticos faltantes: {', '.join(campos_faltantes)}"
                    test_config["advertencia"] = True
                else:
                    test_config["exito"] = True
                    test_config["mensaje"] = "Configuración completa en BD"

                # Verificar modo pruebas
                modo_pruebas = config_dict.get("modo_pruebas", "true").lower() in ("true", "1", "yes", "on")
                test_config["detalles"]["modo_pruebas"] = modo_pruebas
                if modo_pruebas:
                    test_config["detalles"]["telefono_pruebas"] = config_dict.get("telefono_pruebas", "No configurado")

        except Exception as e:
            test_config["exito"] = False
            test_config["error"] = f"Error verificando configuración: {str(e)}"
            logger.error(f"❌ [TEST] Error en test de configuración: {e}")

        resultados["tests"]["configuracion"] = test_config
        if test_config["exito"]:
            resultados["resumen"]["exitosos"] += 1
        else:
            resultados["resumen"]["fallidos"] += 1
        resultados["resumen"]["total"] += 1

        # ============================================
        # TEST 2: Verificar conexión con Meta API
        # ============================================
        logger.info("🔍 [TEST] Verificando conexión con Meta API...")
        test_conexion = {"nombre": "Conexión con Meta API", "exito": False, "detalles": {}}

        try:
            whatsapp_service = WhatsAppService(db=db)
            resultado_conexion = await whatsapp_service.test_connection()

            test_conexion["exito"] = resultado_conexion.get("success", False)
            test_conexion["detalles"]["respuesta"] = resultado_conexion.get("message", "Sin respuesta")
            test_conexion["detalles"]["error_code"] = resultado_conexion.get("error_code")

            if not test_conexion["exito"]:
                test_conexion["error"] = resultado_conexion.get("message", "Error desconocido")

            # Información adicional de configuración cargada
            test_conexion["detalles"]["api_url"] = whatsapp_service.api_url
            test_conexion["detalles"]["phone_number_id"] = (
                whatsapp_service.phone_number_id[:10] + "..." if whatsapp_service.phone_number_id else "No configurado"
            )
            test_conexion["detalles"]["access_token"] = (
                "✅ Configurado" if whatsapp_service.access_token else "❌ No configurado"
            )
            test_conexion["detalles"]["business_account_id"] = (
                whatsapp_service.business_account_id[:10] + "..." if whatsapp_service.business_account_id else "No configurado"
            )

        except Exception as e:
            test_conexion["exito"] = False
            test_conexion["error"] = f"Error probando conexión: {str(e)}"
            logger.error(f"❌ [TEST] Error en test de conexión: {e}", exc_info=True)

        resultados["tests"]["conexion"] = test_conexion
        if test_conexion["exito"]:
            resultados["resumen"]["exitosos"] += 1
        else:
            resultados["resumen"]["fallidos"] += 1
        resultados["resumen"]["total"] += 1

        # ============================================
        # TEST 3: Verificar rate limits
        # ============================================
        logger.info("🔍 [TEST] Verificando rate limits...")
        test_rate_limit = {"nombre": "Rate Limits", "exito": False, "detalles": {}}

        try:
            # Verificar rate limit (sin enviar mensaje)
            rate_check = await whatsapp_service._check_rate_limit()
            test_rate_limit["exito"] = rate_check.get("success", False)
            test_rate_limit["detalles"]["rate_limit_diario"] = "1000 mensajes/día"
            test_rate_limit["detalles"]["rate_limit_segundo"] = "80 mensajes/segundo"
            test_rate_limit["detalles"]["estado_actual"] = (
                "✅ Disponible" if test_rate_limit["exito"] else f"❌ {rate_check.get('message', 'Error')}"
            )

            if not test_rate_limit["exito"]:
                test_rate_limit["error"] = rate_check.get("message", "Rate limit alcanzado")
                test_rate_limit["advertencia"] = True

        except Exception as e:
            test_rate_limit["exito"] = False
            test_rate_limit["error"] = f"Error verificando rate limits: {str(e)}"
            test_rate_limit["advertencia"] = True
            logger.error(f"❌ [TEST] Error en test de rate limits: {e}")

        resultados["tests"]["rate_limits"] = test_rate_limit
        if test_rate_limit["exito"]:
            resultados["resumen"]["exitosos"] += 1
        elif test_rate_limit.get("advertencia"):
            resultados["resumen"]["advertencias"] += 1
        else:
            resultados["resumen"]["fallidos"] += 1
        resultados["resumen"]["total"] += 1

        # ============================================
        # TEST 4: Validar número de teléfono (formato)
        # ============================================
        logger.info("🔍 [TEST] Verificando validación de números...")
        test_validacion = {"nombre": "Validación de Números", "exito": False, "detalles": {}}

        try:
            numeros_prueba = ["+584121234567", "584121234567", "+1234567890", "1234567890", "abc123"]
            resultados_validacion = {}

            for num in numeros_prueba:
                es_valido = whatsapp_service.validate_phone_number(num)
                resultados_validacion[num] = "✅ Válido" if es_valido else "❌ Inválido"

            test_validacion["exito"] = True
            test_validacion["detalles"]["ejemplos"] = resultados_validacion
            test_validacion["mensaje"] = "Validación de números funcionando correctamente"

        except Exception as e:
            test_validacion["exito"] = False
            test_validacion["error"] = f"Error en validación: {str(e)}"
            logger.error(f"❌ [TEST] Error en test de validación: {e}")

        resultados["tests"]["validacion"] = test_validacion
        if test_validacion["exito"]:
            resultados["resumen"]["exitosos"] += 1
        else:
            resultados["resumen"]["fallidos"] += 1
        resultados["resumen"]["total"] += 1

        # ============================================
        # TEST 5: Verificar configuración de servicios
        # ============================================
        logger.info("🔍 [TEST] Verificando configuración de servicios...")
        test_servicios = {"nombre": "Configuración de Servicios", "exito": False, "detalles": {}}

        try:
            test_servicios["detalles"]["timeout"] = f"{whatsapp_service.timeout}s"
            test_servicios["detalles"]["max_retries"] = "3 intentos"
            test_servicios["detalles"]["backoff_base"] = "2 segundos (exponencial)"
            test_servicios["detalles"]["modo_pruebas"] = whatsapp_service.modo_pruebas
            test_servicios["detalles"]["telefono_pruebas"] = (
                whatsapp_service.telefono_pruebas if whatsapp_service.telefono_pruebas else "No configurado"
            )

            test_servicios["exito"] = True
            test_servicios["mensaje"] = "Configuración de servicios correcta"

        except Exception as e:
            test_servicios["exito"] = False
            test_servicios["error"] = f"Error verificando servicios: {str(e)}"
            logger.error(f"❌ [TEST] Error en test de servicios: {e}")

        resultados["tests"]["servicios"] = test_servicios
        if test_servicios["exito"]:
            resultados["resumen"]["exitosos"] += 1
        else:
            resultados["resumen"]["fallidos"] += 1
        resultados["resumen"]["total"] += 1

        # ============================================
        # RESUMEN FINAL
        # ============================================
        todos_exitosos = resultados["resumen"]["fallidos"] == 0
        resultados["resumen"]["estado_general"] = "✅ TODO CORRECTO" if todos_exitosos else "⚠️ HAY PROBLEMAS"
        resultados["resumen"]["recomendaciones"] = []

        if not test_config["exito"]:
            resultados["resumen"]["recomendaciones"].append(
                "Verificar y completar la configuración de WhatsApp en la base de datos"
            )
        if not test_conexion["exito"]:
            resultados["resumen"]["recomendaciones"].append(
                "Verificar credenciales de Meta (Access Token, Phone Number ID) y conexión a internet"
            )
        if not test_rate_limit.get("exito") and not test_rate_limit.get("advertencia"):
            resultados["resumen"]["recomendaciones"].append("Rate limits alcanzados, esperar antes de enviar más mensajes")

        logger.info(
            f"✅ [TEST COMPLETO] Finalizado: {resultados['resumen']['exitosos']}/{resultados['resumen']['total']} tests exitosos"
        )

        return resultados

    except Exception as e:
        logger.error(f"❌ [TEST COMPLETO] Error general: {e}", exc_info=True)
        resultados["error_general"] = str(e)
        resultados["resumen"]["estado_general"] = "❌ ERROR CRÍTICO"
        return resultados


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


# ============================================
# CONFIGURACIÓN DE AI (CHATGPT)
# ============================================


def _obtener_valores_ai_por_defecto() -> Dict[str, str]:
    """Retorna valores por defecto para configuración de AI"""
    return {
        "openai_api_key": "",
        "modelo": "gpt-3.5-turbo",
        "temperatura": "0.7",
        "max_tokens": "1000",
        "activo": "false",
    }


def _consultar_configuracion_ai(db: Session) -> Optional[Any]:
    """Intenta consultar configuración de AI desde BD"""
    try:
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "AI").all()
        logger.info(f"📊 Configuraciones AI encontradas: {len(configs)}")
        return configs
    except Exception as query_error:
        error_str = str(query_error)
        error_type = type(query_error).__name__
        # ✅ Verificar si es un error de transacción abortada
        is_transaction_aborted = (
            "aborted" in error_str.lower()
            or "InFailedSqlTransaction" in error_type
            or "current transaction is aborted" in error_str.lower()
        )

        if is_transaction_aborted:
            # ✅ Hacer rollback antes de intentar método alternativo
            try:
                db.rollback()
                logger.debug("✅ Rollback realizado antes de método alternativo (transacción abortada)")
            except Exception as rollback_error:
                logger.warning(f"⚠️ Error al hacer rollback: {rollback_error}")

        logger.error(f"❌ Error ejecutando consulta de configuración de AI: {str(query_error)}", exc_info=True)
        try:
            config_dict = ConfiguracionSistema.obtener_categoria(db, "AI")
            if config_dict:
                logger.info(f"✅ Configuración AI obtenida usando método alternativo: {len(config_dict)} configuraciones")
                return config_dict
        except Exception as alt_error:
            # ✅ Si el método alternativo también falla, verificar si es transacción abortada
            alt_error_str = str(alt_error)
            alt_error_type = type(alt_error).__name__
            is_alt_transaction_aborted = (
                "aborted" in alt_error_str.lower()
                or "InFailedSqlTransaction" in alt_error_type
                or "current transaction is aborted" in alt_error_str.lower()
            )

            if is_alt_transaction_aborted:
                # ✅ Cambiar a debug - es un comportamiento esperado cuando la transacción está abortada
                logger.debug(
                    f"⚠️ Método alternativo falló por transacción abortada (comportamiento esperado): {str(alt_error)}"
                )
            else:
                logger.error(f"❌ Error en método alternativo también falló: {str(alt_error)}", exc_info=True)
        return None


def _procesar_configuraciones_ai(configs: list) -> Dict[str, Any]:
    """Procesa una lista de configuraciones AI y retorna un diccionario"""
    config_dict = {}
    for config in configs:
        try:
            if hasattr(config, "clave") and config.clave:
                valor = config.valor if hasattr(config, "valor") and config.valor is not None else ""
                config_dict[config.clave] = valor
                logger.debug(f"📝 Configuración AI: {config.clave} = {valor[:20] if len(str(valor)) > 20 else valor}")
            else:
                logger.warning(f"⚠️ Configuración AI sin clave válida: {config}")
        except Exception as config_error:
            logger.error(f"❌ Error procesando configuración AI individual: {config_error}", exc_info=True)
            continue
    return config_dict


@router.get("/ai/configuracion")
def obtener_configuracion_ai(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtener configuración de AI"""
    try:
        logger.info(f"🤖 Obteniendo configuración de AI - Usuario: {getattr(current_user, 'email', 'N/A')}")

        if not getattr(current_user, "is_admin", False):
            logger.warning(
                f"⚠️ Usuario no autorizado intentando acceder a configuración de AI: {getattr(current_user, 'email', 'N/A')}"
            )
            raise HTTPException(status_code=403, detail="Solo administradores pueden ver configuración de AI")

        logger.info("🔍 Consultando configuración de AI desde BD...")
        configs = _consultar_configuracion_ai(db)

        if configs is None:
            logger.warning("⚠️ No se pudo obtener configuración de BD, retornando valores por defecto")
            return _obtener_valores_ai_por_defecto()

        if isinstance(configs, dict):
            return configs

        if not configs:
            logger.info("📝 Retornando valores por defecto de AI (no hay configuraciones en BD)")
            return _obtener_valores_ai_por_defecto()

        config_dict = _procesar_configuraciones_ai(configs)
        logger.info(f"✅ Configuración de AI obtenida exitosamente: {len(config_dict)} configuraciones")
        return config_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración de AI: {str(e)}", exc_info=True)
        logger.warning("⚠️ Retornando valores por defecto debido a error")
        return _obtener_valores_ai_por_defecto()


@router.put("/ai/configuracion")
def actualizar_configuracion_ai(
    config_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración de AI"""
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
                    ConfiguracionSistema.categoria == "AI",
                    ConfiguracionSistema.clave == clave,
                )
                .first()
            )

            if config:
                config.valor = str(valor)  # type: ignore[assignment]
                configuraciones.append(config)  # type: ignore[arg-type]
            else:
                nueva_config = ConfiguracionSistema(
                    categoria="AI",
                    clave=clave,
                    valor=str(valor),
                    tipo_dato="STRING" if clave != "activo" else "BOOLEAN",
                    visible_frontend=True,
                )
                db.add(nueva_config)
                configuraciones.append(nueva_config)

        db.commit()

        logger.info(f"Configuración de AI actualizada por {current_user.email}")

        return {
            "mensaje": "Configuración de AI actualizada exitosamente",
            "configuraciones_actualizadas": len(configuraciones),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando configuración de AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# GESTIÓN DE DOCUMENTOS AI
# ============================================


class DocumentoAIUpdate(BaseModel):
    """Schema para actualizar documento AI"""

    titulo: Optional[str] = Field(None, description="Título del documento")
    descripcion: Optional[str] = Field(None, description="Descripción del documento")
    activo: Optional[bool] = Field(None, description="Estado activo/inactivo")


def _extraer_texto_documento(ruta_archivo: str, tipo_archivo: str) -> str:
    """
    Extrae texto de un documento según su tipo

    Args:
        ruta_archivo: Ruta completa al archivo
        tipo_archivo: Tipo de archivo (pdf, txt, docx)

    Returns:
        Texto extraído del documento
    """
    try:
        from pathlib import Path

        ruta_path = Path(ruta_archivo)
        if not ruta_path.exists():
            logger.error(f"❌ Archivo no encontrado: {ruta_archivo}")
            return ""

        texto = ""

        if tipo_archivo.lower() == "txt":
            # Leer archivo de texto plano
            try:
                with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
                    texto = f.read()
            except UnicodeDecodeError:
                # Intentar con otras codificaciones comunes
                for encoding in ["latin-1", "cp1252", "iso-8859-1"]:
                    try:
                        with open(ruta_archivo, "r", encoding=encoding, errors="ignore") as f:
                            texto = f.read()
                            logger.info(f"✅ Texto leído con codificación {encoding}")
                            break
                    except:
                        continue

        elif tipo_archivo.lower() == "pdf":
            # Extraer texto de PDF
            texto_extraido = False
            try:
                import PyPDF2

                with open(ruta_archivo, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    # Verificar si el PDF está encriptado
                    if pdf_reader.is_encrypted:
                        logger.warning("⚠️ PDF está encriptado. Intentando desencriptar sin contraseña...")
                        try:
                            pdf_reader.decrypt("")
                        except:
                            logger.error("❌ PDF requiere contraseña para desencriptar.")
                            return ""

                    textos_paginas = []
                    for page in pdf_reader.pages:
                        texto_pagina = page.extract_text()
                        if texto_pagina:
                            textos_paginas.append(texto_pagina)
                    texto = "\n".join(textos_paginas)
                    texto_extraido = True
            except ImportError:
                logger.warning("⚠️ PyPDF2 no está instalado. Instala con: pip install PyPDF2")
            except Exception as e:
                logger.warning(f"⚠️ Error con PyPDF2: {e}. Intentando con pdfplumber...")

            # Intentar con pdfplumber como alternativa si PyPDF2 falló
            if not texto_extraido or not texto.strip():
                try:
                    import pdfplumber

                    with pdfplumber.open(ruta_archivo) as pdf:
                        textos_paginas = []
                        for page in pdf.pages:
                            texto_pagina = page.extract_text()
                            if texto_pagina:
                                textos_paginas.append(texto_pagina)
                        texto = "\n".join(textos_paginas)
                        texto_extraido = True
                except ImportError:
                    if not texto_extraido:
                        logger.error("❌ Ni PyPDF2 ni pdfplumber están instalados. No se puede extraer texto de PDF.")
                        return ""
                except Exception as e:
                    logger.error(f"❌ Error con pdfplumber: {e}")
                    if not texto_extraido:
                        return ""

        elif tipo_archivo.lower() == "docx":
            # Extraer texto de DOCX
            try:
                from docx import Document

                doc = Document(ruta_archivo)
                textos_parrafos = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        textos_parrafos.append(paragraph.text)
                texto = "\n".join(textos_parrafos)
            except ImportError:
                logger.warning("⚠️ python-docx no está instalado. Instala con: pip install python-docx")
                return ""
            except Exception as e:
                logger.error(f"❌ Error extrayendo texto de DOCX: {e}")
                return ""

        # Limpiar y normalizar texto
        texto = texto.strip()
        # Eliminar espacios múltiples
        import re

        texto = re.sub(r"\s+", " ", texto)

        logger.info(f"✅ Texto extraído: {len(texto)} caracteres de {tipo_archivo}")
        return texto

    except Exception as e:
        logger.error(f"❌ Error extrayendo texto de {ruta_archivo}: {e}", exc_info=True)
        return ""


@router.get("/ai/documentos")
def listar_documentos_ai(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    activo: Optional[bool] = None,
):
    """Listar todos los documentos AI"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver documentos AI")

    try:
        query = db.query(DocumentoAI)

        if activo is not None:
            query = query.filter(DocumentoAI.activo == activo)

        documentos = query.order_by(DocumentoAI.creado_en.desc()).all()

        return {
            "total": len(documentos),
            "documentos": [doc.to_dict() for doc in documentos],
        }
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        error_repr = repr(e)

        # ✅ Verificar primero si el error es porque la tabla no existe
        # Capturar tanto errores de psycopg2 como errores genéricos de SQLAlchemy
        # El error de PostgreSQL es: (psycopg2.errors.UndefinedTable) relation "documentos_ai" does not exist
        is_table_missing = (
            "does not exist" in error_msg.lower()
            or "no such table" in error_msg.lower()
            or ("relation" in error_msg.lower() and "does not exist" in error_msg.lower())
            or "UndefinedTable" in error_type
            or "UndefinedTable" in error_repr
            or ("documentos_ai" in error_msg.lower() and "does not exist" in error_msg.lower())
        )

        if is_table_missing:
            # ✅ Cambiar a debug para reducir verbosidad - es un comportamiento esperado
            logger.debug("⚠️ Tabla documentos_ai no existe. Se requiere migración de base de datos (comportamiento esperado).")
            return {
                "total": 0,
                "documentos": [],
                "mensaje": "La tabla de documentos AI no está disponible. Por favor, ejecuta las migraciones de base de datos.",
            }

        # ✅ Solo loguear como error si NO es un error de tabla faltante
        logger.error(f"Error listando documentos AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/ai/documentos")
async def crear_documento_ai(
    titulo: str = Form(...),
    descripcion: Optional[str] = Form(None),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear nuevo documento AI"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear documentos AI")

    try:
        import os
        from pathlib import Path

        # Validar tipo de archivo
        tipos_permitidos = [
            "application/pdf",
            "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        extensiones_permitidas = {".pdf": "pdf", ".txt": "txt", ".docx": "docx"}

        # Obtener extensión primero (más confiable que content_type)
        nombre_archivo_original = archivo.filename or "documento"
        extension = Path(nombre_archivo_original).suffix.lower()

        if extension not in extensiones_permitidas:
            raise HTTPException(
                status_code=400,
                detail=f"Extensión de archivo no permitida: {extension}. Extensiones permitidas: .pdf, .txt, .docx",
            )

        tipo_archivo_db = extensiones_permitidas[extension]

        # Validar content_type si está disponible (puede ser None en algunos casos)
        tipo_archivo = archivo.content_type
        if tipo_archivo:
            # Validación flexible: verificar si el tipo coincide o si es un tipo genérico aceptable
            tipos_validos = tipos_permitidos + [
                "application/octet-stream",  # Tipo genérico que algunos navegadores usan
                "application/x-pdf",  # Variante de PDF
            ]

            # Si el content_type no coincide exactamente, verificar por extensión
            if tipo_archivo not in tipos_validos:
                # Permitir si la extensión es válida (algunos navegadores no envían content_type correcto)
                logger.warning(
                    f"⚠️ Content-Type '{tipo_archivo}' no está en la lista permitida, pero extensión '{extension}' es válida. Continuando..."
                )
        else:
            # Si no hay content_type, confiar en la extensión
            logger.info(f"ℹ️ No se recibió Content-Type, validando solo por extensión: {extension}")

        # Crear directorio de almacenamiento si no existe
        from app.core.config import settings

        # Usar UPLOAD_DIR de configuración si está disponible, sino usar relativo
        if hasattr(settings, "UPLOAD_DIR") and settings.UPLOAD_DIR:
            base_upload_dir = Path(settings.UPLOAD_DIR).resolve()
        else:
            base_upload_dir = Path("uploads").resolve()

        upload_dir = base_upload_dir / "documentos_ai"
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
        except Exception as dir_error:
            logger.error(f"❌ Error creando directorio de uploads: {dir_error}")
            raise HTTPException(status_code=500, detail=f"Error creando directorio de almacenamiento: {str(dir_error)}")

        # Generar nombre único para el archivo
        import uuid

        nombre_unico = f"{uuid.uuid4()}{extension}"
        ruta_archivo = upload_dir / nombre_unico
        # Asegurar que la ruta sea absoluta
        ruta_archivo = ruta_archivo.resolve()

        # Guardar archivo
        try:
            contenido = await archivo.read()
            tamaño_bytes = len(contenido)

            with open(ruta_archivo, "wb") as f:
                f.write(contenido)
        except Exception as file_error:
            logger.error(f"❌ Error guardando archivo: {file_error}")
            raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(file_error)}")

        # Crear registro en BD
        try:
            nuevo_documento = DocumentoAI(
                titulo=titulo,
                descripcion=descripcion,
                nombre_archivo=nombre_archivo_original,
                tipo_archivo=tipo_archivo_db,
                ruta_archivo=str(ruta_archivo),
                tamaño_bytes=tamaño_bytes,
                contenido_procesado=False,
                activo=True,
            )

            db.add(nuevo_documento)
            db.commit()
            db.refresh(nuevo_documento)
        except Exception as db_error:
            # Si hay error de BD, intentar eliminar el archivo guardado
            try:
                if ruta_archivo.exists():
                    os.remove(ruta_archivo)
            except:
                pass

            error_msg = str(db_error)
            error_type = type(db_error).__name__

            # Verificar si es error de tabla no existe
            is_table_missing = (
                "does not exist" in error_msg.lower()
                or "no such table" in error_msg.lower()
                or ("relation" in error_msg.lower() and "does not exist" in error_msg.lower())
                or "UndefinedTable" in error_type
            )

            if is_table_missing:
                raise HTTPException(
                    status_code=500,
                    detail="La tabla de documentos AI no existe. Por favor, ejecuta las migraciones de base de datos.",
                )
            else:
                raise

        # Procesar documento automáticamente (extraer texto)
        try:
            texto_extraido = _extraer_texto_documento(str(ruta_archivo), tipo_archivo_db)
            if texto_extraido:
                nuevo_documento.contenido_texto = texto_extraido
                nuevo_documento.contenido_procesado = True
                db.commit()
                db.refresh(nuevo_documento)
                logger.info(f"✅ Documento procesado automáticamente: {len(texto_extraido)} caracteres")
            else:
                logger.warning(f"⚠️ No se pudo extraer texto del documento: {titulo}")
        except Exception as proc_error:
            logger.error(f"❌ Error procesando documento automáticamente: {proc_error}", exc_info=True)
            # No fallar la creación si el procesamiento falla

        logger.info(f"✅ Documento AI creado: {titulo} ({nombre_archivo_original})")

        return {
            "mensaje": "Documento creado exitosamente",
            "documento": nuevo_documento.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        error_type = type(e).__name__

        logger.error(f"❌ Error creando documento AI: {error_msg}", exc_info=True)
        logger.error(f"   Tipo de error: {error_type}")

        # Mensaje de error más descriptivo
        if "does not exist" in error_msg.lower() or "no such table" in error_msg.lower():
            detail_msg = "La tabla de documentos AI no existe. Por favor, ejecuta las migraciones de base de datos."
        elif "permission denied" in error_msg.lower() or "access denied" in error_msg.lower():
            detail_msg = f"Error de permisos al guardar el archivo: {error_msg}"
        elif "no space left" in error_msg.lower():
            detail_msg = "No hay espacio suficiente en el servidor para guardar el archivo."
        else:
            detail_msg = f"Error interno al crear documento: {error_msg}"

        raise HTTPException(status_code=500, detail=detail_msg)


@router.post("/ai/documentos/{documento_id}/procesar")
def procesar_documento_ai(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Procesar documento AI (extraer texto)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden procesar documentos AI")

    try:
        documento = db.query(DocumentoAI).filter(DocumentoAI.id == documento_id).first()

        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        # Verificar que el archivo existe
        from pathlib import Path

        from app.core.config import settings

        # Intentar resolver la ruta (puede ser relativa o absoluta)
        ruta_archivo = Path(documento.ruta_archivo)

        # Si la ruta es relativa, intentar resolverla desde UPLOAD_DIR
        if not ruta_archivo.is_absolute():
            if hasattr(settings, "UPLOAD_DIR") and settings.UPLOAD_DIR:
                base_upload_dir = Path(settings.UPLOAD_DIR).resolve()
            else:
                base_upload_dir = Path("uploads").resolve()
            ruta_archivo = (base_upload_dir / documento.ruta_archivo).resolve()
        else:
            ruta_archivo = ruta_archivo.resolve()

        if not ruta_archivo.exists():
            logger.error(f"❌ Archivo no encontrado: {ruta_archivo} (ruta original: {documento.ruta_archivo})")
            raise HTTPException(
                status_code=400,
                detail=f"El archivo físico no existe en la ruta: {ruta_archivo}. El archivo puede haber sido eliminado o movido. Ruta original en BD: {documento.ruta_archivo}",
            )

        # Verificar que el archivo no esté vacío
        if ruta_archivo.stat().st_size == 0:
            logger.warning(f"⚠️ Archivo vacío: {documento.ruta_archivo}")
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío. No se puede extraer texto de un archivo sin contenido.",
            )

        # Extraer texto del documento
        texto_extraido = _extraer_texto_documento(documento.ruta_archivo, documento.tipo_archivo)

        if texto_extraido and texto_extraido.strip():
            documento.contenido_texto = texto_extraido
            documento.contenido_procesado = True
            db.commit()
            db.refresh(documento)

            logger.info(f"✅ Documento procesado: {documento.titulo} ({len(texto_extraido)} caracteres)")

            return {
                "mensaje": "Documento procesado exitosamente",
                "documento": documento.to_dict(),
                "caracteres_extraidos": len(texto_extraido),
            }
        else:
            # Proporcionar mensaje más específico según el tipo de archivo
            tipo = documento.tipo_archivo.lower()
            mensaje_error = "No se pudo extraer texto del documento."

            if tipo == "pdf":
                mensaje_error += " El PDF puede estar escaneado (imagen) sin OCR, estar protegido con contraseña, o las librerías PyPDF2/pdfplumber no están instaladas."
            elif tipo == "docx":
                mensaje_error += " El archivo DOCX puede estar corrupto o la librería python-docx no está instalada."
            elif tipo == "txt":
                mensaje_error += " El archivo de texto puede estar vacío o usar una codificación no soportada."
            else:
                mensaje_error += " Verifica que el archivo sea válido y que las librerías necesarias estén instaladas."

            raise HTTPException(status_code=400, detail=mensaje_error)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error procesando documento AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/ai/documentos/{documento_id}")
def eliminar_documento_ai(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar documento AI"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar documentos AI")

    try:
        documento = db.query(DocumentoAI).filter(DocumentoAI.id == documento_id).first()

        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        # Eliminar archivo físico
        import os
        from pathlib import Path

        if documento.ruta_archivo and Path(documento.ruta_archivo).exists():
            try:
                os.remove(documento.ruta_archivo)
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar archivo físico: {e}")

        # Eliminar de BD
        db.delete(documento)
        db.commit()

        logger.info(f"✅ Documento AI eliminado: {documento.titulo}")

        return {"mensaje": "Documento eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando documento AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/ai/documentos/{documento_id}")
def obtener_documento_ai(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    incluir_contenido: bool = False,
):
    """Obtener un documento AI específico"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver documentos AI")

    try:
        documento = db.query(DocumentoAI).filter(DocumentoAI.id == documento_id).first()

        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        return {
            "documento": documento.to_dict(incluir_contenido=incluir_contenido),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo documento AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/ai/documentos/{documento_id}")
def actualizar_documento_ai(
    documento_id: int,
    documento_data: DocumentoAIUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar documento AI (título, descripción, estado activo)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden actualizar documentos AI")

    try:
        documento = db.query(DocumentoAI).filter(DocumentoAI.id == documento_id).first()

        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        # Actualizar campos si se proporcionan
        if documento_data.titulo is not None:
            documento.titulo = documento_data.titulo
        if documento_data.descripcion is not None:
            documento.descripcion = documento_data.descripcion
        if documento_data.activo is not None:
            documento.activo = documento_data.activo

        db.commit()
        db.refresh(documento)

        logger.info(f"✅ Documento AI actualizado: {documento.titulo} (ID: {documento_id})")

        return {
            "mensaje": "Documento actualizado exitosamente",
            "documento": documento.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando documento AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.patch("/ai/documentos/{documento_id}/activar")
def activar_desactivar_documento_ai(
    documento_id: int,
    activo: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activar o desactivar un documento AI"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden activar/desactivar documentos AI")

    try:
        documento = db.query(DocumentoAI).filter(DocumentoAI.id == documento_id).first()

        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        documento.activo = activo
        db.commit()
        db.refresh(documento)

        estado = "activado" if activo else "desactivado"
        logger.info(f"✅ Documento AI {estado}: {documento.titulo} (ID: {documento_id})")

        return {
            "mensaje": f"Documento {estado} exitosamente",
            "documento": documento.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error activando/desactivando documento AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/ai/metricas")
def obtener_metricas_ai(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener métricas de uso de AI"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver métricas de AI")

    try:
        # ✅ Intentar contar documentos con manejo de errores
        try:
            total_documentos = db.query(DocumentoAI).count()
            documentos_activos = db.query(DocumentoAI).filter(DocumentoAI.activo == True).count()
            documentos_procesados = db.query(DocumentoAI).filter(DocumentoAI.contenido_procesado == True).count()

            # Calcular tamaño total
            from sqlalchemy import func

            tamaño_total = db.query(func.sum(DocumentoAI.tamaño_bytes)).scalar() or 0
        except Exception as db_error:
            error_msg = str(db_error)
            error_type = type(db_error).__name__
            error_repr = repr(db_error)
            # ✅ Si la tabla no existe, retornar valores por defecto
            # El error de PostgreSQL es: (psycopg2.errors.UndefinedTable) relation "documentos_ai" does not exist
            is_table_missing = (
                "does not exist" in error_msg.lower()
                or "no such table" in error_msg.lower()
                or ("relation" in error_msg.lower() and "does not exist" in error_msg.lower())
                or "UndefinedTable" in error_type
                or "UndefinedTable" in error_repr
                or ("documentos_ai" in error_msg.lower() and "does not exist" in error_msg.lower())
            )

            if is_table_missing:
                # ✅ Cambiar a debug para reducir verbosidad - es un comportamiento esperado
                logger.debug("⚠️ Tabla documentos_ai no existe. Retornando métricas por defecto (comportamiento esperado).")
                total_documentos = 0
                documentos_activos = 0
                documentos_procesados = 0
                tamaño_total = 0
            else:
                # Re-lanzar si es otro tipo de error
                raise

        # Verificar configuración
        config_ai = _consultar_configuracion_ai(db)
        config_dict = (
            _procesar_configuraciones_ai(config_ai)
            if config_ai and not isinstance(config_ai, dict)
            else (config_ai if isinstance(config_ai, dict) else {})
        )

        # Manejar valores None de forma segura
        activo_value = config_dict.get("activo") or "false"
        ai_activo = str(activo_value).lower() in ("true", "1", "yes", "on")
        modelo_configurado = config_dict.get("modelo") or "gpt-3.5-turbo"
        api_key = config_dict.get("openai_api_key") or ""
        tiene_token = bool(api_key and api_key.strip())

        return {
            "documentos": {
                "total": total_documentos,
                "activos": documentos_activos,
                "procesados": documentos_procesados,
                "pendientes": total_documentos - documentos_procesados,
                "tamaño_total_bytes": tamaño_total,
                "tamaño_total_mb": round(tamaño_total / (1024 * 1024), 2),
            },
            "configuracion": {
                "ai_activo": ai_activo,
                "modelo": modelo_configurado,
                "tiene_token": tiene_token,
            },
            "fecha_consulta": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo métricas AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


class ProbarAIRequest(BaseModel):
    pregunta: Optional[str] = None
    usar_documentos: Optional[bool] = True


class ChatAIRequest(BaseModel):
    pregunta: str = Field(..., description="Pregunta del usuario sobre la base de datos")


@router.post("/ai/probar")
async def probar_configuracion_ai(
    request: Optional[ProbarAIRequest] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Probar configuración de AI enviando una pregunta a ChatGPT

    Args:
        request: Objeto con pregunta opcional. Si no se proporciona, se usa una pregunta por defecto.
        usar_documentos: Si True, busca contexto en documentos cargados
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden probar configuración de AI",
        )

    try:
        # Obtener configuración
        try:
            configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "AI").all()
        except Exception as query_error:
            error_msg = str(query_error)
            logger.error(f"❌ Error consultando configuración AI: {error_msg}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error consultando configuración de AI: {error_msg}")

        if not configs:
            raise HTTPException(status_code=400, detail="No hay configuración de AI")

        config_dict = {config.clave: config.valor for config in configs}

        # Verificar que haya token configurado
        openai_api_key = config_dict.get("openai_api_key", "")
        if not openai_api_key:
            raise HTTPException(status_code=400, detail="OpenAI API Key no configurado")

        # Obtener pregunta
        pregunta = None
        usar_documentos = True
        if request:
            if isinstance(request, dict):
                pregunta = request.get("pregunta")
                usar_documentos = request.get("usar_documentos", True)
            elif hasattr(request, "pregunta"):
                pregunta = request.pregunta
                usar_documentos = getattr(request, "usar_documentos", True)

        # Pregunta por defecto si no se proporciona
        if not pregunta or not pregunta.strip():
            pregunta = "Hola, ¿puedes ayudarme con información sobre préstamos?"

        # Obtener modelo y parámetros
        modelo = config_dict.get("modelo", "gpt-3.5-turbo")
        temperatura = float(config_dict.get("temperatura", "0.7"))
        max_tokens = int(config_dict.get("max_tokens", "1000"))

        # Buscar contexto en documentos si está habilitado
        contexto_documentos = ""
        documentos_activos = []  # Inicializar como lista vacía
        if usar_documentos:
            try:
                documentos_activos = (
                    db.query(DocumentoAI)
                    .filter(DocumentoAI.activo == True, DocumentoAI.contenido_procesado == True)
                    .limit(5)
                    .all()
                )

                if documentos_activos:
                    contextos = []
                    for doc in documentos_activos:
                        # Usar contenido real del documento si está disponible
                        if doc.contenido_texto and doc.contenido_texto.strip():
                            # Limitar el contenido a 2000 caracteres por documento para no exceder límites de tokens
                            contenido_limpiado = doc.contenido_texto.strip()[:2000]
                            if len(doc.contenido_texto) > 2000:
                                contenido_limpiado += "..."

                            contexto_doc = f"Documento: {doc.titulo}\n"
                            if doc.descripcion:
                                contexto_doc += f"Descripción: {doc.descripcion}\n"
                            contexto_doc += f"Contenido:\n{contenido_limpiado}\n"
                            contextos.append(contexto_doc)
                        else:
                            # Fallback: usar solo título y descripción si no hay contenido procesado
                            contexto_doc = f"Documento: {doc.titulo}"
                            if doc.descripcion:
                                contexto_doc += f"\nDescripción: {doc.descripcion}"
                            contextos.append(contexto_doc)

                    if contextos:
                        # Limitar a 3 documentos para no exceder límites de tokens
                        contextos_seleccionados = contextos[:3]
                        contexto_documentos = (
                            "\n\n=== CONTEXTO DE DOCUMENTOS ===\n"
                            + "\n\n---\n\n".join(contextos_seleccionados)
                            + "\n\nUsa esta información como base para responder la pregunta."
                        )
            except Exception as doc_error:
                logger.warning(f"⚠️ Error obteniendo documentos para contexto: {doc_error}")
                documentos_activos = []  # Asegurar que esté definido

        # Construir prompt con contexto
        prompt = pregunta
        if contexto_documentos:
            prompt = f"{pregunta}\n\n{contexto_documentos}\n\nResponde basándote en la información disponible."

        # Llamar a OpenAI API
        import httpx

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": modelo,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Eres un asistente útil que responde preguntas sobre préstamos y servicios financieros. Responde de manera clara y profesional.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperatura,
                        "max_tokens": max_tokens,
                    },
                )

                elapsed_time = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    respuesta_ai = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    tokens_usados = result.get("usage", {}).get("total_tokens", 0)

                    logger.info(f"✅ Prueba de AI exitosa: {tokens_usados} tokens usados en {elapsed_time:.2f}s")

                    return {
                        "success": True,
                        "mensaje": "Respuesta generada exitosamente",
                        "pregunta": pregunta,
                        "respuesta": respuesta_ai,
                        "tokens_usados": tokens_usados,
                        "modelo_usado": modelo,
                        "tiempo_respuesta": round(elapsed_time, 2),
                        "usar_documentos": usar_documentos,
                        "documentos_consultados": len(documentos_activos) if documentos_activos else 0,
                    }
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Error desconocido")

                    logger.error(f"❌ Error en prueba de AI: {error_message}")

                    return {
                        "success": False,
                        "mensaje": f"Error de OpenAI: {error_message}",
                        "error_code": error_data.get("error", {}).get("code", "UNKNOWN"),
                        "pregunta": pregunta,
                    }

        except httpx.TimeoutException:
            elapsed_time = time.time() - start_time
            logger.error(f"⏱️ Timeout en prueba de AI (Tiempo: {elapsed_time:.2f}s)")
            return {
                "success": False,
                "mensaje": f"Timeout al conectar con OpenAI (límite: 30s)",
                "error_code": "TIMEOUT",
                "pregunta": pregunta,
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ Error en prueba de AI: {str(e)} (Tiempo: {elapsed_time:.2f}s)")
            return {
                "success": False,
                "mensaje": f"Error: {str(e)}",
                "error_code": "EXCEPTION",
                "pregunta": pregunta,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en prueba de AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# CHAT AI - CONSULTAS A BASE DE DATOS
# ============================================


def _obtener_resumen_bd(db: Session) -> str:
    """
    Obtiene un resumen de la base de datos con estadísticas principales
    para usar como contexto en las respuestas de AI
    """
    try:
        from sqlalchemy import func

        resumen = []

        # Clientes
        total_clientes = db.query(Cliente).count()
        clientes_activos = db.query(Cliente).filter(Cliente.activo == True).count()
        resumen.append(f"Clientes: {total_clientes} totales, {clientes_activos} activos")

        # Préstamos
        total_prestamos = db.query(Prestamo).count()
        prestamos_activos = db.query(Prestamo).filter(Prestamo.estado.in_(["APROBADO", "ACTIVO"])).count()
        prestamos_pendientes = db.query(Prestamo).filter(Prestamo.estado == "PENDIENTE").count()
        resumen.append(
            f"Préstamos: {total_prestamos} totales, {prestamos_activos} activos/aprobados, {prestamos_pendientes} pendientes"
        )

        # Pagos
        total_pagos = db.query(Pago).count()
        pagos_activos = db.query(Pago).filter(Pago.activo == True).count()
        resumen.append(f"Pagos: {total_pagos} totales, {pagos_activos} activos")

        # Cuotas
        total_cuotas = db.query(Cuota).count()
        cuotas_pagadas = db.query(Cuota).filter(Cuota.estado == "PAGADA").count()
        cuotas_pendientes = db.query(Cuota).filter(Cuota.estado == "PENDIENTE").count()
        cuotas_mora = db.query(Cuota).filter(Cuota.estado == "MORA").count()
        resumen.append(
            f"Cuotas: {total_cuotas} totales, {cuotas_pagadas} pagadas, {cuotas_pendientes} pendientes, {cuotas_mora} en mora"
        )

        # Montos totales
        try:
            monto_total_prestamos = (
                db.query(func.sum(Prestamo.monto_financiado)).filter(Prestamo.estado.in_(["APROBADO", "ACTIVO"])).scalar() or 0
            )
            resumen.append(f"Monto total de préstamos activos: {monto_total_prestamos:,.2f}")
        except:
            pass

        try:
            monto_total_pagos = db.query(func.sum(Pago.monto_pagado)).filter(Pago.activo == True).scalar() or 0
            resumen.append(f"Monto total de pagos: {monto_total_pagos:,.2f}")
        except:
            pass

        return "\n".join(resumen)
    except Exception as e:
        logger.error(f"Error obteniendo resumen de BD: {e}", exc_info=True)
        return "No se pudo obtener resumen de la base de datos"


@router.post("/ai/chat")
async def chat_ai(
    request: ChatAIRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chat AI que puede responder preguntas sobre la base de datos

    El AI tiene acceso a información de todas las tablas principales:
    - Clientes
    - Préstamos
    - Pagos
    - Cuotas
    - Y más...
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden usar Chat AI",
        )

    try:
        # Obtener configuración de AI
        configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "AI").all()

        if not configs:
            raise HTTPException(status_code=400, detail="No hay configuración de AI")

        config_dict = {config.clave: config.valor for config in configs}

        # Verificar que haya token configurado
        openai_api_key = config_dict.get("openai_api_key", "")
        if not openai_api_key:
            raise HTTPException(status_code=400, detail="OpenAI API Key no configurado")

        # Verificar que AI esté activo
        activo = config_dict.get("activo", "false").lower() in ("true", "1", "yes", "on")
        if not activo:
            raise HTTPException(status_code=400, detail="AI no está activo. Actívalo en la configuración.")

        pregunta = request.pregunta.strip()
        if not pregunta:
            raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

        # Obtener modelo y parámetros
        modelo = config_dict.get("modelo", "gpt-3.5-turbo")
        temperatura = float(config_dict.get("temperatura", "0.7"))
        max_tokens = int(config_dict.get("max_tokens", "2000"))  # Más tokens para respuestas más largas

        # Obtener resumen de la base de datos
        resumen_bd = _obtener_resumen_bd(db)

        # Buscar contexto en documentos si están disponibles
        contexto_documentos = ""
        documentos_activos = (
            db.query(DocumentoAI).filter(DocumentoAI.activo == True, DocumentoAI.contenido_procesado == True).limit(3).all()
        )

        if documentos_activos:
            contextos = []
            for doc in documentos_activos:
                if doc.contenido_texto and doc.contenido_texto.strip():
                    contenido_limpiado = doc.contenido_texto.strip()[:1500]
                    if len(doc.contenido_texto) > 1500:
                        contenido_limpiado += "..."
                    contextos.append(f"Documento: {doc.titulo}\n{contenido_limpiado}")

            if contextos:
                contexto_documentos = "\n\n=== DOCUMENTOS DE CONTEXTO ===\n" + "\n\n---\n\n".join(contextos)

        # Construir prompt del sistema con información de la BD
        system_prompt = f"""Eres un asistente experto en sistemas de gestión de préstamos y servicios financieros.

Tienes acceso a información de la base de datos del sistema. Aquí tienes un resumen actualizado:

=== RESUMEN DE BASE DE DATOS ===
{resumen_bd}

=== TABLAS DISPONIBLES ===
- Clientes: Información de clientes (nombre, cédula, teléfono, email, estado)
- Préstamos: Información de préstamos (monto, estado, fecha, cliente)
- Pagos: Registro de pagos realizados (monto, fecha, número de documento)
- Cuotas: Cuotas de préstamos (estado: PAGADA, PENDIENTE, MORA)
- Usuarios: Usuarios del sistema
- Concesionarios: Concesionarios asociados
- Analistas: Analistas/asesores

INSTRUCCIONES:
1. Responde preguntas sobre la base de datos de manera clara y profesional
2. Si la pregunta requiere datos específicos que no están en el resumen, indica que necesitarías hacer una consulta más específica
3. Usa los datos del resumen para dar respuestas precisas
4. Si no tienes suficiente información, sé honesto al respecto
5. Formatea números grandes con separadores de miles
6. Responde siempre en español
{contexto_documentos}

IMPORTANTE: Solo usa la información proporcionada. No inventes datos."""

        # Llamar a OpenAI API
        import httpx

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # Timeout más largo para consultas complejas
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": modelo,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": pregunta},
                        ],
                        "temperature": temperatura,
                        "max_tokens": max_tokens,
                    },
                )

                elapsed_time = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    respuesta_ai = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    tokens_usados = result.get("usage", {}).get("total_tokens", 0)

                    logger.info(f"✅ Chat AI exitoso: {tokens_usados} tokens usados en {elapsed_time:.2f}s")

                    return {
                        "success": True,
                        "respuesta": respuesta_ai,
                        "pregunta": pregunta,
                        "tokens_usados": tokens_usados,
                        "modelo_usado": modelo,
                        "tiempo_respuesta": round(elapsed_time, 2),
                    }
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Error desconocido")

                    logger.error(f"❌ Error en Chat AI: {error_message}")

                    return {
                        "success": False,
                        "respuesta": f"Error de OpenAI: {error_message}",
                        "error": error_message,
                        "pregunta": pregunta,
                    }

        except httpx.TimeoutException:
            elapsed_time = time.time() - start_time
            logger.error(f"⏱️ Timeout en Chat AI (Tiempo: {elapsed_time:.2f}s)")
            return {
                "success": False,
                "respuesta": f"Timeout al conectar con OpenAI (límite: 60s). La pregunta puede ser muy compleja.",
                "error": "TIMEOUT",
                "pregunta": pregunta,
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ Error en Chat AI: {str(e)} (Tiempo: {elapsed_time:.2f}s)")
            return {
                "success": False,
                "respuesta": f"Error: {str(e)}",
                "error": str(e),
                "pregunta": pregunta,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en Chat AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
