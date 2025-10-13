import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'
import { apiClient } from '@/services/api'

export function ConnectionTest() {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const testConnection = async () => {
    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      console.log('Probando conexión con el backend...')
      
      // Probar conexión básica
      const response = await apiClient.get('/') as any
      console.log('Respuesta del servidor:', response)
      
      setResult({
        status: 'success',
        data: response.data,
        statusCode: response.status
      })
    } catch (err: any) {
      console.error('Error en prueba de conexión:', err)
      
      setError(err.message || 'Error desconocido')
      setResult({
        status: 'error',
        error: err.message,
        statusCode: err.response?.status,
        response: err.response?.data
      })
    } finally {
      setIsLoading(false)
    }
  }

  const testAuthEndpoint = async () => {
    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      console.log('Probando endpoint de autenticación...')
      
      // Probar endpoint de auth (sin credenciales)
      const response = await apiClient.post('/api/v1/auth/login', {
        email: 'test@test.com',
        password: 'test123'
      }) as any
      
      setResult({
        status: 'success',
        data: response.data,
        statusCode: response.status
      })
    } catch (err: any) {
      console.error('Error en prueba de auth:', err)
      
      // Si es 422 o 401, es normal (credenciales incorrectas)
      if (err.response?.status === 422 || err.response?.status === 401) {
        setResult({
          status: 'expected_error',
          message: 'Endpoint funcionando correctamente (error esperado)',
          statusCode: err.response.status,
          data: err.response.data
        })
      } else {
        setError(err.message || 'Error desconocido')
        setResult({
          status: 'error',
          error: err.message,
          statusCode: err.response?.status,
          response: err.response?.data
        })
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>🔧 Prueba de Conexión - RAPICREDIT</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Button 
            onClick={testConnection} 
            disabled={isLoading}
            variant="outline"
          >
            {isLoading ? 'Probando...' : 'Probar Conexión Básica'}
          </Button>
          
          <Button 
            onClick={testAuthEndpoint} 
            disabled={isLoading}
            variant="outline"
          >
            {isLoading ? 'Probando...' : 'Probar Endpoint Auth'}
          </Button>
        </div>

        {error && (
          <AlertWithIcon
            variant="destructive"
            title="Error de Conexión"
            description={error}
          />
        )}

        {result && (
          <div className="space-y-2">
            <h3 className="font-semibold">
              Resultado: 
              <span className={`ml-2 px-2 py-1 rounded text-sm ${
                result.status === 'success' ? 'bg-green-100 text-green-800' :
                result.status === 'expected_error' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {result.status}
              </span>
            </h3>
            
            {result.statusCode && (
              <p><strong>Código de estado:</strong> {result.statusCode}</p>
            )}
            
            {result.message && (
              <p><strong>Mensaje:</strong> {result.message}</p>
            )}
            
            <details className="mt-2">
              <summary className="cursor-pointer font-medium">Ver detalles técnicos</summary>
              <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}

        <div className="text-sm text-gray-600">
          <p><strong>URL del backend:</strong> https://pagos-f2qf.onrender.com</p>
          <p><strong>Endpoint de prueba:</strong> /api/v1/auth/login</p>
        </div>
      </CardContent>
    </Card>
  )
}
