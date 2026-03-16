# Patch pipeline: import GmailTemporal and insert into gmail_temporal in _guardar_en_bd
import os
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(base, "app", "services", "pagos_gmail", "pipeline.py")

with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

if "GmailTemporal" in c:
    print("Pipeline already patched")
    exit(0)

# 1) Add GmailTemporal to import
old_import = "from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem"
new_import = "from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem, GmailTemporal"
if old_import not in c:
    print("Import line not found")
    exit(1)
c = c.replace(old_import, new_import)

# 2) After db.add(PagosGmailSyncItem(...)) add db.add(GmailTemporal(...))
# Find the block that ends with "return True" after "fila_guardada = True"
old_block = """                        db.add(PagosGmailSyncItem(
                            sync_id=sync_id,
                            correo_origen=correo,
                            asunto=subject,
                            fecha_pago=fecha,
                            cedula=cedula,
                            monto=monto,
                            numero_referencia=referencia,
                            drive_file_id=drive_file_id,
                            drive_link=drive_lnk or None,
                            drive_email_link=email_lnk or None,
                            sheet_name=sheet_name,
                        ))
                        files_ok += 1
                        fila_guardada = True
                        return True"""

new_block = """                        db.add(PagosGmailSyncItem(
                            sync_id=sync_id,
                            correo_origen=correo,
                            asunto=subject,
                            fecha_pago=fecha,
                            cedula=cedula,
                            monto=monto,
                            numero_referencia=referencia,
                            drive_file_id=drive_file_id,
                            drive_link=drive_lnk or None,
                            drive_email_link=email_lnk or None,
                            sheet_name=sheet_name,
                        ))
                        db.add(GmailTemporal(
                            correo_origen=correo,
                            asunto=subject,
                            fecha_pago=fecha,
                            cedula=cedula,
                            monto=monto,
                            numero_referencia=referencia,
                            drive_file_id=drive_file_id,
                            drive_link=drive_lnk or None,
                            drive_email_link=email_lnk or None,
                            sheet_name=sheet_name,
                        ))
                        files_ok += 1
                        fila_guardada = True
                        return True"""

if old_block not in c:
    print("Block not found (maybe whitespace differs)")
    exit(1)
c = c.replace(old_block, new_block)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Pipeline patched: insert into gmail_temporal on each item")
