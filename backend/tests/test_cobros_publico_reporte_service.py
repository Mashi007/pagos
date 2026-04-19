"""Tests unitarios para `cobros_publico_reporte_service` (validación de formulario y comprobante)."""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.cobros import cobros_publico_reporte_service as cpr


def _bytes_jpeg_minimo() -> bytes:
    return bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46])


def _bytes_png_minimo() -> bytes:
    return bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D])


def _bytes_pdf_minimo() -> bytes:
    return b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n"


def _bytes_webp_minimo() -> bytes:
    # RIFF....WEBP (12+ bytes; validate_file_magic pide WEBP en offset 8)
    return b"RIFF" + (4).to_bytes(4, "little") + b"WEBP" + b"\x00" * 20


class TestNormalizarYValidarCamposFormulario:
    def test_usdt_normaliza_a_usd(self):
        err, mon = cpr.normalizar_y_validar_campos_formulario(
            tipo_cedula="V",
            numero_cedula="12345678",
            institucion_financiera="Banco",
            numero_operacion="123",
            monto=10.0,
            moneda="USDT",
            observacion=None,
        )
        assert err is None
        assert mon.moneda_upper == "USDT"
        assert mon.moneda_guardar == "USD"

    def test_bs_se_conserva(self):
        err, mon = cpr.normalizar_y_validar_campos_formulario(
            tipo_cedula="V",
            numero_cedula="12345678",
            institucion_financiera="X",
            numero_operacion="Y",
            monto=100.0,
            moneda="bs",
            observacion="  ok  ",
        )
        assert err is None
        assert mon.moneda_upper == "BS"
        assert mon.moneda_guardar == "BS"
        assert mon.observacion == "  ok  "

    def test_moneda_invalida(self):
        err, _mon = cpr.normalizar_y_validar_campos_formulario(
            tipo_cedula="V",
            numero_cedula="1",
            institucion_financiera="B",
            numero_operacion="N",
            monto=1.0,
            moneda="EUR",
            observacion=None,
        )
        assert err == "Moneda no válida."

    def test_tipo_cedula_demasiado_largo(self):
        err, _mon = cpr.normalizar_y_validar_campos_formulario(
            tipo_cedula="VEC",
            numero_cedula="1",
            institucion_financiera="B",
            numero_operacion="N",
            monto=1.0,
            moneda="BS",
            observacion=None,
        )
        assert err == "Datos inválidos."

    def test_observacion_se_trunca_a_300(self):
        obs = "x" * 400
        err, mon = cpr.normalizar_y_validar_campos_formulario(
            tipo_cedula="V",
            numero_cedula="12345678",
            institucion_financiera="Banco",
            numero_operacion="1",
            monto=1.0,
            moneda="BS",
            observacion=obs,
        )
        assert err is None
        assert mon.observacion is not None
        assert len(mon.observacion) == 300


class TestValidarAdjuntoComprobanteBytes:
    def test_pdf_valido(self):
        body = _bytes_pdf_minimo()
        err, name = cpr.validar_adjunto_comprobante_bytes(
            body, "application/pdf", "doc.pdf", mensaje_excel_largo=True
        )
        assert err is None
        assert name == "doc.pdf"

    def test_jpeg_valido(self):
        body = _bytes_jpeg_minimo()
        err, name = cpr.validar_adjunto_comprobante_bytes(
            body, "image/jpeg", "foto.jpg", mensaje_excel_largo=False
        )
        assert err is None
        assert name == "foto.jpg"

    def test_octet_stream_se_infiera_desde_extension(self):
        body = _bytes_jpeg_minimo()
        err, name = cpr.validar_adjunto_comprobante_bytes(
            body, "application/octet-stream", "comprobante.jpeg", mensaje_excel_largo=True
        )
        assert err is None
        assert "jpeg" in name or name == "comprobante.jpeg"

    def test_contenido_muy_corto(self):
        err, _name = cpr.validar_adjunto_comprobante_bytes(
            b"abc", "image/jpeg", "x.jpg", mensaje_excel_largo=True
        )
        assert err == "El archivo está vacío o no es válido."

    def test_magic_no_coincide_con_declarado(self):
        body = _bytes_pdf_minimo()
        err, _name = cpr.validar_adjunto_comprobante_bytes(
            body, "image/jpeg", "x.jpg", mensaje_excel_largo=True
        )
        assert err == "El archivo no corresponde a una imagen o PDF válido."

    def test_excel_mensaje_largo_vs_corto(self):
        body = _bytes_pdf_minimo()
        mime = "application/vnd.ms-excel"
        err_l, _ = cpr.validar_adjunto_comprobante_bytes(
            body, mime, "x.xls", mensaje_excel_largo=True
        )
        err_c, _ = cpr.validar_adjunto_comprobante_bytes(
            body, mime, "x.xls", mensaje_excel_largo=False
        )
        assert "Excel" in (err_l or "")
        assert err_c is not None
        assert "Excel" not in (err_c or "")

    def test_mime_no_permitido(self):
        body = _bytes_pdf_minimo()
        err, _name = cpr.validar_adjunto_comprobante_bytes(
            body, "image/gif", "anim.gif", mensaje_excel_largo=True
        )
        assert err is not None
        assert "Solo se permiten" in err

    def test_supera_tamano_maximo(self):
        max_b = cpr.MAX_FILE_SIZE
        body = b"x" * (max_b + 1)
        err, name = cpr.validar_adjunto_comprobante_bytes(
            body, "application/pdf", "big.pdf", mensaje_excel_largo=True
        )
        assert err == "El comprobante no puede superar 10 MB."
        assert name == "big.pdf"


class TestMimeEfectivoYSanitize:
    def test_mime_efectivo_normaliza_jpg(self):
        assert cpr.mime_efectivo_comprobante_web("image/jpg", "x") == "image/jpeg"

    def test_inferir_desde_extension_heic(self):
        assert cpr.inferir_mime_comprobante_desde_extension("IMG.HEIC") == "image/heic"

    def test_sanitize_filename_quita_ruta(self):
        assert cpr.sanitize_filename("../../etc/passwd") == "passwd"


def test_webp_valido():
    body = _bytes_webp_minimo()
    err, name = cpr.validar_adjunto_comprobante_bytes(
        body, "image/webp", "c.webp", mensaje_excel_largo=False
    )
    assert err is None
    assert name == "c.webp"


class TestValidarMontoReportePublico:
    def test_bs_fuera_de_rango(self):
        msg = cpr.validar_monto_reporte_publico(0.5, "BS")
        assert msg is not None
        assert "bolivares" in msg.lower()

    def test_usd_positivo_ok(self):
        assert cpr.validar_monto_reporte_publico(100.0, "USD") is None


class TestReferenciaDisplay:
    def test_anade_almohadilla(self):
        assert cpr.referencia_display("RPC-20260101-00001") == "#RPC-20260101-00001"

    def test_vacio_es_guion(self):
        assert cpr.referencia_display("  ") == "-"
