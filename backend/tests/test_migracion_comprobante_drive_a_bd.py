"""Extracción de file id de enlaces Drive (sin red ni BD)."""
from app.services.pagos.migracion_comprobante_drive_a_bd import (
    enlace_requiere_migracion_drive_a_bd,
    extraer_google_drive_file_id,
)


def test_extraer_file_id_file_d():
    fid = "1AbCdEfGhIjKlMnOpQrStUvWxYz123456"
    u = f"https://drive.google.com/file/d/{fid}/view?usp=sharing"
    assert extraer_google_drive_file_id(u) == fid


def test_extraer_file_id_open():
    fid = "1AbCdEfGhIjKlMnOpQrStUvWxYz123456"
    u = f"https://drive.google.com/open?id={fid}&authuser=0"
    assert extraer_google_drive_file_id(u) == fid


def test_extraer_file_id_solo_id():
    fid = "1AbCdEfGhIjKlMnOpQrStUvWxYz123456"
    assert extraer_google_drive_file_id(fid) == fid


def test_extraer_none_comprobante_interno():
    u = "https://api.ejemplo.com/api/v1/pagos/comprobante-imagen/abcdabcdabcdabcdabcdabcdabcd12"
    assert extraer_google_drive_file_id(u) is None


def test_enlace_requiere_migracion():
    assert enlace_requiere_migracion_drive_a_bd("https://drive.google.com/file/d/abc123/view") is True
    assert enlace_requiere_migracion_drive_a_bd("/api/v1/pagos/comprobante-imagen/" + "a" * 32) is False
    assert enlace_requiere_migracion_drive_a_bd("") is False
