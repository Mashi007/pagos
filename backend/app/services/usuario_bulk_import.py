"""
Servicio para procesamiento de importación masiva de usuarios.
"""
import logging
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash
from app.core.user_utils import user_to_response
from app.models.user import User
from app.schemas.usuario_bulk import UserBulkItem, BulkImportResult

logger = logging.getLogger(__name__)


def procesar_importacion_usuarios(
    db: Session,
    usuarios: List[UserBulkItem],
    admin_email: str
) -> tuple[int, int, List[BulkImportResult]]:
    """
    Procesa importación masiva de usuarios.
    
    Args:
        db: Sesión de base de datos
        usuarios: Lista de usuarios a importar
        admin_email: Email del admin que realiza la importación
        
    Returns:
        Tupla con (total_exitosos, total_errores, lista_resultados)
    """
    resultados: List[BulkImportResult] = []
    total_exitosos = 0
    total_errores = 0
    
    # Emails y cédulas ya procesadas en esta carga para evitar duplicados internos
    emails_procesados = set()
    cedulas_procesadas = set()
    
    for item in usuarios:
        email_lower = item.email.lower().strip()
        cedula_clean = item.cedula.strip()
        resultado = BulkImportResult(
            email=item.email,
            status="pending",
            mensaje=""
        )
        
        try:
            # 1. Validación de duplicados en la misma carga
            if email_lower in emails_procesados:
                resultado.status = "error"
                resultado.mensaje = f"Email duplicado dentro de la carga: {item.email}"
                total_errores += 1
                resultados.append(resultado)
                continue
            
            if cedula_clean in cedulas_procesadas:
                resultado.status = "error"
                resultado.mensaje = f"Cédula duplicada dentro de la carga: {cedula_clean}"
                total_errores += 1
                resultados.append(resultado)
                continue
            
            # 2. Validación en BD: email duplicado
            if db.query(User).filter(User.email == email_lower).first():
                resultado.status = "error"
                resultado.mensaje = f"Email ya existe en el sistema: {item.email}"
                total_errores += 1
                resultados.append(resultado)
                continue
            
            # 3. Validación en BD: cédula duplicada
            if db.query(User).filter(User.cedula == cedula_clean).first():
                resultado.status = "error"
                resultado.mensaje = f"Cédula ya existe en el sistema: {cedula_clean}"
                total_errores += 1
                resultados.append(resultado)
                continue
            
            # 4. Crear usuario
            from datetime import datetime
            now = datetime.utcnow()
            usuario = User(
                email=email_lower,
                cedula=cedula_clean,
                password_hash=get_password_hash(item.password),
                nombre=item.nombre.strip(),
                cargo=item.cargo.strip() if item.cargo else None,
                rol=item.rol,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            
            db.add(usuario)
            db.flush()  # Para obtener el ID sin commitear aún
            
            # Marcar como procesados
            emails_procesados.add(email_lower)
            cedulas_procesadas.add(cedula_clean)
            
            resultado.status = "success"
            resultado.mensaje = "Usuario creado exitosamente"
            resultado.usuario_id = usuario.id
            total_exitosos += 1
            
            logger.info(
                f"Usuario creado en importación masiva: email={email_lower}, cedula={cedula_clean}, "
                f"rol={item.rol}, por admin={admin_email}"
            )
            
        except IntegrityError as e:
            db.rollback()
            resultado.status = "error"
            resultado.mensaje = f"Error de integridad en BD: {str(e)}"
            total_errores += 1
            logger.warning(f"IntegrityError en importación: {email_lower} - {e}")
            
        except Exception as e:
            db.rollback()
            resultado.status = "error"
            resultado.mensaje = f"Error procesando usuario: {str(e)}"
            total_errores += 1
            logger.error(f"Error en importación de {email_lower}: {e}")
        
        resultados.append(resultado)
    
    # Commit de todos los usuarios exitosos
    try:
        db.commit()
        logger.info(
            f"Importación masiva completada: {total_exitosos} exitosos, "
            f"{total_errores} errores, por admin={admin_email}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error al commitear importación masiva: {e}")
        # Marcar todos como error
        for resultado in resultados:
            if resultado.status == "success":
                resultado.status = "error"
                resultado.mensaje = f"Error al guardar en BD: {str(e)}"
                total_exitosos -= 1
                total_errores += 1
    
    return total_exitosos, total_errores, resultados
