# Patch: carga masiva -> fecha_aprobacion = fecha_registro
import os
path = os.path.join(os.path.dirname(__file__), "backend", "app", "api", "v1", "endpoints", "prestamos.py")
with open(path, "r", encoding="utf-8") as f:
    s = f.read()

# 1) Replace estado/fecha_aprob logic
old1 = """    fecha_req = payload.fecha_requerimiento or hoy
    estado_inicial = "APROBADO" if getattr(payload, "aprobado_por_carga_masiva", False) else (payload.estado or "DRAFT")
    fecha_aprob = datetime.combine(fecha_req, time.min) if getattr(payload, "aprobado_por_carga_masiva", False) else None
    row = Prestamo("""
new1 = """    es_carga_masiva = getattr(payload, "aprobado_por_carga_masiva", False)
    estado_inicial = "APROBADO" if es_carga_masiva else (payload.estado or "DRAFT")
    # Carga masiva: fecha_aprobacion = fecha_registro (se asigna después del commit/refresh)
    fecha_aprob = None if es_carga_masiva else None
    row = Prestamo("""
if old1 in s:
    s = s.replace(old1, new1)
    print("1) Replaced estado/fecha_aprob block")
else:
    print("1) Block not found (maybe already patched?)")

# 2) After db.refresh(row) add asignación fecha_aprobacion = fecha_registro
old2 = """    db.add(row)
    db.commit()
    db.refresh(row)
    
    # [MEJORA] Generar cuotas autom"""
new2 = """    db.add(row)
    db.commit()
    db.refresh(row)
    if es_carga_masiva and row.fecha_registro:
        row.fecha_aprobacion = row.fecha_registro
        db.commit()
        db.refresh(row)
    
    # [MEJORA] Generar cuotas autom"""
# Try with á in automáticamente
old2_alt = """    db.add(row)
    db.commit()
    db.refresh(row)
    
    # [MEJORA] Generar cuotas automáticamente"""
new2_alt = """    db.add(row)
    db.commit()
    db.refresh(row)
    if es_carga_masiva and row.fecha_registro:
        row.fecha_aprobacion = row.fecha_registro
        db.commit()
        db.refresh(row)
    
    # [MEJORA] Generar cuotas automáticamente"""
if old2 in s:
    s = s.replace(old2, new2)
    print("2) Replaced refresh block (no accent)")
elif old2_alt in s:
    s = s.replace(old2_alt, new2_alt)
    print("2) Replaced refresh block (with accent)")
else:
    print("2) Refresh block not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(s)
print("Done.")
