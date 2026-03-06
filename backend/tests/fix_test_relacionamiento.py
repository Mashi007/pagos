# Script to fix test_relacionamiento_pago_prestamo_cuotas.py
path = r"test_relacionamiento_pago_prestamo_cuotas.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Fix 1: typo
c = c.replace(
    'nombres="Test Relacionamiento",`n        telefono="0000000000",',
    'nombres="Test Relacionamiento",\n        telefono="0000000000",',
)

# Fix 2: second test
old2 = """def test_pago_sin_prestamo_id_no_aplica_a_cuotas(db: Session):
    \"\"\"
    Si un pago no tiene prestamo_id, la aplicación a cuotas no debe modificar ninguna cuota.
    \"\"\"
    from app.models.cuota_pago import CuotaPago
    from sqlalchemy import func

    # Crear un pago sin préstamo
    numero_doc = f"REL-NULL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pago = Pago(
        prestamo_id=None,
        cedula_cliente=cliente.cedula,
        
        fecha_pago=datetime.now(),"""

new2 = """def test_pago_sin_prestamo_id_no_aplica_a_cuotas(db: Session):
    \"\"\"
    Si un pago no tiene prestamo_id, la aplicación a cuotas no debe modificar ninguna cuota.
    \"\"\"
    from datetime import date as date_type
    from app.models.cuota_pago import CuotaPago
    from sqlalchemy import func

    # Cliente mínimo (FK pagos.cedula -> clientes.cedula)
    cedula_null = f"VNULL{datetime.now().strftime('%H%M%S')}"
    cliente = Cliente(
        cedula=cedula_null,
        nombres="Test Null Prestamo",
        telefono="0000000000",
        email="null@test.local",
        direccion="Calle Test",
        fecha_nacimiento=date_type(1990, 1, 1),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="Test pago sin prestamo_id",
    )
    db.add(cliente)
    db.flush()

    # Crear un pago sin préstamo
    numero_doc = f"REL-NULL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pago = Pago(
        prestamo_id=None,
        cedula_cliente=cliente.cedula,
        fecha_pago=datetime.now(),"""

c = c.replace(old2, new2)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")
