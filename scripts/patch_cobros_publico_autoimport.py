# python scripts/patch_cobros_publico_autoimport.py
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "backend/app/api/v1/endpoints/cobros_publico.py"
t = P.read_text(encoding="utf-8")

HELPER = '''

def _intentar_importar_reportado_automatico(
    db: Session,
    pr: PagoReportado,
    referencia: str,
    log_tag: str,
) -> None:
    """
    Si el reporte quedó en estado aprobado: crea Pago (mismas reglas que importar-desde-cobros),
    aplica a cuotas y marca el reporte como importado. Fallos solo en log (no rompe la respuesta al cliente).
    """
    if pr is None or getattr(pr, "estado", None) != "aprobado":
        return
    try:
        from app.models.pago import Pago
        from app.core.documento import normalize_documento
        from app.api.v1.endpoints.pagos import importar_un_pago_reportado_a_pagos, _aplicar_pago_a_cuotas_interno

        db.refresh(pr)
        doc_raw = (pr.referencia_interna or "").strip()[:100]
        doc_norm = normalize_documento(doc_raw)
        docs_bd: set[str] = set()
        if doc_norm:
            row = db.execute(select(Pago.numero_documento).where(Pago.numero_documento == doc_norm)).scalars().first()
            if row:
                docs_bd.add(str(row))
        usuario = "infopagos@rapicredit" if log_tag == "INFOPAGOS" else "cobros-publico@rapicredit"
        res = importar_un_pago_reportado_a_pagos(
            db,
            pr,
            usuario_email=usuario,
            documentos_ya_en_bd=docs_bd,
            docs_en_lote=set(),
            registrar_error_en_tabla=False,
        )
        if not res.get("ok"):
            logger.warning("[%s] Auto-import ref=%s omitido: %s", log_tag, referencia, res.get("error"))
            return
        pago = res["pago"]
        cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)
        if cc > 0 or cp > 0:
            pago.estado = "PAGADO"
        pr.estado = "importado"
        db.commit()
        logger.info("[%s] Auto-import OK ref=%s pago_id=%s", log_tag, referencia, getattr(pago, "id", None))
    except Exception as e:
        logger.warning("[%s] Auto-import fallo ref=%s: %s", log_tag, referencia, e)
        try:
            db.rollback()
        except Exception:
            pass


'''

if "def _intentar_importar_reportado_automatico(" not in t:
    needle = "logger = logging.getLogger(__name__)\n\nrouter = APIRouter"
    if needle not in t:
        raise SystemExit("logger/router needle not found")
    t = t.replace(needle, "logger = logging.getLogger(__name__)" + HELPER + "\nrouter = APIRouter", 1)

old1 = """        db.commit()

        return EnviarReporteResponse(
            ok=True,
            referencia_interna=referencia,
            mensaje="Tu reporte de pago fue recibido exitosamente.",
        )"""
new1 = """        db.commit()
        _intentar_importar_reportado_automatico(db, pr, referencia, "COBROS_PUBLIC")

        return EnviarReporteResponse(
            ok=True,
            referencia_interna=referencia,
            mensaje="Tu reporte de pago fue recibido exitosamente.",
        )"""
if old1 not in t:
    raise SystemExit("enviar_reporte return block not found")
t = t.replace(old1, new1, 1)

old2 = """        recibo_token = create_recibo_infopagos_token(pr.id, expire_hours=2)
        db.commit()
        return EnviarReporteInfopagosResponse(
            ok=True,
            referencia_interna=referencia,
            mensaje="Pago registrado. Se enviA3 el recibo al correo del deudor. Puede descargar el recibo aquA-.",
            recibo_descarga_token=recibo_token,
            pago_id=pr.id,
        )"""

# Message may vary encoding - search flexibly
idx = t.find("recibo_token = create_recibo_infopagos_token(pr.id, expire_hours=2)")
if idx < 0:
    raise SystemExit("infopagos recibo_token not found")
idx2 = t.find("return EnviarReporteInfopagosResponse(", idx)
if idx2 < 0:
    raise SystemExit("infopagos return not found")
# find db.commit before return
sub = t[idx:idx2]
if "db.commit()" not in sub:
    raise SystemExit("db.commit before infopagos return not found")
sub_new = sub.replace(
    "        db.commit()\n",
    "        db.commit()\n        _intentar_importar_reportado_automatico(db, pr, referencia, \"INFOPAGOS\")\n",
    1,
)
t = t[:idx] + sub_new + t[idx2:]

P.write_text(t, encoding="utf-8")
print("patched cobros_publico.py")
