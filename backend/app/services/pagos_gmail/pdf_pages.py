"""
PDF en pipeline Pagos Gmail: cada **página** de un PDF puede ser un candidato a Gemini
(misma regla que imágenes: **un binario = una petición = una fila**).
Los PDF de varias páginas se parten con `pypdf` en PDFs de una sola página; si falla el
análisis, se reintenta con el archivo completo como un solo candidato.
Imágenes no-PDF no se parten por páginas. Requiere `pypdf` para contar y extraer páginas.
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


def _pdf_page_filename(fname: str, page_idx: int) -> str:
    """Nombre estable por página para logs / trazas (p. ej. recibo.pdf -> recibo_pag2.pdf)."""
    raw = (fname or "").strip() or "adjunto.pdf"
    lower = raw.lower()
    if lower.endswith(".pdf"):
        stem = raw[:-4]
        return f"{stem}_pag{page_idx}.pdf"
    return f"{raw}_pag{page_idx}.pdf"


def expand_pipeline_pdf_tuples(
    items: List[Tuple[str, bytes, str, str]],
) -> Tuple[List[Tuple[str, bytes, str, str]], int]:
    """
    Para cada tupla (nombre, bytes, mime, origen): si es PDF, lo divide en páginas y añade
    **un candidato por página** (cada uno es un PDF de 1 pág. listo para Gemini).
    Si es imagen u otro mime, pasa sin cambios.
    Devuelve ``(lista_candidatos, n_adjuntos_pdf_multipagina)`` — el entero es cuántos
    archivos PDF de **entrada** tenían 2+ páginas (métrica / logs; 0 si ninguno).
    """
    expanded: List[Tuple[str, bytes, str, str]] = []
    n_multipage_sources = 0
    for fname, content, mime, origen in items:
        m = (mime or "").lower()
        fn = (fname or "").lower()
        is_pdf = m == "application/pdf" or fn.endswith(".pdf")
        if not is_pdf:
            expanded.append((fname, content, mime, origen))
            continue
        pages = split_pdf_bytes_into_single_page_pdfs(content)
        if not pages:
            logger.warning(
                "[PAGOS_GMAIL] PDF %s: sin paginas extraibles — se usa binario original",
                fname,
            )
            expanded.append((fname, content, mime, origen))
            continue
        if len(pages) > 1:
            n_multipage_sources += 1
            logger.info(
                "[PAGOS_GMAIL] PDF %s: %d paginas — %d candidatos Gemini (una peticion por pagina)",
                fname,
                len(pages),
                len(pages),
            )
            for i, page_bytes in enumerate(pages, start=1):
                expanded.append(
                    (_pdf_page_filename(fname, i), page_bytes, "application/pdf", origen)
                )
            continue
        expanded.append((fname, content, mime, origen))
    return expanded, n_multipage_sources
