import { Link, useNavigate } from 'react-router-dom'

import { FileText, Wallet } from 'lucide-react'

import { Button } from '../components/ui/button'
import { Logo } from '../components/ui/Logo'

import { PUBLIC_STAFF_ENTRY_PATH } from '../config/env'

/**
 * Entrada pública en la raíz del basename (p. ej. /pagos).
 * Evita exponer el formulario de login de personal a quien solo quita el último segmento de la URL.
 * El personal usa la ruta dedicada /acceso-personal (redirige a login con ?personal=1).
 */
export function PublicBasenameIndexPage() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-[100dvh] flex-col bg-slate-950 text-slate-50">
      <header className="border-b border-slate-800 bg-slate-900/80 px-4 py-4">
        <div className="mx-auto flex max-w-3xl items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 p-1.5">
            <Logo size="sm" className="text-white" />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-400">
              RapiCredit
            </p>
            <p className="text-sm text-slate-400">Servicios para clientes</p>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-4 py-10">
        <h1 className="mb-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          ¿Qué desea hacer?
        </h1>
        <p className="mb-8 max-w-xl text-slate-400">
          Elija una opción. Estas consultas no requieren usuario del personal.
        </p>

        <ul className="grid gap-4 sm:grid-cols-2" role="list">
          <li>
            <Button
              type="button"
              variant="secondary"
              className="h-auto min-h-[52px] w-full flex-col items-start gap-2 border border-slate-700 bg-slate-900 py-4 text-left hover:bg-slate-800"
              onClick={() => navigate('/rapicredit-cobros')}
            >
              <span className="flex items-center gap-2 text-base font-semibold text-white">
                <FileText
                  className="h-5 w-5 shrink-0 text-emerald-400"
                  aria-hidden
                />
                Reportar un pago
              </span>
              <span className="text-xs font-normal text-slate-400">
                Envío de comprobante y datos del pago
              </span>
            </Button>
          </li>
          <li>
            <Button
              type="button"
              variant="secondary"
              className="h-auto min-h-[52px] w-full flex-col items-start gap-2 border border-slate-700 bg-slate-900 py-4 text-left hover:bg-slate-800"
              onClick={() => navigate('/rapicredit-estadocuenta')}
            >
              <span className="flex items-center gap-2 text-base font-semibold text-white">
                <Wallet
                  className="h-5 w-5 shrink-0 text-emerald-400"
                  aria-hidden
                />
                Estado de cuenta
              </span>
              <span className="text-xs font-normal text-slate-400">
                Consulta pública con su cédula
              </span>
            </Button>
          </li>
        </ul>
      </main>

      <footer className="border-t border-slate-800 px-4 py-6 text-center">
        <Link
          to={`/${PUBLIC_STAFF_ENTRY_PATH}`}
          className="text-xs text-slate-500 underline-offset-4 hover:text-slate-300 hover:underline"
        >
          Acceso personal del sistema
        </Link>
      </footer>
    </div>
  )
}
