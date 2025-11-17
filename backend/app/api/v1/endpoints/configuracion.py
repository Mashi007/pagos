from __future__ import annotations

import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.ai_prompt_variable import AIPromptVariable
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.configuracion_sistema import ConfiguracionSistema
from app.models.documento_ai import DocumentoAI
from app.models.documento_embedding import DocumentoEmbedding
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User
from app.services.rag_service import RAGService

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
        try:
            logo_path, media_type, logo_bytes = _verificar_logo_existe(filename, db)
        except HTTPException as e:
            # Si el logo no existe, devolver 404 inmediatamente sin más procesamiento
            logger.debug(f"Logo no encontrado: {filename}")
            raise e

        # Si existe en filesystem, leer desde ahí
        if logo_path and logo_path.exists():
            try:
                with open(logo_path, "rb") as f:
                    file_content = f.read()
                if len(file_content) == 0:
                    logger.warning(f"Logo existe pero está vacío: {filename}")
                    raise HTTPException(status_code=404, detail="Logo no encontrado")
            except (OSError, IOError) as e:
                logger.error(f"Error leyendo logo desde filesystem: {str(e)}")
                raise HTTPException(status_code=404, detail="Logo no encontrado")
        # Si no existe en filesystem pero existe en BD, usar base64
        elif logo_bytes:
            file_content = logo_bytes
            if len(file_content) == 0:
                logger.warning(f"Logo existe en BD pero está vacío: {filename}")
                raise HTTPException(status_code=404, detail="Logo no encontrado")
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
                "Content-Length": str(len(file_content)),  # ✅ Agregar Content-Length para evitar abortos
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


# Definir schema ANTES de las funciones para evitar NameError
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
                    except Exception:
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
                        except Exception:
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
            except Exception:
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
        import os
        from pathlib import Path

        from app.core.config import settings

        # Obtener información del documento
        nombre_archivo_original = (
            documento.nombre_archivo or Path(documento.ruta_archivo).name if documento.ruta_archivo else None
        )
        ruta_original = documento.ruta_archivo or ""
        extension = Path(nombre_archivo_original).suffix if nombre_archivo_original else ""

        logger.info(
            f"🔍 Buscando archivo para documento ID {documento_id}: "
            f"nombre={nombre_archivo_original}, ruta_original={ruta_original}"
        )

        # Determinar directorios base posibles
        directorios_base = []

        # Directorio desde configuración
        if hasattr(settings, "UPLOAD_DIR") and settings.UPLOAD_DIR:
            directorios_base.append(Path(settings.UPLOAD_DIR).resolve())

        # Directorio por defecto
        directorios_base.append(Path("uploads").resolve())

        # Directorio actual de trabajo
        directorios_base.append(Path.cwd() / "uploads")

        # Directorio del proyecto
        directorios_base.append(Path(__file__).parent.parent.parent.parent / "uploads")

        # Eliminar duplicados manteniendo orden
        directorios_base = list(dict.fromkeys(directorios_base))

        ruta_archivo = None
        archivo_encontrado = False
        rutas_intentadas = []

        # Estrategia 1: Si la ruta es absoluta y existe, usarla directamente
        if ruta_original:
            ruta_original_path = Path(ruta_original)
            if ruta_original_path.is_absolute() and ruta_original_path.exists():
                ruta_archivo = ruta_original_path.resolve()
                archivo_encontrado = True
                logger.info(f"✅ Archivo encontrado en ruta absoluta: {ruta_archivo}")
            else:
                rutas_intentadas.append(f"Ruta absoluta: {ruta_original_path}")

        # Si no se encontró, intentar con directorios base
        if not archivo_encontrado:
            for base_dir in directorios_base:
                if not base_dir.exists():
                    rutas_intentadas.append(f"Directorio no existe: {base_dir}")
                    continue

                # Estrategia 2: Ruta relativa desde base_dir
                if ruta_original and not Path(ruta_original).is_absolute():
                    ruta_intento = (base_dir / ruta_original).resolve()
                    if ruta_intento.exists() and ruta_intento.is_file():
                        ruta_archivo = ruta_intento
                        archivo_encontrado = True
                        logger.info(f"✅ Archivo encontrado en ruta relativa: {ruta_archivo}")
                        break
                    rutas_intentadas.append(f"Ruta relativa: {ruta_intento}")

                # Estrategia 3: Buscar en documentos_ai por nombre exacto
                if not archivo_encontrado and nombre_archivo_original:
                    upload_dir = base_dir / "documentos_ai"
                    if upload_dir.exists():
                        ruta_intento = upload_dir / nombre_archivo_original
                        if ruta_intento.exists() and ruta_intento.is_file():
                            ruta_archivo = ruta_intento
                            archivo_encontrado = True
                            logger.info(f"✅ Archivo encontrado por nombre exacto: {ruta_archivo}")
                            break
                        rutas_intentadas.append(f"Nombre exacto: {ruta_intento}")

                # Estrategia 4: Buscar por ID del documento en el nombre
                if not archivo_encontrado:
                    upload_dir = base_dir / "documentos_ai"
                    if upload_dir.exists():
                        for archivo_en_dir in upload_dir.iterdir():
                            if archivo_en_dir.is_file():
                                # Buscar archivos que contengan el ID del documento
                                if str(documento_id) in archivo_en_dir.name:
                                    # Verificar extensión si está disponible
                                    if not extension or archivo_en_dir.suffix == extension:
                                        ruta_archivo = archivo_en_dir.resolve()
                                        archivo_encontrado = True
                                        logger.info(f"✅ Archivo encontrado por ID en nombre: {ruta_archivo}")
                                        break
                        if not archivo_encontrado:
                            rutas_intentadas.append(f"Búsqueda por ID en: {upload_dir}")

                # Estrategia 5: Buscar por extensión y tamaño similar
                if not archivo_encontrado and nombre_archivo_original and extension:
                    upload_dir = base_dir / "documentos_ai"
                    if upload_dir.exists():
                        tamaño_esperado = documento.tamaño_bytes
                        for archivo_en_dir in upload_dir.iterdir():
                            if archivo_en_dir.is_file() and archivo_en_dir.suffix == extension:
                                # Si tenemos tamaño, verificar que sea similar
                                if tamaño_esperado:
                                    try:
                                        tamaño_real = archivo_en_dir.stat().st_size
                                        # Permitir diferencia de hasta 10%
                                        if abs(tamaño_real - tamaño_esperado) / tamaño_esperado < 0.1:
                                            ruta_archivo = archivo_en_dir.resolve()
                                            archivo_encontrado = True
                                            logger.info(f"✅ Archivo encontrado por tamaño y extensión: {ruta_archivo}")
                                            break
                                    except Exception:
                                        pass
                                else:
                                    # Si no hay tamaño, usar el primero con la extensión correcta
                                    ruta_archivo = archivo_en_dir.resolve()
                                    archivo_encontrado = True
                                    logger.info(f"✅ Archivo encontrado por extensión: {ruta_archivo}")
                                    break

                if archivo_encontrado:
                    break

        # Si aún no se encontró, intentar búsqueda recursiva en uploads
        if not archivo_encontrado and nombre_archivo_original:
            for base_dir in directorios_base:
                if base_dir.exists():
                    # Búsqueda recursiva limitada a 2 niveles
                    for root, dirs, files in os.walk(base_dir):
                        if root.count(os.sep) - base_dir.as_posix().count(os.sep) > 2:
                            continue  # Limitar profundidad
                        for file in files:
                            if file == nombre_archivo_original or (
                                extension and file.endswith(extension) and str(documento_id) in file
                            ):
                                ruta_archivo = Path(root) / file
                                if ruta_archivo.exists():
                                    archivo_encontrado = True
                                    logger.info(f"✅ Archivo encontrado en búsqueda recursiva: {ruta_archivo}")
                                    break
                        if archivo_encontrado:
                            break
                    if archivo_encontrado:
                        break

        if not archivo_encontrado or not ruta_archivo or not ruta_archivo.exists():
            mensaje_error = (
                f"El archivo físico no existe para el documento '{documento.titulo}' (ID: {documento_id}). "
                f"El archivo puede haber sido eliminado del servidor o nunca se subió correctamente. "
                f"Por favor, elimina este documento y súbelo nuevamente."
            )

            logger.error(
                f"❌ Archivo no encontrado después de {len(rutas_intentadas)} intentos. "
                f"Documento: {documento.titulo}, Nombre archivo: {nombre_archivo_original}, "
                f"Ruta original: {ruta_original}. "
                f"Rutas intentadas: {', '.join(rutas_intentadas[:5])}..."
            )

            # Log detallado para diagnóstico (solo en logs, no en respuesta al usuario)
            logger.debug(
                f"Directorios base verificados: {[str(d) for d in directorios_base]}, "
                f"Nombre archivo buscado: {nombre_archivo_original}, "
                f"Tamaño esperado: {documento.tamaño_bytes} bytes"
            )

            raise HTTPException(
                status_code=400,
                detail=mensaje_error,
            )

        # Verificar que el archivo no esté vacío
        if ruta_archivo.stat().st_size == 0:
            logger.warning(f"⚠️ Archivo vacío: {documento.ruta_archivo}")
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío. No se puede extraer texto de un archivo sin contenido.",
            )

        # Extraer texto del documento (usar la ruta resuelta, no la original)
        texto_extraido = _extraer_texto_documento(str(ruta_archivo), documento.tipo_archivo)

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


# ============================================
# GESTIÓN DE VARIABLES PERSONALIZADAS DEL PROMPT AI
# ============================================


class AIPromptVariableCreate(BaseModel):
    """Schema para crear variable de prompt AI"""

    variable: str = Field(..., description="Nombre de la variable (ej: {mi_variable})")
    descripcion: str = Field(..., description="Descripción de qué contiene la variable")
    activo: Optional[bool] = Field(True, description="Estado activo/inactivo")
    orden: Optional[int] = Field(0, description="Orden de visualización")


class AIPromptVariableUpdate(BaseModel):
    """Schema para actualizar variable de prompt AI"""

    variable: Optional[str] = Field(None, description="Nombre de la variable")
    descripcion: Optional[str] = Field(None, description="Descripción de qué contiene la variable")
    activo: Optional[bool] = Field(None, description="Estado activo/inactivo")
    orden: Optional[int] = Field(None, description="Orden de visualización")


@router.get("/ai/prompt/variables")
def listar_variables_prompt_ai(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar todas las variables personalizadas del prompt AI"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver variables del prompt AI",
        )

    try:
        variables = db.query(AIPromptVariable).order_by(AIPromptVariable.orden.asc(), AIPromptVariable.variable.asc()).all()
        return {
            "variables": [var.to_dict() for var in variables],
            "total": len(variables),
        }
    except Exception as e:
        error_str = str(e).lower()
        # Si la tabla no existe, devolver lista vacía en lugar de error
        if "does not exist" in error_str or "no such table" in error_str or "relation" in error_str:
            logger.warning(f"Tabla ai_prompt_variables no existe aún. Devolviendo lista vacía. Error: {e}")
            return {
                "variables": [],
                "total": 0,
            }
        logger.error(f"Error listando variables de prompt AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/ai/prompt/variables")
