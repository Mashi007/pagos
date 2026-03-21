from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"


def main() -> None:
    api = ROOT / "services/api.ts"
    at = api.read_text(encoding="utf-8")
    at2 = at.replace(
        "const API_BASE_URL = getEffectiveApiBaseUrl()",
        "export const API_BASE_URL = getEffectiveApiBaseUrl()",
        1,
    )
    if at2 == at:
        raise SystemExit("api.ts: pattern not found")
    api.write_text(at2, encoding="utf-8")
    print("api.ts: export API_BASE_URL")

    tc = ROOT / "services/tasaCambioService.ts"
    tct = tc.read_text(encoding="utf-8")
    tct2 = tct.replace(
        "import { API_BASE_URL } from './config'",
        "import { API_BASE_URL } from './api'",
        1,
    )
    if tct2 == tct:
        raise SystemExit("tasaCambioService: import not found")
    tc.write_text(tct2, encoding="utf-8")
    print("tasaCambioService: import from ./api")

    val_path = ROOT / "utils/pagoExcelValidation.ts"
    vt = val_path.read_text(encoding="utf-8")
    if "parsePrestamoIdFromNumeroCredito" not in vt:
        fn = """

export function parsePrestamoIdFromNumeroCredito(val: unknown): number | null {
  if (val == null) return null
  const s = String(val).trim()
  if (s === '' || s === 'none') return null
  if (/^\\d+$/.test(s)) {
    const n = parseInt(s, 10)
    return Number.isNaN(n) ? null : n
  }
  const parts = s.match(/\\d+/g)
  if (!parts?.length) return null
  const n = parseInt(parts[parts.length - 1], 10)
  return Number.isNaN(n) ? null : n
}
"""
        val_path.write_text(vt.rstrip() + fn + "\n", encoding="utf-8")
        print("pagoExcelValidation: added parsePrestamoIdFromNumeroCredito")
    else:
        print("pagoExcelValidation: parsePrestamoIdFromNumeroCredito already present")

    pl = ROOT / "components/pagos/PagosList.tsx"
    plt = pl.read_text(encoding="utf-8")
    if "const [isImportingCobros" not in plt:
        needle = (
            "  const [isDescargandoExcelCobrosErrores, setIsDescargandoExcelCobrosErrores] =\n"
            "    useState(false)"
        )
        if needle not in plt:
            raise SystemExit("PagosList: useState anchor not found")
        plt = plt.replace(
            needle,
            needle + "\n  const [isImportingCobros, setIsImportingCobros] = useState(false)",
            1,
        )
        pl.write_text(plt, encoding="utf-8")
        print("PagosList: added isImportingCobros state")
    else:
        print("PagosList: isImportingCobros already present")

    cp = ROOT / "pages/CobrosPagosReportadosPage.tsx"
    cpt = cp.read_text(encoding="utf-8")
    idx = cpt.find("const handleDescargarPagosTablaTemporalExcel")
    if idx < 0:
        raise SystemExit("Cobros: handler not found")
    start = cpt.rfind("} catch (e: any)", 0, idx)
    if start < 0:
        raise SystemExit("Cobros: catch not found")
    end = cpt.find("  return (", idx)
    if end < 0:
        raise SystemExit("Cobros: return not found")

    new_block = """} catch (e: any) {
      toast.error(
        e?.message ||
          'Se descargo el Excel, pero fallo el marcado de exportados. Recargue e intente de nuevo.'
      )
    }
  }

  const handleDescargarPagosTablaTemporalExcel = async () => {
    setDescargandoTabla(true)

    try {
      await descargarPagosAprobadosExcel()

      toast.success(
        'Excel descargado. Los pagos han sido eliminados de la tabla temporal.'
      )

      await load({ page: 1 })
    } catch (e: any) {
      toast.error(e?.message || 'Error al descargar el Excel.')
    } finally {
      setDescargandoTabla(false)
    }
  }

"""
    cpt2 = cpt[:start] + new_block + cpt[end:]
    cp.write_text(cpt2, encoding="utf-8")
    print("CobrosPagosReportadosPage: fixed handler scope")

    print("done")


if __name__ == "__main__":
    main()
