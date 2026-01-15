"""
Router separado para gestión de logos
Evita conflictos con otras rutas que tienen parámetros Path con rate limiter
"""
import logging
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.rate_limiter import get_rate_limiter
from app.models.configuracion_sistema import ConfiguracionSistema
from app.models.user import User

logger = logging.getLogger(__name__)

# ✅ Router separado solo para logos
logo_router = APIRouter()

# ✅ Rate limiter específico para logos
limiter = get_rate_limiter()


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

    # Validar magic bytes para seguridad adicional
    if contents[:4] == b"<svg" or contents[:2] == b"\x89\x50" or contents[:2] == b"\xff\xd8":
        return
    raise HTTPException(
        status_code=400,
        detail="Formato de archivo no válido según magic bytes",
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


def _obtener_backup_logo_anterior(db: Session) -> Optional[dict]:
    """
    Obtiene un backup completo del logo anterior (filename y logo_data) antes de eliminarlo.
    Retorna un diccionario con 'filename' y 'logo_data' o None si no hay logo anterior.
    """
    try:
        logo_filename = _obtener_logo_anterior(db)
        if not logo_filename:
            return None

        # Obtener logo_data también
        logo_data_config = (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == "GENERAL",
                ConfiguracionSistema.clave == "logo_data",
            )
            .first()
        )

        backup = {
            "filename": logo_filename,
            "logo_data": logo_data_config.valor_json if logo_data_config and logo_data_config.valor_json else None,
            "logo_filename_config": logo_data_config if logo_data_config else None,
        }

        logger.info(f"✅ Backup del logo anterior creado: {logo_filename}")
        return backup
    except Exception as e:
        logger.warning(f"⚠️ Error creando backup del logo anterior: {str(e)}")
        return None


def _restaurar_logo_anterior(db: Session, backup: dict, logos_dir: Path) -> bool:
    """
    Restaura el logo anterior desde el backup si el guardado del nuevo logo falló.
    Retorna True si se restauró exitosamente, False en caso contrario.
    """
    try:
        if not backup or not backup.get("filename"):
            logger.warning("⚠️ No hay backup válido para restaurar")
            return False

        logo_filename = backup["filename"]
        logo_data = backup.get("logo_data")

        # Restaurar logo_filename en BD
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

        # Restaurar logo_data en BD si existe
        if logo_data:
            logo_data_config = (
                db.query(ConfiguracionSistema)
                .filter(
                    ConfiguracionSistema.categoria == "GENERAL",
                    ConfiguracionSistema.clave == "logo_data",
                )
                .first()
            )

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
                    visible_frontend=False,
                )
                db.add(logo_data_config)

        # Intentar restaurar archivo en filesystem desde BD si existe
        if logo_data and isinstance(logo_data, dict) and logo_data.get("base64"):
            try:
                import base64
                logo_bytes = base64.b64decode(logo_data["base64"])
                logo_path = logos_dir / logo_filename

                with open(logo_path, "wb") as f:
                    f.write(logo_bytes)
                logger.info(f"✅ Logo restaurado en filesystem desde BD: {logo_filename}")
            except Exception as fs_error:
                logger.warning(f"⚠️ No se pudo restaurar logo en filesystem: {str(fs_error)}")
                # Continuar - al menos la BD está restaurada

        db.commit()
        logger.info(f"✅ Logo anterior restaurado exitosamente: {logo_filename}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error restaurando logo anterior: {str(e)}", exc_info=True)
        return False


