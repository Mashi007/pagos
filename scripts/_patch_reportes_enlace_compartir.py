from pathlib import Path

def main() -> None:
    p = Path(__file__).resolve().parents[1] / "frontend" / "src" / "pages" / "Reportes.tsx"
    text = p.read_text(encoding="utf-8")

    old = """            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-11 gap-2"
                onClick={() =>
                  copiarEnlaceServicio(
                    PUBLIC_REPORTE_PAGO_PATH,
                    'Reporte de pagos'
                  )
                }
                title="Copiar enlace: Reporte de pagos"
                aria-label="Copiar enlace reporte de pagos"
              >
                <DollarSign className="h-5 w-5" />
                Reporte de pagos
              </Button>"""

    new = """            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-11 gap-2"
                onClick={() =>
                  copiarEnlaceServicio(
                    REPORTES_PAGE_PATH,
                    'Centro de Reportes'
                  )
                }
                title="Copiar enlace: Centro de Reportes (rapicredit.onrender.com/pagos/reportes)"
                aria-label="Copiar enlace Centro de Reportes"
              >
                <Copy className="h-5 w-5" />
                Centro de Reportes
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-11 gap-2"
                onClick={() =>
                  copiarEnlaceServicio(
                    PUBLIC_REPORTE_PAGO_PATH,
                    'Reporte de pagos'
                  )
                }
                title="Copiar enlace: Reporte de pagos"
                aria-label="Copiar enlace reporte de pagos"
              >
                <DollarSign className="h-5 w-5" />
                Reporte de pagos
              </Button>"""

    if old not in text:
        raise SystemExit("block not found")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("OK")


if __name__ == "__main__":
    main()
