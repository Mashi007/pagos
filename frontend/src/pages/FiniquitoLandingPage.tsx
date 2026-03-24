import { useEffect } from 'react'

import { useNavigate } from 'react-router-dom'

import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

/**
 * Entrada directa /pagos/finiquitos (sin pasar por el app).
 * Misma mecánica visual que rapicredit-estadocuenta: bienvenida + Iniciar → login OTP.
 * Los administradores usan el menú del sistema: Reportes → Finiquito (gestión).
 */
export function FiniquitoLandingPage() {
  const navigate = useNavigate()

  const LOGO_PUBLIC_SRC = `${(import.meta.env.BASE_URL || '/').replace(/\/?$/, '')}/logos/rapicredit-public.png`

  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY + '_path', 'finiquitos')
  }, [])

  return (
    <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-100 via-[#e0eaf2] to-[#c9d6e8] p-4 sm:p-6">
      <Card className="mx-1 w-full min-w-0 max-w-lg overflow-hidden rounded-2xl border border-slate-200/90 shadow-2xl shadow-slate-300/40 ring-1 ring-slate-200/50 sm:mx-0">
        <div className="border-b border-slate-100 bg-gradient-to-b from-white to-slate-50/80 px-6 py-6 text-center sm:px-8 sm:py-8">
          <div className="inline-flex flex-col items-center justify-center">
            <img
              src={LOGO_PUBLIC_SRC}
              alt="RapiCredit"
              className="mx-auto h-16 object-contain drop-shadow-sm sm:h-20"
            />

            <p className="mt-3 text-sm font-semibold tracking-wide text-[#b8954a] sm:text-base">
              Finiquito - colaboradores
            </p>
          </div>
        </div>

        <CardHeader className="px-4 pb-2 text-center sm:px-6">
          <CardTitle className="text-2xl font-bold tracking-tight text-[#1e3a5f] sm:text-3xl">
            Bienvenido
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4 px-4 pb-6 sm:space-y-5 sm:px-6">
          <p className="text-center text-sm text-slate-700 sm:text-base">
            Acceso exclusivo para el proceso de finiquito. Primera vez: registre
            su cédula y correo personal. En cada ingreso recibirá un código en
            su correo; solo con ese acceso verá los casos asignados.
          </p>

          <ul className="list-inside list-disc space-y-2 text-left text-sm text-slate-600">
            <li>
              Use el enlace directo a esta página (no es necesario entrar al
              sistema interno).
            </li>
            <li>Tras iniciar sesión solo verá la información de Finiquito.</li>
            <li>
              El personal administrador gestiona los casos desde el menú del
              sistema (Reportes → Finiquito gestión).
            </li>
          </ul>

          <p className="text-center text-xs text-slate-500">
            Si llegó aquí por error buscando el sistema interno, cierre esta
            pestaña e inicie sesión en el panel habitual.
          </p>

          <Button
            className="min-h-[52px] w-full touch-manipulation rounded-xl bg-[#1e3a5f] py-6 text-base font-semibold text-white shadow-lg shadow-[#1e3a5f]/25 transition-all duration-200 hover:bg-[#152a47] hover:shadow-xl active:scale-[0.98]"
            size="lg"
            onClick={() => navigate('/finiquitos/acceso')}
          >
            Iniciar
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
