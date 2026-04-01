import { useNavigate } from 'react-router-dom'

import { LoginForm } from '../components/auth/LoginForm'

import { Button } from '../components/ui/button'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

/**





 * Si el usuario llegó a login desde un flujo público (reporte de pago o estado de cuenta),





 * se muestra "Acceso limitado" y "Continuar" para volver al flujo público (evita que personas





 * mayores que tocaron un link pierdan el proceso).





 */

export function Login() {
  const navigate = useNavigate()

  const fromPublicFlow =
    typeof sessionStorage !== 'undefined' &&
    sessionStorage.getItem(PUBLIC_FLOW_SESSION_KEY) === '1'

  if (fromPublicFlow) {
    const returnPath =
      (typeof sessionStorage !== 'undefined' &&
        sessionStorage.getItem(PUBLIC_FLOW_SESSION_KEY + '_path')) ||
      '/rapicredit-cobros'

    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-900 p-6 text-white">
        <div className="w-full max-w-md space-y-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-red-500 md:text-5xl">
            Acceso limitado
          </h1>

          <p className="text-lg text-slate-300">
            Esta pantalla es para el personal del sistema. Si desea reportar un
            pago o consultar su estado de cuenta, use el botón Continuar para
            volver.
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
            className="mt-4 text-sm text-slate-500 underline hover:text-slate-300"
            onClick={() => {
              sessionStorage.removeItem(PUBLIC_FLOW_SESSION_KEY)
              sessionStorage.removeItem(PUBLIC_FLOW_SESSION_KEY + '_path')
              navigate('/login', { replace: true })
            }}
          >
            Soy personal del sistema — iniciar sesión
          </button>
        </div>
      </div>
    )
  }

  return <LoginForm />
}
