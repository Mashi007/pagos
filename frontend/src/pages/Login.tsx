import { useNavigate } from 'react-router-dom'
import { LoginForm } from '../components/auth/LoginForm'
import { Button } from '../components/ui/button'
import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

/**
 * Si el usuario llegó a login desde un flujo público (reporte de pago o estado de cuenta),
 * se muestra "Acceso prohibido" y "Continuar" para volver al flujo público (evita que personas
 * mayores que tocaron un link pierdan el proceso).
 */
export function Login() {
  const navigate = useNavigate()
  const fromPublicFlow = typeof sessionStorage !== 'undefined' && sessionStorage.getItem(PUBLIC_FLOW_SESSION_KEY) === '1'

  if (fromPublicFlow) {
    const returnPath = (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(PUBLIC_FLOW_SESSION_KEY + '_path')) || '/rapicredit-cobros'
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-900 text-white p-6">
        <div className="max-w-md w-full text-center space-y-8">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-red-500">
            Acceso prohibido
          </h1>
          <p className="text-lg text-slate-300">
            Esta pantalla es para el personal del sistema. Si desea reportar un pago o consultar su estado de cuenta, use el botón Continuar para volver.
          </p>
          <Button
            size="lg"
            className="w-full max-w-xs mx-auto text-lg py-6 font-semibold bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={() => {
              sessionStorage.removeItem(PUBLIC_FLOW_SESSION_KEY)
              sessionStorage.removeItem(PUBLIC_FLOW_SESSION_KEY + '_path')
              navigate(returnPath.startsWith('/') ? returnPath : `/${returnPath}`, { replace: true })
            }}
          >
            Continuar
          </Button>
        </div>
      </div>
    )
  }

  return <LoginForm />
}
