# -*- coding: utf-8 -*-
"""Quita la vista previa del PDF en Estado de cuenta público; solo mensaje y botón descarga."""
import pathlib

path = pathlib.Path(__file__).resolve().parent / "frontend" / "src" / "pages" / "EstadoCuentaPublicoPage.tsx"
text = path.read_text(encoding="utf-8")

old = """            {pdfDataUrl && !loadingPdf && (
              <div className="w-full min-w-0 border rounded-lg overflow-hidden bg-gray-100">
                <iframe
                  title="Estado de cuenta PDF"
                  src={pdfBlobUrl || pdfDataUrl || ''}
                  className="w-full min-h-[50vh] sm:min-h-[60vh] aspect-[3/4] max-h-[70vh] sm:max-h-[80vh] border-0"
                />
              </div>
            )}"""

new = """            {pdfDataUrl && !loadingPdf && (
              <p className="text-center text-lg sm:text-xl text-slate-700 font-medium py-6">
                Descarga tu estado de cuenta
              </p>
            )}"""

if old not in text:
    raise SystemExit("No se encontró el bloque a reemplazar.")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Listo: vista previa reemplazada por mensaje 'Descarga tu estado de cuenta'.")
