import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'
import { useAuth } from '@/store/authStore'

export function TemporaryLogin() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const { setUser, setTokens } = useAuth()

  const handleTemporaryLogin = async (role: string) => {
    setIsLoading(true)
    setError(null)

    try {
      // Simular datos de usuario temporal
      const tempUser = {
        id: '1',
        email: `${role}@sistema.com`,
        nombre: role === 'admin' ? 'Administrador' : role === 'gerente' ? 'Gerente' : 'Asesor',
        apellido: 'Sistema',
        rol: role.toUpperCase(),
        activo: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      const tempTokens = {
        access_token: 'temp_access_token_' + Date.now(),
        refresh_token: 'temp_refresh_token_' + Date.now(),
        token_type: 'bearer',
        expires_in: 3600,
      }

      // Guardar en localStorage
      localStorage.setItem('access_token', tempTokens.access_token)
      localStorage.setItem('refresh_token', tempTokens.refresh_token)
      localStorage.setItem('user', JSON.stringify(tempUser))

      // Actualizar el store
      setUser(tempUser)
      setTokens(tempTokens)

      // Redirigir al dashboard
      navigate('/dashboard')
    } catch (err: any) {
      setError('Error al crear sesión temporal: ' + err.message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-md mx-auto mt-6">
      <CardHeader>
        <CardTitle className="text-center text-orange-600">
          🚀 Acceso Temporal - RAPICREDIT
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <AlertWithIcon
          variant="warning"
          title="Modo Temporal"
          description="El backend está dormido. Usa este acceso temporal para explorar el sistema."
        />

        <div className="space-y-3">
          <Button 
            onClick={() => handleTemporaryLogin('admin')}
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700"
          >
            {isLoading ? 'Accediendo...' : '👑 Acceso Administrador'}
          </Button>

          <Button 
            onClick={() => handleTemporaryLogin('gerente')}
            disabled={isLoading}
            className="w-full bg-green-600 hover:bg-green-700"
          >
            {isLoading ? 'Accediendo...' : '📊 Acceso Gerente'}
          </Button>

          <Button 
            onClick={() => handleTemporaryLogin('asesor')}
            disabled={isLoading}
            className="w-full bg-purple-600 hover:bg-purple-700"
          >
            {isLoading ? 'Accediendo...' : '💼 Acceso Asesor'}
          </Button>
        </div>

        {error && (
          <AlertWithIcon
            variant="destructive"
            title="Error"
            description={error}
          />
        )}

        <div className="text-xs text-gray-500 text-center">
          <p><strong>Nota:</strong> Este es un acceso temporal para demostración.</p>
          <p>Los datos son simulados hasta que el backend esté activo.</p>
        </div>
      </CardContent>
    </Card>
  )
}
