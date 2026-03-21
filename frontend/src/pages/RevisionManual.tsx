import { useState, useEffect, useRef } from 'react'




import { useQuery, useQueryClient } from '@tanstack/react-query'




import { motion } from 'framer-motion'




import { useNavigate, useLocation } from 'react-router-dom'




import {




  Card,




  CardContent,




  CardHeader,




  CardTitle,




} from '../components/ui/card'




import { Button } from '../components/ui/button'




import {




  Loader2,




  Edit,




  AlertCircle,




  RefreshCw,




  Search,




  ChevronLeft,




  ChevronRight,




  Trash2,




} from 'lucide-react'




import { Input } from '../components/ui/input'




import { toast } from 'sonner'




import { revisionManualService } from '../services/revisionManualService'









interface PrestamoRevision {




  prestamo_id: number




  cliente_id: number




  cedula: string




  nombres: string




  total_prestamo: number




  total_abonos: number




  saldo: number




  cuotas_vencidas: number




  cuotas_morosas: number




  estado_revision: string




  fecha_revision: string | null




}









interface ResumenRevision {




  total_prestamos: number




  prestamos_revisados: number




  prestamos_pendientes: number




  porcentaje_completado: number




  prestamos: PrestamoRevision[]




}









const PER_PAGE = 20




const STORAGE_KEY = 'revision-manual-state'









function getStoredState(): { page: number; filtro: 'todos' | 'pendientes' | 'revisados' | 'revisando'; cedulaBuscar: string } {




  try {




    const raw = sessionStorage.getItem(STORAGE_KEY)




    if (!raw) return { page: 1, filtro: 'todos', cedulaBuscar: '' }




    const parsed = JSON.parse(raw)




    const filtros: Array<'todos' | 'pendientes' | 'revisados' | 'revisando'> = ['todos', 'pendientes', 'revisados', 'revisando']




    return {




      page: Math.max(1, Number(parsed.page) || 1),




      filtro: filtros.includes(parsed.filtro) ? parsed.filtro : 'todos',




      cedulaBuscar: typeof parsed.cedulaBuscar === 'string' ? parsed.cedulaBuscar : '',




    }




  } catch {




    return { page: 1, filtro: 'todos', cedulaBuscar: '' }




  }




}









