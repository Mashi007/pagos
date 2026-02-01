import { useState, useEffect } from 'react'
import { Shield, Download, Search, Filter, Calendar, User, Activity, BarChart3, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { auditoriaService, Auditoria as AuditoriaType, AuditoriaStats } from '../services/auditoriaService'
import { toast } from 'sonner'

export function Auditoria() {
  const [auditorias, setAuditorias] = useState<AuditoriaType[]>([])
  const [stats, setStats] = useState<AuditoriaStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(50)

  // Filtros
  const [filtros, setFiltros] = useState({
    usuario_email: '',
    modulo: 'ALL',
    accion: 'ALL',
    fecha_desde: '',
    fecha_hasta: '',
    ordenar_por: 'fecha',
    orden: 'desc'
  })

  // Cargar auditorÃ­a cuando cambian los filtros o la pÃ¡gina
  useEffect(() => {
    cargarAuditoria()
    // Actualizar estadÃ­sticas cuando se recarga la lista
    cargarEstadisticas()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, filtros.usuario_email, filtros.modulo, filtros.accion, filtros.fecha_desde, filtros.fecha_hasta, filtros.ordenar_por, filtros.orden])

  // Cargar estadÃ­sticas al montar y luego con polling mÃ¡s frecuente
  useEffect(() => {
    cargarEstadisticas()

    const interval = setInterval(() => {
      cargarEstadisticas()
    }, 5 * 60 * 1000) // 5 minutos (actualizado desde 30 minutos)

    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cargarAuditoria = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        usuario_email: filtros.usuario_email,
        modulo: filtros.modulo === 'ALL' ? '' : filtros.modulo,
        accion: filtros.accion === 'ALL' ? '' : filtros.accion,
        fecha_desde: filtros.fecha_desde || undefined,
        fecha_hasta: filtros.fecha_hasta || undefined,
        ordenar_por: filtros.ordenar_por,
        orden: filtros.orden
      }

      console.log('ðŸ“¡ Llamando a API: /api/v1/auditoria con params:', params)
      const response = await auditoriaService.listarAuditoria(params)
      console.log('âœ… Respuesta API:', response)
      console.log('ðŸ“Š Items recibidos:', response.items?.length || 0, 'Total:', response.total)

      if (response.items && response.items.length > 0) {
        setAuditorias(response.items)
        setTotal(response.total)
      } else {
        setAuditorias([])
        setTotal(response.total || 0)
        if (response.total === 0) {
          console.warn('âš ï¸ No hay registros de auditorÃ­a en la base de datos')
        }
      }
    } catch (err: any) {
      console.error('âŒ Error API:', err)
      const errorMessage = err?.response?.data?.detail || err?.message || 'Error al cargar auditorÃ­a'
      setError(errorMessage)
      toast.error(`Error al cargar auditorÃ­a: ${errorMessage}`)
      setAuditorias([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  const cargarEstadisticas = async (mostrarToast = false) => {
    try {
      console.log('ðŸ“Š Cargando estadÃ­sticas de auditorÃ­a...')
      const response = await auditoriaService.obtenerEstadisticas()
      console.log('âœ… EstadÃ­sticas recibidas:', response)
      setStats(response)
      if (mostrarToast) {
        toast.success('âœ… KPIs actualizados correctamente')
      }
    } catch (err: any) {
      console.error('âŒ Error cargando estadÃ­sticas:', err)
      const errorMessage = err?.response?.data?.detail || err?.message || 'Error al cargar estadÃ­sticas'
      console.error('âŒ Detalles del error:', errorMessage)
      // Establecer valores por defecto en caso de error
      setStats({
        total_acciones: 0,
        acciones_por_modulo: {},
        acciones_por_usuario: {},
        acciones_hoy: 0,
        acciones_esta_semana: 0,
        acciones_este_mes: 0,
      })
      if (mostrarToast) {
        toast.error(`Error al actualizar KPIs: ${errorMessage}`)
      }
    }
  }

  const handleFiltrar = () => {
    setCurrentPage(1)
    cargarAuditoria()
  }

  const handleLimpiarFiltros = () => {
    setFiltros({
      usuario_email: '',
      modulo: 'ALL',
      accion: 'ALL',
      fecha_desde: '',
      fecha_hasta: '',
      ordenar_por: 'fecha',
      orden: 'desc'
    })
    setCurrentPage(1)
  }

  const handleExportarExcel = async () => {
    try {
      const paramsExport = {
        usuario_email: filtros.usuario_email || undefined,
        modulo: filtros.modulo === 'ALL' ? undefined : filtros.modulo,
        accion: filtros.accion === 'ALL' ? undefined : filtros.accion,
        fecha_desde: filtros.fecha_desde || undefined,
        fecha_hasta: filtros.fecha_hasta || undefined,
      }
      await auditoriaService.descargarExcel(paramsExport)
      toast.success('âœ… AuditorÃ­a exportada exitosamente')
    } catch (err) {
      toast.error('âŒ Error al exportar auditorÃ­a')
      console.error('Error:', err)
    }
  }

  const getAccionBadgeColor = (accion: string) => {
    const colors: any = {
      'CREAR': 'bg-green-600',
      'ACTUALIZAR': 'bg-blue-600',
      'ELIMINAR': 'bg-red-600',
      'LOGIN': 'bg-purple-600',
      'LOGOUT': 'bg-gray-600',
      'APROBAR': 'bg-green-600',
      'RECHAZAR': 'bg-red-600',
      'ACTIVAR': 'bg-green-600',
      'DESACTIVAR': 'bg-red-600',
    }
    return colors[accion] || 'bg-gray-600'
  }

  const getModuloBadgeColor = (modulo: string) => {
    const colors: any = {
      'USUARIOS': 'bg-red-600',
      'CLIENTES': 'bg-blue-600',
      'PRESTAMOS': 'bg-green-600',
      'PAGOS': 'bg-yellow-600',
      'AUDITORIA': 'bg-purple-600',
      'CONFIGURACION': 'bg-gray-600',
    }
    return colors[modulo] || 'bg-gray-600'
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AuditorÃ­a del Sistema</h1>
          <p className="text-gray-500 mt-1">
            Seguimiento completo de todas las acciones realizadas
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => cargarEstadisticas(true)}
            variant="outline"
            disabled={loading}
            title="Actualizar estadÃ­sticas"
          >
            <Activity className="w-4 h-4 mr-2" />
            Actualizar KPIs
          </Button>
          <Button onClick={handleExportarExcel} className="bg-green-600 hover:bg-green-700">
            <Download className="w-4 h-4 mr-2" />
            Exportar Excel
          </Button>
        </div>
      </div>

      {/* Stats Dashboard */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Acciones</p>
                <p className="text-2xl font-bold">
                  {stats ? stats.total_acciones.toLocaleString() : '0'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Registros histÃ³ricos
                </p>
              </div>
              <Activity className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Hoy</p>
                <p className="text-2xl font-bold text-green-600">
                  {stats ? stats.acciones_hoy.toLocaleString() : '0'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Acciones realizadas
                </p>
              </div>
              <Calendar className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Esta Semana</p>
                <p className="text-2xl font-bold text-blue-600">
                  {stats ? stats.acciones_esta_semana.toLocaleString() : '0'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Ãšltimos 7 dÃ­as
                </p>
              </div>
              <BarChart3 className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Este Mes</p>
                <p className="text-2xl font-bold text-purple-600">
                  {stats ? stats.acciones_este_mes.toLocaleString() : '0'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Ãšltimos 30 dÃ­as
                </p>
              </div>
              <Shield className="w-8 h-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Filter className="w-5 h-5 mr-2" />
            Filtros de BÃºsqueda
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-sm font-medium mb-1">Email Usuario</label>
              <Input
                placeholder="Buscar por email..."
                value={filtros.usuario_email}
                onChange={(e) => setFiltros({ ...filtros, usuario_email: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">MÃ³dulo</label>
              <Select value={filtros.modulo} onValueChange={(value) => setFiltros({ ...filtros, modulo: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar mÃ³dulo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Todos los mÃ³dulos</SelectItem>
                  <SelectItem value="USUARIOS">Usuarios</SelectItem>
                  <SelectItem value="CLIENTES">Clientes</SelectItem>
                  <SelectItem value="PRESTAMOS">PrÃ©stamos</SelectItem>
                  <SelectItem value="PAGOS">Pagos</SelectItem>
                  <SelectItem value="COBRANZAS">Cobranzas</SelectItem>
                  <SelectItem value="REPORTES">Reportes</SelectItem>
                  <SelectItem value="AUDITORIA">AuditorÃ­a</SelectItem>
                  <SelectItem value="CONFIGURACION">ConfiguraciÃ³n</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">AcciÃ³n</label>
              <Select value={filtros.accion} onValueChange={(value) => setFiltros({ ...filtros, accion: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar acciÃ³n" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Todas las acciones</SelectItem>
                  <SelectItem value="CREAR">Crear</SelectItem>
                  <SelectItem value="ACTUALIZAR">Actualizar</SelectItem>
                  <SelectItem value="ELIMINAR">Eliminar</SelectItem>
                  <SelectItem value="LOGIN">Login</SelectItem>
                  <SelectItem value="LOGOUT">Logout</SelectItem>
                  <SelectItem value="APROBAR">Aprobar</SelectItem>
                  <SelectItem value="RECHAZAR">Rechazar</SelectItem>
                  <SelectItem value="ACTIVAR">Activar</SelectItem>
                  <SelectItem value="DESACTIVAR">Desactivar</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 mt-4">
            <div>
              <label className="block text-sm font-medium mb-1">Fecha Desde</label>
              <Input
                type="date"
                value={filtros.fecha_desde}
                onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Fecha Hasta</label>
              <Input
                type="date"
                value={filtros.fecha_hasta}
                onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })}
              />
            </div>
          </div>

          <div className="flex gap-2 mt-4">
            <Button onClick={handleFiltrar}>
              <Search className="w-4 h-4 mr-2" />
              Filtrar
            </Button>
            <Button variant="outline" onClick={handleLimpiarFiltros}>
              Limpiar Filtros
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardContent className="pt-6">
          <Table className="[&_table]:table-fixed">
            <TableHeader>
              <TableRow>
                <TableHead className="w-[180px]">Email Usuario</TableHead>
                <TableHead className="w-[120px]">AcciÃ³n</TableHead>
                <TableHead className="w-[120px]">MÃ³dulo</TableHead>
                <TableHead className="w-[140px]">Campo</TableHead>
                <TableHead className="min-w-[200px]">DescripciÃ³n</TableHead>
                <TableHead className="w-[110px]">Resultado</TableHead>
                <TableHead className="w-[160px]">Fecha</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    <p className="text-gray-500">Cargando auditorÃ­a...</p>
                  </TableCell>
                </TableRow>
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-red-500">{error}</p>
                    <Button onClick={cargarAuditoria} className="mt-2">
                      Reintentar
                    </Button>
                  </TableCell>
                </TableRow>
              ) : auditorias.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-gray-500">No se encontraron registros de auditorÃ­a</p>
                  </TableCell>
                </TableRow>
              ) : (
                auditorias.map((auditoria) => (
                  <TableRow key={auditoria.id}>
                    <TableCell className="w-[180px]">
                      <div className="flex items-center text-sm">
                        <User className="w-3 h-3 mr-1 text-gray-400 flex-shrink-0" />
                        <span className="truncate">{auditoria.usuario_email || 'N/A'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="w-[120px]">
                      <Badge className={getAccionBadgeColor(auditoria.accion)}>
                        {auditoria.accion}
                      </Badge>
                    </TableCell>
                    <TableCell className="w-[120px]">
                      <Badge className={getModuloBadgeColor(auditoria.modulo)}>
                        {auditoria.modulo}
                      </Badge>
                    </TableCell>
                    <TableCell className="w-[140px] text-sm text-gray-600 font-medium">
                      <span className="truncate block">{auditoria.campo || '-'}</span>
                    </TableCell>
                    <TableCell className="min-w-[200px] text-sm text-gray-600">
                      <span className="line-clamp-2">{auditoria.descripcion || `${auditoria.accion} en ${auditoria.modulo}${auditoria.registro_id ? ` #${auditoria.registro_id}` : ''}`}</span>
                    </TableCell>
                    <TableCell className="w-[110px]">
                      <Badge className={auditoria.resultado === 'EXITOSO' ? 'bg-green-600' : 'bg-red-600'}>
                        {auditoria.resultado}
                      </Badge>
                    </TableCell>
                    <TableCell className="w-[160px] text-sm text-gray-600 whitespace-nowrap">
                      {new Date(auditoria.fecha).toLocaleString('es-VE', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          {/* PaginaciÃ³n */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-gray-500">
                Mostrando {((currentPage - 1) * pageSize) + 1} a {Math.min(currentPage * pageSize, total)} de {total} registros
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  Anterior
                </Button>
                <span className="px-3 py-1 text-sm">
                  PÃ¡gina {currentPage} de {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