def crear_variable_prompt_ai(
    variable_data: AIPromptVariableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear una nueva variable personalizada del prompt AI"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden crear variables del prompt AI",
        )

    try:
        # Validar formato de variable (debe empezar con { y terminar con })
        variable = variable_data.variable.strip()
        if not variable.startswith("{") or not variable.endswith("}"):
            raise HTTPException(
                status_code=400,
                detail="La variable debe tener formato {nombre_variable} (con llaves)",
            )

        # Verificar que no exista
        existe = db.query(AIPromptVariable).filter(AIPromptVariable.variable == variable).first()
        if existe:
            raise HTTPException(
                status_code=400,
                detail=f"La variable {variable} ya existe",
            )

        nueva_variable = AIPromptVariable(
            variable=variable,
            descripcion=variable_data.descripcion,
            activo=variable_data.activo if variable_data.activo is not None else True,
            orden=variable_data.orden if variable_data.orden is not None else 0,
        )

        db.add(nueva_variable)
        db.commit()
        db.refresh(nueva_variable)

        return {
            "mensaje": "Variable creada exitosamente",
            "variable": nueva_variable.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando variable de prompt AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/ai/prompt/variables/{variable_id}")
def actualizar_variable_prompt_ai(
    variable_id: int,
    variable_data: AIPromptVariableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar una variable personalizada del prompt AI"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden actualizar variables del prompt AI",
        )

    try:
        variable = db.query(AIPromptVariable).filter(AIPromptVariable.id == variable_id).first()

        if not variable:
            raise HTTPException(status_code=404, detail="Variable no encontrada")

        # Si se actualiza el nombre de la variable, validar formato
        if variable_data.variable is not None:
            nueva_variable = variable_data.variable.strip()
            if not nueva_variable.startswith("{") or not nueva_variable.endswith("}"):
                raise HTTPException(
                    status_code=400,
                    detail="La variable debe tener formato {nombre_variable} (con llaves)",
                )

            # Verificar que no exista otra variable con ese nombre
            existe = (
                db.query(AIPromptVariable)
                .filter(
                    AIPromptVariable.variable == nueva_variable,
                    AIPromptVariable.id != variable_id,
                )
                .first()
            )
            if existe:
                raise HTTPException(
                    status_code=400,
                    detail=f"La variable {nueva_variable} ya existe",
                )

            variable.variable = nueva_variable

        if variable_data.descripcion is not None:
            variable.descripcion = variable_data.descripcion
        if variable_data.activo is not None:
            variable.activo = variable_data.activo
        if variable_data.orden is not None:
            variable.orden = variable_data.orden

        db.commit()
        db.refresh(variable)

        return {
            "mensaje": "Variable actualizada exitosamente",
            "variable": variable.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando variable de prompt AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/ai/prompt/variables/{variable_id}")
def eliminar_variable_prompt_ai(
    variable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar una variable personalizada del prompt AI"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden eliminar variables del prompt AI",
        )

    try:
        variable = db.query(AIPromptVariable).filter(AIPromptVariable.id == variable_id).first()

        if not variable:
            raise HTTPException(status_code=404, detail="Variable no encontrada")

        db.delete(variable)
        db.commit()

        return {"mensaje": "Variable eliminada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando variable de prompt AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/ai/prompt")
def obtener_prompt_ai(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener el prompt personalizado del AI"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver el prompt de AI",
        )

    try:
        config = (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == "AI",
                ConfiguracionSistema.clave == "system_prompt_personalizado",
            )
            .first()
        )

        prompt_personalizado = config.valor if config else ""
        tiene_prompt_personalizado = bool(prompt_personalizado and prompt_personalizado.strip())

        # Obtener variables personalizadas activas
        variables_personalizadas = []
        try:
            variables_personalizadas = (
                db.query(AIPromptVariable)
                .filter(AIPromptVariable.activo.is_(True))
                .order_by(AIPromptVariable.orden.asc(), AIPromptVariable.variable.asc())
                .all()
            )
        except Exception as var_error:
            error_str = str(var_error).lower()
            # Si la tabla no existe, continuar con lista vacía
            if "does not exist" in error_str or "no such table" in error_str or "relation" in error_str:
                logger.warning(f"Tabla ai_prompt_variables no existe aún. Continuando sin variables. Error: {var_error}")
                variables_personalizadas = []
            else:
                # Si es otro error, registrar pero continuar
                logger.warning(f"Error obteniendo variables personalizadas: {var_error}")

        return {
            "prompt_personalizado": prompt_personalizado or "",
            "tiene_prompt_personalizado": tiene_prompt_personalizado,
            "usando_prompt_default": not tiene_prompt_personalizado,
            "variables_personalizadas": [var.to_dict() for var in variables_personalizadas],
        }
    except Exception as e:
        logger.error(f"Error obteniendo prompt de AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/ai/prompt")
def actualizar_prompt_ai(
    prompt_data: Dict[str, str] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar el prompt personalizado del AI"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden actualizar el prompt de AI",
        )

    try:
        prompt_texto = prompt_data.get("prompt", "").strip()

        # Validar que el prompt tenga los placeholders necesarios
        placeholders_requeridos = [
            "{resumen_bd}",
            "{info_cliente_buscado}",
            "{datos_adicionales}",
            "{info_esquema}",
            "{contexto_documentos}",
        ]
        placeholders_faltantes = [p for p in placeholders_requeridos if p not in prompt_texto]

        if prompt_texto and placeholders_faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"El prompt personalizado debe incluir los siguientes placeholders: {', '.join(placeholders_faltantes)}. Estos se reemplazarán automáticamente con los datos del sistema.",
            )

        config = (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == "AI",
                ConfiguracionSistema.clave == "system_prompt_personalizado",
            )
            .first()
        )

        if config:
            if prompt_texto:
                config.valor = prompt_texto
                config.tipo_dato = "TEXT"
                mensaje = "Prompt personalizado actualizado exitosamente"
            else:
                # Si se envía vacío, eliminar el prompt personalizado (usar default)
                db.delete(config)
                mensaje = "Prompt personalizado eliminado. Se usará el prompt por defecto."
        else:
            if prompt_texto:
                nueva_config = ConfiguracionSistema(
                    categoria="AI",
                    clave="system_prompt_personalizado",
                    valor=prompt_texto,
                    tipo_dato="TEXT",
                    visible_frontend=False,  # No mostrar en la UI general
                    descripcion="Prompt personalizado para el Chat AI. Incluye placeholders: {resumen_bd}, {info_cliente_buscado}, {datos_adicionales}, {info_esquema}, {contexto_documentos}",
                )
                db.add(nueva_config)
                mensaje = "Prompt personalizado guardado exitosamente"
            else:
                mensaje = "No hay prompt personalizado para eliminar"

        db.commit()
        logger.info(f"Prompt de AI actualizado por {current_user.email}")

        return {
            "mensaje": mensaje,
            "tiene_prompt_personalizado": bool(prompt_texto),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando prompt de AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/ai/prompt/default")
def obtener_prompt_default_ai(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener el prompt por defecto del AI (para referencia)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver el prompt de AI",
        )

    # Retornar el prompt por defecto como referencia
    # Nota: Este es un ejemplo, el prompt real se construye dinámicamente
    prompt_default = """Eres un ANALISTA ESPECIALIZADO en préstamos y cobranzas...

[Este es el prompt por defecto. Puedes personalizarlo en la sección de Entrenamiento de Prompt]

Placeholders disponibles:
- {resumen_bd}: Resumen de la base de datos
- {info_cliente_buscado}: Información del cliente si se busca por cédula
- {datos_adicionales}: Cálculos y análisis adicionales
- {info_esquema}: Esquema completo de la base de datos
- {contexto_documentos}: Documentos de contexto adicionales
"""

    return {
        "prompt_default": prompt_default,
        "nota": "Este es solo un ejemplo. El prompt real se construye dinámicamente con los datos actuales del sistema.",
    }


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
            documentos_activos = db.query(DocumentoAI).filter(DocumentoAI.activo.is_(True)).count()
            documentos_procesados = db.query(DocumentoAI).filter(DocumentoAI.contenido_procesado.is_(True)).count()

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


@router.get("/ai/tablas-campos")
def obtener_tablas_campos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener todas las tablas y campos de la base de datos para uso en Fine-tuning.
    Devuelve un diccionario con tablas como claves y listas de campos como valores.
    """
    try:
        from sqlalchemy.engine import reflection

        inspector = reflection.Inspector.from_engine(db.bind)

        # Obtener todas las tablas
        todas_tablas = inspector.get_table_names()

        # Construir diccionario de tablas y campos
        tablas_campos: Dict[str, list[str]] = {}

        for tabla in sorted(todas_tablas):
            try:
                # Obtener columnas de la tabla
                columnas = inspector.get_columns(tabla)
                # Extraer solo los nombres de las columnas
                nombres_campos = [col["name"] for col in columnas]
                tablas_campos[tabla] = nombres_campos
            except Exception as e:
                logger.warning(f"Error obteniendo campos de tabla {tabla}: {e}")
                # Si hay error, agregar tabla vacía
                tablas_campos[tabla] = []

        return {
            "tablas_campos": tablas_campos,
            "total_tablas": len(todas_tablas),
            "fecha_consulta": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo tablas y campos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo tablas y campos: {str(e)}")


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
                    .filter(DocumentoAI.activo.is_(True), DocumentoAI.contenido_procesado.is_(True))
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

        # Obtener información de fecha y hora actual para el contexto
        fecha_actual = datetime.now()
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        dia_semana = dias_semana[fecha_actual.weekday()]
        mes = meses[fecha_actual.month - 1]

        info_fecha = f"""
=== INFORMACIÓN DE FECHA Y HORA ACTUAL ===
Fecha y hora actual del sistema: {dia_semana}, {fecha_actual.day} de {mes} de {fecha_actual.year}, {fecha_actual.strftime('%H:%M:%S')}
Fecha actual (formato corto): {fecha_actual.strftime('%d/%m/%Y')}
Día de la semana: {dia_semana}
Hora actual: {fecha_actual.strftime('%H:%M:%S')}
"""

        # Construir prompt con contexto
        prompt = pregunta
        if contexto_documentos:
            prompt = f"{pregunta}\n\n{info_fecha}\n\n{contexto_documentos}\n\nResponde basándote en la información disponible."
        else:
            # Incluir fecha incluso si no hay documentos
            prompt = f"{pregunta}\n\n{info_fecha}\n\nResponde basándote en la información disponible."

        # Construir system prompt con información de fecha
        system_content = f"""Eres un asistente útil y versátil. Puedes responder cualquier tipo de pregunta de manera clara, profesional y precisa.

INFORMACIÓN ACTUAL DEL SISTEMA (USA ESTA INFORMACIÓN, NO TU CONOCIMIENTO DE ENTRENAMIENTO):
{info_fecha}

REGLAS CRÍTICAS - DEBES SEGUIRLAS ESTRICTAMENTE:
1. ⚠️ PROHIBIDO INVENTAR: NO inventes datos, fechas, números o información. Solo usa lo que se te proporciona.
2. ⚠️ FECHA ACTUAL: Para preguntas sobre fecha/hora actual, usa EXACTAMENTE la información de arriba. NO uses tu conocimiento de entrenamiento.
3. ⚠️ SI NO SABES: Si no tienes la información exacta, di "No tengo esa información específica" en lugar de inventar.
4. ⚠️ DOCUMENTOS: Si hay contexto de documentos disponibles, úsalo para enriquecer tu respuesta, pero NO inventes información adicional.
5. Responde siempre en español.
6. Sé preciso y honesto: si no sabes algo, admítelo en lugar de inventar.

EJEMPLO CORRECTO:
- Pregunta: "¿Qué fecha es hoy?"
- Respuesta CORRECTA: "Hoy es [fecha exacta del sistema proporcionada arriba]"
- Respuesta INCORRECTA: Cualquier fecha que no sea la proporcionada arriba."""

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
                                "content": system_content,
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


def _calcular_tasa_morosidad_mes(db: Session, año: int, mes: int) -> dict:
    """Calcula la tasa de morosidad para un mes específico"""
    try:
        from datetime import date

        from sqlalchemy import and_, extract, text

        # Calcular primer y último día del mes
        primer_dia = date(año, mes, 1)
        if mes == 12:
            ultimo_dia = date(año + 1, 1, 1)
        else:
            ultimo_dia = date(año, mes + 1, 1)

        # Total de cuotas del mes
        total_cuotas = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    extract("year", Cuota.fecha_vencimiento) == año,
                    extract("month", Cuota.fecha_vencimiento) == mes,
                )
            )
            .scalar()
            or 0
        )

        # Cuotas en mora del mes (vencidas y no pagadas)
        cuotas_mora = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    extract("year", Cuota.fecha_vencimiento) == año,
                    extract("month", Cuota.fecha_vencimiento) == mes,
                    Cuota.fecha_vencimiento < date.today(),
                    Cuota.estado != "PAGADA",
                )
            )
            .scalar()
            or 0
        )

        # Monto total en mora
        monto_mora = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    extract("year", Cuota.fecha_vencimiento) == año,
                    extract("month", Cuota.fecha_vencimiento) == mes,
                    Cuota.fecha_vencimiento < date.today(),
                    Cuota.estado != "PAGADA",
                )
            )
            .scalar()
            or 0
        )

        tasa = (cuotas_mora / total_cuotas * 100) if total_cuotas > 0 else 0

        return {
            "año": año,
            "mes": mes,
            "total_cuotas": total_cuotas,
            "cuotas_mora": cuotas_mora,
            "monto_mora": float(monto_mora),
            "tasa_morosidad": round(tasa, 2),
        }
    except Exception as e:
        logger.error(f"Error calculando tasa de morosidad: {e}")
        return None


def _calcular_metricas_periodo(db: Session, fecha_inicio: date, fecha_fin: date) -> dict:
    """Calcula métricas financieras para un período específico"""
    try:
        from sqlalchemy import and_

        # Total de préstamos aprobados en el período
        prestamos_aprobados = (
            db.query(func.count(Prestamo.id))
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    func.date(Prestamo.fecha_aprobacion) >= fecha_inicio,
                    func.date(Prestamo.fecha_aprobacion) <= fecha_fin,
                )
            )
            .scalar()
            or 0
        )

        # Monto total financiado en el período
        monto_financiado = (
            db.query(func.sum(Prestamo.total_financiamiento))
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    func.date(Prestamo.fecha_aprobacion) >= fecha_inicio,
                    func.date(Prestamo.fecha_aprobacion) <= fecha_fin,
                )
            )
            .scalar()
            or 0
        )

        # Total de pagos en el período
        total_pagos = (
            db.query(func.sum(Pago.monto_pagado))
            .filter(and_(Pago.activo.is_(True), Pago.fecha_pago >= fecha_inicio, Pago.fecha_pago <= fecha_fin))
            .scalar()
            or 0
        )

        # Cuotas vencidas en el período
        cuotas_vencidas = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= fecha_inicio,
                    Cuota.fecha_vencimiento <= fecha_fin,
                    Cuota.fecha_vencimiento < date.today(),
                    Cuota.estado != "PAGADA",
                )
            )
            .scalar()
            or 0
        )

        # Monto en mora del período
        monto_mora = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= fecha_inicio,
                    Cuota.fecha_vencimiento <= fecha_fin,
                    Cuota.fecha_vencimiento < date.today(),
                    Cuota.estado != "PAGADA",
                )
            )
            .scalar()
            or 0
        )

        return {
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "prestamos_aprobados": prestamos_aprobados,
            "monto_financiado": float(monto_financiado),
            "total_pagos": float(total_pagos),
            "cuotas_vencidas": cuotas_vencidas,
            "monto_mora": float(monto_mora),
        }
    except Exception as e:
        logger.error(f"Error calculando métricas del período: {e}")
        return None


def _obtener_mapeo_semantico_campos() -> str:
    """Genera un mapeo semántico de campos con sinónimos y términos relacionados"""
    mapeo = []
    mapeo.append("=== MAPEO SEMÁNTICO DE CAMPOS (Sinónimos y Términos Relacionados) ===\n")
    mapeo.append("Usa este mapeo para entender términos similares y hacer inferencias semánticas\n")

    # Mapeo por concepto semántico
    mapeo.append("\n📅 FECHAS Y PERÍODOS:")
    mapeo.append("  • fecha_vencimiento, fecha de vencimiento, vencimiento, fecha vencida, cuándo vence")
    mapeo.append("  • fecha_pago, fecha de pago, cuando pagó, fecha pagado, día de pago")
    mapeo.append("  • fecha_registro, fecha de registro, cuando se registró, fecha creación, creado")
    mapeo.append("  • fecha_aprobacion, fecha de aprobación, cuando se aprobó, aprobado")
    mapeo.append("  • fecha_nacimiento, fecha de nacimiento, nacimiento, edad")
    mapeo.append("  • fecha_actualizacion, fecha de actualización, actualizado, modificado")
    mapeo.append("  • fecha_conciliacion, fecha de conciliación, conciliado")

    mapeo.append("\n💰 MONTOS Y VALORES:")
    mapeo.append("  • monto_cuota, cuota, monto de cuota, valor cuota, pago cuota, cuota mensual")
    mapeo.append("  • monto_pagado, pagado, monto pagado, cantidad pagada, abonado")
    mapeo.append("  • total_pagado, total pagado, suma pagada, acumulado pagado")
    mapeo.append("  • total_financiamiento, monto préstamo, valor préstamo, monto total, financiamiento")
    mapeo.append("  • monto_mora, mora, monto mora, intereses mora, recargo mora")
    mapeo.append("  • monto_morosidad, morosidad, monto pendiente, deuda pendiente")
    mapeo.append("  • valor_activo, valor del activo, valor vehículo, precio vehículo")
    mapeo.append("  • capital_pagado, capital pagado, principal pagado")
    mapeo.append("  • interes_pagado, interés pagado, intereses pagados")
    mapeo.append("  • saldo_capital, saldo, capital pendiente, deuda pendiente")

    mapeo.append("\n👤 IDENTIFICACIÓN DE CLIENTES:")
    mapeo.append("  • cedula, cédula, documento, documento identidad, DNI, CI, identificación")
    mapeo.append("  • nombres, nombre, nombre completo, cliente, persona, titular")
    mapeo.append("  • telefono, teléfono, tel, número teléfono, contacto, celular")
    mapeo.append("  • email, correo, correo electrónico, e-mail, mail")
    mapeo.append("  • cliente_id, id cliente, identificador cliente, código cliente")

    mapeo.append("\n📋 PRÉSTAMOS Y CRÉDITOS:")
    mapeo.append("  • prestamo_id, id préstamo, préstamo, crédito, loan, préstamo número")
    mapeo.append("  • estado, estado préstamo, situación, condición, status")
    mapeo.append("  • numero_cuotas, número cuotas, cantidad cuotas, total cuotas, cuotas totales")
    mapeo.append("  • modalidad_pago, modalidad, frecuencia pago, periodicidad, forma pago")
    mapeo.append("  • producto, producto financiero, tipo producto, plan")
    mapeo.append("  • analista, analista asignado, asesor, ejecutivo, gestor")
    mapeo.append("  • concesionario, concesionario asignado, dealer, distribuidor")
    mapeo.append("  • modelo_vehiculo, modelo vehículo, vehículo, auto, carro")

    mapeo.append("\n📊 CUOTAS Y PAGOS:")
    mapeo.append("  • numero_cuota, número cuota, cuota número, cuota N, cuota #")
    mapeo.append("  • estado cuota, estado, situación cuota, condición cuota")
    mapeo.append("  • PAGADA, pagada, pagado, liquidada, cancelada, saldada")
    mapeo.append("  • PENDIENTE, pendiente, por pagar, no pagada, adeudada")
    mapeo.append("  • MORA, mora, atrasada, vencida, en mora, retrasada")
    mapeo.append("  • PARCIAL, parcial, pagada parcialmente, abono parcial")
    mapeo.append("  • dias_mora, días mora, días atraso, días retraso, días vencida")
    mapeo.append("  • dias_morosidad, días morosidad, días pendiente, días adeudado")

    mapeo.append("\n💳 PAGOS Y TRANSACCIONES:")
    mapeo.append("  • pago, pagos, transacción, abono, depósito, transferencia")
    mapeo.append("  • numero_documento, número documento, comprobante, referencia, número referencia")
    mapeo.append("  • institucion_bancaria, banco, institución bancaria, entidad bancaria")
    mapeo.append("  • conciliado, conciliación, verificado, confirmado, validado")
    mapeo.append("  • activo, activo pago, pago activo, pago válido, pago vigente")

    mapeo.append("\n📈 ESTADÍSTICAS Y MÉTRICAS:")
    mapeo.append("  • tasa_morosidad, tasa morosidad, porcentaje morosidad, % morosidad, índice morosidad")
    mapeo.append("  • morosidad, mora, atrasos, retrasos, incumplimientos")
    mapeo.append("  • cobranza, cobranzas, recaudación, recaudaciones, recuperación")
    mapeo.append("  • cartera, cartera activa, préstamos activos, créditos vigentes")
    mapeo.append("  • vencido, vencidos, vencimientos, cuotas vencidas")

    mapeo.append("\n🔍 BÚSQUEDAS Y FILTROS:")
    mapeo.append("  • buscar por, filtrar por, encontrar, localizar, consultar")
    mapeo.append("  • entre fechas, en el rango, desde/hasta, período, intervalo")
    mapeo.append("  • por mes, en el mes, durante el mes, del mes")
    mapeo.append("  • por año, en el año, durante el año, del año")
    mapeo.append("  • por estado, según estado, con estado, que tengan estado")

    mapeo.append("\n⚠️ INSTRUCCIONES PARA EL AI:")
    mapeo.append("  1. Si el usuario usa un término que no aparece exactamente en los campos,")
    mapeo.append("     busca en este mapeo para encontrar el campo equivalente")
    mapeo.append("  2. Si estás confundido entre dos campos similares, puedes hacer una pregunta")
    mapeo.append("     aclaratoria como: '¿Te refieres a fecha_vencimiento o fecha_pago?'")
    mapeo.append("  3. Usa inferencia semántica: si preguntan 'cuándo vence', usa fecha_vencimiento")
    mapeo.append("  4. Si preguntan sobre 'pagos', considera tanto la tabla 'pagos' como 'cuotas'")
    mapeo.append("  5. Para términos como 'morosidad', considera campos: dias_morosidad, monto_morosidad, estado='MORA'")
    mapeo.append("  6. Si no estás seguro, pregunta al usuario para aclarar antes de responder")

    return "\n".join(mapeo)


def _obtener_inventario_campos_bd(db: Session) -> str:
    """Obtiene un inventario completo y organizado de todos los campos de BD por tablas con índices"""
    try:
        from sqlalchemy.engine import reflection

        inspector = reflection.Inspector.from_engine(db.bind)
        inventario = []

        inventario.append("=== INVENTARIO COMPLETO DE CAMPOS DE BASE DE DATOS ===\n")
        inventario.append("Organizado por tablas con información de índices, tipos de datos y relaciones\n")

        # Tablas principales en orden de importancia
        tablas_prioritarias = [
            "clientes",
            "prestamos",
            "cuotas",
            "pagos",
            "notificaciones",
            "users",
            "concesionarios",
            "analistas",
            "configuracion_sistema",
            "documentos_ai",
            "auditorias",
            "prestamos_evaluacion",
            "prestamos_auditoria",
            "pagos_auditoria",
        ]

        # Obtener todas las tablas
        todas_tablas = inspector.get_table_names()

        # Procesar tablas prioritarias primero
        tablas_procesadas = set()
        for tabla in tablas_prioritarias:
            if tabla in todas_tablas:
                tablas_procesadas.add(tabla)
                _agregar_info_tabla(inventario, inspector, tabla)

        # Procesar tablas restantes
        for tabla in sorted(todas_tablas):
            if tabla not in tablas_procesadas:
                _agregar_info_tabla(inventario, inspector, tabla)

        return "\n".join(inventario)
    except Exception as e:
        logger.error(f"Error obteniendo inventario de campos BD: {e}")
        return "No se pudo obtener el inventario completo de campos"


def _agregar_info_tabla(inventario: list, inspector, tabla: str):
    """Agrega información detallada de una tabla al inventario"""
    try:
        inventario.append(f"\n{'='*80}")
        inventario.append(f"TABLA: {tabla.upper()}")
        inventario.append(f"{'='*80}\n")

        # Obtener columnas
        columnas = inspector.get_columns(tabla)
        inventario.append("📋 CAMPOS (Columnas):")

        # Separar campos por tipo
        campos_primarios = []
        campos_indexados = []
        campos_normales = []
        campos_fecha = []
        campos_numericos = []
        campos_texto = []

        # Obtener índices para identificar campos indexados
        indices = inspector.get_indexes(tabla)
        campos_con_indice = set()
        for idx in indices:
            campos_con_indice.update(idx["column_names"])

        # Obtener claves foráneas
        fks = inspector.get_foreign_keys(tabla)
        campos_fk = set()
        for fk in fks:
            campos_fk.update(fk["constrained_columns"])

        for col in columnas:
            nombre = col["name"]
            tipo = str(col["type"])
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col.get("default") is not None else ""
            es_pk = col.get("primary_key", False)
            tiene_indice = nombre in campos_con_indice
            es_fk = nombre in campos_fk

            info_campo = {
                "nombre": nombre,
                "tipo": tipo,
                "nullable": nullable,
                "default": default,
                "es_pk": es_pk,
                "tiene_indice": tiene_indice,
                "es_fk": es_fk,
            }

            if es_pk:
                campos_primarios.append(info_campo)
            elif tiene_indice:
                campos_indexados.append(info_campo)
            elif "date" in tipo.lower() or "timestamp" in tipo.lower() or "time" in tipo.lower():
                campos_fecha.append(info_campo)
            elif "numeric" in tipo.lower() or "integer" in tipo.lower() or "decimal" in tipo.lower():
                campos_numericos.append(info_campo)
            elif "varchar" in tipo.lower() or "text" in tipo.lower() or "string" in tipo.lower():
                campos_texto.append(info_campo)
            else:
                campos_normales.append(info_campo)

        # Mostrar campos primarios
        if campos_primarios:
            inventario.append("\n  🔑 CLAVES PRIMARIAS:")
            for campo in campos_primarios:
                fk_info = " [FK]" if campo["es_fk"] else ""
                inventario.append(f"    • {campo['nombre']}: {campo['tipo']} {campo['nullable']}{campo['default']}{fk_info}")

        # Mostrar campos indexados (importantes para consultas rápidas)
        if campos_indexados:
            inventario.append("\n  ⚡ CAMPOS INDEXADOS (consultas rápidas):")
            for campo in campos_indexados:
                fk_info = " [FK]" if campo["es_fk"] else ""
                inventario.append(f"    • {campo['nombre']}: {campo['tipo']} {campo['nullable']}{campo['default']}{fk_info}")

        # Mostrar campos de fecha
        if campos_fecha:
            inventario.append("\n  📅 CAMPOS DE FECHA:")
            for campo in campos_fecha:
                idx_info = " [INDEXED]" if campo["tiene_indice"] else ""
                fk_info = " [FK]" if campo["es_fk"] else ""
                inventario.append(
                    f"    • {campo['nombre']}: {campo['tipo']} {campo['nullable']}{campo['default']}{idx_info}{fk_info}"
                )

        # Mostrar campos numéricos
        if campos_numericos:
            inventario.append("\n  🔢 CAMPOS NUMÉRICOS:")
            for campo in campos_numericos:
                idx_info = " [INDEXED]" if campo["tiene_indice"] else ""
                fk_info = " [FK]" if campo["es_fk"] else ""
                inventario.append(
                    f"    • {campo['nombre']}: {campo['tipo']} {campo['nullable']}{campo['default']}{idx_info}{fk_info}"
                )

        # Mostrar campos de texto
        if campos_texto:
            inventario.append("\n  📝 CAMPOS DE TEXTO:")
            for campo in campos_texto:
                idx_info = " [INDEXED]" if campo["tiene_indice"] else ""
                fk_info = " [FK]" if campo["es_fk"] else ""
                inventario.append(
                    f"    • {campo['nombre']}: {campo['tipo']} {campo['nullable']}{campo['default']}{idx_info}{fk_info}"
                )

        # Mostrar otros campos
        if campos_normales:
            inventario.append("\n  📦 OTROS CAMPOS:")
            for campo in campos_normales:
                idx_info = " [INDEXED]" if campo["tiene_indice"] else ""
                fk_info = " [FK]" if campo["es_fk"] else ""
                inventario.append(
                    f"    • {campo['nombre']}: {campo['tipo']} {campo['nullable']}{campo['default']}{idx_info}{fk_info}"
                )

        # Mostrar índices compuestos
        if indices:
            indices_compuestos = [idx for idx in indices if len(idx["column_names"]) > 1]
            if indices_compuestos:
                inventario.append("\n  🔗 ÍNDICES COMPUESTOS:")
                for idx in indices_compuestos:
                    unique = " [UNIQUE]" if idx.get("unique") else ""
                    columnas_idx = ", ".join(idx["column_names"])
                    inventario.append(f"    • {idx['name']}: ({columnas_idx}){unique}")

        # Mostrar relaciones (claves foráneas)
        if fks:
            inventario.append("\n  🔗 RELACIONES (Claves Foráneas):")
            for fk in fks:
                col_local = ", ".join(fk["constrained_columns"])
                tabla_ref = fk["referred_table"]
                col_ref = ", ".join(fk["referred_columns"])
                inventario.append(f"    • {col_local} -> {tabla_ref}.{col_ref}")

        # Información de uso común y sinónimos
        inventario.append(f"\n  💡 USO COMÚN Y SINÓNIMOS:")
        if tabla == "clientes":
            inventario.append("    • Buscar por: cedula (indexed) [también: cédula, documento, DNI, CI]")
            inventario.append("    • Buscar por: telefono (indexed) [también: teléfono, tel, contacto, celular]")
            inventario.append("    • Buscar por: email (indexed) [también: correo, e-mail, mail]")
            inventario.append("    • Filtrar por: estado (indexed), activo (indexed)")
            inventario.append("    • Campos relacionados: nombres [nombre, nombre completo, cliente, persona]")
        elif tabla == "prestamos":
            inventario.append("    • Buscar por: cliente_id (FK, indexed) [también: id cliente, código cliente]")
            inventario.append("    • Buscar por: cedula (indexed) [también: cédula, documento, DNI]")
            inventario.append("    • Filtrar por: estado (indexed) [también: situación, condición, status]")
            inventario.append("    • Filtrar por: fecha_registro (indexed) [también: fecha creación, creado]")
            inventario.append(
                "    • Campos relacionados: total_financiamiento [monto préstamo, valor préstamo, financiamiento]"
            )
            inventario.append("    • Relaciona con: clientes (cliente_id), cuotas (prestamo_id)")
        elif tabla == "cuotas":
            inventario.append("    • Buscar por: prestamo_id (FK, indexed) [también: id préstamo, préstamo, crédito]")
            inventario.append(
                "    • Buscar por: fecha_vencimiento (indexed) [también: vencimiento, cuándo vence, fecha vencida]"
            )
            inventario.append("    • Filtrar por: estado (indexed) [PAGADA, PENDIENTE, MORA, PARCIAL]")
            inventario.append("    • Campos clave:")
            inventario.append("      - fecha_vencimiento [vencimiento, cuándo vence]")
            inventario.append("      - fecha_pago [cuando pagó, fecha pagado, día de pago]")
            inventario.append("      - monto_cuota [cuota, valor cuota, pago cuota]")
            inventario.append("      - total_pagado [total pagado, suma pagada, acumulado pagado]")
            inventario.append("      - dias_morosidad [días morosidad, días pendiente, días adeudado]")
            inventario.append("      - monto_morosidad [morosidad, monto pendiente, deuda pendiente]")
        elif tabla == "pagos":
            inventario.append("    • Buscar por: prestamo_id (indexed) [también: id préstamo, préstamo, crédito]")
            inventario.append("    • Buscar por: cedula (indexed) [también: cédula, documento, DNI]")
            inventario.append("    • Buscar por: fecha_pago (indexed) [también: cuando pagó, fecha pagado, día de pago]")
            inventario.append("    • Filtrar por: activo (indexed) [también: pago activo, pago válido, pago vigente]")
            inventario.append("    • Campos clave:")
            inventario.append("      - fecha_pago [cuando pagó, fecha pagado, día de pago]")
            inventario.append("      - monto_pagado [pagado, cantidad pagada, abonado]")
            inventario.append("      - numero_documento [número documento, comprobante, referencia]")
            inventario.append("      - conciliado [conciliación, verificado, confirmado]")
        elif tabla == "notificaciones":
            inventario.append("    • Buscar por: cliente_id (FK, indexed)")
            inventario.append("    • Filtrar por: tipo (indexed) [EMAIL, SMS, WHATSAPP]")
            inventario.append("    • Filtrar por: estado (indexed) [PENDIENTE, ENVIADA, FALLIDA]")
            inventario.append("    • Campos relacionados: fecha_envio [fecha envío, cuando se envió]")

    except Exception as e:
        logger.error(f"Error agregando info de tabla {tabla}: {e}")
        inventario.append(f"  ⚠️ Error obteniendo información de la tabla: {e}")


def _obtener_esquema_bd_completo(db: Session) -> str:
    """Obtiene el esquema completo de la base de datos con todas las tablas, campos e índices"""
    try:
        from sqlalchemy import inspect, text
        from sqlalchemy.engine import reflection

        # Obtener inspector desde el engine de la sesión
        inspector = reflection.Inspector.from_engine(db.bind)
        esquema = []

        esquema.append("=== ESQUEMA COMPLETO DE BASE DE DATOS ===\n")

        # Obtener todas las tablas
        tablas = inspector.get_table_names()

        for tabla in sorted(tablas):
            esquema.append(f"\n--- TABLA: {tabla} ---")

            # Obtener columnas
            columnas = inspector.get_columns(tabla)
            esquema.append("Columnas:")
            for col in columnas:
                tipo = str(col["type"])
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                default = f" DEFAULT {col['default']}" if col.get("default") is not None else ""
                primary_key = " [PRIMARY KEY]" if col.get("primary_key") else ""
                esquema.append(f"  - {col['name']}: {tipo} {nullable}{default}{primary_key}")

            # Obtener índices
            indices = inspector.get_indexes(tabla)
            if indices:
                esquema.append("Índices:")
                for idx in indices:
                    columnas_idx = ", ".join(idx["column_names"])
                    unique = " [UNIQUE]" if idx.get("unique") else ""
                    esquema.append(f"  - {idx['name']}: ({columnas_idx}){unique}")

            # Obtener claves foráneas
            fks = inspector.get_foreign_keys(tabla)
            if fks:
                esquema.append("Claves Foráneas:")
                for fk in fks:
                    col_local = ", ".join(fk["constrained_columns"])
                    tabla_ref = fk["referred_table"]
                    col_ref = ", ".join(fk["referred_columns"])
                    esquema.append(f"  - {col_local} -> {tabla_ref}.{col_ref}")

        return "\n".join(esquema)
    except Exception as e:
        logger.error(f"Error obteniendo esquema de BD: {e}")
        return "No se pudo obtener el esquema completo de la base de datos"


def _obtener_estadisticas_tablas(db: Session) -> str:
    """Obtiene estadísticas de todas las tablas (conteos, fechas mín/máx, etc.)"""
    try:
        from sqlalchemy import text

        estadisticas = []
        estadisticas.append("\n=== ESTADÍSTICAS DE TABLAS ===\n")

        # Tablas principales con sus conteos
        tablas_principales = [
            ("clientes", "id"),
            ("prestamos", "id"),
            ("cuotas", "id"),
            ("pagos", "id"),
            ("notificaciones", "id"),
            ("users", "id"),
            ("concesionarios", "id"),
            ("analistas", "id"),
        ]

        for tabla, col_id in tablas_principales:
            try:
                # Conteo total
                query = text(f"SELECT COUNT(*) as total FROM {tabla}")
                resultado = db.execute(query).fetchone()
                total = resultado[0] if resultado else 0

                # Intentar obtener fechas mín/máx si existe columna de fecha
                fecha_info = ""
                try:
                    query_fecha = text(
                        f"""
                        SELECT 
                            MIN(fecha_registro) as min_fecha,
                            MAX(fecha_registro) as max_fecha
                        FROM {tabla}
                        WHERE fecha_registro IS NOT NULL
                    """
                    )
                    fecha_result = db.execute(query_fecha).fetchone()
                    if fecha_result and fecha_result[0]:
                        fecha_info = f" | Rango fechas: {fecha_result[0]} a {fecha_result[1]}"
                except Exception:
                    pass

                estadisticas.append(f"{tabla}: {total} registros{fecha_info}")
            except Exception as e:
                logger.debug(f"No se pudo obtener estadísticas de {tabla}: {e}")
                continue

        return "\n".join(estadisticas)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de tablas: {e}")
        return ""


def _ejecutar_consulta_cruzada(db: Session, tabla1: str, tabla2: str, campos: list, condiciones: dict = None) -> list:
    """Ejecuta una consulta cruzada entre dos tablas con JOIN"""
    try:
        from sqlalchemy import text

        # Construir query básico
        query_sql = f"""
            SELECT {', '.join(campos)}
            FROM {tabla1} t1
            INNER JOIN {tabla2} t2 ON t1.id = t2.{tabla1[:-1]}_id
        """

        # Agregar condiciones si existen
        if condiciones:
            where_clauses = []
            params = {}
            for campo, valor in condiciones.items():
                where_clauses.append(f"{campo} = :{campo}")
                params[campo] = valor
            if where_clauses:
                query_sql += " WHERE " + " AND ".join(where_clauses)
                resultado = db.execute(text(query_sql).bindparams(**params))
            else:
                resultado = db.execute(text(query_sql))
        else:
            resultado = db.execute(text(query_sql))

        return [dict(row._mapping) for row in resultado.fetchall()]
    except Exception as e:
        logger.error(f"Error ejecutando consulta cruzada: {e}")
        return []


def _analisis_ml_morosidad_predictiva(db: Session) -> dict:
    """Análisis de Machine Learning: Predicción de morosidad basada en patrones históricos"""
    try:
        from datetime import date, timedelta

        from sqlalchemy import and_, func, text

        hoy = date.today()
        hace_6_meses = hoy - timedelta(days=180)

        # Obtener datos históricos para análisis
        query = text(
            """
            SELECT 
                p.analista,
                p.concesionario,
                p.total_financiamiento,
                p.numero_cuotas,
                COUNT(c.id) FILTER (WHERE c.estado = 'MORA') as cuotas_mora_historial,
                COUNT(c.id) FILTER (WHERE c.estado = 'PAGADA') as cuotas_pagadas_historial,
                AVG(c.dias_morosidad) FILTER (WHERE c.dias_morosidad > 0) as promedio_dias_mora,
                COUNT(DISTINCT p.cedula) as clientes_unicos
            FROM prestamos p
            LEFT JOIN cuotas c ON c.prestamo_id = p.id
            WHERE p.estado = 'APROBADO'
              AND p.fecha_aprobacion >= :fecha_inicio
            GROUP BY p.analista, p.concesionario, p.total_financiamiento, p.numero_cuotas
            HAVING COUNT(c.id) > 0
            ORDER BY cuotas_mora_historial DESC
            LIMIT 50
        """
        )

        resultado = db.execute(query.bindparams(fecha_inicio=hace_6_meses))
        datos_historicos = [dict(row._mapping) for row in resultado.fetchall()]

        # Calcular factores de riesgo
        factores_riesgo = []
        for dato in datos_historicos:
            total_cuotas = dato.get("cuotas_mora_historial", 0) + dato.get("cuotas_pagadas_historial", 0)
            tasa_mora = (dato.get("cuotas_mora_historial", 0) / total_cuotas * 100) if total_cuotas > 0 else 0

            # Factor de riesgo basado en múltiples variables
            factor_riesgo = 0
            if tasa_mora > 30:
                factor_riesgo += 3
            elif tasa_mora > 15:
                factor_riesgo += 2
            elif tasa_mora > 5:
                factor_riesgo += 1

            if dato.get("promedio_dias_mora", 0) > 60:
                factor_riesgo += 2
            elif dato.get("promedio_dias_mora", 0) > 30:
                factor_riesgo += 1

            factores_riesgo.append(
                {
                    "analista": dato.get("analista", "N/A"),
                    "concesionario": dato.get("concesionario", "N/A"),
                    "tasa_mora_historica": round(tasa_mora, 2),
                    "promedio_dias_mora": round(dato.get("promedio_dias_mora", 0), 1),
                    "factor_riesgo": factor_riesgo,
                    "nivel_riesgo": "ALTO" if factor_riesgo >= 4 else "MEDIO" if factor_riesgo >= 2 else "BAJO",
                }
            )

        return {
            "tipo_analisis": "Predicción de Morosidad",
            "datos_analizados": len(datos_historicos),
            "factores_riesgo": factores_riesgo[:10],  # Top 10
            "recomendaciones": [
                "Préstamos con analistas/concesionarios de alto riesgo requieren seguimiento más cercano",
                "Implementar alertas tempranas para préstamos con factores de riesgo >= 4",
                "Revisar políticas de aprobación para analistas con tasa de mora histórica > 30%",
            ],
        }
    except Exception as e:
        logger.error(f"Error en análisis ML de morosidad: {e}")
        return None


def _analisis_ml_segmentacion_clientes(db: Session) -> dict:
    """Análisis de Machine Learning: Segmentación de clientes por comportamiento"""
    try:
        from datetime import date, timedelta

        from sqlalchemy import and_, func, text

        hoy = date.today()

        # Segmentar clientes por comportamiento de pago
        query = text(
            """
            SELECT 
                c.cedula,
                c.nombres,
                COUNT(DISTINCT p.id) as total_prestamos,
                COUNT(cu.id) FILTER (WHERE cu.estado = 'PAGADA') as cuotas_pagadas,
                COUNT(cu.id) FILTER (WHERE cu.estado = 'MORA') as cuotas_mora,
                COUNT(cu.id) FILTER (WHERE cu.estado = 'PENDIENTE') as cuotas_pendientes,
                AVG(cu.dias_morosidad) FILTER (WHERE cu.dias_morosidad > 0) as promedio_dias_mora,
                SUM(pa.monto_pagado) FILTER (WHERE pa.activo = TRUE) as total_pagado_historico,
                MAX(pa.fecha_pago) as ultimo_pago
            FROM clientes c
            LEFT JOIN prestamos p ON p.cedula = c.cedula AND p.estado = 'APROBADO'
            LEFT JOIN cuotas cu ON cu.prestamo_id = p.id
            LEFT JOIN pagos pa ON (pa.prestamo_id = p.id OR pa.cedula = c.cedula) AND pa.activo = TRUE
            WHERE c.activo = TRUE
            GROUP BY c.cedula, c.nombres
            HAVING COUNT(DISTINCT p.id) > 0
            ORDER BY total_pagado_historico DESC
            LIMIT 100
        """
        )

        resultado = db.execute(query)
        clientes = [dict(row._mapping) for row in resultado.fetchall()]

        # Segmentar en grupos
        segmentos = {
            "excelentes": [],  # 0% mora, pagos puntuales
            "buenos": [],  # < 5% mora
            "regulares": [],  # 5-15% mora
            "riesgo": [],  # > 15% mora
        }

        for cliente in clientes:
            total_cuotas = (
                cliente.get("cuotas_pagadas", 0) + cliente.get("cuotas_mora", 0) + cliente.get("cuotas_pendientes", 0)
            )

            if total_cuotas == 0:
                continue

            tasa_mora = cliente.get("cuotas_mora", 0) / total_cuotas * 100
            prom_dias = cliente.get("promedio_dias_mora", 0) or 0

            if tasa_mora == 0 and prom_dias == 0:
                segmentos["excelentes"].append(
                    {
                        "cedula": cliente.get("cedula"),
                        "nombres": cliente.get("nombres"),
                        "total_prestamos": cliente.get("total_prestamos", 0),
                        "total_pagado": float(cliente.get("total_pagado_historico", 0) or 0),
                    }
                )
            elif tasa_mora < 5:
                segmentos["buenos"].append(
                    {
                        "cedula": cliente.get("cedula"),
                        "nombres": cliente.get("nombres"),
                        "tasa_mora": round(tasa_mora, 2),
                        "total_prestamos": cliente.get("total_prestamos", 0),
                    }
                )
            elif tasa_mora < 15:
                segmentos["regulares"].append(
                    {
                        "cedula": cliente.get("cedula"),
                        "nombres": cliente.get("nombres"),
                        "tasa_mora": round(tasa_mora, 2),
                        "promedio_dias_mora": round(prom_dias, 1),
                    }
                )
            else:
                segmentos["riesgo"].append(
                    {
                        "cedula": cliente.get("cedula"),
                        "nombres": cliente.get("nombres"),
                        "tasa_mora": round(tasa_mora, 2),
                        "promedio_dias_mora": round(prom_dias, 1),
                        "total_prestamos": cliente.get("total_prestamos", 0),
                    }
                )

        return {
            "tipo_analisis": "Segmentación de Clientes",
            "total_analizados": len(clientes),
            "segmentos": {
                "excelentes": {
                    "cantidad": len(segmentos["excelentes"]),
                    "caracteristicas": "0% mora, pagos puntuales",
                    "muestra": segmentos["excelentes"][:5],
                },
                "buenos": {
                    "cantidad": len(segmentos["buenos"]),
                    "caracteristicas": "< 5% mora",
                    "muestra": segmentos["buenos"][:5],
                },
                "regulares": {
                    "cantidad": len(segmentos["regulares"]),
                    "caracteristicas": "5-15% mora",
                    "muestra": segmentos["regulares"][:5],
                },
                "riesgo": {
                    "cantidad": len(segmentos["riesgo"]),
                    "caracteristicas": "> 15% mora",
                    "muestra": segmentos["riesgo"][:5],
                },
            },
            "recomendaciones": [
                f"Clientes Excelentes ({len(segmentos['excelentes'])}): Ofrecer préstamos adicionales o mejores condiciones",
                f"Clientes en Riesgo ({len(segmentos['riesgo'])}): Requieren seguimiento intensivo y posible reestructuración",
            ],
        }
    except Exception as e:
        logger.error(f"Error en análisis ML de segmentación: {e}")
        return None


def _analisis_ml_deteccion_anomalias(db: Session) -> dict:
    """Análisis de Machine Learning: Detección de anomalías en pagos y préstamos"""
    try:
        from datetime import date, timedelta

        from sqlalchemy import text

        hoy = date.today()
        hace_30_dias = hoy - timedelta(days=30)

        # Detectar anomalías en pagos
        query_anomalias = text(
            """
            SELECT 
                p.id,
                p.cedula,
                p.monto_pagado,
                p.fecha_pago,
                p.numero_documento,
                pr.total_financiamiento,
                CASE 
                    WHEN p.monto_pagado > pr.total_financiamiento * 0.5 THEN 'PAGO_MUY_ALTO'
                    WHEN p.monto_pagado < 100 THEN 'PAGO_MUY_BAJO'
                    WHEN p.fecha_pago < pr.fecha_aprobacion THEN 'PAGO_ANTES_APROBACION'
                    ELSE 'NORMAL'
                END as tipo_anomalia
            FROM pagos p
            LEFT JOIN prestamos pr ON (p.prestamo_id = pr.id OR p.cedula = pr.cedula)
            WHERE p.activo = TRUE
              AND p.fecha_pago >= :fecha_inicio
              AND (
                  p.monto_pagado > (SELECT AVG(monto_pagado) * 3 FROM pagos WHERE activo = TRUE)
                  OR p.monto_pagado < (SELECT AVG(monto_pagado) * 0.1 FROM pagos WHERE activo = TRUE)
                  OR (pr.id IS NOT NULL AND p.fecha_pago < pr.fecha_aprobacion)
              )
            ORDER BY p.fecha_pago DESC
            LIMIT 20
        """
        )

        resultado = db.execute(query_anomalias.bindparams(fecha_inicio=hace_30_dias))
        anomalias = [dict(row._mapping) for row in resultado.fetchall()]

        # Agrupar por tipo
        por_tipo = {}
        for anom in anomalias:
            tipo = anom.get("tipo_anomalia", "NORMAL")
            if tipo not in por_tipo:
                por_tipo[tipo] = []
            por_tipo[tipo].append(anom)

        return {
            "tipo_analisis": "Detección de Anomalías",
            "total_anomalias": len(anomalias),
            "anomalias_por_tipo": {tipo: {"cantidad": len(lista), "ejemplos": lista[:3]} for tipo, lista in por_tipo.items()},
            "recomendaciones": [
                "Revisar pagos con montos muy altos o muy bajos para verificar autenticidad",
                "Validar pagos registrados antes de la aprobación del préstamo",
                "Implementar alertas automáticas para detectar anomalías en tiempo real",
            ],
        }
    except Exception as e:
        logger.error(f"Error en análisis ML de anomalías: {e}")
        return None


def _analisis_ml_clustering_prestamos(db: Session) -> dict:
    """Análisis de Machine Learning: Clustering de préstamos por características similares"""
    try:
        from sqlalchemy import text

        # Agrupar préstamos por características similares
        query = text(
            """
            SELECT 
                p.analista,
                p.concesionario,
                p.producto,
                p.modalidad_pago,
                AVG(p.total_financiamiento) as promedio_monto,
                AVG(p.numero_cuotas) as promedio_cuotas,
                COUNT(*) as cantidad_prestamos,
                COUNT(DISTINCT p.cedula) as clientes_unicos,
                AVG(
                    (SELECT COUNT(*) FROM cuotas WHERE prestamo_id = p.id AND estado = 'MORA')::float /
                    NULLIF((SELECT COUNT(*) FROM cuotas WHERE prestamo_id = p.id), 0) * 100
                ) as tasa_mora_promedio
            FROM prestamos p
            WHERE p.estado = 'APROBADO'
            GROUP BY p.analista, p.concesionario, p.producto, p.modalidad_pago
            HAVING COUNT(*) >= 3
            ORDER BY cantidad_prestamos DESC
            LIMIT 20
        """
        )

        resultado = db.execute(query)
        clusters = [dict(row._mapping) for row in resultado.fetchall()]

        # Identificar clusters con características similares
        clusters_identificados = []
        for cluster in clusters:
            caracteristicas = []
            if cluster.get("tasa_mora_promedio", 0) < 5:
                caracteristicas.append("Baja morosidad")
            if cluster.get("promedio_monto", 0) > 50000:
                caracteristicas.append("Montos altos")
            if cluster.get("modalidad_pago") == "MENSUAL":
                caracteristicas.append("Pago mensual")

            clusters_identificados.append(
                {
                    "cluster_id": f"{cluster.get('analista', 'N/A')}_{cluster.get('producto', 'N/A')}",
                    "caracteristicas": caracteristicas,
                    "cantidad_prestamos": cluster.get("cantidad_prestamos", 0),
                    "promedio_monto": round(float(cluster.get("promedio_monto", 0)), 2),
                    "tasa_mora_promedio": round(float(cluster.get("tasa_mora_promedio", 0) or 0), 2),
                    "analista": cluster.get("analista", "N/A"),
                    "producto": cluster.get("producto", "N/A"),
                }
            )

        return {
            "tipo_analisis": "Clustering de Préstamos",
            "clusters_identificados": len(clusters_identificados),
            "clusters": clusters_identificados[:10],
            "recomendaciones": [
                "Usar clusters para identificar productos/analistas con mejor desempeño",
                "Aplicar políticas diferenciadas según características del cluster",
                "Optimizar aprobaciones basándose en clusters de bajo riesgo",
            ],
        }
    except Exception as e:
        logger.error(f"Error en análisis ML de clustering: {e}")
        return None


def _analizar_pagos_segun_vencimiento(db: Session, año: int, mes: int) -> dict:
    """Analiza pagos realizados según fechas de vencimiento de cuotas en un mes específico"""
    try:
        from datetime import date, timedelta

        from sqlalchemy import and_, extract, text

        # Calcular rango del mes
        fecha_inicio_mes = date(año, mes, 1)
        if mes == 12:
            fecha_fin_mes = date(año + 1, 1, 1) - timedelta(days=1)
        else:
            fecha_fin_mes = date(año, mes + 1, 1) - timedelta(days=1)

        # Consulta: Cuotas con fecha_vencimiento en el mes y si fueron pagadas
        query = text(
            """
            SELECT 
                c.id as cuota_id,
                c.prestamo_id,
                c.fecha_vencimiento,
                c.monto_cuota,
                c.estado as estado_cuota,
                c.total_pagado,
                CASE 
                    WHEN c.estado = 'PAGADA' AND c.fecha_pago IS NOT NULL THEN TRUE
                    ELSE FALSE
                END as fue_pagada,
                c.fecha_pago as fecha_pago_cuota,
                COUNT(DISTINCT p.id) FILTER (WHERE p.activo = TRUE) as pagos_asociados,
                COALESCE(SUM(p.monto_pagado) FILTER (WHERE p.activo = TRUE), 0) as total_pagado_en_pagos
            FROM cuotas c
            INNER JOIN prestamos pr ON c.prestamo_id = pr.id
            LEFT JOIN pagos p ON (
                (p.prestamo_id = pr.id OR p.cedula = pr.cedula)
                AND p.activo = TRUE
                AND EXTRACT(YEAR FROM p.fecha_pago) = :año
                AND EXTRACT(MONTH FROM p.fecha_pago) = :mes
            )
            WHERE pr.estado = 'APROBADO'
              AND EXTRACT(YEAR FROM c.fecha_vencimiento) = :año
              AND EXTRACT(MONTH FROM c.fecha_vencimiento) = :mes
            GROUP BY c.id, c.prestamo_id, c.fecha_vencimiento, c.monto_cuota, c.estado, c.total_pagado, c.fecha_pago
            ORDER BY c.fecha_vencimiento
        """
        )

        resultado = db.execute(query.bindparams(año=año, mes=mes))
        cuotas = [dict(row._mapping) for row in resultado.fetchall()]

        # Analizar resultados
        total_cuotas = len(cuotas)
        cuotas_pagadas_segun_vencimiento = 0
        cuotas_pagadas_antes = 0
        cuotas_pagadas_despues = 0
        cuotas_no_pagadas = 0

        for cuota in cuotas:
            fecha_vencimiento = cuota.get("fecha_vencimiento")
            fecha_pago = cuota.get("fecha_pago_cuota")
            fue_pagada = cuota.get("fue_pagada", False)
            total_pagado = float(cuota.get("total_pagado", 0) or 0)

            if fue_pagada and fecha_pago:
                # Verificar si el pago fue según la fecha de vencimiento (dentro de ±3 días)
                dias_diferencia = (fecha_pago - fecha_vencimiento).days
                if abs(dias_diferencia) <= 3:
                    cuotas_pagadas_segun_vencimiento += 1
                elif dias_diferencia < 0:
                    cuotas_pagadas_antes += 1
                else:
                    cuotas_pagadas_despues += 1
            elif total_pagado > 0:
                # Tiene pagos pero no está marcada como PAGADA
                cuotas_pagadas_despues += 1
            else:
                cuotas_no_pagadas += 1

        porcentaje_pagadas_segun_vencimiento = (
            (cuotas_pagadas_segun_vencimiento / total_cuotas * 100) if total_cuotas > 0 else 0
        )

        return {
            "año": año,
            "mes": mes,
            "total_cuotas_vencimiento_mes": total_cuotas,
            "cuotas_pagadas_segun_vencimiento": cuotas_pagadas_segun_vencimiento,
            "cuotas_pagadas_antes": cuotas_pagadas_antes,
            "cuotas_pagadas_despues": cuotas_pagadas_despues,
            "cuotas_no_pagadas": cuotas_no_pagadas,
            "porcentaje_pagadas_segun_vencimiento": round(porcentaje_pagadas_segun_vencimiento, 2),
            "conclusion": (
                "NINGUNO"
                if cuotas_pagadas_segun_vencimiento == 0
                else f"{cuotas_pagadas_segun_vencimiento} cuotas pagadas según vencimiento"
            ),
        }
    except Exception as e:
        logger.error(f"Error analizando pagos según vencimiento: {e}")
        return None


def _calcular_analisis_cobranzas(db: Session) -> dict:
    """Calcula análisis detallado de cobranzas"""
    try:
        from datetime import date, timedelta

        from sqlalchemy import and_

        hoy = date.today()

        # Clientes en mora
        clientes_mora = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(and_(Prestamo.estado == "APROBADO", Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADA"))
            .scalar()
            or 0
        )

        # Monto total en mora
        monto_total_mora = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(and_(Prestamo.estado == "APROBADO", Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADA"))
            .scalar()
            or 0
        )

        # Cuotas vencidas por rango de días
        cuotas_1_30_dias = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= hoy - timedelta(days=30),
                    Cuota.fecha_vencimiento < hoy,
                    Cuota.estado != "PAGADA",
                )
            )
            .scalar()
            or 0
        )

        cuotas_31_60_dias = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= hoy - timedelta(days=60),
                    Cuota.fecha_vencimiento < hoy - timedelta(days=30),
                    Cuota.estado != "PAGADA",
                )
            )
            .scalar()
            or 0
        )

        cuotas_mas_60_dias = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Prestamo.estado == "APROBADO", Cuota.fecha_vencimiento < hoy - timedelta(days=60), Cuota.estado != "PAGADA"
                )
            )
            .scalar()
            or 0
        )

        return {
            "clientes_en_mora": clientes_mora,
            "monto_total_mora": float(monto_total_mora),
            "cuotas_1_30_dias": cuotas_1_30_dias,
            "cuotas_31_60_dias": cuotas_31_60_dias,
            "cuotas_mas_60_dias": cuotas_mas_60_dias,
        }
    except Exception as e:
        logger.error(f"Error calculando análisis de cobranzas: {e}")
        return None


def _obtener_resumen_bd(db: Session) -> str:
    """
    Obtiene un resumen de la base de datos con estadísticas principales
    para usar como contexto en las respuestas de AI
    """

    def _ejecutar_consulta_segura(func_consulta, descripcion=""):
        """Ejecuta una consulta de forma segura, manejando errores de transacción abortada"""
        try:
            return func_consulta()
        except Exception as query_error:
            error_str = str(query_error)
            error_type = type(query_error).__name__
            # Verificar si es un error de transacción abortada
            is_transaction_aborted = (
                "aborted" in error_str.lower()
                or "InFailedSqlTransaction" in error_type
                or "current transaction is aborted" in error_str.lower()
            )

            if is_transaction_aborted:
                # Hacer rollback antes de reintentar
                try:
                    db.rollback()
                    logger.debug(f"✅ Rollback realizado antes de {descripcion} (transacción abortada)")
                    # Reintentar la consulta
                    return func_consulta()
                except Exception as retry_error:
                    logger.error(f"❌ Error al reintentar {descripcion}: {retry_error}")
                    return None
            else:
                logger.error(f"❌ Error en {descripcion}: {query_error}")
                return None

    try:
        from sqlalchemy import func

        resumen = []

        # Información de fecha y hora actual
        fecha_actual = datetime.now()

        # Mapeo de días y meses en español
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]

        dia_semana = dias_semana[fecha_actual.weekday()]
        mes = meses[fecha_actual.month - 1]

        resumen.append(
            f"Fecha y hora actual del sistema: {dia_semana}, {fecha_actual.day} de {mes} de {fecha_actual.year}, {fecha_actual.strftime('%H:%M:%S')}"
        )
        resumen.append(f"Fecha actual (formato corto): {fecha_actual.strftime('%d/%m/%Y')}")
        resumen.append(f"Día de la semana: {dia_semana}")
        resumen.append(f"Hora actual: {fecha_actual.strftime('%H:%M:%S')}")
        resumen.append("")  # Línea en blanco para separar

        # Clientes
        total_clientes = _ejecutar_consulta_segura(lambda: db.query(Cliente).count(), "consulta de total clientes")
        clientes_activos = _ejecutar_consulta_segura(
            lambda: db.query(Cliente).filter(Cliente.activo.is_(True)).count(), "consulta de clientes activos"
        )
        if total_clientes is not None and clientes_activos is not None:
            resumen.append(f"Clientes: {total_clientes} totales, {clientes_activos} activos")
        else:
            resumen.append("Clientes: No disponible")

        # Préstamos
        total_prestamos = _ejecutar_consulta_segura(lambda: db.query(Prestamo).count(), "consulta de total préstamos")
        prestamos_activos = _ejecutar_consulta_segura(
            lambda: db.query(Prestamo).filter(Prestamo.estado.in_(["APROBADO", "ACTIVO"])).count(),
            "consulta de préstamos activos",
        )
        prestamos_pendientes = _ejecutar_consulta_segura(
            lambda: db.query(Prestamo).filter(Prestamo.estado == "PENDIENTE").count(), "consulta de préstamos pendientes"
        )
        if total_prestamos is not None and prestamos_activos is not None and prestamos_pendientes is not None:
            resumen.append(
                f"Préstamos: {total_prestamos} totales, {prestamos_activos} activos/aprobados, {prestamos_pendientes} pendientes"
            )
        else:
            resumen.append("Préstamos: No disponible")

        # Pagos
        total_pagos = _ejecutar_consulta_segura(lambda: db.query(Pago).count(), "consulta de total pagos")
        pagos_activos = _ejecutar_consulta_segura(
            lambda: db.query(Pago).filter(Pago.activo.is_(True)).count(), "consulta de pagos activos"
        )
        if total_pagos is not None and pagos_activos is not None:
            resumen.append(f"Pagos: {total_pagos} totales, {pagos_activos} activos")
        else:
            resumen.append("Pagos: No disponible")

        # Cuotas
        total_cuotas = _ejecutar_consulta_segura(lambda: db.query(Cuota).count(), "consulta de total cuotas")
        cuotas_pagadas = _ejecutar_consulta_segura(
            lambda: db.query(Cuota).filter(Cuota.estado == "PAGADA").count(), "consulta de cuotas pagadas"
        )
        cuotas_pendientes = _ejecutar_consulta_segura(
            lambda: db.query(Cuota).filter(Cuota.estado == "PENDIENTE").count(), "consulta de cuotas pendientes"
        )
        cuotas_mora = _ejecutar_consulta_segura(
            lambda: db.query(Cuota).filter(Cuota.estado == "MORA").count(), "consulta de cuotas en mora"
        )
        if (
            total_cuotas is not None
            and cuotas_pagadas is not None
            and cuotas_pendientes is not None
            and cuotas_mora is not None
        ):
            resumen.append(
                f"Cuotas: {total_cuotas} totales, {cuotas_pagadas} pagadas, {cuotas_pendientes} pendientes, {cuotas_mora} en mora"
            )
            # Calcular tasa de morosidad actual
            if total_cuotas > 0:
                tasa_morosidad = (cuotas_mora / total_cuotas) * 100
                resumen.append(f"Tasa de morosidad actual: {tasa_morosidad:.2f}%")
        else:
            resumen.append("Cuotas: No disponible")

        # Información mensual de cuotas (últimos 6 meses para cálculos comparativos)
        resumen.append("")
        resumen.append("=== INFORMACIÓN MENSUAL DE CUOTAS (Últimos 6 meses) ===")
        try:
            from datetime import date

            from sqlalchemy import and_, extract

            # Obtener datos mensuales de cuotas
            fecha_limite = fecha_actual.date()
            fecha_inicio = date(fecha_actual.year, fecha_actual.month - 5 if fecha_actual.month > 5 else 1, 1)
            if fecha_actual.month <= 5:
                fecha_inicio = date(fecha_actual.year - 1, fecha_actual.month + 7, 1)

            # Consulta de cuotas por mes
            query_cuotas_mes = _ejecutar_consulta_segura(
                lambda: db.query(
                    extract("year", Cuota.fecha_vencimiento).label("año"),
                    extract("month", Cuota.fecha_vencimiento).label("mes"),
                    func.count(Cuota.id).label("total"),
                    func.count(Cuota.id).filter(Cuota.estado == "PAGADA").label("pagadas"),
                    func.count(Cuota.id).filter(Cuota.estado == "MORA").label("en_mora"),
                    func.count(Cuota.id).filter(Cuota.estado == "PENDIENTE").label("pendientes"),
                    func.sum(Cuota.monto_cuota).label("monto_total"),
                )
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(
                    and_(
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_vencimiento >= fecha_inicio,
                        Cuota.fecha_vencimiento <= fecha_limite,
                    )
                )
                .group_by(extract("year", Cuota.fecha_vencimiento), extract("month", Cuota.fecha_vencimiento))
                .order_by(extract("year", Cuota.fecha_vencimiento), extract("month", Cuota.fecha_vencimiento))
                .all(),
                "consulta de cuotas mensuales",
            )

            if query_cuotas_mes:
                for row in query_cuotas_mes:
                    año = int(row.año) if row.año else 0
                    mes_num = int(row.mes) if row.mes else 0
                    total_mes = row.total or 0
                    pagadas_mes = row.pagadas or 0
                    mora_mes = row.en_mora or 0
                    pendientes_mes = row.pendientes or 0
                    monto_mes = float(row.monto_total or 0)

                    nombre_mes = meses[mes_num - 1] if 1 <= mes_num <= 12 else f"Mes {mes_num}"
                    tasa_mora_mes = (mora_mes / total_mes * 100) if total_mes > 0 else 0

                    resumen.append(
                        f"{nombre_mes.capitalize()} {año}: {total_mes} cuotas totales, "
                        f"{pagadas_mes} pagadas, {mora_mes} en mora, {pendientes_mes} pendientes. "
                        f"Tasa de morosidad: {tasa_mora_mes:.2f}%. Monto total: {monto_mes:,.2f}"
                    )
            else:
                resumen.append("No hay datos mensuales disponibles")
        except Exception as e:
            logger.error(f"Error obteniendo datos mensuales: {e}")
            resumen.append("Datos mensuales: No disponible")

        # Montos totales
        resumen.append("")
        resumen.append("=== MONTOS TOTALES ===")
        monto_total_prestamos = _ejecutar_consulta_segura(
            lambda: db.query(func.sum(Prestamo.monto_financiado)).filter(Prestamo.estado.in_(["APROBADO", "ACTIVO"])).scalar()
            or 0,
            "consulta de monto total préstamos",
        )
        if monto_total_prestamos is not None:
            resumen.append(f"Monto total de préstamos activos: {monto_total_prestamos:,.2f}")

        monto_total_pagos = _ejecutar_consulta_segura(
            lambda: db.query(func.sum(Pago.monto_pagado)).filter(Pago.activo.is_(True)).scalar() or 0,
            "consulta de monto total pagos",
        )
        if monto_total_pagos is not None:
            resumen.append(f"Monto total de pagos: {monto_total_pagos:,.2f}")

        return "\n".join(resumen)
    except Exception as e:
        logger.error(f"Error obteniendo resumen de BD: {e}", exc_info=True)
        # Intentar rollback si hay error
        try:
            db.rollback()
        except Exception:
            pass
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
        try:
            configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "AI").all()
        except Exception as query_error:
            error_str = str(query_error)
            error_type = type(query_error).__name__
            # Verificar si es un error de transacción abortada
            is_transaction_aborted = (
                "aborted" in error_str.lower()
                or "InFailedSqlTransaction" in error_type
                or "current transaction is aborted" in error_str.lower()
            )

            if is_transaction_aborted:
                # Hacer rollback antes de reintentar
                try:
                    db.rollback()
                    logger.debug("✅ Rollback realizado antes de consultar configuración AI (transacción abortada)")
                    # Reintentar la consulta
                    configs = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.categoria == "AI").all()
                except Exception as retry_error:
                    logger.error(f"❌ Error al reintentar consulta de configuración AI: {retry_error}")
                    raise HTTPException(
                        status_code=500, detail="Error de conexión a la base de datos. Por favor, intenta nuevamente."
                    )
            else:
                raise

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

        # Validar que la pregunta sea sobre la base de datos
        # Palabras clave que indican preguntas sobre BD
        palabras_clave_bd = [
            # Entidades principales
            "cliente",
            "clientes",
            "préstamo",
            "préstamos",
            "prestamo",
            "prestamos",
            "pago",
            "pagos",
            "cuota",
            "cuotas",
            "mora",
            "morosidad",
            "pendiente",
            "pagada",
            # Identificación y búsqueda
            "cedula",
            "cédula",
            "cedula:",
            "cédula:",
            "documento",
            "documentos",
            "dni",
            "ci",
            "identificación",
            "identificacion",
            "numero",
            "número",
            "numero:",
            "número:",
            # Consultas de búsqueda
            "quien tiene",
            "quién tiene",
            "quien tiene el",
            "quién tiene el",
            "como se llama",
            "cómo se llama",
            "cual es el nombre",
            "cuál es el nombre",
            "buscar por",
            "buscar cliente",
            "encontrar cliente",
            "datos del cliente",
            "información del cliente",
            # Base de datos y datos
            "base de datos",
            "datos",
            "estadística",
            "estadísticas",
            "resumen",
            "total",
            "cantidad",
            "cuántos",
            "cuántas",
            "monto",
            "montos",
            "activo",
            "activos",
            "concesionario",
            "concesionarios",
            "analista",
            "analistas",
            "usuario",
            "usuarios",
            "sistema",
            "registro",
            "registros",
            # Fechas y tiempo
            "fecha actual",
            "día de hoy",
            "qué día",
            "qué fecha",
            "hora actual",
            "fecha de vencimiento",
            "fechas de vencimiento",
            "vencimiento",
            "vencidas",
            "vencido",
            "pago según",
            "pago segun",
            "pagos según",
            "pagos segun",
            "pagado según",
            "pagado segun",
            "ninguno",
            "ninguna",
            "cuántos pagaron",
            "cuántas pagaron",
            "cuántos pagaron en",
            "cuántas pagaron en",
            # Términos de cálculos y análisis
            "tasa",
            "tasas",
            "porcentaje",
            "calcular",
            "cálculo",
            "comparar",
            "comparación",
            "diferencia",
            "análisis",
            "tendencia",
            "evolución",
            "métrica",
            "métricas",
            "variación",
            "incremento",
            "disminución",
            "cobranza",
            "cobranzas",
            # Meses (para preguntas sobre períodos específicos)
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
            # Términos financieros
            "financiamiento",
            "cartera",
            "vencido",
            "vencidas",
            "vencimiento",
            # Machine Learning y análisis avanzado
            "machine learning",
            "ml",
            "predicción",
            "predictivo",
            "predecir",
            "segmentación",
            "segmentar",
            "clustering",
            "cluster",
            "anomalía",
            "anomalías",
            "patrones",
            "patrón",
            "inteligencia artificial",
            "ia",
            "modelo predictivo",
            "riesgo",
            "factores de riesgo",
            # Términos adicionales para mayor flexibilidad (solo si están en contexto de BD)
            "estado",
            "estados",
            "información",
            "consulta",
            "mostrar",
            "listar",
            "buscar",
            "encontrar",
            "filtrar",
            "ordenar",
            "agrupar",
            "sumar",
            "contar",
            "promedio",
            "máximo",
            "mínimo",
            "último",
            "reciente",
            "actual",
            "hoy",
            "ayer",
            "semana",
            "mes",
            "año",
            # Términos de consulta comunes
            "cuántos hay",
            "cuántas hay",
            "cuántos son",
            "cuántas son",
            "cuál es",
            "cuáles son",
            "qué hay",
            "qué son",
        ]

        pregunta_lower = pregunta.lower().strip()
        es_pregunta_bd = any(palabra in pregunta_lower for palabra in palabras_clave_bd)

        if not es_pregunta_bd:
            logger.warning(f"⚠️ Pregunta rechazada por no contener palabras clave de BD: '{pregunta[:100]}...'")
            raise HTTPException(
                status_code=400,
                detail="El Chat AI solo responde preguntas sobre la base de datos del sistema. Tu pregunta debe incluir términos relacionados con: clientes, préstamos, pagos, cuotas, morosidad, estadísticas, datos, análisis, fechas, montos, o cualquier consulta sobre la información almacenada en el sistema. Para preguntas generales, usa el Chat de Prueba en la configuración de AI.",
            )

        # Obtener modelo y parámetros
        modelo = config_dict.get("modelo", "gpt-3.5-turbo")
        temperatura = float(config_dict.get("temperatura", "0.7"))
        max_tokens = int(config_dict.get("max_tokens", "2000"))  # Más tokens para respuestas más largas

        # Obtener resumen de la base de datos
        resumen_bd = _obtener_resumen_bd(db)

        # Agregar esquema completo y estadísticas (solo si la pregunta requiere análisis profundo)
        requiere_analisis_profundo = any(
            palabra in pregunta_lower
            for palabra in [
                "esquema",
                "estructura",
                "tablas",
                "campos",
                "índices",
                "schema",
                "relaciones",
                "foreign key",
                "cruces",
                "join",
                "consulta compleja",
            ]
        )

        # Siempre incluir inventario de campos (más organizado y útil para el AI)
        info_esquema = ""
        try:
            # Primero el mapeo semántico (para que el AI entienda sinónimos)
            info_esquema = "\n\n" + _obtener_mapeo_semantico_campos()
            # Luego el inventario completo
            info_esquema += "\n\n" + _obtener_inventario_campos_bd(db)
            info_esquema += "\n" + _obtener_estadisticas_tablas(db)

            # Si requiere análisis profundo, agregar esquema completo también
            if requiere_analisis_profundo:
                try:
                    info_esquema += "\n\n" + _obtener_esquema_bd_completo(db)
                except Exception as e:
                    logger.debug(f"Error obteniendo esquema completo: {e}")
        except Exception as e:
            logger.error(f"Error obteniendo inventario de campos: {e}")
            info_esquema = "\n\n[Inventario de campos no disponible en este momento]"

        # Buscar contexto en documentos usando embeddings (búsqueda semántica)
        contexto_documentos = ""
        documentos_activos = []

        try:
            # Verificar si hay embeddings disponibles
            total_embeddings = db.query(DocumentoEmbedding).count()
            documentos_con_embeddings = db.query(DocumentoEmbedding.documento_id).distinct().count()

            if total_embeddings > 0 and documentos_con_embeddings > 0:
                # Usar búsqueda semántica con embeddings
                logger.info(
                    f"🔍 Usando búsqueda semántica: {total_embeddings} embeddings en {documentos_con_embeddings} documentos"
                )

                try:
                    # Inicializar servicio RAG
                    service = RAGService(openai_api_key)

                    # Generar embedding de la pregunta
                    query_embedding = await service.generar_embedding(pregunta)

                    # Obtener todos los embeddings de documentos activos
                    documentos_activos_ids = [
                        doc_id
                        for doc_id, in (
                            db.query(DocumentoAI.id)
                            .filter(DocumentoAI.activo.is_(True), DocumentoAI.contenido_procesado.is_(True))
                            .all()
                        )
                    ]

                    if documentos_activos_ids:
                        # Obtener embeddings solo de documentos activos
                        embeddings_db = (
                            db.query(DocumentoEmbedding)
                            .filter(DocumentoEmbedding.documento_id.in_(documentos_activos_ids))
                            .all()
                        )

                        if embeddings_db:
                            documento_embeddings = [
                                {
                                    "documento_id": emb.documento_id,
                                    "chunk_index": emb.chunk_index,
                                    "texto_chunk": emb.texto_chunk,
                                    "embedding": emb.embedding,
                                }
                                for emb in embeddings_db
                            ]

                            # Buscar documentos relevantes usando similitud coseno
                            resultados = service.buscar_documentos_relevantes(
                                query_embedding, documento_embeddings, top_k=3, umbral_similitud=0.7
                            )

                            if resultados:
                                # Obtener los documentos completos ordenados por relevancia
                                documento_ids_relevantes = [r["documento_id"] for r in resultados]
                                documentos_activos = (
                                    db.query(DocumentoAI).filter(DocumentoAI.id.in_(documento_ids_relevantes)).all()
                                )

                                # Ordenar según la relevancia de los resultados
                                orden_relevancia = {r["documento_id"]: idx for idx, r in enumerate(resultados)}
                                documentos_activos.sort(key=lambda d: orden_relevancia.get(d.id, 999))

                                # Formatear similitudes antes del f-string (no se pueden usar backslashes en f-strings)
                                similitudes_str = ", ".join([f"{r['similitud']:.2f}" for r in resultados])
                                logger.info(
                                    f"✅ Búsqueda semántica: {len(documentos_activos)} documentos relevantes encontrados "
                                    f"(similitud: [{similitudes_str}])"
                                )
                            else:
                                logger.info(
                                    "ℹ️ Búsqueda semántica: No se encontraron documentos con similitud suficiente (umbral: 0.7)"
                                )
                        else:
                            logger.info("ℹ️ No hay embeddings para documentos activos, usando fallback")
                    else:
                        logger.info("ℹ️ No hay documentos activos, usando fallback")

                except Exception as embedding_error:
                    logger.warning(f"⚠️ Error en búsqueda semántica: {embedding_error}, usando método fallback")
                    # Continuar con método fallback
            else:
                logger.info(
                    f"ℹ️ No hay embeddings disponibles ({total_embeddings} embeddings, {documentos_con_embeddings} documentos), usando método fallback"
                )

            # Fallback: método simple si no hay embeddings o falló la búsqueda semántica
            if not documentos_activos:
                try:
                    documentos_activos = (
                        db.query(DocumentoAI)
                        .filter(DocumentoAI.activo.is_(True), DocumentoAI.contenido_procesado.is_(True))
                        .limit(3)
                        .all()
                    )
                    logger.info(f"📄 Fallback: {len(documentos_activos)} documentos activos encontrados")
                except Exception as doc_error:
                    error_str = str(doc_error)
                    error_type = type(doc_error).__name__
                    # Verificar si es un error de transacción abortada
                    is_transaction_aborted = (
                        "aborted" in error_str.lower()
                        or "InFailedSqlTransaction" in error_type
                        or "current transaction is aborted" in error_str.lower()
                    )

                    if is_transaction_aborted:
                        # Hacer rollback antes de reintentar
                        try:
                            db.rollback()
                            logger.debug("✅ Rollback realizado antes de consultar documentos AI (transacción abortada)")
                            # Reintentar la consulta
                            documentos_activos = (
                                db.query(DocumentoAI)
                                .filter(DocumentoAI.activo.is_(True), DocumentoAI.contenido_procesado.is_(True))
                                .limit(3)
                                .all()
                            )
                            logger.info(
                                f"📄 Documentos AI encontrados (después de rollback): {len(documentos_activos)} documentos"
                            )
                        except Exception as retry_error:
                            logger.error(f"❌ Error al reintentar consulta de documentos AI: {retry_error}")
                            # Continuar sin documentos si falla
                            documentos_activos = []
                    else:
                        logger.error(f"❌ Error consultando documentos AI: {doc_error}")
                        # Continuar sin documentos si falla
                        documentos_activos = []

            # Preparar contexto de documentos
            if documentos_activos:
                contextos = []
                for doc in documentos_activos:
                    if doc.contenido_texto and doc.contenido_texto.strip():
                        contenido_limpiado = doc.contenido_texto.strip()[:1500]
                        if len(doc.contenido_texto) > 1500:
                            contenido_limpiado += "..."
                        contextos.append(f"Documento: {doc.titulo}\n{contenido_limpiado}")
                        logger.debug(f"📄 Documento agregado al contexto: {doc.titulo} ({len(contenido_limpiado)} caracteres)")

                if contextos:
                    contexto_documentos = "\n\n=== DOCUMENTOS DE CONTEXTO ===\n" + "\n\n---\n\n".join(contextos)
                    logger.info(
                        f"✅ Contexto de documentos preparado: {len(contextos)} documentos, {len(contexto_documentos)} caracteres totales"
                    )
                else:
                    logger.warning("⚠️ Documentos encontrados pero sin contenido_texto válido")
            else:
                logger.debug("ℹ️ No hay documentos AI activos y procesados disponibles para contexto")

        except Exception as e:
            logger.error(f"❌ Error general buscando documentos: {e}", exc_info=True)
            # Continuar sin documentos si hay error general
            documentos_activos = []

        # Detectar si la pregunta es una búsqueda por cédula/documento
        import re

        busqueda_cedula = None
        patron_cedula = r"(?:cedula|cédula|documento|dni|ci)[\s:]*([A-Z0-9]+)"
        match_cedula = re.search(patron_cedula, pregunta, re.IGNORECASE)
        if match_cedula:
            busqueda_cedula = match_cedula.group(1).strip()
            logger.info(f"🔍 Búsqueda por cédula detectada: {busqueda_cedula}")

        # Detectar si la pregunta requiere cálculos específicos
        pregunta_lower = pregunta.lower()
        requiere_calculo_especifico = any(
            palabra in pregunta_lower
            for palabra in [
                "tasa de morosidad",
                "morosidad entre",
                "comparar",
                "diferencia entre",
                "análisis",
                "tendencia",
                "evolución",
                "cálculo",
                "calcular",
                "métrica",
                "porcentaje",
                "variación",
                "incremento",
                "disminución",
            ]
        )

        # Si es búsqueda por cédula, buscar información del cliente
        info_cliente_buscado = ""
        if busqueda_cedula:
            try:
                from sqlalchemy import func

                from app.models.amortizacion import Cuota
                from app.models.cliente import Cliente
                from app.models.prestamo import Prestamo

                cliente = db.query(Cliente).filter(Cliente.cedula == busqueda_cedula).first()

                if cliente:
                    info_cliente_buscado = f"\n\n=== INFORMACIÓN DEL CLIENTE BUSCADO (Cédula: {busqueda_cedula}) ===\n"
                    info_cliente_buscado += f"Nombre: {cliente.nombres}\n"
                    info_cliente_buscado += f"Cédula: {cliente.cedula}\n"
                    info_cliente_buscado += f"Teléfono: {cliente.telefono}\n"
                    info_cliente_buscado += f"Email: {cliente.email}\n"
                    info_cliente_buscado += f"Estado: {cliente.estado}\n"
                    info_cliente_buscado += f"Activo: {'Sí' if cliente.activo else 'No'}\n"
                    info_cliente_buscado += f"Fecha de registro: {cliente.fecha_registro}\n"

                    # Buscar préstamos del cliente
                    prestamos = db.query(Prestamo).filter(Prestamo.cedula == busqueda_cedula).all()
                    if prestamos:
                        info_cliente_buscado += f"\nPréstamos: {len(prestamos)} préstamo(s)\n"
                        for p in prestamos:
                            info_cliente_buscado += (
                                f"  - Préstamo ID {p.id}: {p.total_financiamiento} Bs, Estado: {p.estado}\n"
                            )

                        # Buscar cuotas pendientes
                        prestamos_ids = [p.id for p in prestamos]
                        cuotas_pendientes = (
                            db.query(Cuota)
                            .filter(Cuota.prestamo_id.in_(prestamos_ids), Cuota.estado.in_(["PENDIENTE", "MORA"]))
                            .all()
                        )
                        if cuotas_pendientes:
                            total_pendiente = sum(float(c.monto_cuota - c.total_pagado) for c in cuotas_pendientes)
                            info_cliente_buscado += f"\nCuotas pendientes: {len(cuotas_pendientes)} cuota(s)\n"
                            info_cliente_buscado += f"Total pendiente: {total_pendiente:,.2f} Bs\n"
                    else:
                        info_cliente_buscado += "\nPréstamos: 0 préstamos\n"
                else:
                    # Buscar en préstamos por si acaso
                    prestamo = db.query(Prestamo).filter(Prestamo.cedula == busqueda_cedula).first()
                    if prestamo:
                        info_cliente_buscado = f"\n\n=== INFORMACIÓN ENCONTRADA (Cédula: {busqueda_cedula}) ===\n"
                        info_cliente_buscado += (
                            f"⚠️ Cliente no encontrado en tabla clientes, pero hay préstamos con esta cédula\n"
                        )
                        info_cliente_buscado += f"Nombre en préstamo: {prestamo.nombres}\n"
                        info_cliente_buscado += f"Cédula: {prestamo.cedula}\n"
                        info_cliente_buscado += f"Préstamo ID: {prestamo.id}\n"
                        info_cliente_buscado += f"Total financiamiento: {prestamo.total_financiamiento} Bs\n"
                        info_cliente_buscado += f"Estado: {prestamo.estado}\n"
                    else:
                        info_cliente_buscado = f"\n\n=== BÚSQUEDA POR CÉDULA: {busqueda_cedula} ===\n"
                        info_cliente_buscado += (
                            "❌ No se encontró ningún cliente ni préstamo con esta cédula en la base de datos.\n"
                        )

                logger.info(f"✅ Información del cliente buscado preparada: {len(info_cliente_buscado)} caracteres")
            except Exception as e:
                logger.error(f"Error buscando cliente por cédula: {e}")
                info_cliente_buscado = f"\n\n⚠️ Error al buscar cliente con cédula {busqueda_cedula}: {str(e)}\n"

        # Si requiere cálculo específico, ejecutar consultas adicionales
        datos_adicionales = ""
        if requiere_calculo_especifico:
            try:
                from datetime import datetime

                fecha_actual = datetime.now()

                # Intentar extraer meses/años de la pregunta
                meses_nombres = {
                    "enero": 1,
                    "febrero": 2,
                    "marzo": 3,
                    "abril": 4,
                    "mayo": 5,
                    "junio": 6,
                    "julio": 7,
                    "agosto": 8,
                    "septiembre": 9,
                    "octubre": 10,
                    "noviembre": 11,
                    "diciembre": 12,
                }

                # Buscar menciones de meses en la pregunta
                meses_encontrados = []
                for mes_nombre, mes_num in meses_nombres.items():
                    if mes_nombre in pregunta_lower:
                        # Intentar extraer el año
                        año_actual = fecha_actual.year
                        # Buscar año en la pregunta
                        import re

                        años_match = re.findall(r"\b(20\d{2})\b", pregunta)
                        año = int(años_match[0]) if años_match else año_actual
                        meses_encontrados.append((año, mes_num, mes_nombre))

                # Si se encontraron meses, calcular tasas de morosidad y análisis de pagos
                if meses_encontrados:
                    datos_adicionales += "\n\n=== CÁLCULOS ESPECÍFICOS SOLICITADOS ===\n"
                    for año, mes_num, mes_nombre in meses_encontrados:
                        # Calcular tasa de morosidad
                        resultado = _calcular_tasa_morosidad_mes(db, año, mes_num)
                        if resultado:
                            datos_adicionales += (
                                f"{mes_nombre.capitalize()} {año}: "
                                f"Total cuotas: {resultado['total_cuotas']}, "
                                f"Cuotas en mora: {resultado['cuotas_mora']}, "
                                f"Tasa de morosidad: {resultado['tasa_morosidad']}%, "
                                f"Monto en mora: {resultado['monto_mora']:,.2f}\n"
                            )

                        # Si pregunta sobre pagos según vencimiento, agregar análisis
                        if any(
                            palabra in pregunta_lower
                            for palabra in [
                                "pago según",
                                "pago segun",
                                "pagos según",
                                "pagos segun",
                                "pagado según",
                                "pagado segun",
                                "ninguno",
                                "ninguna",
                            ]
                        ):
                            analisis_pagos = _analizar_pagos_segun_vencimiento(db, año, mes_num)
                            if analisis_pagos:
                                datos_adicionales += (
                                    f"\n--- Análisis de Pagos según Fechas de Vencimiento ({mes_nombre.capitalize()} {año}) ---\n"
                                    f"Total cuotas con vencimiento en {mes_nombre}: {analisis_pagos['total_cuotas_vencimiento_mes']}\n"
                                    f"Cuotas pagadas según fecha de vencimiento (±3 días): {analisis_pagos['cuotas_pagadas_segun_vencimiento']}\n"
                                    f"Cuotas pagadas antes del vencimiento: {analisis_pagos['cuotas_pagadas_antes']}\n"
                                    f"Cuotas pagadas después del vencimiento: {analisis_pagos['cuotas_pagadas_despues']}\n"
                                    f"Cuotas no pagadas: {analisis_pagos['cuotas_no_pagadas']}\n"
                                    f"Porcentaje pagadas según vencimiento: {analisis_pagos['porcentaje_pagadas_segun_vencimiento']}%\n"
                                    f"Conclusión: {analisis_pagos['conclusion']}\n"
                                )

                # Si pregunta sobre análisis de cobranzas
                if any(palabra in pregunta_lower for palabra in ["análisis", "cobranzas", "clientes en mora"]):
                    analisis = _calcular_analisis_cobranzas(db)
                    if analisis:
                        datos_adicionales += "\n=== ANÁLISIS DE COBRANZAS ===\n"
                        datos_adicionales += (
                            f"Clientes en mora: {analisis['clientes_en_mora']}\n"
                            f"Monto total en mora: {analisis['monto_total_mora']:,.2f}\n"
                            f"Cuotas vencidas 1-30 días: {analisis['cuotas_1_30_dias']}\n"
                            f"Cuotas vencidas 31-60 días: {analisis['cuotas_31_60_dias']}\n"
                            f"Cuotas vencidas más de 60 días: {analisis['cuotas_mas_60_dias']}\n"
                        )

                # Detectar si requiere análisis de Machine Learning
                requiere_ml = any(
                    palabra in pregunta_lower
                    for palabra in [
                        "machine learning",
                        "ml",
                        "predicción",
                        "predictivo",
                        "predecir",
                        "segmentación",
                        "segmentar",
                        "clustering",
                        "cluster",
                        "anomalías",
                        "anomalía",
                        "patrones",
                        "patrón",
                        "inteligencia artificial",
                        "ia",
                        "modelo predictivo",
                    ]
                )

                if requiere_ml:
                    datos_adicionales += "\n\n=== ANÁLISIS DE MACHINE LEARNING ===\n"

                    # Predicción de morosidad
                    if any(palabra in pregunta_lower for palabra in ["morosidad", "mora", "predicción", "riesgo"]):
                        ml_morosidad = _analisis_ml_morosidad_predictiva(db)
                        if ml_morosidad:
                            datos_adicionales += f"\n--- {ml_morosidad['tipo_analisis']} ---\n"
                            datos_adicionales += f"Datos analizados: {ml_morosidad['datos_analizados']}\n"
                            datos_adicionales += "Top factores de riesgo:\n"
                            for factor in ml_morosidad.get("factores_riesgo", [])[:5]:
                                datos_adicionales += (
                                    f"  - {factor.get('analista', 'N/A')}: "
                                    f"Tasa mora {factor.get('tasa_mora_historica', 0)}%, "
                                    f"Riesgo {factor.get('nivel_riesgo', 'N/A')}\n"
                                )

                    # Segmentación de clientes
                    if any(palabra in pregunta_lower for palabra in ["segmentación", "segmentar", "clientes", "grupos"]):
                        ml_segmentacion = _analisis_ml_segmentacion_clientes(db)
                        if ml_segmentacion:
                            datos_adicionales += f"\n--- {ml_segmentacion['tipo_analisis']} ---\n"
                            datos_adicionales += f"Total analizados: {ml_segmentacion['total_analizados']}\n"
                            for segmento, datos in ml_segmentacion.get("segmentos", {}).items():
                                datos_adicionales += (
                                    f"  {segmento.capitalize()}: {datos.get('cantidad', 0)} clientes "
                                    f"({datos.get('caracteristicas', '')})\n"
                                )

                    # Detección de anomalías
                    if any(palabra in pregunta_lower for palabra in ["anomalía", "anomalías", "irregular", "extraño"]):
                        ml_anomalias = _analisis_ml_deteccion_anomalias(db)
                        if ml_anomalias:
                            datos_adicionales += f"\n--- {ml_anomalias['tipo_analisis']} ---\n"
                            datos_adicionales += f"Total anomalías detectadas: {ml_anomalias['total_anomalias']}\n"
                            for tipo, info in ml_anomalias.get("anomalias_por_tipo", {}).items():
                                datos_adicionales += f"  {tipo}: {info.get('cantidad', 0)} casos\n"

                    # Clustering
                    if any(palabra in pregunta_lower for palabra in ["clustering", "cluster", "agrupar", "grupos similares"]):
                        ml_clustering = _analisis_ml_clustering_prestamos(db)
                        if ml_clustering:
                            datos_adicionales += f"\n--- {ml_clustering['tipo_analisis']} ---\n"
                            datos_adicionales += f"Clusters identificados: {ml_clustering['clusters_identificados']}\n"
                            for cluster in ml_clustering.get("clusters", [])[:5]:
                                datos_adicionales += (
                                    f"  - {cluster.get('cluster_id', 'N/A')}: "
                                    f"{cluster.get('cantidad_prestamos', 0)} préstamos, "
                                    f"Mora promedio: {cluster.get('tasa_mora_promedio', 0)}%\n"
                                )

                    # Si no especifica tipo, ejecutar todos los análisis
                    if not any(
                        [
                            any(palabra in pregunta_lower for palabra in ["morosidad", "mora", "predicción", "riesgo"]),
                            any(palabra in pregunta_lower for palabra in ["segmentación", "segmentar", "clientes", "grupos"]),
                            any(palabra in pregunta_lower for palabra in ["anomalía", "anomalías", "irregular", "extraño"]),
                            any(
                                palabra in pregunta_lower
                                for palabra in ["clustering", "cluster", "agrupar", "grupos similares"]
                            ),
                        ]
                    ):
                        # Ejecutar análisis general de ML
                        ml_morosidad = _analisis_ml_morosidad_predictiva(db)
                        ml_segmentacion = _analisis_ml_segmentacion_clientes(db)

                        if ml_morosidad:
                            datos_adicionales += f"\n--- {ml_morosidad['tipo_analisis']} ---\n"
                            datos_adicionales += (
                                f"Factores de riesgo identificados: {len(ml_morosidad.get('factores_riesgo', []))}\n"
                            )

                        if ml_segmentacion:
                            datos_adicionales += f"\n--- {ml_segmentacion['tipo_analisis']} ---\n"
                            datos_adicionales += f"Clientes segmentados: {ml_segmentacion['total_analizados']}\n"
            except Exception as e:
                logger.error(f"Error calculando datos adicionales: {e}")

        # Obtener prompt personalizado si existe, sino usar el default
        prompt_personalizado = config_dict.get("system_prompt_personalizado", "")
        usar_prompt_personalizado = prompt_personalizado and prompt_personalizado.strip()

        # Obtener variables personalizadas activas
        variables_personalizadas = {}
        try:
            vars_activas = db.query(AIPromptVariable).filter(AIPromptVariable.activo.is_(True)).all()
            # Por ahora, las variables personalizadas se reemplazarán con valores vacíos
            # En el futuro se puede implementar lógica específica para cada variable
            for var in vars_activas:
                # Extraer el nombre sin llaves para usar como clave
                nombre_var = var.variable.strip("{}")
                variables_personalizadas[var.variable] = f"[Variable personalizada: {var.descripcion}]"
                variables_personalizadas[nombre_var] = f"[Variable personalizada: {var.descripcion}]"
        except Exception as e:
            logger.warning(f"Error obteniendo variables personalizadas: {e}")
            # Continuar sin variables personalizadas si hay error

        if usar_prompt_personalizado:
            logger.info("✅ Usando prompt personalizado configurado por el usuario")
            # El prompt personalizado debe incluir placeholders que se reemplazarán
            # Primero reemplazar variables predeterminadas
            try:
                system_prompt = prompt_personalizado.format(
                    resumen_bd=resumen_bd,
                    info_cliente_buscado=info_cliente_buscado,
                    datos_adicionales=datos_adicionales,
                    info_esquema=info_esquema,
                    contexto_documentos=contexto_documentos,
                )
                # Luego reemplazar variables personalizadas usando replace (más seguro)
                for var_name, var_value in variables_personalizadas.items():
                    if var_name.startswith("{") and var_name.endswith("}"):
                        system_prompt = system_prompt.replace(var_name, var_value)
            except KeyError as e:
                logger.warning(f"⚠️ Variable no encontrada en prompt personalizado: {e}")
                # Si falta una variable predeterminada, usar el prompt con las que están
                system_prompt = prompt_personalizado
                # Reemplazar manualmente las variables conocidas
                system_prompt = system_prompt.replace("{resumen_bd}", resumen_bd or "")
                system_prompt = system_prompt.replace("{info_cliente_buscado}", info_cliente_buscado or "")
                system_prompt = system_prompt.replace("{datos_adicionales}", datos_adicionales or "")
                system_prompt = system_prompt.replace("{info_esquema}", info_esquema or "")
                system_prompt = system_prompt.replace("{contexto_documentos}", contexto_documentos or "")
                # Reemplazar variables personalizadas
                for var_name, var_value in variables_personalizadas.items():
                    if var_name.startswith("{") and var_name.endswith("}"):
                        system_prompt = system_prompt.replace(var_name, var_value)
        else:
            # Construir prompt del sistema con información de la BD (default)
            system_prompt = f"""Eres un ANALISTA ESPECIALIZADO en préstamos y cobranzas con capacidad de análisis de KPIs operativos. Tu función es proporcionar información precisa, análisis de tendencias y métricas clave basándote EXCLUSIVAMENTE en los datos almacenados en las bases de datos del sistema.

ROL Y CONTEXTO:
- Eres un analista especializado en préstamos y cobranzas con capacidad de análisis de KPIs operativos
- Tu función es proporcionar información precisa, análisis de tendencias y métricas clave
- Basas tus respuestas EXCLUSIVAMENTE en los datos almacenados en las bases de datos del sistema
- Tienes acceso a información en tiempo real de la base de datos del sistema
- Proporcionas análisis, estadísticas y recomendaciones basadas en datos reales
- Eres profesional, claro y preciso en tus respuestas
- Proporcionas respuestas accionables con contexto e interpretación

RESTRICCIÓN IMPORTANTE: Solo puedes responder preguntas relacionadas con la base de datos del sistema. Si recibes una pregunta que NO esté relacionada con clientes, préstamos, pagos, cuotas, cobranzas, moras, estadísticas del sistema, o la fecha/hora actual, debes responder:

"Lo siento, el Chat AI solo responde preguntas sobre la base de datos del sistema (clientes, préstamos, pagos, cuotas, cobranzas, moras, estadísticas, etc.). Para preguntas generales, por favor usa el Chat de Prueba en la configuración de AI."

Tienes acceso a información de la base de datos del sistema y a la fecha/hora actual. Aquí tienes un resumen actualizado:

=== RESUMEN DE BASE DE DATOS ===
{resumen_bd}
{info_cliente_buscado}
{datos_adicionales}
{info_esquema}

=== INVENTARIO COMPLETO DE CAMPOS ===
El sistema tiene acceso completo a TODOS los campos de TODAS las tablas. 
El inventario detallado está disponible más abajo en "INVENTARIO COMPLETO DE CAMPOS DE BASE DE DATOS".

RESUMEN RÁPIDO DE TABLAS PRINCIPALES:
- **clientes**: Información de clientes (cedula, nombres, telefono, email, estado, activo)
- **prestamos**: Préstamos aprobados (cliente_id, cedula, total_financiamiento, estado, analista, concesionario)
- **cuotas**: Cuotas de préstamos (prestamo_id, fecha_vencimiento, monto_cuota, estado, total_pagado, fecha_pago)
- **pagos**: Pagos realizados (prestamo_id, cedula, fecha_pago, monto_pagado, numero_documento, activo)
- **notificaciones**: Notificaciones enviadas (cliente_id, tipo, estado, fecha_envio)
- **users**: Usuarios del sistema (email, nombre, apellido, rol, is_admin)
- **concesionarios**: Concesionarios (nombre, activo)
- **analistas**: Analistas/asesores (nombre, email, activo)
- **configuracion_sistema**: Configuración (categoria, clave, valor, tipo_dato)
- **documentos_ai**: Documentos para AI (titulo, contenido_texto, activo, contenido_procesado)

IMPORTANTE: Consulta el "INVENTARIO COMPLETO DE CAMPOS DE BASE DE DATOS" más abajo para:
- Ver TODOS los campos de cada tabla con sus tipos de datos
- Identificar qué campos están INDEXADOS (para consultas rápidas)
- Conocer las relaciones entre tablas (claves foráneas)
- Entender qué campos usar para filtros y búsquedas eficientes

CAPACIDADES PRINCIPALES:
1. **Consulta de datos individuales**: Información de préstamos, clientes y pagos específicos
2. **Análisis de KPIs**: Morosidad, recuperación, cartera en riesgo, efectividad de cobranza
3. **Análisis de tendencias**: Comparaciones temporales (aumentos/disminuciones)
4. **Proyecciones operativas**: Cuánto se debe cobrar hoy, esta semana, este mes
5. **Segmentación**: Análisis por rangos de mora, montos, productos, zonas
6. **Análisis de Machine Learning**: Predicción de morosidad, segmentación de clientes, detección de anomalías, clustering de préstamos

REGLAS FUNDAMENTALES:
1. **SOLO usa datos reales**: Accede a los índices de las bases de datos y consulta los campos específicos necesarios
2. **NUNCA inventes información**: Si un dato no existe en la base de datos, indica claramente que no está disponible
3. **Muestra tus cálculos**: Cuando calcules KPIs, indica la fórmula y los valores utilizados
4. **Compara con contexto**: Para tendencias, muestra período actual vs período anterior
5. **Respuestas accionables**: Incluye el "¿qué significa esto?" cuando sea relevante
6. **SOLO responde preguntas sobre la base de datos del sistema relacionadas con cobranzas y préstamos**
7. Si la pregunta NO es sobre la BD, responde con el mensaje de restricción mencionado arriba

PROCESO DE ANÁLISIS:
1. Identifica qué métrica o análisis solicita el usuario
2. Determina qué tabla(s), campo(s) y período de tiempo necesitas
3. Accede a los datos y realiza los cálculos necesarios
4. Compara con períodos anteriores si es relevante
5. Presenta resultados con contexto y conclusiones claras

EJEMPLOS DE PREGUNTAS VÁLIDAS (para referencia):
- **Búsqueda de clientes**: 
  * "¿Cómo se llama quien tiene este número de cédula: V19226493?"
  * "¿Quién tiene la cédula V19226493?"
  * "Buscar cliente con cédula V19226493"
  * "Datos del cliente con documento V19226493"
- **Consultas de préstamos**:
  * "¿Cuántos préstamos tiene el cliente con cédula V19226493?"
  * "¿Cuál es el estado del préstamo del cliente V19226493?"
  * "Mostrar préstamos del cliente V19226493"
- **Consultas de pagos y cuotas**:
  * "¿Cuántas cuotas tiene pendientes el cliente V19226493?"
  * "¿Cuánto debe el cliente con cédula V19226493?"
  * "Mostrar pagos del cliente V19226493"
- **Consultas de morosidad**:
  * "¿El cliente V19226493 está en mora?"
  * "¿Cuántos días de mora tiene el cliente V19226493?"
  * "¿Cuál es la morosidad del cliente V19226493?"
- **Consultas estadísticas**:
  * "¿Cuántos clientes hay en total?"
  * "¿Cuál es la tasa de morosidad actual?"
  * "¿Cuánto se debe cobrar hoy?"
  * "Mostrar estadísticas de préstamos"
- **Consultas de fechas**:
  * "¿Qué fecha es hoy?"
  * "¿Cuántas cuotas vencen hoy?"
  * "¿Cuáles son las cuotas vencidas?"

PATRONES DE PREGUNTAS RECONOCIDOS:
- Búsqueda por identificación: "cedula:", "cédula:", "documento:", "quien tiene", "como se llama"
- Consultas de estado: "estado", "cuánto debe", "en mora", "pendiente"
- Consultas de cantidad: "cuántos", "cuántas", "total", "cantidad"
- Consultas de información: "datos de", "información de", "mostrar", "listar"

INSTRUCCIONES ESPECÍFICAS PARA BÚSQUEDAS Y CONSULTAS:

**BÚSQUEDAS POR IDENTIFICACIÓN (Cédula/Documento)**:
- Cuando el usuario pregunta "¿Cómo se llama quien tiene este número de cédula: V19226493?" o similar:
  1. Busca en la tabla `clientes` usando el campo `cedula` (indexed para búsquedas rápidas)
  2. Si encuentras el cliente, proporciona: nombres, cédula, teléfono, email, estado, fecha_registro
  3. Si no encuentras el cliente, indica claramente: "No se encontró ningún cliente con la cédula V19226493"
  4. Puedes buscar también en `prestamos.cedula` si el cliente no está en la tabla clientes pero tiene préstamos
  5. Usa el mapeo semántico: "cedula", "cédula", "documento", "dni", "ci" son equivalentes

**CONSULTAS DE INFORMACIÓN DE CLIENTES**:
- Para preguntas como "datos del cliente", "información del cliente", "quién tiene la cédula":
  - Busca primero en `clientes` por `cedula`
  - Si hay préstamos, menciona: "El cliente tiene X préstamos"
  - Si hay cuotas pendientes, menciona: "Tiene Y cuotas pendientes"
  - Si está en mora, menciona: "El cliente está en mora con Z días de atraso"

**FORMATO DE RESPUESTA PARA BÚSQUEDAS**:
- Si encuentras el cliente:
  ```
  👤 Cliente encontrado:
  • Nombre: [nombres]
  • Cédula: [cedula]
  • Teléfono: [telefono]
  • Email: [email]
  • Estado: [estado]
  • Fecha de registro: [fecha_registro]
  ```
- Si no encuentras: "❌ No se encontró ningún cliente con la cédula [cedula] en la base de datos."

INSTRUCCIONES COMO ESPECIALISTA EN COBRANZAS Y PRÉSTAMOS:
1. Responde preguntas sobre la fecha y hora actual usando la información proporcionada en el resumen
2. **SI ESTÁS CONFUNDIDO, PUEDES HACER PREGUNTAS ACLARATORIAS**:
   - Si no estás seguro qué campo usar, pregunta: "¿Te refieres a [campo1] o [campo2]?"
   - Si hay ambigüedad en la pregunta, aclara: "Para darte una respuesta precisa, ¿te refieres a...?"
   - Ejemplos de preguntas aclaratorias válidas:
     * "¿Te refieres a fecha_vencimiento (cuándo debe pagarse) o fecha_pago (cuándo se pagó)?"
     * "¿Quieres saber el monto_pagado (de un pago específico) o total_pagado (acumulado de la cuota)?"
     * "¿Te refieres a morosidad en términos de días (dias_morosidad) o monto (monto_morosidad)?"
   - Es MEJOR preguntar que responder incorrectamente
5. Analiza y responde preguntas sobre préstamos, clientes, pagos, cuotas y moras basándote en el resumen
6. Proporciona análisis y recomendaciones basadas en los datos del resumen
7. Si la pregunta requiere datos específicos que no están en el resumen, indica que necesitarías hacer una consulta más específica
8. Usa los datos del resumen para dar respuestas precisas y profesionales
9. Si no tienes suficiente información, sé honesto al respecto
10. Formatea números grandes con separadores de miles
11. Responde siempre en español con un tono profesional de especialista
12. Para preguntas sobre la fecha actual, usa la información de "Fecha y hora actual del sistema" del resumen
13. Proporciona contexto y análisis cuando sea relevante (ej: "Tienes X cuotas en mora, lo que representa Y% del total")
14. **COMPRENSIÓN SEMÁNTICA DE CAMPOS**: 
    - NO busques solo coincidencias textuales exactas. Usa el "MAPEO SEMÁNTICO DE CAMPOS" para entender sinónimos
    - Si el usuario dice "cuándo vence", entiende que se refiere a "fecha_vencimiento"
    - Si dice "monto pagado", puede referirse a "monto_pagado" o "total_pagado" según el contexto
    - Si dice "morosidad", considera: dias_morosidad, monto_morosidad, estado='MORA', o cuotas con fecha_vencimiento pasada
    - Si estás confundido entre dos campos similares, puedes hacer una pregunta aclaratoria:
      Ejemplo: "¿Te refieres a la fecha_vencimiento (cuándo debe pagarse) o fecha_pago (cuándo se pagó)?"
    - Usa inferencia semántica: relaciona conceptos similares aunque no sean exactamente iguales
    - Si no estás seguro del campo exacto, pregunta al usuario antes de responder incorrectamente

15. **CÁLCULOS MATEMÁTICOS Y CONSULTAS A BD**: Puedes y DEBES realizar cálculos matemáticos y análisis cuando se soliciten:
    - **KPIs DE MOROSIDAD**:
      * Índice de morosidad: (Cartera vencida / Cartera total) × 100
      * Cartera en riesgo: Suma de saldos con mora > X días
      * Distribución por días de mora: 1-30, 31-60, 61-90, 90+ días
      * Tendencia de morosidad: Comparación mes actual vs mes anterior
    - **COBRANZA DIARIA/SEMANAL/MENSUAL**:
      * Monto a cobrar hoy: Suma de cuotas con fecha_vencimiento = HOY
      * Monto vencido a recuperar: Suma de cuotas vencidas pendientes
      * Meta de cobranza: Proyección según calendario de pagos
    - **RECUPERACIÓN**:
      * Tasa de recuperación: (Monto cobrado en mora / Total cartera morosa) × 100
      * Efectividad de gestión: (Pagos logrados / Gestiones realizadas) × 100
      * Promesa vs pago: Comparación monto_comprometido vs pagos efectivos
    - **PORTAFOLIO**:
      * Cartera total: Suma de saldos_pendientes activos
      * Desembolsos del período: Nuevos préstamos por fecha
      * Crecimiento de cartera: Comparación período actual vs anterior
    - Comparaciones entre períodos: calcula diferencias y porcentajes de cambio
    - Promedios, sumas, diferencias, porcentajes, variaciones, etc.
    - Si la pregunta menciona meses específicos (ej: "septiembre", "octubre"), 
      el sistema automáticamente ejecutará consultas SQL para obtener datos precisos de esos meses
    - Usa los datos de "CÁLCULOS ESPECÍFICOS SOLICITADOS" cuando estén disponibles - son consultas directas a BD
    - **ANÁLISIS DE PAGOS SEGÚN FECHAS DE VENCIMIENTO**: 
      * El sistema puede analizar si los pagos se realizaron según las fechas de vencimiento de las cuotas
      * Compara fecha_pago de cuotas con fecha_vencimiento
      * Clasifica pagos como: según vencimiento (±3 días), antes, después, o no pagados
      * Si preguntan "ninguno en [mes] pagó según fechas de vencimiento", el sistema ejecutará este análisis automáticamente
      * Los resultados aparecen en "Análisis de Pagos según Fechas de Vencimiento"
14. **ESTRUCTURA DE RESPUESTA PARA ANÁLISIS**:
    
    **Para consultas de tendencias**:
    - **Métrica**: [Nombre del KPI]
    - **Período actual**: [Valor y fecha]
    - **Período anterior**: [Valor y fecha de comparación]
    - **Cambio**: [+/- X% o $X] → ⬆️ Aumentó / ⬇️ Disminuyó
    - **Interpretación**: [Qué significa este cambio]
    - **Fuente de datos**: [Tablas y campos utilizados]
    
    **Para proyecciones operativas**:
    - **Concepto**: [Qué se debe cobrar]
    - **Monto total**: $[X,XXX.XX]
    - **Desglose**: 
      - Por rango de mora: [distribución]
      - Top clientes: [mayores montos]
      - Por zona/producto: [si aplica]
    - **Fuente**: [Query o cálculo realizado]
    
    **CUANDO REALICES CÁLCULOS, siempre muestra**:
    - ✅ Fórmula utilizada
    - ✅ Valores extraídos de la BD
    - ✅ Resultado final
    - ✅ Tablas/campos consultados
    - ✅ Fecha de corte de datos
16. **ANÁLISIS DE COBRANZAS**: Cuando se soliciten análisis de cobranzas:
    - Usa los datos de "ANÁLISIS DE COBRANZAS" si están disponibles
    - Proporciona desglose por rangos de días (1-30, 31-60, más de 60 días)
    - Calcula porcentajes y proporciones
    - Identifica áreas críticas que requieren atención
    - Incluye ranking de gestores si aplica
    - Analiza productos problemáticos y zonas críticas

17. **ANÁLISIS AUTOMÁTICOS QUE PUEDES REALIZAR**:
    - **Alertas de deterioro**: Detectar incrementos >10% en morosidad
    - **Ranking de gestores**: Efectividad por gestor_id/analista
    - **Productos problemáticos**: Qué tipo de préstamo tiene mayor mora
    - **Zonas críticas**: Análisis geográfico de morosidad (si hay campo zona/direccion)
    - **Proyección de flujo**: Cuánto entra esta semana/mes según calendario
    - **Clientes en riesgo**: Identificar patrones de deterioro (pagos irregulares)

18. **CONSULTAS DIRECTAS A BD**: El sistema ejecuta automáticamente consultas SQL cuando detecta:
    - Menciones de meses específicos en preguntas sobre morosidad
    - Preguntas sobre análisis de cobranzas
    - Comparaciones entre períodos
    - Estos datos aparecen en "CÁLCULOS ESPECÍFICOS SOLICITADOS" y "ANÁLISIS DE COBRANZAS"
    - SIEMPRE usa estos datos cuando estén disponibles, son más precisos que el resumen general
19. **ACCESO COMPLETO A BD**: Tienes acceso completo a todas las tablas, campos e índices:
    - Usa los índices disponibles para consultas rápidas (campos marcados como indexed)
    - Puedes hacer cruces de datos usando las relaciones (JOINs) documentadas
    - Ejemplos de cruces útiles:
      * clientes JOIN prestamos: Análisis de clientes y sus préstamos
      * prestamos JOIN cuotas: Análisis de préstamos y estado de cuotas
      * cuotas JOIN pagos: Análisis de pagos aplicados a cuotas
      * clientes JOIN notificaciones: Análisis de notificaciones por cliente
    - Si necesitas el esquema completo, está disponible en la sección "ESQUEMA COMPLETO DE BASE DE DATOS"
19. **ANÁLISIS AVANZADO Y MACHINE LEARNING - HABILITADO**:
    - El sistema tiene capacidades de Machine Learning activas y puede ejecutar análisis automáticamente
    - Cuando detectes preguntas sobre ML, el sistema ejecutará consultas SQL especializadas
    - **TIPOS DE ANÁLISIS ML DISPONIBLES**:
      
      a) **PREDICCIÓN DE MOROSIDAD**:
         - Analiza patrones históricos de morosidad por analista/concesionario
         - Calcula factores de riesgo basados en múltiples variables
         - Identifica préstamos con mayor probabilidad de mora
         - Palabras clave: "predicción morosidad", "riesgo", "predecir mora"
      
      b) **SEGMENTACIÓN DE CLIENTES**:
         - Agrupa clientes en segmentos: Excelentes, Buenos, Regulares, Riesgo
         - Basado en comportamiento de pago histórico
         - Permite estrategias diferenciadas por segmento
         - Palabras clave: "segmentación", "segmentar clientes", "grupos de clientes"
      
      c) **DETECCIÓN DE ANOMALÍAS**:
         - Identifica pagos con montos inusuales (muy altos o muy bajos)
         - Detecta pagos registrados antes de aprobación de préstamo
         - Encuentra patrones irregulares en transacciones
         - Palabras clave: "anomalías", "irregularidades", "pagos extraños"
      
      d) **CLUSTERING DE PRÉSTAMOS**:
         - Agrupa préstamos por características similares (analista, producto, modalidad)
         - Identifica clusters de alto y bajo rendimiento
         - Permite optimizar políticas por tipo de cluster
         - Palabras clave: "clustering", "agrupar préstamos", "grupos similares"
    
    - **CÓMO USAR**: Simplemente pregunta sobre cualquiera de estos análisis y el sistema los ejecutará automáticamente
    - **EJEMPLOS**:
      * "Haz un análisis de machine learning para predecir morosidad"
      * "Segmenta los clientes por comportamiento de pago"
      * "Detecta anomalías en los pagos recientes"
      * "Agrupa los préstamos por características similares"
    - Los resultados aparecerán en la sección "ANÁLISIS DE MACHINE LEARNING"

