import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'

export function BackendStatus() {
  const [isChecking, setIsChecking] = useState(false)
  const [status, setStatus] = useState<any>(null)

  const checkBackendStatus = async () => {
    setIsChecking(true)
    try {
      const response = await fetch('https://pagos-f2qf.onrender.com/', {
        method: 'GET',
        mode: 'cors'
      })
      
      if (response.ok) {
        const data = await response.json()
        setStatus({
          status: 'success',
          message: 'Backend activo y funcionando',
          data: data
        })
      } else {
        setStatus({
          status: 'error',
          message: `Backend respondió con código ${response.status}`,
          code: response.status
        })
      }
    } catch (error: any) {
      setStatus({
        status: 'error',
        message: 'Backend no disponible - Error 503',
        error: error.message
      })
    } finally {
      setIsChecking(false)
    }
  }

  return (
    <Card className="w-full max-w-md mx-auto mt-4">
      <CardHeader>
        <CardTitle className="text-center">🔧 Estado del Backend</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button 
          onClick={checkBackendStatus} 
          disabled={isChecking}
          className="w-full"
        >
          {isChecking ? 'Verificando...' : 'Verificar Estado del Backend'}
        </Button>

        {status && (
          <div className="space-y-2">
            <div className={`p-3 rounded-lg ${
              status.status === 'success' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              <strong>Estado:</strong> {status.message}
            </div>
            
            {status.data && (
              <div className="text-sm text-gray-600">
                <strong>Datos:</strong> {JSON.stringify(status.data)}
              </div>
            )}
            
            {status.code && (
              <div className="text-sm text-gray-600">
                <strong>Código:</strong> {status.code}
              </div>
            )}
          </div>
        )}

        <div className="text-xs text-gray-500 text-center">
          <p><strong>URL:</strong> https://pagos-f2qf.onrender.com</p>
          <p>Si el backend está dormido, puede tomar 1-2 minutos en activarse</p>
        </div>
      </CardContent>
    </Card>
  )
}
