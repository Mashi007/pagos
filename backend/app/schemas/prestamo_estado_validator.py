# Validación de estado de préstamo para evitar que se persistan PROBADO/RAFT.
# Añadir al inicio de app/schemas/prestamo.py (después de los imports) y usar
# field_validator en PrestamoBase y PrestamoUpdate.

PRESTAMO_ESTADOS_VALIDOS = frozenset({"APROBADO", "DRAFT", "EN_REVISION", "EVALUADO", "RECHAZADO", "DESEMBOLSADO"})


def normalizar_estado_prestamo(v: Optional[str]) -> str:
    """Corrige typos conocidos (PROBADO->APROBADO, RAFT->DRAFT) y devuelve valor normalizado."""
    if not v or not str(v).strip():
        return "DRAFT"
    s = str(v).strip().upper()
    if s == "PROBADO":
        return "APROBADO"
    if s == "RAFT":
        return "DRAFT"
    return s
