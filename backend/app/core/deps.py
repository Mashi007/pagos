"""
Dependencias reutilizables para la API (autenticación, BD).
get_current_user: exige Bearer token válido; se usa en routers protegidos.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.env_admin_auth import is_configured_env_admin_email
from app.core.rol_normalization import canonical_rol
from app.core.security import decode_token
from app.core.user_utils import user_to_response
from app.models.finiquito import FiniquitoUsuarioAcceso
from app.models.user import User
from app.schemas.auth import UserResponse

security = HTTPBearer(auto_error=True)
security_optional_bearer = HTTPBearer(auto_error=False)


logger = logging.getLogger(__name__)

# Roles estándar (RBAC - Role-Based Access Control)
# admin: Full access
# manager: Gestión operativa
# operator: Operaciones básicas
# viewer: Solo lectura

ROLES_BLOQUEADOS_AUDITORIA_CARTERA = frozenset({"operator", "viewer"})


def _fake_user_response(email: str) -> UserResponse:
    """Usuario mínimo cuando no existe en BD (admin desde env)."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return UserResponse(
        id=1,
        email=email.lower(),
        nombre="Admin",
        apellido="Sistema",
        cargo="Administrador",
        rol="admin",
        is_active=True,
        created_at=now,
        updated_at=now,
        last_login=now,
    )


def staff_user_from_access_token_payload(db: Session, payload: dict) -> UserResponse:
    """
    Resuelve UserResponse desde un JWT de acceso de personal (no scope finiquito).
    """
    if payload.get("scope") == "finiquito":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no valido para sesion de personal",
        )
    sub = payload.get("sub") or payload.get("email")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    email = sub if "@" in sub else f"{sub}@admin.local"
    try:
        u = db.query(User).filter(User.email == email).first()
    except OperationalError as e:
        logger.warning("get_current_user: fallo de BD al cargar usuario: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
    if u and u.is_active:
        return user_to_response(u)
    if is_configured_env_admin_email(email):
        return _fake_user_response(email)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario no encontrado o inactivo",
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Obtiene el usuario actual a partir del Bearer token (desde BD o admin env).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token",
        )
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    if payload.get("scope") == "finiquito":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Use el token solo en el portal Finiquito",
        )
    return staff_user_from_access_token_payload(db, payload)


def require_admin(
    current: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Solo rol admin (acceso total)."""
    if canonical_rol(current.rol) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden acceder a este recurso.",
        )
    return current


def require_admin_or_operator(
    current: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Panel de gestión Finiquito (bandejas): admin, operario o gerente (rutas /finiquito/admin)."""
    rol = canonical_rol(current.rol)
    if rol not in ("admin", "operator", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador, operario o gerente.",
        )
    return current


def require_manager_or_admin(
    current: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Solo rol manager o admin (gestión operativa)."""
    rol = canonical_rol(current.rol)
    if rol not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de gerente o administrador.",
        )
    return current


def require_operator_or_higher(
    current: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Rol operator, manager o admin (operaciones)."""
    rol = canonical_rol(current.rol)
    if rol not in ("admin", "manager", "operator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere acceso de operario o superior.",
        )
    return current


def forbid_operator_clientes_gestion(
    current: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    CRM / gestión de clientes (listado, KPIs, alta/edición/baja, carga masiva, revisar).
    Los operadores no tienen acceso; sí pueden usar GET /clientes con búsqueda (mín. 2 caracteres)
    desde flujos como préstamos (ver lógica en endpoints.clientes.get_clientes).
    """
    if canonical_rol(current.rol) == "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Su rol no tiene acceso al módulo de gestión de clientes.",
        )
    return current




def require_auditoria_cartera_access(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Auditoria de cartera: denegado a rol operator / viewer."""
    r = canonical_rol(current_user.rol)
    if r in ROLES_BLOQUEADOS_AUDITORIA_CARTERA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La auditoria de cartera no esta disponible para su rol.",
        )
    return current_user


def get_finiquito_usuario_acceso(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional_bearer),
    db: Session = Depends(get_db),
) -> FiniquitoUsuarioAcceso:
    """
    Usuario del portal Finiquito (JWT con scope=finiquito, sub=id en finiquito_usuario_acceso).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token",
        )
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    if payload.get("scope") != "finiquito":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no válido para el portal Finiquito",
        )
    sub = payload.get("sub")
    if sub is None or str(sub).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    try:
        uid = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    u = (
        db.query(FiniquitoUsuarioAcceso)
        .filter(
            FiniquitoUsuarioAcceso.id == uid,
            FiniquitoUsuarioAcceso.is_active.is_(True),
        )
        .first()
    )
    if not u:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario Finiquito inactivo o inexistente",
        )
    return u


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> Optional[UserResponse]:
    """
    Usuario actual si hay Bearer token válido; None en caso contrario.
    """
    if not credentials or not credentials.credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None
    if payload.get("scope") == "finiquito":
        return None
    sub = payload.get("sub") or payload.get("email")
    if not sub:
        return None
    email = sub if "@" in sub else f"{sub}@admin.local"
    try:
        u = db.query(User).filter(User.email == email).first()
    except OperationalError as e:
        logger.warning("get_current_user: fallo de BD al cargar usuario: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)


@dataclass
class ComprobanteImagenReader:
    """Quién solicita GET /pagos/comprobante-imagen/{id}: personal o portal Finiquito."""

    staff: Optional[UserResponse] = None
    finiquito: Optional[FiniquitoUsuarioAcceso] = None


def get_comprobante_imagen_reader(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional_bearer),
    db: Session = Depends(get_db),
) -> ComprobanteImagenReader:
    """
    Bearer de personal (tabla users) o JWT portal Finiquito (misma ruta de comprobante).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token",
        )
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    if payload.get("scope") == "finiquito":
        sub = payload.get("sub")
        if sub is None or str(sub).strip() == "":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )
        try:
            uid = int(sub)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )
        u = (
            db.query(FiniquitoUsuarioAcceso)
            .filter(
                FiniquitoUsuarioAcceso.id == uid,
                FiniquitoUsuarioAcceso.is_active.is_(True),
            )
            .first()
        )
        if not u:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario Finiquito inactivo o inexistente",
            )
        return ComprobanteImagenReader(finiquito=u)
    staff = staff_user_from_access_token_payload(db, payload)
    return ComprobanteImagenReader(staff=staff)
