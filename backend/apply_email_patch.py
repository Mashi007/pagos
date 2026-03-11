# Apply email config validation patch
from pathlib import Path

path = Path("app/api/v1/endpoints/configuracion_email.py")
text = path.read_text(encoding="utf-8")

# 1. Add import
import_line = "from app.api.v1.endpoints.email_config_validacion import validar_config_email_para_guardar"
if import_line not in text:
    text = text.replace(
        "from app.models.configuracion import Configuracion\n\nlogger",
        "from app.models.configuracion import Configuracion\n" + import_line + "\n\nlogger",
        1,
    )
    print("Import added")

# 2. Add validation in PUT (before update_from_api and _persist)
old = "    update_from_api(_email_config_stub)\n    _persist_email_config(db)"
detail_join = '"; ".join(errores)'
new = (
    "    valido, errores = validar_config_email_para_guardar(_email_config_stub)\n"
    "    if not valido:\n"
    "        raise HTTPException(status_code=400, detail=" + repr(detail_join) + ")\n"
    "    update_from_api(_email_config_stub)\n"
    "    _persist_email_config(db)"
)
# Fix: detail must be the result of join, not the string '"; ".join(errores)'
new = (
    "    valido, errores = validar_config_email_para_guardar(_email_config_stub)\n"
    "    if not valido:\n"
    '        raise HTTPException(status_code=400, detail="; ".join(errores))\n'
    "    update_from_api(_email_config_stub)\n"
    "    _persist_email_config(db)"
)
if old in text and "validar_config_email_para_guardar(_email_config_stub)" not in text:
    text = text.replace(old, new, 1)
    print("Validation block added")

path.write_text(text, encoding="utf-8")
print("Patch applied.")
