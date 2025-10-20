import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Calculator, 
  Search, 
  Download, 
  FileText,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  Calendar,
  DollarSign,
  User
} from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { prestamoService } from '@/services/prestamoService'
import toast from 'react-hot-toast'

interface ClienteData {
  id: number
  cedula: string
  nombres: string
  apellidos: string
  telefono: string
  email: string
  direccion: string
}

interface PrestamoData {
  id: number
  cliente_id: number
  codigo_prestamo: string
  monto_total: number
  monto_financiado: number
  numero_cuotas: number
  monto_cuota: number
  tasa_interes: number
  fecha_primer_vencimiento: string
  modalidad: string
}

interface CuotaAmortizacion {
  numero: number
  fecha_vencimiento: string
  monto_cuota: number
  capital: number
  interes: number
  saldo_pendiente: number
}

interface TablaAmortizacionProps {
  onClose: () => void
}

export function TablaAmortizacion({ onClose }: TablaAmortizacionProps) {
  const [cedula, setCedula] = useState('')
  const [isSearchingClient, setIsSearchingClient] = useState(false)
  const [clienteEncontrado, setClienteEncontrado] = useState<ClienteData | null>(null)
  const [prestamoEncontrado, setPrestamoEncontrado] = useState<PrestamoData | null>(null)
  const [tablaAmortizacion, setTablaAmortizacion] = useState<CuotaAmortizacion[]>([])
  const [cedulaError, setCedulaError] = useState('')
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false)

  // Función para buscar cliente por cédula
  const buscarCliente = async (cedulaValue: string) => {
    if (!cedulaValue || cedulaValue.length < 8) {
      setCedulaError('')
      setClienteEncontrado(null)
      setPrestamoEncontrado(null)
      setTablaAmortizacion([])
      return
    }

    setIsSearchingClient(true)
    setCedulaError('')

    try {
      const cliente = await prestamoService.buscarClientePorCedula(cedulaValue)
      setClienteEncontrado(cliente)
      
      // Buscar préstamos del cliente
      const prestamos = await prestamoService.listarPrestamos({ cliente_id: cliente.id })
      if (prestamos.items && prestamos.items.length > 0) {
        const prestamo = prestamos.items[0] // Tomar el primer préstamo
        setPrestamoEncontrado(prestamo)
        generarTablaAmortizacion(prestamo)
        toast.success(`✅ Cliente y préstamo encontrados`)
      } else {
        setCedulaError('Cliente encontrado pero sin préstamos activos')
        setPrestamoEncontrado(null)
        setTablaAmortizacion([])
      }
    } catch (error) {
      setCedulaError('Cliente no encontrado')
      setClienteEncontrado(null)
      setPrestamoEncontrado(null)
      setTablaAmortizacion([])
    } finally {
      setIsSearchingClient(false)
    }
  }

  // Función para generar tabla de amortización
  const generarTablaAmortizacion = (prestamo: PrestamoData) => {
    const cuotas: CuotaAmortizacion[] = []
    let saldoPendiente = prestamo.monto_financiado
    const tasaMensual = prestamo.tasa_interes / 100 / 12
    const fechaInicio = new Date(prestamo.fecha_primer_vencimiento)

    for (let i = 1; i <= prestamo.numero_cuotas; i++) {
      const interes = saldoPendiente * tasaMensual
      const capital = prestamo.monto_cuota - interes
      saldoPendiente -= capital

      // Calcular fecha de vencimiento según modalidad
      const fechaVencimiento = new Date(fechaInicio)
      switch (prestamo.modalidad) {
        case 'SEMANAL':
          fechaVencimiento.setDate(fechaInicio.getDate() + (i * 7))
          break
        case 'QUINCENAL':
          fechaVencimiento.setDate(fechaInicio.getDate() + (i * 15))
          break
        case 'MENSUAL':
          fechaVencimiento.setMonth(fechaInicio.getMonth() + i)
          break
        case 'BIMESTRAL':
          fechaVencimiento.setMonth(fechaInicio.getMonth() + (i * 2))
          break
        default:
          fechaVencimiento.setMonth(fechaInicio.getMonth() + i)
      }

      cuotas.push({
        numero: i,
        fecha_vencimiento: fechaVencimiento.toISOString().split('T')[0],
        monto_cuota: prestamo.monto_cuota,
        capital: Math.max(0, capital),
        interes: Math.max(0, interes),
        saldo_pendiente: Math.max(0, saldoPendiente)
      })
    }

    setTablaAmortizacion(cuotas)
  }

  // Función para generar PDF
  const generarPDF = async () => {
    if (!clienteEncontrado || !prestamoEncontrado || tablaAmortizacion.length === 0) {
      toast.error('❌ No hay datos para generar PDF')
      return
    }

    setIsGeneratingPDF(true)
    
    try {
      // Crear contenido HTML para el PDF
      const htmlContent = `
        <html>
          <head>
            <title>Tabla de Amortización - ${clienteEncontrado.nombres} ${clienteEncontrado.apellidos}</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 20px; }
              .header { text-align: center; margin-bottom: 30px; }
              .client-info { margin-bottom: 20px; }
              table { width: 100%; border-collapse: collapse; margin-top: 20px; }
              th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
              th { background-color: #f2f2f2; }
              .total { font-weight: bold; background-color: #f9f9f9; }
            </style>
          </head>
          <body>
            <div class="header">
              <h1>Tabla de Amortización</h1>
              <h2>${clienteEncontrado.nombres} ${clienteEncontrado.apellidos}</h2>
              <p>Cédula: ${clienteEncontrado.cedula}</p>
            </div>
            
            <div class="client-info">
              <p><strong>Préstamo:</strong> ${prestamoEncontrado.codigo_prestamo}</p>
              <p><strong>Monto Total:</strong> $${prestamoEncontrado.monto_total.toLocaleString()}</p>
              <p><strong>Monto Financiado:</strong> $${prestamoEncontrado.monto_financiado.toLocaleString()}</p>
              <p><strong>Número de Cuotas:</strong> ${prestamoEncontrado.numero_cuotas}</p>
              <p><strong>Modalidad:</strong> ${prestamoEncontrado.modalidad}</p>
            </div>

            <table>
              <thead>
                <tr>
                  <th>Cuota</th>
                  <th>Fecha Vencimiento</th>
                  <th>Monto Cuota</th>
                  <th>Capital</th>
                  <th>Interés</th>
                  <th>Saldo Pendiente</th>
                </tr>
              </thead>
              <tbody>
                ${tablaAmortizacion.map(cuota => `
                  <tr>
                    <td>${cuota.numero}</td>
                    <td>${new Date(cuota.fecha_vencimiento).toLocaleDateString()}</td>
                    <td>$${cuota.monto_cuota.toLocaleString()}</td>
                    <td>$${cuota.capital.toLocaleString()}</td>
                    <td>$${cuota.interes.toLocaleString()}</td>
                    <td>$${cuota.saldo_pendiente.toLocaleString()}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </body>
        </html>
      `

      // Crear ventana nueva para imprimir
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(htmlContent)
        printWindow.document.close()
        printWindow.print()
        toast.success('✅ PDF generado exitosamente')
      }
    } catch (error) {
      toast.error('❌ Error al generar PDF')
    } finally {
      setIsGeneratingPDF(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
    >
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold flex items-center">
              <Calculator className="mr-2 h-6 w-6" />
              Tabla de Amortización
            </h2>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Búsqueda de Cliente */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center">
                <User className="mr-2 h-5 w-5" />
                Buscar Cliente
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-4">
                <div className="flex-1">
                  <label htmlFor="cedula" className="block text-sm font-medium text-gray-700 mb-1">Cédula del Cliente</label>
                  <div className="relative">
                    <Input
                      id="cedula"
                      placeholder="Ej: V-12345678"
                      value={cedula}
                      onChange={(e) => {
                        setCedula(e.target.value)
                        buscarCliente(e.target.value)
                      }}
                      className={cedulaError ? 'border-red-500' : ''}
                    />
                    {isSearchingClient && (
                      <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 animate-spin text-blue-600" />
                    )}
                  </div>
                  {cedulaError && (
                    <p className="text-sm text-red-600 mt-1">{cedulaError}</p>
                  )}
                </div>
              </div>

              {/* Datos del Cliente Encontrado */}
              {clienteEncontrado && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg"
                >
                  <div className="flex items-center mb-2">
                    <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
                    <span className="font-semibold text-green-800">Cliente Encontrado</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium">Nombre:</span> {clienteEncontrado.nombres} {clienteEncontrado.apellidos}
                    </div>
                    <div>
                      <span className="font-medium">Cédula:</span> {clienteEncontrado.cedula}
                    </div>
                    <div>
                      <span className="font-medium">Teléfono:</span> {clienteEncontrado.telefono}
                    </div>
                    <div>
                      <span className="font-medium">Email:</span> {clienteEncontrado.email}
                    </div>
                  </div>
                </motion.div>
              )}
            </CardContent>
          </Card>

          {/* Tabla de Amortización */}
          {tablaAmortizacion.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center">
                    <FileText className="mr-2 h-5 w-5" />
                    Tabla de Amortización Detallada
                  </CardTitle>
                  <Button onClick={generarPDF} disabled={isGeneratingPDF}>
                    {isGeneratingPDF ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generando...
                      </>
                    ) : (
                      <>
                        <Download className="h-4 w-4 mr-2" />
                        Generar PDF
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Cuota</TableHead>
                        <TableHead>Fecha de Pago</TableHead>
                        <TableHead>Monto a Pagar</TableHead>
                        <TableHead>Capital</TableHead>
                        <TableHead>Interés</TableHead>
                        <TableHead>Saldo Pendiente</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tablaAmortizacion.map((cuota) => (
                        <TableRow key={cuota.numero}>
                          <TableCell className="font-medium">
                            {cuota.numero}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center">
                              <Calendar className="h-4 w-4 mr-2 text-blue-600" />
                              {new Date(cuota.fecha_vencimiento).toLocaleDateString()}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center">
                              <DollarSign className="h-4 w-4 mr-2 text-green-600" />
                              ${cuota.monto_cuota.toLocaleString()}
                            </div>
                          </TableCell>
                          <TableCell>${cuota.capital.toLocaleString()}</TableCell>
                          <TableCell>${cuota.interes.toLocaleString()}</TableCell>
                          <TableCell>${cuota.saldo_pendiente.toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Resumen */}
                <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-blue-800">Total a Pagar</h3>
                    <p className="text-2xl font-bold text-blue-600">
                      ${tablaAmortizacion.reduce((sum, cuota) => sum + cuota.monto_cuota, 0).toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-green-800">Total Capital</h3>
                    <p className="text-2xl font-bold text-green-600">
                      ${tablaAmortizacion.reduce((sum, cuota) => sum + cuota.capital, 0).toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-orange-800">Total Interés</h3>
                    <p className="text-2xl font-bold text-orange-600">
                      ${tablaAmortizacion.reduce((sum, cuota) => sum + cuota.interes, 0).toLocaleString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Botones */}
          <div className="flex justify-end space-x-3 mt-6">
            <Button variant="outline" onClick={onClose}>
              Cerrar
            </Button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
