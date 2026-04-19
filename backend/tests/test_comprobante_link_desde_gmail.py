"""URLs de comprobante: no tratar rutas API como id de archivo Drive."""

from app.services.pagos.comprobante_link_desde_gmail import drive_raw_a_url


def test_drive_raw_a_url_api_path_no_drive_prefix() -> None:
    path = "/api/v1/pagos/comprobante-imagen/2b6a6eeaa1654a2e901a750493166402"
    assert drive_raw_a_url(path) == path


def test_drive_raw_a_url_drive_id_still_wrapped() -> None:
    fid = "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"
    assert drive_raw_a_url(fid) == f"https://drive.google.com/file/d/{fid}/view"


def test_drive_raw_a_url_https_unchanged() -> None:
    u = "https://drive.google.com/file/d/abc/view"
    assert drive_raw_a_url(u) == u
