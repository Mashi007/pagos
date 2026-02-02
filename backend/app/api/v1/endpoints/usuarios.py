"""
Endpoints de usuarios. Sin tabla users: listado devuelve admin desde env (si existe)
para que Tickets/Comunicaciones tengan al menos un usuario para asignación.
GET /api/v1/usuarios/ con page, page_size, is_active.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, Depends

from app.core.config import settings
from app.core.deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

_ISO_NOW = datetime.now(timezone.utc).isoformat()


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def listar_usuarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    is_active: Optional[bool] = Query(None),
):
    """
    Listado de usuarios. Sin tabla users: devuelve un único usuario admin desde env (ADMIN_EMAIL)
    para que el frontend no devuelva 404 y Tickets/Comunicaciones puedan asignar.
    """
    items = []
    admin_email = getattr(settings, "ADMIN_EMAIL", None) or ""
    if admin_email and admin_email.strip():
        # Un solo usuario "admin" para asignación en Tickets/Comunicaciones
        items.append({
            "id": 1,
            "email": admin_email.strip(),
            "nombre": "Admin",
            "apellido": "",
            "is_admin": True,
            "is_active": True,
            "created_at": _ISO_NOW,
            "updated_at": _ISO_NOW,
        })
    if is_active is True:
        items = [u for u in items if u.get("is_active")]
    elif is_active is False:
        items = [u for u in items if not u.get("is_active")]
    total = len(items)
    # Paginación simbólica
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
