import { useEffect } from 'react'

import { Link, Navigate, useNavigate } from 'react-router-dom'

import { CheckCircle2, Loader2, Search, XCircle } from 'lucide-react'

import { Button } from '../components/ui/button'

import { FiniquitoWorkspaceShell } from '../components/finiquito/FiniquitoWorkspaceShell'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

import { BASE_PATH } from '../config/env'

import { useSimpleAuth } from '../store/simpleAuthStore'

import { cn } from '../utils'

/**
 * /finiquitos: mismo espacio visual que /finiquitos/gestion.
 * Administrador ya autenticado en el panel → redireccion a gestion con Layout.
 * Colaboradores y sesiones sin admin → bienvenida en el mismo marco de trabajo.
 */
export function FiniquitoRootPage() {
  const navigate = useNavigate()

  const { isAuthenticated, user, isLoading } = useSimpleAuth()

  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')

    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY + '_path', 'finiquitos')
  }, [])

  if (isLoading) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-slate-100/80">
        <Loader2
          className="h-10 w-10 animate-spin text-slate-500"
          aria-label="Cargando"
        />
      </div>
    )
  }

  if (isAuthenticated && user && (user.rol || 'viewer') === 'admin') {
    return <Navigate to="/finiquitos/gestion" replace />
  }

  const loginHref = `${(BASE_PATH || '').replace(/\/$/, '') || ''}/login`

  return (
    <FiniquitoWorkspaceShell
      description={
        <p>
          Mismo entorno de trabajo que la gestión interna. Colaboradores:
          registro y acceso con código al correo personal. Administradores del
          sistema: inicie sesión en el panel; si ya está autenticado, será
          enviado a la bandeja de gestión.
        </p>
      }
    >
      <section
        className={cn(
          'overflow-hidden rounded-2xl border border-emerald-200/90 bg-white shadow-md',
          'ring-1 ring-emerald-100/80'
        )}
        aria-labelledby="finiquito-publico-area-trabajo"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-200/80 bg-gradient-to-r from-emerald-800 to-emerald-600 px-4 py-3.5 text-white sm:px-5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 shadow-inner">
              <CheckCircle2 className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <h2
                id="finiquito-publico-area-trabajo"
                className="text-sm font-bold tracking-tight sm:text-base"
              >
                Área de trabajo
              </h2>
              <p className="text-xs text-emerald-100">
                Portal colaboradores · acceso por cédula y código en correo
              </p>
            </div>
          </div>
        </div>
        <div className="space-y-4 bg-gradient-to-b from-emerald-50/50 to-white p-4 sm:p-6">
          <p className="text-center text-sm text-slate-700 sm:text-left sm:text-base">
            Acceso exclusivo para el proceso de finiquito. Primera vez: registre
            su cédula y correo personal. En cada ingreso recibirá un código en
            su correo; solo con ese acceso verá los casos asignados.
          </p>
          <ul className="list-inside list-disc space-y-2 text-sm text-slate-600">
            <li>
              Use este enlace directo (no es necesario entrar al sistema
              interno).
            </li>
            <li>Tras iniciar sesión solo verá la información de Finiquito.</li>
            <li>
              El correo del código usa el mismo flujo que Estado de cuenta;
              revise spam.
            </li>
          </ul>
          <p className="text-center text-xs text-slate-500 sm:text-left">
            Si llegó por error buscando el sistema interno, cierre esta pestaña
            e inicie sesión en el panel habitual.
          </p>
          <Button
            className="min-h-[48px] w-full touch-manipulation rounded-xl bg-[#1e3a5f] py-6 text-base font-semibold text-white shadow-lg shadow-[#1e3a5f]/25 hover:bg-[#152a47] sm:w-auto sm:px-10"
            size="lg"
            onClick={() => navigate('/finiquitos/acceso')}
          >
            Iniciar acceso colaborador
          </Button>
        </div>
      </section>

      <section
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-md"
        aria-labelledby="finiquito-publico-bandeja"
      >
        <div className="border-b border-slate-200 bg-slate-50/90 px-4 py-4 sm:px-5">
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm">
              <Search className="h-5 w-5 text-slate-600" aria-hidden />
            </span>
            <div>
              <h2
                id="finiquito-publico-bandeja"
                className="text-base font-bold text-[#1e3a5f]"
              >
                Bandeja principal
              </h2>
              <p className="text-xs text-slate-600 sm:text-sm">
                Tras verificar el código verá sus casos en revisión y podrá
                aceptar o rechazar desde el mismo diseño de tablas que usa
                gestión.
              </p>
            </div>
          </div>
        </div>
        <div className="p-4 sm:p-5">
          <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-8 text-center text-sm leading-relaxed text-slate-600">
            Pulse <strong>Iniciar acceso colaborador</strong> para registrar la
            pareja cédula + correo o solicitar el código de un acceso ya
            registrado.
          </p>
        </div>
      </section>

      <section
        className={cn(
          'overflow-hidden rounded-2xl border-2 border-dashed border-amber-400/85',
          'bg-amber-50/40 shadow-inner'
        )}
        aria-labelledby="finiquito-publico-admin"
      >
        <div className="border-b border-amber-200/90 bg-amber-100/95 px-4 py-3.5 sm:px-5">
          <div className="flex flex-wrap items-center gap-3 text-amber-950">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-300/90 bg-amber-50 shadow-sm">
              <XCircle className="h-5 w-5 text-amber-800" aria-hidden />
            </span>
            <div>
              <h2
                id="finiquito-publico-admin"
                className="text-sm font-bold tracking-tight sm:text-base"
              >
                Administradores
              </h2>
              <p className="text-xs text-amber-900/85">
                Gestión de casos, refresco materializado y bandejas completas
              </p>
            </div>
          </div>
        </div>
        <div className="space-y-3 p-4 sm:p-5">
          <p className="text-sm text-amber-950/90">
            Si gestiona finiquitos desde el sistema, inicie sesión y abra{' '}
            <strong className="font-semibold">
              Reportes → Finiquito (gestión)
            </strong>{' '}
            o vaya directamente a{' '}
            <Link
              to="/finiquitos/gestion"
              className="font-semibold text-[#1e3a5f] underline underline-offset-2 hover:text-[#152a47]"
            >
              /finiquitos/gestion
            </Link>{' '}
            (requiere rol administrador).
          </p>
          <Button
            variant="outline"
            size="sm"
            asChild
            className="border-amber-300"
          >
            <a href={loginHref}>Ir al inicio de sesión del panel</a>
          </Button>
        </div>
      </section>
    </FiniquitoWorkspaceShell>
  )
}
