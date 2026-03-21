// frontend/src/pages/Analistas.tsx

import { useState, useEffect } from 'react'

import { motion } from 'framer-motion'

import {
  Users,
  Plus,
  Search,
  Edit,
  Trash2,
  UserCheck,
  UserX,
  Loader2,
  RefreshCw,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Badge } from '../components/ui/badge'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'

import {
  Analista,
  AnalistaUpdate,
  AnalistaCreate,
} from '../services/analistaService'

import {
  useAnalistas,
  useDeleteAnalista,
  useUpdateAnalista,
  useCreateAnalista,
} from '../hooks/useAnalistas'

import toast from 'react-hot-toast'

export function Analistas() {
  const [searchTerm, setSearchTerm] = useState('')

  const [showCreateForm, setShowCreateForm] = useState(false)

  const [editingAnalista, setEditingAnalista] = useState<Analista | null>(null)

  const [formData, setFormData] = useState<AnalistaCreate>({
    nombre: '',

    activo: true,
  })

  const [validationError, setValidationError] = useState<string>('')

  const [currentPage, setCurrentPage] = useState(1)

  const itemsPerPage = 10

  const [archivoExcel, setArchivoExcel] = useState<File | null>(null)

  // Usar hooks de React Query

  const {
    data: analistasData,

    isLoading: loading,

    error,

    refetch,
  } = useAnalistas({ limit: 1000 })

  const deleteAnalistaMutation = useDeleteAnalista()

  const updateAnalistaMutation = useUpdateAnalista()

  const createAnalistaMutation = useCreateAnalista()

  const analistas = analistasData?.items || []

  const handleEliminar = async (id: number) => {
    try {
      // Confirmar eliminación permanente

      const confirmar = window.confirm(
        'âš ï¸ ¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE este analista?\n\n' +
          'Esta acción NO se puede deshacer y el analista será borrado completamente de la base de datos.'
      )

      if (!confirmar) {
        return
      }

      await deleteAnalistaMutation.mutateAsync(id)
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const validateNombre = (nombre: string): string => {
    if (!nombre.trim()) {
      return 'El nombre es requerido'
    }

    // Limpiar espacios extras

    const nombreLimpio = nombre.trim().replace(/\s+/g, ' ')

    // Verificar cantidad de palabras (mínimo 2, máximo 4)

    const palabras = nombreLimpio.split(' ')

    if (palabras.length < 2) {
      return 'Debe ingresar al menos 2 palabras (Nombre y Apellido)'
    }

    if (palabras.length > 4) {
      return 'Debe ingresar máximo 4 palabras'
    }

    // Verificar que cada palabra tenga al menos 2 caracteres

    for (const palabra of palabras) {
      if (palabra.length < 2) {
        return 'Cada palabra debe tener al menos 2 caracteres'
      }
    }

    return ''
  }

  const formatNombre = (nombre: string): string => {
    // Limpiar espacios extras

    const nombreLimpio = nombre.trim().replace(/\s+/g, ' ')

    // Capitalizar primera letra de cada palabra

    return nombreLimpio
      .split(' ')
      .map(word => {
        if (word.length === 0) return word

        return word[0].toUpperCase() + word.slice(1).toLowerCase()
      })
      .join(' ')
  }

  const handleEdit = (analista: Analista) => {
    setEditingAnalista(analista)

    setFormData({
      nombre: analista.nombre,

      activo: analista.activo,
    })

    setValidationError('')

    setShowCreateForm(true)
  }

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validar nombre

    const error = validateNombre(formData.nombre)

    if (error) {
      setValidationError(error)

      return
    }

    setValidationError('')

    try {
      // Formatear nombre (capitalizar primera letra de cada palabra)

      const nombreFormateado = formatNombre(formData.nombre)

      if (editingAnalista) {
        // Al editar, mantener el estado actual

        await updateAnalistaMutation.mutateAsync({
          id: editingAnalista.id,

          data: { ...formData, nombre: nombreFormateado },
        })

        toast.success('âœ… Analista actualizado exitosamente')
      } else {
        // Al crear, ya tiene activo: true por defecto

        await createAnalistaMutation.mutateAsync({
          ...formData,
          nombre: nombreFormateado,
        })

        toast.success('âœ… Analista creado exitosamente')
      }

      resetForm()

      refetch()
    } catch (err) {
      console.error('Error:', err)

      toast.error('âŒ Error al guardar analista')
    }
  }

  const resetForm = () => {
    setFormData({
      nombre: '',

      activo: true,
    })

    setValidationError('')

    setEditingAnalista(null)

    setShowCreateForm(false)
  }

  const handleRefresh = () => {
    refetch()
  }

  // Filtrar analistas por término de búsqueda

  const filteredAnalistas = (analistas || []).filter(analista =>
    analista.nombre.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Paginación

  const totalPages = Math.ceil(filteredAnalistas.length / itemsPerPage)

  const startIndex = (currentPage - 1) * itemsPerPage

  const endIndex = startIndex + itemsPerPage

  const paginatedAnalistas = filteredAnalistas.slice(startIndex, endIndex)

  // Resetear a página 1 cuando cambia el filtro de búsqueda

  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-6 w-6 animate-spin" />

          <span>Cargando analistas...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <p className="mb-4 text-red-500">Error al cargar analistas</p>

          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Reintentar
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analistas</h1>

          <p className="text-muted-foreground">
            Gestiona los analistas del sistema
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            onClick={() => {
              setEditingAnalista(null)

              setFormData({ nombre: '', activo: true })

              setValidationError('')

              setShowCreateForm(true)
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            Nuevo Analista
          </Button>
        </div>
      </div>

      {/* Stats Cards */}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Analistas
            </CardTitle>

            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>

          <CardContent>
            <div className="text-2xl font-bold">{analistas?.length || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>

            <UserCheck className="h-4 w-4 text-green-600" />
          </CardHeader>

          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {
                (analistas || []).filter(
                  a => a.activo === true || a.activo === 1
                ).length
              }
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Inactivos</CardTitle>

            <UserX className="h-4 w-4 text-red-600" />
          </CardHeader>

          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {
                (analistas || []).filter(
                  a => a.activo === false || a.activo === 2 || a.activo === 0
                ).length
              }
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mostrados</CardTitle>

            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>

          <CardContent>
            <div className="text-2xl font-bold">{filteredAnalistas.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}

      <Card>
        <CardContent className="p-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

            <Input
              placeholder="Buscar por nombre..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Analistas Table */}

      <Card>
        <CardHeader>
          <CardTitle>Lista de Analistas</CardTitle>
        </CardHeader>

        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>

                <TableHead>Nombre</TableHead>

                <TableHead>Estado</TableHead>

                <TableHead>Fecha Creación</TableHead>

                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {paginatedAnalistas.map(analista => (
                <TableRow key={analista.id}>
                  <TableCell className="font-medium">{analista.id}</TableCell>

                  <TableCell>{analista.nombre}</TableCell>

                  <TableCell>
                    <Badge
                      variant={
                        analista.activo === true || analista.activo === 1
                          ? 'default'
                          : 'secondary'
                      }
                    >
                      {analista.activo === true || analista.activo === 1
                        ? 'Activo'
                        : 'Inactivo'}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    {analista.created_at
                      ? (() => {
                          const date = new Date(analista.created_at)

                          return isNaN(date.getTime())
                            ? '01/10/2025'
                            : date.toLocaleDateString('es-VE', {
                                year: 'numeric',

                                month: '2-digit',

                                day: '2-digit',
                              })
                        })()
                      : '01/10/2025'}
                  </TableCell>

                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(analista)}
                        title="Editar analista"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEliminar(analista.id)}
                        className="text-red-600 hover:text-red-700"
                        title="Eliminar analista"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {filteredAnalistas.length === 0 && (
            <div className="py-8 text-center text-muted-foreground">
              {searchTerm
                ? 'No se encontraron analistas con ese nombre'
                : 'No hay analistas disponibles'}
            </div>
          )}

          {/* Paginación */}

          {filteredAnalistas.length > itemsPerPage && (
            <div className="flex items-center justify-between border-t px-2 py-4">
              <div className="text-sm text-gray-500">
                Mostrando {startIndex + 1} a{' '}
                {Math.min(endIndex, filteredAnalistas.length)} de{' '}
                {filteredAnalistas.length} analistas
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  Anterior
                </Button>

                <div className="flex items-center space-x-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                    page => (
                      <Button
                        key={page}
                        variant={currentPage === page ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setCurrentPage(page)}
                        className={
                          currentPage === page ? 'bg-blue-600 text-white' : ''
                        }
                      >
                        {page}
                      </Button>
                    )
                  )}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setCurrentPage(prev => Math.min(totalPages, prev + 1))
                  }
                  disabled={currentPage === totalPages}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Importación desde Excel */}

      <Card>
        <CardHeader>
          <CardTitle>Importar Analistas (Excel)</CardTitle>
        </CardHeader>

        <CardContent className="space-y-3">
          <div className="text-sm text-gray-600">
            Columnas requeridas: <b>nombre</b>. Opcional: <b>activo</b> (por
            defecto: True).
          </div>

          <div className="flex items-center gap-2">
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={e => setArchivoExcel(e.target.files?.[0] || null)}
              className="hidden"
              id="excel-file-analistas"
            />

            <label
              htmlFor="excel-file-analistas"
              className="cursor-pointer rounded-md border border-gray-300 bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200"
            >
              Examinar...
            </label>

            <span className="text-sm text-gray-600">
              {archivoExcel
                ? archivoExcel.name
                : 'No se ha seleccionado ningún archivo.'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              disabled={!archivoExcel}
              onClick={async () => {
                if (!archivoExcel) return

                try {
                  const svc = (await import('../services/analistaService'))
                    .analistaService

                  const res = await svc.importarDesdeExcel(archivoExcel)

                  const msg = `Importado: ${res.creados} creados, ${res.actualizados} actualizados`

                  if (res.errores && res.errores.length > 0) {
                    toast.success(msg)

                    toast.error(
                      `Errores en ${res.errores.length} fila(s): ${res.errores.slice(0, 3).join(', ')}`
                    )
                  } else {
                    toast.success(msg)
                  }

                  setArchivoExcel(null)

                  // Resetear el input file

                  const fileInput = document.getElementById(
                    'excel-file-analistas'
                  ) as HTMLInputElement

                  if (fileInput) fileInput.value = ''

                  await refetch()
                } catch (err: unknown) {
                  const { getErrorMessage, getErrorDetail } =
                    await import('../types/errors')

                  let errorMessage = getErrorMessage(err)

                  const detail = getErrorDetail(err)

                  if (detail) {
                    errorMessage = detail
                  }

                  toast.error(errorMessage || 'Error al importar')
                }
              }}
            >
              Cargar Excel
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Create/Edit Form Modal */}

      {showCreateForm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={resetForm}
        >
          <div
            className="w-full max-w-md rounded-lg bg-white shadow-xl"
            onClick={e => e.stopPropagation()}
          >
            <Card>
              <CardHeader>
                <CardTitle>
                  {editingAnalista ? 'Editar Analista' : 'Nuevo Analista'}
                </CardTitle>
              </CardHeader>

              <CardContent>
                <form onSubmit={handleCreateOrUpdate} className="space-y-4">
                  <div>
                    <label className="mb-2 block text-sm font-medium">
                      Nombre del Analista *
                    </label>

                    <Input
                      value={formData.nombre}
                      onChange={e => {
                        setFormData({ ...formData, nombre: e.target.value })

                        setValidationError('') // Limpiar error al escribir
                      }}
                      placeholder="Ingrese nombre completo (2-4 palabras)"
                      required
                      autoFocus
                      className={validationError ? 'border-red-500' : ''}
                    />

                    {validationError && (
                      <p className="mt-1 text-xs text-red-500">
                        {validationError}
                      </p>
                    )}

                    {!editingAnalista && !validationError && (
                      <p className="mt-1 text-xs text-gray-500">
                        Ejemplo: Juan Pérez (mínimo 2, máximo 4 palabras)
                      </p>
                    )}
                  </div>

                  {editingAnalista && (
                    <div>
                      <label className="mb-2 block text-sm font-medium">
                        Estado *
                      </label>

                      <select
                        value={formData.activo ? 'ACTIVO' : 'INACTIVO'}
                        onChange={e =>
                          setFormData({
                            ...formData,
                            activo: e.target.value === 'ACTIVO',
                          })
                        }
                        className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <option value="ACTIVO">Activo</option>

                        <option value="INACTIVO">Inactivo</option>
                      </select>
                    </div>
                  )}

                  <div className="flex items-center space-x-2 pt-4">
                    <Button
                      type="submit"
                      disabled={
                        createAnalistaMutation.isPending ||
                        updateAnalistaMutation.isPending
                      }
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {createAnalistaMutation.isPending ||
                      updateAnalistaMutation.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Guardando...
                        </>
                      ) : (
                        <>
                          <Edit className="mr-2 h-4 w-4" />
                          {editingAnalista ? 'Actualizar' : 'Crear'} Analista
                        </>
                      )}
                    </Button>

                    <Button type="button" variant="outline" onClick={resetForm}>
                      Cancelar
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}

export default Analistas
