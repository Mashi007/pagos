from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def test():
    return {"mensaje": "Router independiente funcionando", "status": "ok"}
