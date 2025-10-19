import React, { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Building2,
  Upload,
  FileSpreadsheet,
  Download,
  X,
  CheckCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  BarChart3,
  FileText,
  Users,
  DollarSign,
  TrendingUp,
  Eye,
  Edit,
  Trash2,
  Calendar,
  Search,
  Filter,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { AlertWithIcon } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { pagoService, type EstadoConciliacion, type ResultadoConciliacion, type ConciliacionCreate } from '@/services/pagoService'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import * as XLSX from 'xlsx'

interface ConciliacionRow {
  fila: number
  fecha: string
  numero_documento: string
  estado: string
  pago_id?: number
}

interface DesconciliacionForm {
  cedula_cliente: string
  numero_documento_anterior: string
  numero_documento_nuevo: string
  cedula_nueva: string
  nota: string
}

export function ConciliacionBancariaPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingProgress, setProcessingProgress] = useState(0)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [resultadosConciliacion, setResultadosConciliacion] = useState<ResultadoConciliacion | null>(null)
  const [showDesconciliacionForm, setShowDesconciliacionForm] = useState(false)
  const [pagoSeleccionado, setPagoSeleccionado] = useState<any>(null)
  
  const [desconciliacionForm, setDesconciliacionForm] = useState<DesconciliacionForm>({
    cedula_cliente: '',
    numero_documento_anterior: '',
    numero_documento_nuevo: '',
    cedula_nueva: '',
    nota: ''
  })

  // ============================================
  // QUERIES
  // ============================================

  const { data: estadoConciliacion, isLoading: estadoLoading, error: estadoError } = useQuery({
    queryKey: ['estado-conciliacion'],
    queryFn: () => pagoService.obtenerEstadoConciliacion(),
    refetchInterval: 30000,
  })

  // ============================================
  // HANDLERS
  // ============================================

  const handleDownloadTemplate = async () => {
    try {
      await pagoService.descargarTemplateConciliacion()
      toast.success('✅ Template descargado exitosamente')
    } catch (error) {
      toast.error('❌ Error al descargar el template')
    }
  }

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['estado-conciliacion'] })
    queryClient.invalidateQueries({ queryKey: ['pagos-list'] })
    queryClient.invalidateQueries({ queryKey: ['pagos-kpis'] })
    toast.success('🔄 Datos actualizados')
  }

  const processConciliacionFile = async (file: File) => {
    setIsProcessing(true)
    setProcessingProgress(0)
    setUploadedFile(file)
    setResultadosConciliacion(null)

    try {
      const resultado = await pagoService.procesarConciliacion(file)
      setResultadosConciliacion(resultado)
      toast.success(`✅ Conciliación procesada: ${resultado.resumen.conciliados} conciliados, ${resultado.resumen.pendientes} pendientes`)
      
      // Actualizar datos
      queryClient.invalidateQueries({ queryKey: ['estado-conciliacion'] })
      queryClient.invalidateQueries({ queryKey: ['pagos-list'] })
      queryClient.invalidateQueries({ queryKey: ['pagos-kpis'] })
    } catch (error) {
      toast.error('❌ Error procesando conciliación')
      console.error('Error procesando conciliación:', error)
    } finally {
      setIsProcessing(false)
      setProcessingProgress(0)
    }
  }

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      processConciliacionFile(file)
    }
  }

  const handleDesconciliarPago = (pago: any) => {
    setPagoSeleccionado(pago)
    setDesconciliacionForm({
      cedula_cliente: pago.cedula_cliente,
      numero_documento_anterior: pago.numero_documento,
      numero_documento_nuevo: '',
      cedula_nueva: '',
      nota: ''
    })
    setShowDesconciliacionForm(true)
  }

  const handleSaveDesconciliacion = async () => {
    try {
      await pagoService.desconciliarPago(desconciliacionForm)
      toast.success('✅ Pago desconciliado exitosamente')
      setShowDesconciliacionForm(false)
      setPagoSeleccionado(null)
      
      // Actualizar datos
      queryClient.invalidateQueries({ queryKey: ['estado-conciliacion'] })
      queryClient.invalidateQueries({ queryKey: ['pagos-list'] })
      queryClient.invalidateQueries({ queryKey: ['pagos-kpis'] })
    } catch (error) {
      toast.error('❌ Error desconciliando pago')
      console.error('Error desconciliando pago:', error)
    }
  }

  const handleDesconciliacionChange = (field: keyof DesconciliacionForm, value: string) => {
    setDesconciliacionForm(prev => ({ ...prev, [field]: value }))
  }

  // ============================================
  // RENDER
  // ============================================

  if (estadoError) {
    return (
      <div className="p-6">
        <AlertWithIcon
          variant="destructive"
          title="Error cargando datos"
          description="No se pudieron cargar los datos de conciliación. Intenta nuevamente."
        />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Building2 className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Conciliación Bancaria</h1>
            <p className="text-gray-600">Procesar conciliación y gestionar estados</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={estadoLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${estadoLoading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button
            onClick={() => navigate('/pagos')}
            variant="outline"
            size="sm"
          >
            <X className="h-4 w-4 mr-2" />
            Volver a Pagos
          </Button>
        </div>
      </div>

      {/* Estado de Conciliación */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Pagos</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {estadoLoading ? '...' : estadoConciliacion?.estadisticas.total_pagos || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Registros totales
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conciliados</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {estadoLoading ? '...' : estadoConciliacion?.estadisticas.pagos_conciliados || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Pagos conciliados
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pendientes</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {estadoLoading ? '...' : estadoConciliacion?.estadisticas.pagos_pendientes || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Por conciliar
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">% Conciliación</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {estadoLoading ? '...' : estadoConciliacion?.estadisticas.porcentaje_conciliacion || 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              Eficiencia
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Procesar Conciliación */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileSpreadsheet className="h-5 w-5" />
              <span>Procesar Conciliación Bancaria</span>
            </div>
            <Button
              onClick={handleDownloadTemplate}
              variant="outline"
              size="sm"
            >
              <Download className="h-4 w-4 mr-2" />
              Template
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!uploadedFile ? (
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
              <Upload className="h-16 w-16 mx-auto text-gray-400 mb-4" />
              <p className="text-lg text-gray-700 mb-2">Arrastra tu archivo Excel de conciliación aquí</p>
              <p className="text-sm text-gray-500 mb-4">o haz clic para seleccionar</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileInputChange}
                className="hidden"
              />
              <Button onClick={() => fileInputRef.current?.click()} disabled={isProcessing}>
                Seleccionar Archivo
              </Button>
              {isProcessing && (
                <Progress value={processingProgress} className="w-full mt-4" />
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileSpreadsheet className="h-5 w-5 text-blue-600" />
                  <span>Archivo: {uploadedFile.name}</span>
                </div>
                <Button
                  variant="ghost"
                  onClick={() => setUploadedFile(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              {isProcessing ? (
                <div className="space-y-2">
                  <p>Procesando conciliación...</p>
                  <Progress value={processingProgress} className="w-full" />
                </div>
              ) : resultadosConciliacion ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <Card className="text-center">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Total Registros</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{resultadosConciliacion.resumen.total_registros}</div>
                      </CardContent>
                    </Card>
                    <Card className="text-center border-green-400 bg-green-50">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-green-700">Conciliados</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-green-800">{resultadosConciliacion.resumen.conciliados}</div>
                      </CardContent>
                    </Card>
                    <Card className="text-center border-orange-400 bg-orange-50">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-orange-700">Pendientes</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-orange-800">{resultadosConciliacion.resumen.pendientes}</div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Tabla de Resultados */}
                  <div className="overflow-x-auto max-h-96 border rounded-lg">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fila</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Número Documento</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {resultadosConciliacion.resultados.map((resultado, index) => (
                          <tr key={index} className={resultado.estado === 'CONCILIADO' ? 'hover:bg-green-50' : 'hover:bg-orange-50'}>
                            <td className="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                              {resultado.fila}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                              {resultado.fecha}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                              {resultado.numero_documento}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                              <Badge variant={resultado.estado === 'CONCILIADO' ? 'success' : 'warning'}>
                                {resultado.estado}
                              </Badge>
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                              {resultado.estado === 'CONCILIADO' && resultado.pago_id && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDesconciliarPago({ 
                                    id: resultado.pago_id, 
                                    cedula_cliente: '', 
                                    numero_documento: resultado.numero_documento 
                                  })}
                                >
                                  <Edit className="h-4 w-4" />
                                </Button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal de Desconciliación */}
      <AnimatePresence>
        {showDesconciliacionForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="bg-gradient-to-r from-red-600 to-red-700 text-white p-6 rounded-t-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Edit className="h-6 w-6" />
                    <h2 className="text-xl font-bold">Desconciliar Pago</h2>
                  </div>
                  <Button
                    onClick={() => setShowDesconciliacionForm(false)}
                    variant="ghost"
                    size="sm"
                    className="text-white hover:bg-white/20"
                  >
                    <X className="h-5 w-5" />
                  </Button>
                </div>
              </div>

              <div className="p-6 space-y-4">
                <AlertWithIcon
                  variant="destructive"
                  title="Atención"
                  description="Esta acción desconciliará el pago y se registrará en auditoría. No se puede deshacer."
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">Cédula del Cliente *</label>
                    <Input
                      value={desconciliacionForm.cedula_cliente}
                      onChange={(e) => handleDesconciliacionChange('cedula_cliente', e.target.value)}
                      placeholder="V12345678"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Número de Documento Anterior *</label>
                    <Input
                      value={desconciliacionForm.numero_documento_anterior}
                      onChange={(e) => handleDesconciliacionChange('numero_documento_anterior', e.target.value)}
                      placeholder="DOC001234"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Número de Documento Nuevo *</label>
                    <Input
                      value={desconciliacionForm.numero_documento_nuevo}
                      onChange={(e) => handleDesconciliacionChange('numero_documento_nuevo', e.target.value)}
                      placeholder="DOC005678"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Cédula Nueva *</label>
                    <Input
                      value={desconciliacionForm.cedula_nueva}
                      onChange={(e) => handleDesconciliacionChange('cedula_nueva', e.target.value)}
                      placeholder="V87654321"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Nota Explicativa *</label>
                  <textarea
                    className="w-full p-3 border border-gray-300 rounded-md resize-none"
                    rows={3}
                    placeholder="Explica el motivo de la desconciliación..."
                    value={desconciliacionForm.nota}
                    onChange={(e) => handleDesconciliacionChange('nota', e.target.value)}
                  />
                </div>

                <div className="flex justify-end space-x-2">
                  <Button
                    onClick={() => setShowDesconciliacionForm(false)}
                    variant="outline"
                  >
                    Cancelar
                  </Button>
                  <Button
                    onClick={handleSaveDesconciliacion}
                    variant="destructive"
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Desconciliar Pago
                  </Button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
