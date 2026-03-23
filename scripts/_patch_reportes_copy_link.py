"""One-off patch: add copy-link icon to Reportes page header."""
from pathlib import Path

def main() -> None:
    p = Path(__file__).resolve().parents[1] / "frontend" / "src" / "pages" / "Reportes.tsx"
    text = p.read_text(encoding="utf-8")

    old1 = """  Search,
  Building2,
} from 'lucide-react'"""
    new1 = """  Search,
  Building2,
  Copy,
} from 'lucide-react'"""
    if old1 not in text:
        raise SystemExit("block1 not found")
    text = text.replace(old1, new1, 1)

    old2 = """const INFOPAGOS_PATH = 'infopagos'

function getLinkParaCompartir(path: string): string {"""
    new2 = """const INFOPAGOS_PATH = 'infopagos'

/** Ruta relativa de esta pagina (compartir URL del Centro de Reportes). */

const REPORTES_PAGE_PATH = 'reportes'

function getLinkParaCompartir(path: string): string {"""
    if old2 not in text:
        raise SystemExit("block2 not found")
    text = text.replace(old2, new2, 1)

    old3 = """      <header className="border-b border-gray-200 pb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
            <FileText className="h-7 w-7 text-blue-600" />
          </div>

          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
              Centro de Reportes
            </h1>

            <p className="mt-1 text-sm text-gray-500 sm:text-base">
              Descargue reportes en Excel, comparta enlaces y consulte el
              historial de notificaciones.
            </p>
          </div>
        </div>
      </header>"""
    new3 = """      <header className="border-b border-gray-200 pb-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-100">
              <FileText className="h-7 w-7 text-blue-600" />
            </div>

            <div className="min-w-0">
              <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
                Centro de Reportes
              </h1>

              <p className="mt-1 text-sm text-gray-500 sm:text-base">
                Descargue reportes en Excel, comparta enlaces y consulte el
                historial de notificaciones.
              </p>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-11 w-11 shrink-0"
            onClick={() =>
              copiarEnlaceServicio(REPORTES_PAGE_PATH, 'Centro de Reportes')
            }
            title="Copiar enlace de esta pagina"
            aria-label="Copiar enlace del Centro de Reportes"
          >
            <Copy className="h-5 w-5" aria-hidden />
          </Button>
        </div>
      </header>"""
    if old3 not in text:
        raise SystemExit("block3 not found")
    text = text.replace(old3, new3, 1)

    p.write_text(text, encoding="utf-8")
    print("OK:", p)


if __name__ == "__main__":
    main()
