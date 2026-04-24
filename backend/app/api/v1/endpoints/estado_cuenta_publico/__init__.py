"""Estado de cuenta público: router FastAPI."""

from .routes import router
from .autoresponder import router as _autoresponder_router

router.include_router(_autoresponder_router)

__all__ = ["router"]