def _eliminar_logo_anterior(db: Session, logos_dir: Path, nuevo_logo_filename: str) -> None:
    """
    Elimina el logo anterior del filesystem y limpia datos antiguos de la BD.
    SOLO se debe llamar DESPUÉS de confirmar que el nuevo logo se guardó exitosamente.
    """
    try:
        logo_anterior_filename = _obtener_logo_anterior(db)

        # ✅ Eliminar todos los logos antiguos del filesystem (cualquier logo-custom.*)
        # excepto el nuevo si tiene el mismo nombre
        try:
            for archivo in logos_dir.glob("logo-custom.*"):
                # No eliminar si es el nuevo logo
                if archivo.name == nuevo_logo_filename:
                    continue
                try:
                    archivo.unlink()
                    logger.info(f"🗑️ Logo anterior eliminado del filesystem: {archivo.name}")
                except Exception as fs_error:
                    logger.warning(f"⚠️ No se pudo eliminar {archivo.name}: {str(fs_error)}")
        except Exception as glob_error:
            logger.warning(f"⚠️ Error buscando logos antiguos: {str(glob_error)}")

        # ✅ Limpiar datos antiguos de la BD si el nombre es diferente
        # (Si es el mismo nombre, _guardar_logo_en_bd lo actualizará)
        if logo_anterior_filename and logo_anterior_filename != nuevo_logo_filename:
            try:
                # Eliminar logo_data anterior si existe y es diferente
                logo_data_config = (
                    db.query(ConfiguracionSistema)
                    .filter(
                        ConfiguracionSistema.categoria == "GENERAL",
                        ConfiguracionSistema.clave == "logo_data",
                    )
                    .first()
                )

                if logo_data_config and logo_data_config.valor_json:
                    logo_data = logo_data_config.valor_json
                    if isinstance(logo_data, dict) and logo_data.get("filename") == logo_anterior_filename:
                        # Solo eliminar si el filename coincide con el anterior
                        db.delete(logo_data_config)
                        db.flush()  # Flush para asegurar que se elimine antes del commit
                        logger.info(f"🗑️ Logo data anterior eliminado de BD: {logo_anterior_filename}")
            except Exception as db_error:
                logger.warning(f"⚠️ No se pudo eliminar logo anterior de BD: {str(db_error)}")
                # No hacer rollback aquí, solo loguear el warning
    except Exception as e:
        # No fallar si no se puede eliminar el logo anterior
        logger.warning(f"⚠️ No se pudo eliminar logo anterior: {str(e)}")


def _guardar_logo_en_bd(db: Session, logo_filename: str, logo_base64: str, content_type: str) -> None:
    """
    Guarda o actualiza la referencia del logo en la base de datos.
    Almacena tanto el filename como el contenido base64 para persistencia.
    """
    import json

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


def _obtener_logo_desde_bd(filename: str, db: Session) -> Optional[tuple[bytes, str]]:
    """
    Intenta obtener el logo desde la BD (base64) como fallback si no existe en filesystem.
    Retorna (contenido_bytes, content_type) o None si no existe en BD.
    """
    import base64

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

    # ✅ Validación mejorada: verificar formato de filename
    if not filename.startswith("logo-custom") or not any(filename.endswith(ext) for ext in [".svg", ".png", ".jpg", ".jpeg"]):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")

    # ✅ Prevenir path traversal: validar que no contenga caracteres peligrosos
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo contiene caracteres no permitidos")

    # Usar path absoluto si UPLOAD_DIR está configurado
    if hasattr(settings, "UPLOAD_DIR") and settings.UPLOAD_DIR:
        uploads_dir = Path(settings.UPLOAD_DIR).resolve()
    else:
        uploads_dir = Path("uploads").resolve()

    logos_dir = uploads_dir / "logos"
    logo_path = logos_dir / filename

    # ✅ Validar path traversal: asegurar que el path resuelto esté dentro del directorio permitido
    try:
        logo_path_resolved = logo_path.resolve()
        logos_dir_resolved = logos_dir.resolve()
        # Verificar que el path resuelto esté dentro del directorio de logos
        if not str(logo_path_resolved).startswith(str(logos_dir_resolved)):
            raise HTTPException(status_code=400, detail="Intento de acceso a ruta no permitida")
    except (OSError, ValueError) as e:
        logger.error(f"Error validando path del logo: {e}")
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")

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


# ✅ IMPORTANTE: Las rutas sin parámetros deben ir ANTES de las rutas con parámetros
# Esto evita que FastAPI intente hacer match de /logo con /logo/{filename}

@logo_router.options("/logo")
async def eliminar_logo_options(request: Request):
    """Manejar preflight OPTIONS para DELETE /logo (CORS)"""
    return {"message": "OK"}


