path = "test_pagos_gmail.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# test_find_most_recent_data_zero: use mock execute
old = """    db.add(
        PagosGmailSyncItem(
            sync_id=sync.id,
            sheet_name="2026-01-01",
            correo_origen="one@test.com",
            asunto="Test",
            fecha_pago="",
            cedula="",
            monto="",
            numero_referencia="",
        )
    )
    db.commit()

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS = 0
        _, _, items = _find_most_recent_data(db)
    assert len(items) == 1"""

new = """    one = PagosGmailSyncItem(sync_id=sync.id, sheet_name="2026-01-01", correo_origen="one@test.com", asunto="Test", fecha_pago="", cedula="", monto="", numero_referencia="")
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS = 0
        with patch.object(db, "execute") as mock_exec:
            mock_exec.return_value.scalars().all.return_value = [one]
            _, _, items = _find_most_recent_data(db)
    assert len(items) == 1"""
c = c.replace(old, new)

# test_download_excel_logs: patch _find_most_recent_data
old2 = """    db.add(
        PagosGmailSyncItem(
            sync_id=sync.id,
            sheet_name="2026-01-01",
            correo_origen="log@test.com",
            asunto="Test",
            fecha_pago="",
            cedula="",
            monto="",
            numero_referencia="",
        )
    )
    db.commit()

    resp = download_excel(fecha=None, db=db)"""

new2 = """    from datetime import datetime as dt
    item = PagosGmailSyncItem(sync_id=sync.id, sheet_name="2026-01-01", correo_origen="log@test.com", asunto="Test", fecha_pago="", cedula="", monto="", numero_referencia="", drive_link=None, drive_email_link=None)
    with patch("app.api.v1.endpoints.pagos_gmail._find_most_recent_data", return_value=("2026-01-01", dt(2026, 1, 1), [item])):
        resp = download_excel(fecha=None, db=db)"""
c = c.replace(old2, new2)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Patched")
