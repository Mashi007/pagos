import { useEffect } from 'react'

import { useNavigate, useSearchParams } from 'react-router-dom'

import { LoginForm } from '../components/auth/LoginForm'

import { Button } from '../components/ui/button'

import { PUBLIC_FLOW_SESSION_KEY, STAFF_LOGIN_SEARCH } from '../config/env'

/**





 * Si el usuario llegó a login desde un flujo público (reporte de pago o estado de cuenta),





 * se muestra "Acceso limitado" y "Continuar" para volver al flujo público (evita que personas





 * mayores que tocaron un link pierdan el proceso).





 */

export function Login() {
  const navigate = useNavigate()

  const [searchParams] = useSearchParams()

  const staffIntent =
    searchParams.get('personal') === '1' || searchParams.get('staff') === '1'

  useEffect(() => {
    if (!staffIntent) return
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.removeItem(PUBLIC_FLOW_SESSION_KEY)
      sessionStorage.removeItem(PUBLIC_FLOW_SESSION_KEY + '_path')
    }
    navigate('/login', { replace: true })
  }, [staffIntent, navigate])

  if (!staffIntent) {
    const returnPath =
      (typeof sessionStorage !== 'undefined' &&
        sessionStorage.getItem(PUBLIC_FLOW_SESSION_KEY + '_path')) ||
      '/rapicredit-cobros'

    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-900 p-6 text-white">
        <div className="w-full max-w-md space-y-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-red-500 md:text-5xl">
            Acceso no autorizado
          </h1>

          <p className="text-lg text-slate-300">
            Esta pantalla es exclusiva para personal autorizado. Para reportar
            pagos o consultar estado de cuenta, use el botón Continuar.
          </p>

          <Button
            size="lg"
            className="mx-auto w-full max-w-xs bg-emerald-600 py-6 text-lg font-semibold text-white hover:bg-emerald-700"
            onClick={() => {
              sessionStorage.removeItem(PUBLIC_FLOW_SESSION_KEY)

              sessionStorage.removeItem(PUBLIC_FLOW_SESSION_KEY + '_path')

              navigate(
                returnPath.startsWith('/') ? returnPath : `/${returnPath}`,
                { replace: true }
              )
            }}
          >
            Continuar
          </Button>

          <button
            type="button"
            className="mt-4 text-sm text-slate-500 underline hover:text-slate-300"
            onClick={() => {
              navigate(`/login${STAFF_LOGIN_SEARCH}`, { replace: true })
            }}
          >
            Soy personal del sistema - iniciar sesión
          </button>
        </div>
      </div>
    )
  }

  return <LoginForm />
}