@logo_router.delete("/logo")
@limiter.limit("5/minute")  # ✅ Rate limiting: máximo 5 eliminaciones por minuto
async def eliminar_logo(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar logo personalizado y restaurar logo por defecto (solo administradores)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden eliminar el logo",
        )

    try:
        from app.core.config import settings

        # Obtener logo anterior desde BD
        logo_filename = _obtener_logo_anterior(db)

        if not logo_filename:
            logger.info("⚠️ No hay logo personalizado para eliminar")
            return {
                "message": "No hay logo personalizado para eliminar",
                "status": "success",
            }

        # Eliminar logo del filesystem si existe
        try:
            if hasattr(settings, "UPLOAD_DIR") and settings.UPLOAD_DIR:
                uploads_dir = Path(settings.UPLOAD_DIR).resolve()
            else:
                uploads_dir = Path("uploads").resolve()

            logos_dir = uploads_dir / "logos"
            logo_path = logos_dir / logo_filename

            if logo_path.exists():
                logo_path.unlink()
                logger.info(f"🗑️ Logo eliminado del filesystem: {logo_filename}")
        except Exception as fs_error:
            logger.warning(f"⚠️ No se pudo eliminar logo del filesystem: {str(fs_error)}")
            # Continuar - eliminaremos de BD de todas formas

        # Eliminar logo de la BD
        try:
            # Eliminar logo_filename
            logo_config = (
                db.query(ConfiguracionSistema)
                .filter(
                    ConfiguracionSistema.categoria == "GENERAL",
                    ConfiguracionSistema.clave == "logo_filename",
                )
                .first()
            )

            if logo_config:
                db.delete(logo_config)
                logger.info(f"🗑️ Logo filename eliminado de BD: {logo_filename}")

            # Eliminar logo_data
            logo_data_config = (
                db.query(ConfiguracionSistema)
                .filter(
                    ConfiguracionSistema.categoria == "GENERAL",
                    ConfiguracionSistema.clave == "logo_data",
                )
                .first()
            )

            if logo_data_config:
                db.delete(logo_data_config)
                logger.info(f"🗑️ Logo data eliminado de BD")

            db.commit()
            logger.info(f"✅ Logo personalizado eliminado exitosamente. Se usará el logo por defecto.")

            return {
                "message": "Logo personalizado eliminado exitosamente. Se usará el logo por defecto.",
                "status": "success",
                "filename": logo_filename,
            }
        except Exception as db_error:
            db.rollback()
            logger.error(f"❌ Error eliminando logo de BD: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error eliminando configuración de logo en base de datos: {str(db_error)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar logo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al eliminar logo: {str(e)}")


@logo_router.head("/logo/{filename}")
async def verificar_logo_existe(
    filename: Annotated[str, Path(..., description="Nombre del archivo del logo")],
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


@logo_router.get("/logo/{filename}")
async def obtener_logo(
    filename: Annotated[str, Path(..., description="Nombre del archivo del logo")],
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
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo logo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo logo: {str(e)}")


@logo_router.post("/upload-logo")
@limiter.limit("10/minute")  # ✅ Rate limiting: máximo 10 uploads por minuto
async def upload_logo(
    request: Request,
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

        # ✅ CREAR BACKUP del logo anterior ANTES de hacer cualquier cambio
        # Esto permite restaurarlo si falla el guardado del nuevo logo
        backup_logo_anterior = _obtener_backup_logo_anterior(db)

        # ✅ Eliminar el nuevo archivo si ya existe (por si acaso)
        if logo_path.exists():
            try:
                logo_path.unlink()
                logger.info(f"🗑️ Archivo existente eliminado antes de guardar nuevo: {logo_filename}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ No se pudo eliminar archivo existente: {str(cleanup_error)}")

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

        # Intentar guardar en BD (filename + base64)
        try:
            _guardar_logo_en_bd(db, logo_filename, logo_base64, content_type)
            # ✅ SOLO DESPUÉS de confirmar que se guardó exitosamente, eliminar el logo anterior
            _eliminar_logo_anterior(db, logos_dir, logo_filename)
        except Exception as db_error:
            db.rollback()

            # ✅ RESTAURAR logo anterior si falla el guardado del nuevo
            if backup_logo_anterior:
                logger.warning(f"⚠️ Error guardando nuevo logo, restaurando logo anterior...")
                if _restaurar_logo_anterior(db, backup_logo_anterior, logos_dir):
                    logger.info(f"✅ Logo anterior restaurado exitosamente después del error")
                else:
                    logger.error(f"❌ No se pudo restaurar el logo anterior")

            # Eliminar archivo nuevo si existe y falló el guardado
            try:
                if logo_path.exists():
                    logo_path.unlink()
                    logger.info(f"🗑️ Archivo de logo nuevo eliminado debido a error en BD: {logo_filename}")
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
