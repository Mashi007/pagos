# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "src" / "components" / "pagos" / "PagosList.tsx"
t = p.read_text(encoding="utf-8")

old1 = """  const {
    loading: loadingGmail,
    gmailStatus,
    setGmailStatus,
    run: runGmail,
  } = useGmailPipeline({
    onStatusUpdate: s => setGmailStatus(s),
  })"""

new1 = """  const {
    loading: loadingGmail,
    gmailStatus,
    setGmailStatus,
    run: runGmail,
    stopPolling: stopGmailPolling,
  } = useGmailPipeline({
    onStatusUpdate: s => setGmailStatus(s),
  })"""

old2 = """  useEffect(() => {
    pagoService
      .getCedulasReportarBs()
      .then(r => setCedulasReportarBsTotal(r.total))
      .catch(() => setCedulasReportarBsTotal(0))
  }, [])

  const handleGenerarExcelDesdeGmail = () => {"""

new2 = """  useEffect(() => {
    pagoService
      .getCedulasReportarBs()
      .then(r => setCedulasReportarBsTotal(r.total))
      .catch(() => setCedulasReportarBsTotal(0))
  }, [])

  useEffect(() => {
    return () => {
      stopGmailPolling()
    }
  }, [stopGmailPolling])

  const handleDetenerSeguimientoGmail = () => {
    stopGmailPolling()
    toast.info(
      'Seguimiento en pantalla detenido. El servidor puede seguir procesando el pipeline en segundo plano.'
    )
  }

  const handleGenerarExcelDesdeGmail = () => {"""

marker = """                    </button>
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm hover:bg-blue-50 disabled:opacity-50"
                      onClick={async () => {
                        setAgregarPagoOpen(false)
                        setIsDescargandoGmailExcel(true)"""

insert = """                    </button>
                    {loadingGmail && (
                      <button
                        type="button"
                        className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm text-amber-800 hover:bg-amber-50"
                        onClick={handleDetenerSeguimientoGmail}
                      >
                        <X className="h-4 w-4 shrink-0" />
                        <span>Detener seguimiento (deja de consultar el estado)</span>
                      </button>
                    )}
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm hover:bg-blue-50 disabled:opacity-50"
                      onClick={async () => {
                        setAgregarPagoOpen(false)
                        setIsDescargandoGmailExcel(true)"""

if old1 not in t:
    raise SystemExit("block1 not found")
t = t.replace(old1, new1)

if old2 not in t:
    raise SystemExit("block2 not found")
t = t.replace(old2, new2)

if marker not in t:
    raise SystemExit("marker not found for button insert")
# Only replace first occurrence
t = t.replace(marker, insert, 1)

p.write_text(t, encoding="utf-8")
print("PagosList patched OK")
