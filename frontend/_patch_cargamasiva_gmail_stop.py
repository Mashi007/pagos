# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "src" / "components" / "pagos" / "CargaMasivaMenu.tsx"
t = p.read_text(encoding="utf-8")

t = t.replace(
    "import { Upload, FileSpreadsheet, ChevronDown, Mail } from 'lucide-react'",
    "import { Upload, FileSpreadsheet, ChevronDown, Mail, X } from 'lucide-react'",
)

old_hook = """  const {
    loading: loadingGmail,
    gmailStatus,
    setGmailStatus,
    run: runGmail,
  } = useGmailPipeline({"""

new_hook = """  const {
    loading: loadingGmail,
    gmailStatus,
    setGmailStatus,
    run: runGmail,
    stopPolling: stopGmailPolling,
  } = useGmailPipeline({"""

if old_hook not in t:
    raise SystemExit("hook block not found")
t = t.replace(old_hook, new_hook)

old_after = """  useEffect(() => {
    if (!isOpen) return

    pagoService
      .getGmailStatus()
      .then(setGmailStatus)
      .catch(() => setGmailStatus(null))
  }, [isOpen])

  async function handleGenerarExcelDesdeGmail() {"""

new_after = """  useEffect(() => {
    if (!isOpen) return

    pagoService
      .getGmailStatus()
      .then(setGmailStatus)
      .catch(() => setGmailStatus(null))
  }, [isOpen])

  useEffect(() => {
    return () => {
      stopGmailPolling()
    }
  }, [stopGmailPolling])

  function handleDetenerSeguimientoGmail() {
    stopGmailPolling()
    toast(
      'Seguimiento en pantalla detenido. El servidor puede seguir procesando el pipeline en segundo plano.',
      { duration: 5000 }
    )
  }

  async function handleGenerarExcelDesdeGmail() {"""

if old_after not in t:
    raise SystemExit("after isOpen effect not found")
t = t.replace(old_after, new_after)

old_btn = """            <button
              className="flex w-full items-center rounded-md px-3 py-2.5 text-sm transition-colors hover:bg-gray-100 disabled:opacity-50"
              onClick={handleGenerarExcelDesdeGmail}
              disabled={loadingGmail}
            >
              <Mail className="mr-2 h-4 w-4" />

              {loadingGmail ? 'Generando...' : 'Generar Excel desde Gmail'}
            </button>

            <p className="mt-1 border-t border-gray-100 px-2 py-1 text-xs text-gray-500">"""

new_btn = """            <button
              className="flex w-full items-center rounded-md px-3 py-2.5 text-sm transition-colors hover:bg-gray-100 disabled:opacity-50"
              onClick={handleGenerarExcelDesdeGmail}
              disabled={loadingGmail}
            >
              <Mail className="mr-2 h-4 w-4" />

              {loadingGmail ? 'Generando...' : 'Generar Excel desde Gmail'}
            </button>

            {loadingGmail && (
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-amber-800 transition-colors hover:bg-amber-50"
                onClick={handleDetenerSeguimientoGmail}
              >
                <X className="h-4 w-4 shrink-0" />
                Detener seguimiento (deja de consultar el estado)
              </button>
            )}

            <p className="mt-1 border-t border-gray-100 px-2 py-1 text-xs text-gray-500">"""

if old_btn not in t:
    raise SystemExit("button block not found")
t = t.replace(old_btn, new_btn)

p.write_text(t, encoding="utf-8")
print("CargaMasivaMenu patched OK")