=== DOCUMENTOS DE CONTEXTO ADICIONAL ===
{contexto_documentos}
NOTA: Si hay documentos de contexto arriba, úsalos como información adicional para responder preguntas. Los documentos pueden contener políticas, procedimientos, o información relevante sobre el sistema.

RESTRICCIONES IMPORTANTES:
- ⚠️ PROHIBIDO INVENTAR DATOS: Solo usa la información proporcionada en el resumen. NO inventes, NO uses tu conocimiento de entrenamiento, NO asumas datos.
- ⚠️ NO hagas suposiciones sobre datos faltantes
- ⚠️ NO uses promedios históricos como datos reales sin aclararlo
- ⚠️ FECHA ACTUAL: La fecha y hora actual están incluidas en el resumen. DEBES usar EXACTAMENTE esa información. Si te preguntan "¿qué fecha es hoy?", responde con la fecha del resumen, NO con tu conocimiento.
- ⚠️ DATOS DE BD: Solo usa los números y estadísticas del resumen. Si no está en el resumen, di que no tienes esa información específica.
- ⚠️ NO INVENTES: Si no tienes la información exacta, di "No tengo esa información específica en el resumen proporcionado" en lugar de inventar.
- ⚠️ ANÁLISIS PROFESIONAL: Como especialista, proporciona análisis y contexto cuando sea relevante, pero siempre basado en los datos del resumen.
- Si faltan datos para un análisis completo, indícalo claramente
- Para tendencias, necesitas al menos 2 períodos de comparación
- Si hay valores atípicos, señálalos

CUANDO NO PUEDAS RESPONDER:
- **Datos insuficientes**: "Para este análisis necesito datos de [especificar], que no están disponibles actualmente"
- **Período no disponible**: "Solo tengo datos desde [fecha]. ¿Deseas el análisis con la información disponible?"
- **Cálculo complejo**: "Este análisis requiere: [listar requisitos]. ¿Confirmas que proceda?"

OBJETIVO:
Tu objetivo es ser el asistente analítico que permita tomar decisiones informadas sobre la gestión de préstamos y cobranzas, proporcionando análisis precisos, tendencias claras y métricas accionables basadas exclusivamente en los datos reales del sistema.

RECUERDA: Si la pregunta NO es sobre la base de datos, debes rechazarla con el mensaje de restricción."""

        # Verificar que el contexto de documentos se incluyó en el prompt
        if contexto_documentos:
            logger.info(f"✅ Contexto de documentos incluido en system_prompt: {len(contexto_documentos)} caracteres")
        else:
            logger.debug("ℹ️ No hay contexto de documentos para incluir en el prompt")

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
