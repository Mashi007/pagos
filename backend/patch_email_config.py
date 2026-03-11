# Script one-off: integrar validacion en configuracion_email y actualizar docstring
from pathlib import Path

p = Path("app/api/v1/endpoints/configuracion_email.py")
t = p.read_text(encoding="utf-8")

# 1) Add import after Configuracion
old_import = "from app.models.configuracion import Configuracion\n\nlogger"
new_import = "from app.models.configuracion import Configuracion\nfrom app.api.v1.endpoints.email_config_validacion import validar_config_email_para_guardar\n\nlogger"
if "validar_config_email_para_guardar" not in t:
    t = t.replace(
        "from app.models.configuracion import Configuracion\n\nlogger",
        new_import,
        1,
    )
    print("Added import")
else:
    print("Import already present")

# 2) In PUT: after merging into stub, add validation and raise if invalid
old_put_block = """    update_from_api(_email_config_stub)
    _persist_email_config(db)
    logger.info("Configuracion email actualizada y persistida en BD (campos: %s)", list(data.keys()))"""
new_put_block = """    # Legitimacion: validar antes de persistir (emails, puertos, obligatorios)
    valido, errores = validar_config_email_para_guardar(_email_config_stub)
    if not valido:
        raise HTTPException(status_code=400, detail="; ".join(errores))
    update_from_api(_email_config_stub)
    _persist_email_config(db)
    logger.info("Configuracion email actualizada y persistida en BD (campos: %s)", list(data.keys()))"""
if "validar_config_email_para_guardar(_email_config_stub)" not in t:
    t = t.replace(old_put_block, new_put_block, 1)
    print("Added validation in PUT")
else:
    print("Validation already in PUT")

p.write_text(t, encoding="utf-8")
print("Done.")
