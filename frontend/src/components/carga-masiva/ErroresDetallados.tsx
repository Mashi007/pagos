import { useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Download, Eye, EyeOff, CheckCircle, XCircle, FileSpreadsheet, ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'

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

  const getErrorType = (error: string): string => {
    const errorMsg = error.toLowerCase()
    
    if (errorMsg.includes('cedula')) return 'Cédula'
    if (errorMsg.includes('telefono') || errorMsg.includes('móvil')) return 'Teléfono'
    if (errorMsg.includes('email')) return 'Email'
    if (errorMsg.includes('monto')) return 'Monto'
    if (errorMsg.includes('fecha')) return 'Fecha'
    if (errorMsg.includes('no encontrado')) return 'Cliente'
    if (errorMsg.includes('formato')) return 'Formato'
    if (errorMsg.includes('requerido') || errorMsg.includes('obligatorio')) return 'Requerido'
    
    return 'Validación'
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
      <Card className="border-red-200 bg-gradient-to-r from-red-50 to-red-100">
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-red-800">
            <div className="flex items-center space-x-3">
              <div className="bg-red-500 rounded-full p-2">
                <AlertTriangle className="h-5 w-5 text-white" />
              </div>
              <div>
                <span className="text-lg font-bold">Errores Requieren Corrección Manual</span>
                <p className="text-sm font-normal text-red-600 mt-1">
                  {errores.length} registros con problemas de validación
                </p>
              </div>
            </div>
            <div className="flex space-x-2">
              <Button
                onClick={generarArchivoCorreccion}
                variant="outline"
                size="sm"
                className="text-red-700 border-red-300 hover:bg-red-100 font-medium"
              >
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Lista de Correcciones
              </Button>
              <Button
                onClick={onDescargarErrores}
                variant="outline"
                size="sm"
                className="text-red-700 border-red-300 hover:bg-red-100 font-medium"
              >
                <Download className="h-4 w-4 mr-2" />
                Solo Errores
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <AlertWithIcon
            variant="destructive"
            title={`${errores.length} registros requieren corrección manual`}
            description="Estos registros no pudieron procesarse automáticamente. Descarga la lista para corregirlos y volver a cargar."
          />
          
          {/* Tabla de errores mejorada */}
          <div className="bg-white rounded-lg border border-red-200 overflow-hidden">
            <Table>
              <TableHeader className="bg-red-50">
                <TableRow>
                  <TableHead className="text-red-800 font-semibold">Fila</TableHead>
                  <TableHead className="text-red-800 font-semibold">Cédula</TableHead>
                  <TableHead className="text-red-800 font-semibold">Tipo de Error</TableHead>
                  <TableHead className="text-red-800 font-semibold">Descripción</TableHead>
                  <TableHead className="text-red-800 font-semibold">Acción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {errores.map((error, index) => (
                  <motion.tr
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="hover:bg-red-50/50 transition-colors"
                  >
                    <TableCell className="font-medium">
                      <Badge variant="outline" className="bg-red-100 text-red-800 border-red-300">
                        {error.row}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {error.cedula}
                    </TableCell>
                    <TableCell>
                      <Badge variant="destructive" className="text-xs">
                        {getErrorType(error.error)}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-md">
                      <p className="text-sm text-gray-700 line-clamp-2">
                        {error.error}
                      </p>
                    </TableCell>
                    <TableCell>
                      <Button
                        onClick={() => toggleError(error.row)}
                        variant="ghost"
                        size="sm"
                        className="text-red-600 hover:text-red-800"
                      >
                        {erroresExpandidos.has(error.row) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                  </motion.tr>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Detalles expandibles */}
          {errores.map((error, index) => (
            erroresExpandidos.has(error.row) && (
              <motion.div
                key={`detail-${index}`}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-white border border-red-200 rounded-lg p-4"
              >
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                      <XCircle className="h-4 w-4 mr-2 text-red-500" />
                      Datos Originales
                    </h4>
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap">
                        {JSON.stringify(error.data, null, 2)}
                      </pre>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                      <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                      Corrección Sugerida
                    </h4>
                    <div className="bg-green-50 p-3 rounded-lg border border-green-200">
                      <p className="text-sm text-green-800">
                        {generarCorreccionSugerida(error)}
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )
          ))}
          
          {/* Instrucciones mejoradas */}
          <div className="bg-gradient-to-r from-blue-50 to-blue-100 p-6 rounded-lg border border-blue-200">
            <h4 className="font-bold text-blue-900 mb-4 flex items-center">
              <FileSpreadsheet className="h-5 w-5 mr-2" />
              📋 Instrucciones para Corrección
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h5 className="font-semibold text-blue-800 mb-2">Pasos a seguir:</h5>
                <ol className="text-sm text-blue-700 space-y-2 list-decimal list-inside">
                  <li>Descarga la lista de errores usando el botón "Lista de Correcciones"</li>
                  <li>Corrige los datos en Excel según las sugerencias mostradas</li>
                  <li>Guarda el archivo corregido</li>
                  <li>Vuelve a cargar el archivo corregido</li>
                </ol>
              </div>
              <div>
                <h5 className="font-semibold text-blue-800 mb-2">Tipos de errores comunes:</h5>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• <strong>Cédula:</strong> Formato V12345678</li>
                  <li>• <strong>Teléfono:</strong> +5804123456789</li>
                  <li>• <strong>Email:</strong> usuario@dominio.com</li>
                  <li>• <strong>Monto:</strong> Solo números con punto decimal</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
