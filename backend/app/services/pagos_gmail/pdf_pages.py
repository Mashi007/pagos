"""
Divide PDFs en una entrada por página para el pipeline Pagos Gmail (un pago = una página).
Requiere `pypdf` en el entorno de ejecución.
"""
from __future__ import annotations

import logging
from io import BytesIO
from typing import List, Tuple

logger = logging.getLogger(__name__)


def split_pdf_bytes_into_single_page_pdfs(pdf_bytes: bytes) -> List[bytes]:
    """
    Devuelve una lista de PDFs de una sola página (mismo orden que el documento).
    Si falla la librería o el PDF es inválido, devuelve [pdf_bytes] (una sola pasada a Gemini).
    """
    if not pdf_bytes or len(pdf_bytes) < 8:
        return []
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        logger.warning(
            "[PAGOS_GMAIL] pypdf no instalado (%s); PDF multi-página se trata como un solo binario",
            exc,
        )
        return [pdf_bytes]
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        n = len(reader.pages)
        if n <= 0:
            return [pdf_bytes]
        out: List[bytes] = []
        for i in range(n):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            buf = BytesIO()
            writer.write(buf)
            out.append(buf.getvalue())
        return out if out else [pdf_bytes]
    except Exception as exc:
        logger.warning(
            "[PAGOS_GMAIL] No se pudo dividir PDF en páginas (%s); se usa el archivo completo",
            exc,
        )
        return [pdf_bytes]


def expand_pipeline_pdf_tuples(
    items: List[Tuple[str, bytes, str, str]],
) -> List[Tuple[str, bytes, str, str]]:
    """
    Para cada tupla (nombre, bytes, mime, origen): si es PDF, reemplaza por N tuplas (una por página).
    Los nombres pasan a ser `stem_pag1.pdf`, `stem_pag2.pdf`, ...
    """
    expanded: List[Tuple[str, bytes, str, str]] = []
    for fname, content, mime, origen in items:
        m = (mime or "").lower()
        fn = (fname or "").lower()
        is_pdf = m == "application/pdf" or fn.endswith(".pdf")
        if not is_pdf:
            expanded.append((fname, content, mime, origen))
            continue
        pages = split_pdf_bytes_into_single_page_pdfs(content)
        if len(pages) <= 1:
            expanded.append((fname, content, mime, origen))
            continue
        base = fname.rsplit(".", 1)[0] if "." in fname else fname
        ext = fname.rsplit(".", 1)[-1] if "." in fname else "pdf"
        for idx, pb in enumerate(pages, start=1):
            expanded.append((f"{base}_pag{idx}.{ext}", pb, "application/pdf", origen))
        logger.info(
            "[PAGOS_GMAIL] PDF %s dividido en %d página(s) (una fila por página)",
            fname,
            len(pages),
        )
    return expanded
