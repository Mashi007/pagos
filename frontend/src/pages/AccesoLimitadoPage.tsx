import { AlertCircle, Lock, Key } from 'lucide-react'
import { Button } from '../components/ui/button'

export default function AccesoLimitadoPage() {
  const handleLogin = () => {
    window.location.href = '/pagos/login'
  }

  const handleVolverAInfopagos = () => {
    window.location.href = '/pagos/infopagos'
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-white p-8 shadow-2xl">
        <div className="mb-6 flex justify-center">
          <div className="rounded-full bg-red-100 p-4">
            <AlertCircle className="h-8 w-8 text-red-600" />
          </div>
        </div>

        <h1 className="mb-3 text-center text-2xl font-bold text-slate-900">
          Acceso Limitado
        </h1>

        <p className="mb-6 text-center text-slate-600">
          No tienes permiso para acceder a esta sección. Si deseas continuar,
          debes iniciar sesión con tus credenciales.
        </p>

        <div className="mb-8 rounded-lg bg-blue-50 p-4">
          <div className="flex items-start gap-3">
            <Lock className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" />
            <p className="text-sm text-blue-700">
              Esta área está protegida. Solo usuarios autenticados pueden
              acceder.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <Button
            onClick={handleLogin}
            className="w-full bg-blue-600 hover:bg-blue-700"
          >
            <Key className="mr-2 h-4 w-4" />
            Iniciar Sesión
          </Button>

          <Button
            onClick={handleVolverAInfopagos}
            variant="outline"
            className="w-full"
          >
            Volver a Infopagos
          </Button>
        </div>

        <p className="mt-6 text-center text-xs text-slate-500">
          © RapiCredit. Todos los derechos reservados.
        </p>
      </div>
    </div>
  )
}