export function RevisionManual() {




  const stored = getStoredState()




  const [filtro, setFiltro] = useState<'todos' | 'pendientes' | 'revisados' | 'revisando'>(stored.filtro)




  const [page, setPage] = useState(stored.page)




  const [cedulaBuscar, setCedulaBuscar] = useState(stored.cedulaBuscar)




  const [cedulaInput, setCedulaInput] = useState(stored.cedulaBuscar) // valor del input (para debounce o submit)




  const [prestamosOcultos, setPrestamosOcultos] = useState<Set<number>>(new Set())




  const timeoutsRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())




  const queryClient = useQueryClient()




  const navigate = useNavigate()




  const location = useLocation()









  // Al volver tras finalizar (Guardar y Cerrar), mostrar "Todos" para que el préstamo finalizado sea visible




  useEffect(() => {




    const state = location.state as { fromFinalize?: boolean } | null




    if (state?.fromFinalize) {




      setFiltro('todos')




      setPage(1)




      navigate(location.pathname, { replace: true, state: {} })




    }




  }, [location.state, location.pathname, navigate])









  // Persistir estado para mantener posición al volver de editar (Guardar y cerrar)




  useEffect(() => {




    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ page, filtro, cedulaBuscar }))




  }, [page, filtro, cedulaBuscar])









  // Limpiar timeouts al desmontar




  useEffect(() => {




    return () => {




      timeoutsRef.current.forEach((t) => clearTimeout(t))




      timeoutsRef.current.clear()




    }




  }, [])









  const programarOcultarEn30s = (prestamoId: number) => {




    const existing = timeoutsRef.current.get(prestamoId)




    if (existing) clearTimeout(existing)




    const t = setTimeout(() => {




      setPrestamosOcultos((prev) => new Set([...prev, prestamoId]))




      timeoutsRef.current.delete(prestamoId)




    }, 30000)




    timeoutsRef.current.set(prestamoId, t)




  }









  const { data, isLoading, error, refetch } = useQuery({




    queryKey: ['revision-manual-prestamos', filtro, page, cedulaBuscar],




    queryFn: () => revisionManualService.getPreslamosRevision(filtro, page, PER_PAGE, cedulaBuscar || undefined),




    staleTime: 15 * 1000,




    refetchOnWindowFocus: true,




  })









  const handleConfirmarSi = async (prestamoId: number, nombres: string) => {




    const confirmar = window.confirm(




      `⚠️ CONFIRMAR REVISIÓN - ${nombres}\n\n` +




      '✓ Se marcarán TODOS los datos como correctos:\n' +




      '  - Datos del cliente\n' +




      '  - Datos del préstamo\n' +




      '  - Cuotas y pagos\n\n' +




      '✓ El préstamo desaparecerá de esta lista\n' +




      '✓ NO PODRÁS EDITAR ESTE PRÉSTAMO DE NUEVO\n\n' +




      '¿Confirmas que todo está correcto?'




    )




    if (!confirmar) {




      toast.info('ℹ️ Confirmación cancelada')




      return




    }









    try {




      const res = await revisionManualService.confirmarPrestamoRevisado(prestamoId)




      toast.success(`✅ ${res.mensaje}`)




      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })




      programarOcultarEn30s(prestamoId)




    } catch (err: any) {




      const errorMsg = err?.response?.data?.detail || 'Error al confirmar'




      toast.error(`❌ ${errorMsg}`)




      console.error('Error confirmando:', err)




    }




  }









  const handleEditarNo = (prestamoId: number) => {




    // Confirmar antes de abrir editor




    const confirmar = window.confirm(




      '⚠️ INICIAR EDICIÓN\n\n' +




      'Al presionar "No", accederás a la interfaz de edición donde podrás:\n' +




      '✓ Editar datos del cliente\n' +




      '✓ Editar datos del préstamo\n' +




      '✓ Editar cuotas y pagos\n\n' +




      '✓ Puedes guardar cambios parciales (Guardar Parciales)\n' +




      '✓ O finalizar la revisión (Guardar y Cerrar)\n\n' +




      '¿Deseas continuar?'




    )




    if (!confirmar) {




      toast.info('ℹ️ Edición cancelada')




      return




    }









    // Inicia revisión (cambia estado a 'revisando')




    revisionManualService.iniciarRevision(prestamoId).then(() => {




      toast.info('ℹ️ Edición iniciada. Abriendo editor...')




      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })




      // Navega a página de edición




      navigate(`/revision-manual/editar/${prestamoId}`)




    }).catch((err: any) => {




      const errorMsg = err?.response?.data?.detail || 'Error al iniciar revisión'




      toast.error(`❌ ${errorMsg}`)




      console.error('Error iniciando revisión:', err)




    })




  }









  const handleEliminar = async (prestamoId: number, nombres: string) => {




    const confirmar = window.confirm(




      `⚠️ ELIMINAR PRÉSTAMO - ${nombres}\n\n` +




      'Esta acción eliminará permanentemente:\n' +




      '  - El préstamo\n' +




      '  - Todas las cuotas asociadas\n' +




      '  - El registro de revisión manual\n\n' +




      '¿Estás seguro de que deseas eliminar?'




    )




    if (!confirmar) {




      toast.info('ℹ️ Eliminación cancelada')




      return




    }









    try {




      await revisionManualService.eliminarPrestamo(prestamoId)




      toast.success('✅ Préstamo eliminado')




      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })




      queryClient.invalidateQueries({ queryKey: ['prestamos'] })




      queryClient.invalidateQueries({ queryKey: ['clientes'] })




      queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })




      queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })




      queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })




    } catch (err: any) {




      const errorMsg = err?.response?.data?.detail || 'Error al eliminar'




      toast.error(`❌ ${errorMsg}`)




      console.error('Error eliminando:', err)




    }




  }









  const datosVisibles = (data?.prestamos?? []).filter(




    (p) => !prestamosOcultos.has(p.prestamo_id)




  )




  const totalPrestamos = data?.total_prestamos?? 0




  const totalPages = Math.ceil(totalPrestamos / PER_PAGE) || 1









  const handleBuscarCedula = () => {




    setCedulaBuscar(cedulaInput.trim())




    setPage(1)




  }









  const handleLimpiarBusqueda = () => {




    setCedulaInput('')




    setCedulaBuscar('')




    setPage(1)




  }









  return (




    <motion.div




      initial={{ opacity: 0, y: 20 }}




      animate={{ opacity: 1, y: 0 }}




      transition={{ duration: 0.3 }}




      className="space-y-6 p-4 sm:p-6"




    >




      {/* Header */}




      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">




        <div className="space-y-1">




          <h1 className="text-3xl font-bold text-gray-900">Revisión Manual de Préstamos</h1>




          <p className="text-sm text-gray-600">




            Verifica y confirma los detalles de cada préstamo post-migración




          </p>




        </div>




        <Button




          variant="outline"




          size="sm"




          onClick={() => {




            refetch()




            toast.info('Actualizando...')




          }}




          disabled={isLoading}




        >




          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />




          Actualizar




        </Button>




      </div>









      {/* Barra de Progreso */}




      {data && (




        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">




          <CardHeader className="pb-3">




            <CardTitle className="text-lg">Progreso de Revisión</CardTitle>




          </CardHeader>




          <CardContent className="space-y-4">




            <div className="flex items-center justify-between">




              <div>




                <p className="text-sm font-medium text-gray-700">




                  {data.prestamos_revisados} de {data.total_prestamos} préstamos revisados




                </p>




                <p className="text-xs text-gray-500 mt-1">




                  Faltan: {data.prestamos_pendientes} préstamos por revisar




                </p>




              </div>




              <div className="text-3xl font-bold text-blue-600">{data.porcentaje_completado}%</div>




            </div>




            {/* Barra gráfica */}




            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">




              <motion.div




                initial={{ width: 0 }}




                animate={{ width: `${data.porcentaje_completado}%` }}




                transition={{ duration: 0.5 }}




                className="bg-gradient-to-r from-blue-500 to-indigo-600 h-full"




              />




            </div>




          </CardContent>




        </Card>




      )}









      {/* Filtros */}




      <div className="flex gap-2 flex-wrap">




        <Button




          variant={filtro === 'todos' ? 'default' : 'outline'}




          size="sm"




          onClick={() => { setFiltro('todos'); setPage(1) }}




        >




          Todos




        </Button>




        <Button




          variant={filtro === 'pendientes' ? 'default' : 'outline'}




          size="sm"




          onClick={() => { setFiltro('pendientes'); setPage(1) }}




        >




          Pendientes ({data?.prestamos_pendientes || 0})




        </Button>




        <Button




          variant={filtro === 'revisando' ? 'default' : 'outline'}




          size="sm"




          onClick={() => { setFiltro('revisando'); setPage(1) }}




        >




          🔄 Revisando




        </Button>




        <Button




          variant={filtro === 'revisados' ? 'default' : 'outline'}




          size="sm"




          onClick={() => { setFiltro('revisados'); setPage(1) }}




        >




          ✓ Revisados ({data?.prestamos_revisados || 0})




        </Button>




      </div>









      {/* Búsqueda por cédula */}




      <Card className="border-blue-100 bg-blue-50/30">




        <CardContent className="pt-4">




          <div className="flex flex-col sm:flex-row gap-3">




            <div className="flex-1 flex gap-2">




              <Search className="h-4 w-4 text-gray-500 self-center shrink-0" />




              <Input




                placeholder="Buscar por cédula para acceder a un caso específico..."




                value={cedulaInput}




                onChange={(e) => setCedulaInput(e.target.value)}




                onKeyDown={(e) => e.key === 'Enter' && handleBuscarCedula()}




                className="max-w-md"




              />




              <Button size="sm" onClick={handleBuscarCedula} disabled={isLoading}>




                Buscar




              </Button>




              {cedulaBuscar && (




                <Button size="sm" variant="ghost" onClick={handleLimpiarBusqueda}>




                  Limpiar




                </Button>




              )}




            </div>




            {cedulaBuscar && (




              <span className="text-sm text-gray-600 self-center">




                Mostrando resultados para cédula: <strong>{cedulaBuscar}</strong>




              </span>




            )}




          </div>




        </CardContent>




      </Card>









      {/* Tabla de Préstamos */}




      <Card>




        <CardHeader>




          <CardTitle className="flex items-center gap-2">




            <AlertCircle className="h-5 w-5" />




            Lista de Préstamos




          </CardTitle>




        </CardHeader>




        <CardContent>




          {isLoading ? (




            <div className="flex justify-center py-12">




              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />




            </div>




          ) : error ? (




            <div className="text-center py-8 text-red-600">




              <p>Error al cargar préstamos</p>




            </div>




          ) : datosVisibles.length === 0 ? (




            <div className="text-center py-8 text-gray-500">




              <p>No hay préstamos para mostrar</p>




            </div>




          ) : (




            <div className="overflow-x-auto">




              <table className="w-full text-sm">




                <thead className="bg-gray-50 border-b">




                  <tr>




                    <th className="px-4 py-2 text-left font-semibold">Nombre</th>




                    <th className="px-4 py-2 text-left font-semibold">Cédula</th>




                    <th className="px-4 py-2 text-right font-semibold">Total Préstamo</th>




                    <th className="px-4 py-2 text-right font-semibold">Total Abonos</th>




                    <th className="px-4 py-2 text-right font-semibold">Saldo</th>




                    <th className="px-4 py-2 text-center font-semibold">Vencidas</th>




                    <th className="px-4 py-2 text-center font-semibold">Morosas</th>




                    <th className="px-4 py-2 text-center font-semibold">Estado</th>




                    <th className="px-4 py-2 text-center font-semibold">Decisión</th>




                  </tr>




                </thead>




                <tbody className="divide-y">




                  {datosVisibles.map((prestamo) => (




                    <motion.tr




                      key={prestamo.prestamo_id}




                      initial={{ opacity: 0 }}




                      animate={{ opacity: 1 }}




                      className="hover:bg-gray-50 transition"




                    >




                      <td className="px-4 py-3 font-medium">{prestamo.nombres}</td>




                      <td className="px-4 py-3 text-gray-600">{prestamo.cedula}</td>




                      <td className="px-4 py-3 text-right font-semibold">




                        ${prestamo.total_prestamo.toLocaleString('es-ES', { maximumFractionDigits: 2 })}




                      </td>




                      <td className="px-4 py-3 text-right text-green-600 font-semibold">




                        ${prestamo.total_abonos.toLocaleString('es-ES', { maximumFractionDigits: 2 })}




                      </td>




                      <td className="px-4 py-3 text-right font-semibold text-orange-600">




                        ${prestamo.saldo.toLocaleString('es-ES', { maximumFractionDigits: 2 })}




                      </td>




                      <td className="px-4 py-3 text-center">




                        <span className={`px-2 py-1 rounded text-xs font-semibold ${prestamo.cuotas_vencidas > 0 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100'}`}>




                          {prestamo.cuotas_vencidas}




                        </span>




                      </td>




                      <td className="px-4 py-3 text-center">




                        <span className={`px-2 py-1 rounded text-xs font-semibold ${prestamo.cuotas_morosas > 0 ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}>




                          {prestamo.cuotas_morosas}




                        </span>




                      </td>




                      <td className="px-4 py-3 text-center">




                        {prestamo.estado_revision === 'revisado' && (




                          <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">✓ Revisado</span>




                        )}




                        {prestamo.estado_revision === 'revisando' && (




                          <span className="px-2 py-1 rounded text-xs font-semibold bg-yellow-100 text-yellow-800">🔄 Revisando</span>




                        )}




                        {prestamo.estado_revision === 'pendiente' && (




                          <span className="px-2 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-800">Pendiente</span>




                        )}




                      </td>




                      <td className="px-4 py-3 text-center">




                        {prestamo.estado_revision === 'pendiente' && (




                          <div className="flex gap-2 justify-center flex-wrap">




                            <Button




                              size="sm"




                              className="bg-green-600 hover:bg-green-700 text-white text-xs h-8 px-2"




                              onClick={() => handleConfirmarSi(prestamo.prestamo_id, prestamo.nombres)}




                            >




                              ✓ Sí




                            </Button>




                            <Button




                              size="sm"




                              className="bg-blue-600 hover:bg-blue-700 text-white text-xs h-8 px-2"




                              onClick={() => handleEditarNo(prestamo.prestamo_id)}




                            >




                              ✎ No




                            </Button>




                            <Button




                              size="sm"




                              variant="outline"




                              className="text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300 text-xs h-8 px-2"




                              onClick={() => handleEliminar(prestamo.prestamo_id, prestamo.nombres)}




                            >




                              <Trash2 className="h-3 w-3 mr-1" />




                              Eliminar




                            </Button>




                          </div>




                        )}




                        {prestamo.estado_revision === 'revisando' && (




                          <div className="flex gap-2 justify-center">




                            <Button




                              size="sm"




                              variant="outline"




                              className="text-blue-600 text-xs h-8"




                              onClick={() => navigate(`/revision-manual/editar/${prestamo.prestamo_id}`)}




                            >




                              <Edit className="h-3 w-3 mr-1" />




                              Continuar




                            </Button>




                            <Button




                              size="sm"




                              variant="outline"




                              className="text-red-600 border-red-200 hover:bg-red-50 text-xs h-8"




                              onClick={() => handleEliminar(prestamo.prestamo_id, prestamo.nombres)}




                            >




                              <Trash2 className="h-3 w-3 mr-1" />




                              Eliminar




                            </Button>




                          </div>




                        )}




                        {prestamo.estado_revision === 'revisado' && (




                          <span className="text-xs text-gray-500">Finalizado</span>




                        )}




                      </td>




                    </motion.tr>




                  ))}




                </tbody>




              </table>




            </div>




          )}









          {/* Paginación */}




          {!isLoading && !error && totalPrestamos > 0 && (




            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-4 pt-4 border-t">




              <p className="text-sm text-gray-600">




                Mostrando <strong>{(page - 1) * PER_PAGE + 1}</strong> -{' '}




                <strong>{Math.min(page * PER_PAGE, totalPrestamos)}</strong> de{' '}




                <strong>{totalPrestamos}</strong> préstamos




              </p>




              <div className="flex gap-2">




                <Button




                  variant="outline"




                  size="sm"




                  onClick={() => setPage((p) => Math.max(1, p - 1))}




                  disabled={page <= 1}




                >




                  <ChevronLeft className="h-4 w-4" />




                  Anterior




                </Button>




                <span className="px-3 py-1.5 text-sm font-medium text-gray-700">




                  Página {page} de {totalPages}




                </span>




                <Button




                  variant="outline"




                  size="sm"




                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}




                  disabled={page >= totalPages}




                >




                  Siguiente




                  <ChevronRight className="h-4 w-4" />




                </Button>




              </div>




            </div>




          )}




        </CardContent>




      </Card>




    </motion.div>




  )




}









export default RevisionManual




