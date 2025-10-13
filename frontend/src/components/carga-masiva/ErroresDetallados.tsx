import { useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Download, Eye, EyeOff, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'

interface ErrorDetail {
  row: number
  cedula: string
  error: string
  data: any
  tipo: 'cliente' | 'pago'
}

interface ErroresDetalladosProps {
  errores: ErrorDetail[]
  tipo: 'clientes' | 'pagos'
  onDescargarErrores: () => void
}

export function ErroresDetallados({ errores, tipo, onDescargarErrores }: ErroresDetalladosProps) {
  const [erroresExpandidos, setErroresExpandidos] = useState<Set<number>>(new Set())

  const toggleError = (row: number) => {
    const nuevosExpandidos = new Set(erroresExpandidos)
    if (nuevosExpandidos.has(row)) {
      nuevosExpandidos.delete(row)
    } else {
      nuevosExpandidos.add(row)
    }
    setErroresExpandidos(nuevosExpandidos)
  }

  const generarArchivoCorreccion = () => {
    const headers = tipo === 'clientes' 
      ? ['cedula', 'nombre', 'telefono', 'email', 'error', 'correccion_sugerida']
      : ['cedula', 'fecha', 'monto_pagado', 'documento_pago', 'error', 'correccion_sugerida']
    
    const datosCorreccion = errores.map(error => {
      const correccionSugerida = generarCorreccionSugerida(error)
      return [
        error.cedula,
        error.data.nombre || error.data.fecha || '',
        error.data.telefono || error.data.monto_pagado || '',
        error.data.email || error.data.documento_pago || '',
        error.error,
        correccionSugerida
      ]
    })

    const csvContent = [headers, ...datosCorreccion]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `errores_${tipo}_para_corregir.csv`
    link.click()
  }

  const generarCorreccionSugerida = (error: ErrorDetail): string => {
    const errorMsg = error.error.toLowerCase()
    
    if (errorMsg.includes('cedula')) {
      return 'Verificar formato de cédula venezolana (V12345678)'
    }
    if (errorMsg.includes('telefono')) {
      return 'Formato: +5804123456789 o 04123456789'
    }
    if (errorMsg.includes('email')) {
      return 'Formato válido: usuario@dominio.com'
    }
    if (errorMsg.includes('monto')) {
      return 'Solo números, usar punto para decimales (ej: 108.50)'
    }
    if (errorMsg.includes('fecha')) {
      return 'Formato: DD/MM/YYYY o YYYY-MM-DD'
    }
    if (errorMsg.includes('no encontrado')) {
      return 'Primero cargar el cliente con esta cédula'
    }
    
    return 'Revisar datos y formato'
  }

  if (errores.length === 0) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      <Card className="border-red-200 bg-red-50">
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-red-800">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5" />
              <span>Errores Requieren Corrección Manual</span>
            </div>
            <div className="flex space-x-2">
              <Button
                onClick={generarArchivoCorreccion}
                variant="outline"
                size="sm"
                className="text-red-700 border-red-300 hover:bg-red-100"
              >
                <Download className="h-4 w-4 mr-2" />
                Descargar Lista de Correcciones
              </Button>
              <Button
                onClick={onDescargarErrores}
                variant="outline"
                size="sm"
                className="text-red-700 border-red-300 hover:bg-red-100"
              >
                <Download className="h-4 w-4 mr-2" />
                Descargar Solo Errores
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AlertWithIcon
            variant="destructive"
            title={`${errores.length} registros requieren corrección manual`}
            description="Estos registros no pudieron procesarse automáticamente. Descarga la lista para corregirlos y volver a cargar."
          />
          
          <div className="mt-4 space-y-3 max-h-96 overflow-y-auto">
            {errores.map((error, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="border border-red-200 rounded-lg p-3 bg-white"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <XCircle className="h-5 w-5 text-red-500" />
                    <div>
                      <p className="font-medium text-gray-900">
                        Fila {error.row} - Cédula: {error.cedula}
                      </p>
                      <p className="text-sm text-red-600">{error.error}</p>
                    </div>
                  </div>
                  <Button
                    onClick={() => toggleError(error.row)}
                    variant="ghost"
                    size="sm"
                  >
                    {erroresExpandidos.has(error.row) ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                
                {erroresExpandidos.has(error.row) && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-3 pt-3 border-t border-red-100"
                  >
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="font-medium text-gray-700 mb-1">Datos Originales:</p>
                        <div className="bg-gray-50 p-2 rounded text-xs font-mono">
                          {JSON.stringify(error.data, null, 2)}
                        </div>
                      </div>
                      <div>
                        <p className="font-medium text-gray-700 mb-1">Corrección Sugerida:</p>
                        <div className="bg-green-50 p-2 rounded text-xs">
                          {generarCorreccionSugerida(error)}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
          
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">📋 Instrucciones para Corrección:</h4>
            <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
              <li>Descarga la lista de errores usando el botón "Descargar Lista de Correcciones"</li>
              <li>Corrige los datos en Excel según las sugerencias</li>
              <li>Guarda el archivo corregido</li>
              <li>Vuelve a cargar el archivo corregido</li>
              <li>Los registros corregidos se procesarán automáticamente</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
