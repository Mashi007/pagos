# One-off script to fix create_prestamo except block
path = "backend/app/api/v1/endpoints/prestamos.py"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()

old = """    monto_cuota = _resolver_monto_cuota(row, total_financiamiento, numero_cuotas)
    
    try:
        cuotas_generadas = _generar_cuotas_amortizacion(db, row, hoy, numero_cuotas, monto_cuota)
        db.commit()
        logger.info(f"Préstamo {row.id}: {cuotas_generadas} cuotas generadas automáticamente")
    except Exception as e:
        logger.error(f"Error generando cuotas para préstamo {row.id}: {e}")
        db.rollback()
        raise HTTPException("""

new = """    monto_cuota = _resolver_monto_cuota(row, total_financiamiento, numero_cuotas)
    prestamo_id = row.id  # guardar antes del try para no acceder a row tras rollback

    try:
        cuotas_generadas = _generar_cuotas_amortizacion(db, row, hoy, numero_cuotas, monto_cuota)
        db.commit()
        logger.info(f"Préstamo {prestamo_id}: {cuotas_generadas} cuotas generadas automáticamente")
    except Exception as e:
        db.rollback()
        logger.error("Error generando cuotas para préstamo %s: %s", prestamo_id, str(e))
        raise HTTPException("""

if old in s:
    s = s.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    print("Patch applied.")
else:
    print("Pattern not found in file.")
