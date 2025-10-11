# backend/app/api/v1/endpoints/test.py
from fastapi import APIRouter, Body
from pydantic import BaseModel

router = APIRouter()


class TestModel(BaseModel):
    nombre: str
    edad: int


@router.post("/simple")
def test_simple(data: TestModel):
    """Test endpoint ultra simple"""
    return {
        "recibido": True,
        "nombre": data.nombre,
        "edad": data.edad
    }


@router.post("/raw")
def test_raw(data: dict = Body(...)):
    """Test con dict raw"""
    return {
        "recibido": True,
        "data": data
    }
