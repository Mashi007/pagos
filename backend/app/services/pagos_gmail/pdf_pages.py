"""
PDF en pipeline Pagos Gmail: **solo se digitaliza (Gemini) si el PDF tiene exactamente 1 página**.
Si el PDF tiene **2 o más páginas**, no se envía a escaneo: se omite aquí y el pipeline etiqueta el hilo en Gmail como **MANUAL**.
Imágenes no-PDF no se parten por páginas. Requiere `pypdf` para contar páginas.
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
) -> Tuple[List[Tuple[str, bytes, str, str]], int]:
    """
    Para cada tupla (nombre, bytes, mime, origen): si es PDF con **una sola página**, deja un candidato.
    Si el PDF tiene **2+ páginas**, **no** añade candidatos (no escaneo Gemini); el pipeline aplica etiqueta Gmail **MANUAL**.
    Devuelve ``(lista_candidatos, pdf_multipagina_omitidos)``.
    """
    expanded: List[Tuple[str, bytes, str, str]] = []
    multipage_omitidos = 0
    for fname, content, mime, origen in items:
        m = (mime or "").lower()
        fn = (fname or "").lower()
        is_pdf = m == "application/pdf" or fn.endswith(".pdf")
        if not is_pdf:
            expanded.append((fname, content, mime, origen))
            continue
        pages = split_pdf_bytes_into_single_page_pdfs(content)
        if len(pages) > 1:
            multipage_omitidos += 1
            logger.info(
                "[PAGOS_GMAIL] PDF %s: %d paginas (>1) — sin escaneo automatico; se clasifica como MANUAL en Gmail",
                fname,
                len(pages),
            )
            continue
        expanded.append((fname, content, mime, origen))
    return expanded, multipage_omitidos
