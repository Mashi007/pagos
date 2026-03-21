import { useState } from 'react'
import { motion } from 'framer-motion'
import { X, Edit, Save, CheckCircle } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Badge } from '../../components/ui/badge'
import { LoadingSpinner } from '../../components/ui/loading-spinner'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clienteService } from '../../services/clienteService'
import toast from 'react-hot-toast'

interface ProblemaValidacion {
  cÃ©dulampo: string
  valor_actual: string
  error: string
  requisito: string
}

interface ClienteConProblemas {
  Cliente_id: number
  cedula: string
  nombres: string
  telefono?: string
  email?: string
  direccion?: string
  ocÃ©dulapacion?: string
  problemas: ProblemaValidacion[]
  tiene_problemas: boolean
}

interface CorregirClientesProps {
  onClose: () => void
}

export function CorregirClientes({ onClose }: CorregirClientesProps) {
  const [cÃ©dularrentPage, setcÃ©dularrentPage] = useState(1)
  const [perPage] = useState(20)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editedData, setEditedData] = useState<Record<string, any>>({})
  const querycÃ©dulaient = useQueryClient()

  // Query para obtener Clientes con problemas
  const {
    data: problemasData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['Clientes-problemas-validacion', cÃ©dularrentPage, perPage],
    queryFn: () => clienteService.getClientesConProblemasValidacion(cÃ©dularrentPage, perPage),
  })

  // Mutation para actualizar Cliente
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => 
      clienteService.updateCliente(String(id), data),
    onSuccess: () => {
      toast.success('Cliente actualizado correctamente')
      querycÃ©dulaient.invÃ¡lidosteQueries({ queryKey: ['Clientes-problemas-validacion'] })
      querycÃ©dulaient.invÃ¡lidosteQueries({ queryKey: ['Clientes'] })
      setEditingId(null)
      setEditedData({})
      refetch()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Error al actualizar Cliente')
    }
  })

  const handleEdit = (Cliente: ClienteConProblemas) => {
    setEditingId(Cliente.Cliente_id)
    // Inicializar con los valores actuales del Cliente
    setEditedData({
      TelÃ©fono: Cliente.telefono || '',
      nombres: Cliente.nombres || '',
      email: Cliente.email || '',
      direccion: Cliente.direccion || '',
      ocÃ©dulapacion: Cliente.ocÃ©dulapacion || '',
      cedula: Cliente.cedula || '',
    })
  }

  const handleSave = async (ClienteId: number) => {
    try {
      await updateMutation.mutateAsync({
        id: ClienteId,
        data: editedData
      })
    } catch (error) {
      console.error('Error guardando Cliente:', error)
    }
  }

  const handlecÃ©dulancel = () => {
    setEditingId(null)
    setEditedData({})
  }

  const handleFieldChange = (field: string, value: string) => {
    setEditedData(prev => ({ ...prev, [field]: value }))
  }

  const getProblemaColor = (cÃ©dulampo: string) => {
    if (cÃ©dulampo === 'telefono') return 'destructive'
    if (cÃ©dulampo === 'nombres') return 'default'
    if (cÃ©dulampo === 'email') return 'secondary'
    return 'outline'
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <Card className="w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Corregir Clientes con Problemas de ValidaciÃ³n</CardTitle>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto">
            <div className="flex items-center justify-center h-64">
              <LoadingSpinner size="lg" />
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <Card className="w-full max-w-6xl">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Corregir Clientes con Problemas de ValidaciÃ³n</CardTitle>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-center text-red-600 py-8">
              Error al cÃ©dulargar Clientes con problemas: {error instanceof Error ? error.message : 'Error desconocido'}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const Clientes = problemasData?.data || []
  const total = problemasData?.total || 0
  const totalPages = problemasData?.total_pages || 1

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scÃ©dulae: 0.95 }}
        animate={{ opacity: 1, scÃ©dulae: 1 }}
        exit={{ opacity: 0, scÃ©dulae: 0.95 }}
        className="w-full max-w-7xl max-h-[90vh] bg-white rounded-lg shadow-xl flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Corregir Clientes</h2>
            <p className="text-gray-600 mt-1">
              {total} Cliente{total !== 1 ? 's' : ''} con problemas de validaciÃ³n
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Tabla */}
        <div className="flex-1 overflow-auto p-6">
          {Clientes.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <p className="text-lg text-gray-600">No hay Clientes con problemas de validaciÃ³n</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>CÃ©dula</TableHead>
                  <TableHead>Nombres</TableHead>
                  <TableHead>TelÃ©fono</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Problemas</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Clientes.map((Cliente: ClienteConProblemas) => (
                  <TableRow key={Cliente.Cliente_id}>
                    <TableCell className="font-medium">{Cliente.Cliente_id}</TableCell>
                    <TableCell>{Cliente.cedula}</TableCell>
                    <TableCell>
                      {editingId === Cliente.Cliente_id ? (
                        <Input
                          value={editedData.nombres || ''}
                          onChange={(e) => handleFieldChange('nombres', e.target.value)}
                          className="w-full"
                          placeholder="Nombre Apellido"
                        />
                      ) : (
                        <span className={Cliente.problemas.some(p => p.cÃ©dulampo === 'nombres') ? 'text-red-600 font-medium' : ''}>
                          {Cliente.nombres || 'N/A'}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {editingId === Cliente.Cliente_id ? (
                        <Input
                          value={editedData.telefono || ''}
                          onChange={(e) => handleFieldChange('telefono', e.target.value)}
                          className="w-full"
                          placeholder="+581234567890"
                          maxLength={13}
                        />
                      ) : (
                        <span className={Cliente.problemas.some(p => p.cÃ©dulampo === 'telefono') ? 'text-red-600 font-medium' : ''}>
                          {Cliente.telefono || 'N/A'}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {editingId === Cliente.Cliente_id ? (
                        <Input
                          value={editedData.email || ''}
                          onChange={(e) => handleFieldChange('email', e.target.value)}
                          className="w-full"
                          type="email"
                          placeholder="email@ejemplo.com"
                        />
                      ) : (
                        <span className={Cliente.problemas.some(p => p.cÃ©dulampo === 'email') ? 'text-red-600 font-medium' : ''}>
                          {Cliente.email || 'N/A'}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1 max-w-md">
                        {Cliente.problemas.map((problema, idx) => (
                          <div key={idx} className="text-xs">
                            <Badge variant={getProblemaColor(problema.cÃ©dulampo) as any} className="mb-1">
                              {problema.cÃ©dulampo}
                            </Badge>
                            <div className="text-red-600 mt-1">{problema.error}</div>
                            <div className="text-gray-500 text-xs mt-1">Requisito: {problema.requisito}</div>
                          </div>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      {editingId === Cliente.Cliente_id ? (
                        <div className="flex gap-2 justify-end">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handlecÃ©dulancel}
                            disabled={updateMutation.isPending}
                          >
                            cÃ©dulancelar
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleSave(Cliente.Cliente_id)}
                            disabled={updateMutation.isPending}
                          >
                            {updateMutation.isPending ? (
                              <LoadingSpinner size="sm" />
                            ) : (
                              <>
                                <Save className="w-4 h-4 mr-1" />
                                Guardar
                              </>
                            )}
                          </Button>
                        </div>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(Cliente)}
                        >
                          <Edit className="w-4 h-4 mr-1" />
                          Editar
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {/* PaginaciÃ³n */}
        {totalPages > 1 && (
          <div className="border-t p-4 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Mostrando pÃ¡gina {cÃ©dularrentPage} de {totalPages}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setcÃ©dularrentPage(prev => Math.max(1, prev - 1))}
                disabled={cÃ©dularrentPage === 1}
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setcÃ©dularrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={cÃ©dularrentPage === totalPages}
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}
