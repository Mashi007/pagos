from pathlib import Path

P = Path("c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/api/v1/endpoints/pagos.py")
s = P.read_text(encoding="utf-8")
old = '''

def numero_documento_ya_registrado(

    db: Session, numero_documento: Optional[str], exclude_pago_id: Optional[int] = None

) -> bool:

    """Regla general: no duplicados en documentos. Comprueba si ya existe un pago con ese Nº documento."""

    num = normalize_documento(numero_documento)

    if not num:

        return False

    q = select(Pago.id).where(Pago.numero_documento == num)

    if exclude_pago_id is not None:

        q = q.where(Pago.id != exclude_pago_id)

    return db.scalar(q) is not None





'''
if old not in s:
    raise SystemExit("dup fn block not found")
s = s.replace(old, "\n\n", 1)
P.write_text(s, encoding="utf-8")
print("removed local duplicate")
