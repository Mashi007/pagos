import { useNavigate } from 'react-router-dom'

import { FileText, Shield } from 'lucide-react'

import { useSimpleAuth } from '../store/simpleAuthStore'

import { Button } from '../components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'

/**
 * Entrada /finiquitos: dos modalidades de acceso (encargado OTP vs administrador panel).
 */
export function FiniquitoLandingPage() {
  const navigate = useNavigate()

  const { isAuthenticated, user } = useSimpleAuth()

  const esAdmin = (user?.rol || 'operativo') === 'administrador'

  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 p-4 sm:p-6">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-[#1e3a5f] sm:text-3xl">
          Finiquito
        </h1>
        <p className="mt-2 max-w-lg text-sm text-slate-600 sm:text-base">
          Elija cómo desea ingresar: acceso para encargados del proceso (cédula y
          correo con código) o acceso de administrador del sistema.
        </p>
      </div>

      <div className="grid w-full max-w-3xl gap-6 sm:grid-cols-2">
        <Card className="border-slate-200 shadow-lg">
          <CardHeader>
            <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-[#1e3a5f]/10">
              <FileText className="h-7 w-7 text-[#1e3a5f]" aria-hidden />
            </div>
            <CardTitle className="text-lg text-[#1e3a5f]">
              Encargado Finiquito
            </CardTitle>
            <CardDescription>
              Primera vez: registre cédula y correo personal. En cada ingreso
              recibirá un código en su correo para acceder solo a esta sección.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              className="w-full bg-[#1e3a5f] hover:bg-[#152a47]"
              size="lg"
              onClick={() => navigate('/finiquitos/acceso')}
            >
              Ingresar con cédula y correo
            </Button>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-lg">
          <CardHeader>
            <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-amber-100">
              <Shield className="h-7 w-7 text-amber-800" aria-hidden />
            </div>
            <CardTitle className="text-lg text-[#1e3a5f]">
              Administrador
            </CardTitle>
            <CardDescription>
              Use el mismo usuario y contraseña del sistema RapiCredit para
              revisar bandejas (incluidos casos rechazados) y cambiar estados.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isAuthenticated && esAdmin ? (
              <Button
                variant="outline"
                className="w-full border-2 border-[#1e3a5f] text-[#1e3a5f] hover:bg-slate-50"
                size="lg"
                onClick={() => navigate('/finiquitos/gestion')}
              >
                Ir a administración Finiquito
              </Button>
            ) : (
              <Button
                variant="outline"
                className="w-full border-2 border-[#1e3a5f] text-[#1e3a5f] hover:bg-slate-50"
                size="lg"
                onClick={() =>
                  navigate('/login', {
                    state: { from: { pathname: '/finiquitos/gestion' } },
                  })
                }
              >
                Ir al login del sistema
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
