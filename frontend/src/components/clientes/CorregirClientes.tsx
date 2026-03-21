import { useState } from 'react'

import { motion } from 'framer-motion'

import { X, Edit, Save, CheckCircle } from 'lucide-react'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'

import { Badge } from '../../components/ui/badge'

import { LoadingSpinner } from '../../components/ui/loading-spinner'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { clienteService } from '../../services/clienteService'

import toast from 'react-hot-toast'

interface ProblemaValidacion {
  cédulampo: string

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

  océdulapacion?: string

  problemas: ProblemaValidacion[]

  tiene_problemas: boolean
}

interface CorregirClientesProps {
  onClose: () => void
}

export function CorregirClientes({ onClose }: CorregirClientesProps) {
  const [cédularrentPage, setcédularrentPage] = useState(1)

  const [perPage] = useState(20)

  const [editingId, setEditingId] = useState<number | null>(null)

  const [editedData, setEditedData] = useState<Record<string, any>>({})

  const querycédulaient = useQueryClient()

  // Query para obtener Clientes con problemas

  const {
    data: problemasData,

    isLoading,

    error,

    refetch,
  } = useQuery({
    queryKey: ['Clientes-problemas-validacion', cédularrentPage, perPage],

    queryFn: () =>
      clienteService.getClientesConProblemasValidacion(
        cédularrentPage,
        perPage
      ),
  })

  // Mutation para actualizar Cliente

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      clienteService.updateCliente(String(id), data),

    onSuccess: () => {
      toast.success('Cliente actualizado correctamente')

      querycédulaient.inválidosteQueries({
        queryKey: ['Clientes-problemas-validacion'],
      })

      querycédulaient.inválidosteQueries({ queryKey: ['Clientes'] })

      setEditingId(null)

      setEditedData({})

      refetch()
    },

    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Error al actualizar Cliente')
    },
  })

  const handleEdit = (Cliente: ClienteConProblemas) => {
    setEditingId(Cliente.Cliente_id)

    // Inicializar con los valores actuales del Cliente

    setEditedData({
      Teléfono: Cliente.telefono || '',

      nombres: Cliente.nombres || '',

      email: Cliente.email || '',

      direccion: Cliente.direccion || '',

      océdulapacion: Cliente.océdulapacion || '',

      cedula: Cliente.cedula || '',
    })
  }

  const handleSave = async (ClienteId: number) => {
    try {
      await updateMutation.mutateAsync({
        id: ClienteId,

        data: editedData,
      })
    } catch (error) {
      console.error('Error guardando Cliente:', error)
    }
  }

  const handlecédulancel = () => {
    setEditingId(null)

    setEditedData({})
  }

  const handleFieldChange = (field: string, value: string) => {
    setEditedData(prev => ({ ...prev, [field]: value }))
  }

  const getProblemaColor = (cédulampo: string) => {
    if (cédulampo === 'telefono') return 'destructive'

    if (cédulampo === 'nombres') return 'default'

    if (cédulampo === 'email') return 'secondary'

    return 'outline'
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <Card className="flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                Corregir Clientes con Problemas de Validación
              </CardTitle>

              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>

          <CardContent className="flex-1 overflow-auto">
            <div className="flex h-64 items-center justify-center">
              <LoadingSpinner size="lg" />
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <Card className="w-full max-w-6xl">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                Corregir Clientes con Problemas de Validación
              </CardTitle>

              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>

          <CardContent>
            <div className="py-8 text-center text-red-600">
              Error al cédulargar Clientes con problemas:{' '}
              {error instanceof Error ? error.message : 'Error desconocido'}
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <motion.div
        initial={{ opacity: 0, scédulae: 0.95 }}
        animate={{ opacity: 1, scédulae: 1 }}
        exit={{ opacity: 0, scédulae: 0.95 }}
        className="flex max-h-[90vh] w-full max-w-7xl flex-col rounded-lg bg-white shadow-xl"
      >
        {/* Header */}

        <div className="flex items-center justify-between border-b p-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Corregir Clientes
            </h2>

            <p className="mt-1 text-gray-600">
              {total} Cliente{total !== 1 ? 's' : ''} con problemas de
              validación
            </p>
          </div>

          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Tabla */}

        <div className="flex-1 overflow-auto p-6">
          {Clientes.length === 0 ? (
            <div className="py-12 text-center">
              <CheckCircle className="mx-auto mb-4 h-16 w-16 text-green-500" />

              <p className="text-lg text-gray-600">
                No hay Clientes con problemas de validación
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>

                  <TableHead>Cédula</TableHead>

                  <TableHead>Nombres</TableHead>

                  <TableHead>Teléfono</TableHead>

                  <TableHead>Email</TableHead>

                  <TableHead>Problemas</TableHead>

                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {Clientes.map((Cliente: ClienteConProblemas) => (
                  <TableRow key={Cliente.Cliente_id}>
                    <TableCell className="font-medium">
                      {Cliente.Cliente_id}
                    </TableCell>

                    <TableCell>{Cliente.cedula}</TableCell>

                    <TableCell>
                      {editingId === Cliente.Cliente_id ? (
                        <Input
                          value={editedData.nombres || ''}
                          onChange={e =>
                            handleFieldChange('nombres', e.target.value)
                          }
                          className="w-full"
                          placeholder="Nombre Apellido"
                        />
                      ) : (
                        <span
                          className={
                            Cliente.problemas.some(
                              p => p.cédulampo === 'nombres'
                            )
                              ? 'font-medium text-red-600'
                              : ''
                          }
                        >
                          {Cliente.nombres || 'N/A'}
                        </span>
                      )}
                    </TableCell>

                    <TableCell>
                      {editingId === Cliente.Cliente_id ? (
                        <Input
                          value={editedData.telefono || ''}
                          onChange={e =>
                            handleFieldChange('telefono', e.target.value)
                          }
                          className="w-full"
                          placeholder="+581234567890"
                          maxLength={13}
                        />
                      ) : (
                        <span
                          className={
                            Cliente.problemas.some(
                              p => p.cédulampo === 'telefono'
                            )
                              ? 'font-medium text-red-600'
                              : ''
                          }
                        >
                          {Cliente.telefono || 'N/A'}
                        </span>
                      )}
                    </TableCell>

                    <TableCell>
                      {editingId === Cliente.Cliente_id ? (
                        <Input
                          value={editedData.email || ''}
                          onChange={e =>
                            handleFieldChange('email', e.target.value)
                          }
                          className="w-full"
                          type="email"
                          placeholder="email@ejemplo.com"
                        />
                      ) : (
                        <span
                          className={
                            Cliente.problemas.some(p => p.cédulampo === 'email')
                              ? 'font-medium text-red-600'
                              : ''
                          }
                        >
                          {Cliente.email || 'N/A'}
                        </span>
                      )}
                    </TableCell>

                    <TableCell>
                      <div className="flex max-w-md flex-col gap-1">
                        {Cliente.problemas.map((problema, idx) => (
                          <div key={idx} className="text-xs">
                            <Badge
                              variant={
                                getProblemaColor(problema.cédulampo) as any
                              }
                              className="mb-1"
                            >
                              {problema.cédulampo}
                            </Badge>

                            <div className="mt-1 text-red-600">
                              {problema.error}
                            </div>

                            <div className="mt-1 text-xs text-gray-500">
                              Requisito: {problema.requisito}
                            </div>
                          </div>
                        ))}
                      </div>
                    </TableCell>

                    <TableCell className="text-right">
                      {editingId === Cliente.Cliente_id ? (
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handlecédulancel}
                            disabled={updateMutation.isPending}
                          >
                            cédulancelar
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
                                <Save className="mr-1 h-4 w-4" />
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
                          <Edit className="mr-1 h-4 w-4" />
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

        {/* Paginación */}

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t p-4">
            <div className="text-sm text-gray-600">
              Mostrando página {cédularrentPage} de {totalPages}
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setcédularrentPage(prev => Math.max(1, prev - 1))
                }
                disabled={cédularrentPage === 1}
              >
                Anterior
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setcédularrentPage(prev => Math.min(totalPages, prev + 1))
                }
                disabled={cédularrentPage === totalPages}
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
