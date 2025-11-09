import { useEffect, useMemo, useRef, useState } from 'react'
import { notificacionService, NotificacionPlantilla, NotificacionVariable } from '@/services/notificacionService'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { Tabs } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import toast from 'react-hot-toast'
import { Upload, Search, FileText, Database, ChevronDown, ChevronUp } from 'lucide-react'

type EditorFocus = 'asunto' | 'encabezado' | 'cuerpo' | 'firma'

interface PlantillasNotificacionesProps {
  plantillaInicial?: NotificacionPlantilla | null
  onPlantillaCargada?: () => void
}

export function PlantillasNotificaciones({ plantillaInicial, onPlantillaCargada }: PlantillasNotificacionesProps = {}) {
  const [plantillas, setPlantillas] = useState<NotificacionPlantilla[]>([])
  const [plantillasFiltradas, setPlantillasFiltradas] = useState<NotificacionPlantilla[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<NotificacionPlantilla | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [filtroTipo, setFiltroTipo] = useState('')
  const [filtroActiva, setFiltroActiva] = useState<boolean | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState('') // Mantener para compatibilidad con edición individual
  const [tiposSeleccionados, setTiposSeleccionados] = useState<string[]>([]) // Para creación múltiple
  const [activa, setActiva] = useState(true)
  const [asunto, setAsunto] = useState('')
  const [encabezado, setEncabezado] = useState('')
  const [cuerpo, setCuerpo] = useState('')
  const [firma, setFirma] = useState('')
  const [variable, setVariable] = useState('')
  const [focus, setFocus] = useState<EditorFocus>('cuerpo')
  const [variablesConfiguradas, setVariablesConfiguradas] = useState<NotificacionVariable[]>([])
  const [mostrarVariables, setMostrarVariables] = useState(true) // Por defecto visible
  const [busquedaVariable, setBusquedaVariable] = useState('')
  const [filtroTablaVariable, setFiltroTablaVariable] = useState<string>('') // Filtro por tabla
  const asuntoRef = useRef<HTMLTextAreaElement | HTMLInputElement>(null)
  const encRef = useRef<HTMLTextAreaElement>(null)
  const cuerpoRef = useRef<HTMLTextAreaElement>(null)
  const firmaRef = useRef<HTMLTextAreaElement>(null)

  const cuerpoFinal = useMemo(() => {
    const parts = [encabezado, cuerpo, firma].filter(Boolean)
    return parts.join('\n\n')
  }, [encabezado, cuerpo, firma])

  const variablesSugeridas = [
    'nombre', 'monto', 'fecha_vencimiento', 'numero_cuota', 'credito_id', 'cedula', 'dias_atraso'
  ]

  // Tipos organizados por categorías
  const tiposPorCategoria = {
    antes: [
      { valor: 'PAGO_5_DIAS_ANTES', label: '5 días antes' },
      { valor: 'PAGO_3_DIAS_ANTES', label: '3 días antes' },
      { valor: 'PAGO_1_DIA_ANTES', label: '1 día antes' },
    ],
    diaPago: [
      { valor: 'PAGO_DIA_0', label: 'Día de pago' },
    ],
    retraso: [
      { valor: 'PAGO_1_DIA_ATRASADO', label: '1 día de retraso' },
      { valor: 'PAGO_3_DIAS_ATRASADO', label: '3 días de retraso' },
      { valor: 'PAGO_5_DIAS_ATRASADO', label: '5 días de retraso' },
    ],
    prejudicial: [
      { valor: 'PREJUDICIAL', label: 'Prejudicial' },
    ],
  }

  const tiposSugeridos = [
    'PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES', 'PAGO_DIA_0', 
    'PAGO_1_DIA_ATRASADO', 'PAGO_3_DIAS_ATRASADO', 'PAGO_5_DIAS_ATRASADO', 'PREJUDICIAL'
  ]

  const todosLosTipos = [
    ...tiposPorCategoria.antes,
    ...tiposPorCategoria.diaPago,
    ...tiposPorCategoria.retraso,
    ...tiposPorCategoria.prejudicial,
  ]

  const cargar = async () => {
    setLoading(true)
    try {
      const data = await notificacionService.listarPlantillas(undefined, false)
      setPlantillas(data)
      setPlantillasFiltradas(data)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al cargar plantillas')
    } finally {
      setLoading(false)
    }
  }

  const cargarVariables = async () => {
    try {
      const vars = await notificacionService.listarVariables(true) // Solo variables activas
      setVariablesConfiguradas(vars || [])
    } catch (error: any) {
      // Si falla, usar lista vacía (puede que no exista el endpoint aún)
      setVariablesConfiguradas([])
    }
  }

  useEffect(() => {
    cargar()
    cargarVariables()
  }, [])

  // Cargar plantilla inicial si se proporciona (para edición desde Resumen)
  useEffect(() => {
    if (plantillaInicial && plantillas.length > 0) {
      // Buscar la plantilla en la lista cargada para asegurar que esté actualizada
      const plantillaEncontrada = plantillas.find(p => p.id === plantillaInicial.id)
      const plantillaACargar = plantillaEncontrada || plantillaInicial
      
      setSelected(plantillaACargar)
      setNombre(plantillaACargar.nombre)
      setTipo(plantillaACargar.tipo)
      setTiposSeleccionados([plantillaACargar.tipo])
      setActiva(Boolean(plantillaACargar.activa))
      setAsunto(plantillaACargar.asunto)
      setEncabezado('')
      setCuerpo(plantillaACargar.cuerpo)
      setFirma('')
      
      // Notificar que la plantilla fue cargada
      if (onPlantillaCargada) {
        onPlantillaCargada()
      }
    }
  }, [plantillaInicial, plantillas, onPlantillaCargada])

  // Filtrar plantillas
  useEffect(() => {
    let filtradas = [...plantillas]
    
    if (busqueda) {
      filtradas = filtradas.filter(p => 
        p.nombre.toLowerCase().includes(busqueda.toLowerCase()) ||
        p.tipo.toLowerCase().includes(busqueda.toLowerCase()) ||
        p.asunto?.toLowerCase().includes(busqueda.toLowerCase())
      )
    }
    
    if (filtroTipo) {
      filtradas = filtradas.filter(p => p.tipo === filtroTipo)
    }
    
    if (filtroActiva !== null) {
      filtradas = filtradas.filter(p => Boolean(p.activa) === filtroActiva)
    }
    
    setPlantillasFiltradas(filtradas)
  }, [plantillas, busqueda, filtroTipo, filtroActiva])

  const limpiar = () => {
    setSelected(null)
    setNombre('')
    setTipo('')
    setTiposSeleccionados([])
    setActiva(true)
    setAsunto('')
    setEncabezado('')
    setCuerpo('')
    setFirma('')
  }

  const seleccionar = (p: NotificacionPlantilla) => {
    setSelected(p)
    setNombre(p.nombre)
    setTipo(p.tipo)
    setTiposSeleccionados([p.tipo]) // Al editar, solo un tipo
    setActiva(Boolean(p.activa))
    setAsunto(p.asunto)
    setEncabezado('')
    setCuerpo(p.cuerpo)
    setFirma('')
  }

  const toggleTipo = (tipoValor: string) => {
    setTiposSeleccionados(prev => {
      if (prev.includes(tipoValor)) {
        return prev.filter(t => t !== tipoValor)
      } else {
        return [...prev, tipoValor]
      }
    })
  }

  const seleccionarTodos = () => {
    setTiposSeleccionados(todosLosTipos.map(t => t.valor))
  }

  const deseleccionarTodos = () => {
    setTiposSeleccionados([])
  }

  const insertarVariable = (nombreVariable?: string) => {
    const varName = nombreVariable || variable
    if (!varName) return
    const token = `{{${varName}}}`
    const insertInto = (el: HTMLTextAreaElement | HTMLInputElement | null, setter: (v: string) => void, current: string) => {
      if (!el) {
        setter(current + token)
        return
      }
      const start = (el as any).selectionStart ?? current.length
      const end = (el as any).selectionEnd ?? current.length
      const next = current.slice(0, start) + token + current.slice(end)
      setter(next)
      setTimeout(() => {
        try {
          (el as any).focus()
          ;(el as any).setSelectionRange(start + token.length, start + token.length)
        } catch {}
      }, 0)
    }

    if (focus === 'asunto') return insertInto(asuntoRef.current, setAsunto, asunto)
    if (focus === 'encabezado') return insertInto(encRef.current, setEncabezado, encabezado)
    if (focus === 'cuerpo') return insertInto(cuerpoRef.current, setCuerpo, cuerpo)
    if (focus === 'firma') return insertInto(firmaRef.current, setFirma, firma)
  }

  const variablesFiltradas = useMemo(() => {
    let filtradas = variablesConfiguradas
    
    // Filtrar por tabla
    if (filtroTablaVariable) {
      filtradas = filtradas.filter(v => v.tabla === filtroTablaVariable)
    }
    
    // Filtrar por búsqueda
    if (busquedaVariable) {
      filtradas = filtradas.filter(v => 
        v.nombre_variable.toLowerCase().includes(busquedaVariable.toLowerCase()) ||
        (v.descripcion ?? '').toLowerCase().includes(busquedaVariable.toLowerCase()) ||
        v.tabla.toLowerCase().includes(busquedaVariable.toLowerCase()) ||
        v.campo_bd.toLowerCase().includes(busquedaVariable.toLowerCase())
      )
    }
    
    return filtradas
  }, [variablesConfiguradas, busquedaVariable, filtroTablaVariable])
  
  // Agrupar variables por tabla
  const variablesPorTabla = useMemo(() => {
    const agrupadas: Record<string, NotificacionVariable[]> = {}
    variablesFiltradas.forEach(v => {
      if (!agrupadas[v.tabla]) {
        agrupadas[v.tabla] = []
      }
      agrupadas[v.tabla].push(v)
    })
    return agrupadas
  }, [variablesFiltradas])
  
  // Obtener tablas únicas
  const tablasUnicas = useMemo(() => {
    return Array.from(new Set(variablesConfiguradas.map(v => v.tabla))).sort()
  }, [variablesConfiguradas])


  const aplicarFormato = (tag: 'b' | 'i' | 'u' | 'ul' | 'a') => {
    const wrap = (el: HTMLTextAreaElement | null, setter: (v: string) => void, current: string) => {
      if (!el) return
      const start = el.selectionStart ?? 0
      const end = el.selectionEnd ?? 0
      const selected = current.slice(start, end)
      let before = '', after = ''
      if (tag === 'a') {
        before = '<a href="https://">'
        after = '</a>'
      } else if (tag === 'ul') {
        const lines = selected || 'Elemento 1\nElemento 2'
        const wrapped = lines.split('\n').map(l => `<li>${l || 'Elemento'}</li>`).join('\n')
        const next = current.slice(0, start) + `<ul>\n${wrapped}\n</ul>` + current.slice(end)
        setter(next)
        return
      } else {
        before = `<${tag}>`
        after = `</${tag}>`
      }
      const next = current.slice(0, start) + before + (selected || 'texto') + after + current.slice(end)
      setter(next)
      setTimeout(() => {
        try { el.focus() } catch {}
      }, 0)
    }
    if (focus === 'encabezado') return wrap(encRef.current, setEncabezado, encabezado)
    if (focus === 'cuerpo') return wrap(cuerpoRef.current, setCuerpo, cuerpo)
    if (focus === 'firma') return wrap(firmaRef.current, setFirma, firma)
    if (focus === 'asunto') return // no aplicar html al asunto
  }

  const validarObligatorias = (tipoValidar?: string): string | null => {
    const tipoAValidar = tipoValidar || tipo
    if (!tipoAValidar) return null
    
    // Reglas básicas por tipo
    const requeridasPorTipo: Record<string, string[]> = {
      'PAGO_5_DIAS_ANTES': ['nombre', 'monto', 'fecha_vencimiento'],
      'PAGO_3_DIAS_ANTES': ['nombre', 'monto', 'fecha_vencimiento'],
      'PAGO_1_DIA_ANTES': ['nombre', 'monto', 'fecha_vencimiento'],
      'PAGO_DIA_0': ['nombre', 'monto', 'fecha_vencimiento'],
      'PAGO_1_DIA_ATRASADO': ['nombre', 'monto', 'fecha_vencimiento', 'dias_atraso'],
      'PAGO_3_DIAS_ATRASADO': ['nombre', 'monto', 'fecha_vencimiento', 'dias_atraso'],
      'PAGO_5_DIAS_ATRASADO': ['nombre', 'monto', 'fecha_vencimiento', 'dias_atraso'],
      'PREJUDICIAL': ['nombre', 'monto', 'fecha_vencimiento', 'dias_atraso'],
    }
    const requeridas = requeridasPorTipo[tipoAValidar] || []
    const faltantes = requeridas.filter(v => !(`${asunto} ${cuerpoFinal}`).includes(`{{${v}}}`))
    if (faltantes.length) return `Para ${tipoAValidar} faltan variables obligatorias: ${faltantes.join(', ')}`
    return null
  }

  const guardar = async () => {
    // Si estamos editando una plantilla existente, guardar solo esa
    if (selected?.id) {
      const error = validarObligatorias()
      if (error) {
        toast.error(error)
        return
      }

      if (!nombre.trim() || !tipo || !asunto.trim() || !cuerpoFinal.trim()) {
        toast.error('Complete todos los campos obligatorios')
        return
      }

      try {
        const payload = {
          nombre,
          tipo,
          asunto,
          cuerpo: cuerpoFinal,
          activa,
        }

        await notificacionService.actualizarPlantilla(selected.id, payload)
        toast.success('Plantilla actualizada exitosamente')
        await cargar()
        limpiar()
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || 'Error al guardar plantilla')
      }
      return
    }

    // Si estamos creando nuevas plantillas, validar tipos seleccionados
    if (tiposSeleccionados.length === 0) {
      toast.error('Seleccione al menos un tipo de notificación')
      return
    }

    if (!nombre.trim() || !asunto.trim() || !cuerpoFinal.trim()) {
      toast.error('Complete todos los campos obligatorios')
      return
    }

    // Validar variables obligatorias para cada tipo
    const errores: string[] = []
    tiposSeleccionados.forEach(t => {
      const error = validarObligatorias(t)
      if (error) errores.push(error)
    })

    if (errores.length > 0) {
      toast.error(errores[0]) // Mostrar solo el primer error
      return
    }

    try {
      // Crear una plantilla para cada tipo seleccionado
      const plantillasCreadas: string[] = []
      const erroresCreacion: string[] = []

      for (const tipoSeleccionado of tiposSeleccionados) {
        try {
          const nombrePlantilla = `${nombre} - ${todosLosTipos.find(t => t.valor === tipoSeleccionado)?.label || tipoSeleccionado}`
          
          const payload = {
            nombre: nombrePlantilla,
            tipo: tipoSeleccionado,
            asunto,
            cuerpo: cuerpoFinal,
            activa,
          }

          await notificacionService.crearPlantilla(payload)
          plantillasCreadas.push(tipoSeleccionado)
        } catch (error: any) {
          erroresCreacion.push(`${tipoSeleccionado}: ${error?.response?.data?.detail || 'Error'}`)
        }
      }

      if (plantillasCreadas.length > 0) {
        toast.success(`Se crearon ${plantillasCreadas.length} plantilla(s) exitosamente`)
      }

      if (erroresCreacion.length > 0) {
        toast.error(`Errores al crear algunas plantillas: ${erroresCreacion.join(', ')}`)
      }

      await cargar()
      limpiar()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al guardar plantillas')
    }
  }

  const eliminar = async () => {
    if (!selected?.id) {
      toast.error('Seleccione una plantilla para eliminar')
      return
    }
    
    if (!window.confirm(`¿Eliminar plantilla "${selected.nombre}"?`)) return
    
    try {
      await notificacionService.eliminarPlantilla(selected.id)
      toast.success('Plantilla eliminada exitosamente')
      limpiar()
      await cargar()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al eliminar plantilla')
    }
  }

  const exportar = async () => {
    if (!selected?.id) {
      toast.error('Seleccione una plantilla para exportar')
      return
    }
    
    try {
      const data = await notificacionService.exportarPlantilla(selected.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `plantilla_${selected.nombre.replace(/[^a-z0-9]/gi, '_')}.json`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Plantilla exportada exitosamente')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al exportar plantilla')
    }
  }

  const importar = () => {
    fileInputRef.current?.click()
  }

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const data = JSON.parse(text)
      
      if (!data.nombre || !data.tipo || !data.asunto || !data.cuerpo) {
        toast.error('Archivo JSON inválido: faltan campos obligatorios')
        return
      }

      setNombre(data.nombre)
      setTipo(data.tipo)
      setAsunto(data.asunto)
      setCuerpo(data.cuerpo || '')
      setEncabezado('')
      setFirma('')
      setActiva(Boolean(data.activa))
      setSelected(null)
      
      toast.success('Plantilla importada. Revise y guarde cuando esté lista.')
    } catch (error: any) {
      toast.error('Error al leer el archivo JSON: ' + (error.message || 'Formato inválido'))
    }
    
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }


  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Plantillas</h2>
          <div className="flex gap-2">
            <Button onClick={importar} variant="outline" size="sm" title="Importar plantilla">
              <Upload className="h-4 w-4" />
            </Button>
            <input ref={fileInputRef} type="file" accept=".json" onChange={handleImportFile} className="hidden" />
            <Button onClick={limpiar} variant="secondary" size="sm">Nueva</Button>
          </div>
        </div>
        
        {/* Búsqueda y filtros */}
        <div className="space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input 
              value={busqueda} 
              onChange={e => setBusqueda(e.target.value)}
              placeholder="Buscar plantillas..." 
              className="pl-10"
            />
          </div>
          <div className="flex gap-2">
            <select 
              value={filtroTipo} 
              onChange={e => setFiltroTipo(e.target.value)}
              className="flex-1 border rounded px-2 py-1 text-sm"
            >
              <option value="">Todos los tipos</option>
              {tiposSugeridos.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select 
              value={filtroActiva === null ? '' : String(filtroActiva)} 
              onChange={e => setFiltroActiva(e.target.value === '' ? null : e.target.value === 'true')}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="">Todas</option>
              <option value="true">Solo activas</option>
              <option value="false">Solo inactivas</option>
            </select>
          </div>
        </div>

        <div className="border rounded-lg divide-y max-h-[60vh] overflow-auto">
          {loading && <div className="p-3 text-sm text-gray-500">Cargando...</div>}
          {!loading && plantillasFiltradas.length === 0 && (
            <div className="p-3 text-sm text-gray-500 text-center">
              {busqueda || filtroTipo || filtroActiva !== null 
                ? 'No se encontraron plantillas con los filtros seleccionados'
                : 'No hay plantillas. Cree una nueva.'}
            </div>
          )}
          {!loading && plantillasFiltradas.map(p => (
            <button key={p.id} onClick={() => seleccionar(p)} className={`w-full text-left p-3 hover:bg-gray-50 ${selected?.id===p.id?'bg-gray-50':''}`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{p.nombre}</div>
                  <div className="text-xs text-gray-500">{p.tipo}</div>
                </div>
                {p.activa ? <Badge variant="success">Activa</Badge> : <Badge variant="secondary">Inactiva</Badge>}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="col-span-8 space-y-4">
        <Card className="p-4 space-y-3">
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="text-sm text-gray-600">Nombre</label>
              <Input value={nombre} onChange={e=>setNombre(e.target.value)} placeholder="Recordatorio de pago" />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-2 block">
                Tipos de Notificación {selected ? '(Edición - Solo un tipo)' : '(Seleccione uno o más para crear múltiples plantillas)'}
              </label>
              
              {selected ? (
                // Al editar, mostrar solo el tipo actual
                <select value={tipo} onChange={e=>setTipo(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                  <option value="">Seleccione...</option>
                  {tiposSugeridos.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              ) : (
                // Al crear, mostrar selector múltiple por categorías
                <div className="border rounded-lg p-4 bg-gray-50 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-600">
                      {tiposSeleccionados.length} tipo(s) seleccionado(s)
                    </span>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={seleccionarTodos}
                        className="text-xs"
                      >
                        Seleccionar todos
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={deseleccionarTodos}
                        className="text-xs"
                      >
                        Deseleccionar todos
                      </Button>
                    </div>
                  </div>

                  {/* Antes de vencimiento */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2 text-blue-700">📅 Antes de Fecha de Vencimiento</h4>
                    <div className="grid grid-cols-3 gap-2">
                      {tiposPorCategoria.antes.map(t => (
                        <label key={t.valor} className="flex items-center gap-2 p-2 border rounded hover:bg-white cursor-pointer">
                          <input
                            type="checkbox"
                            checked={tiposSeleccionados.includes(t.valor)}
                            onChange={() => toggleTipo(t.valor)}
                            className="rounded"
                          />
                          <span className="text-sm">{t.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Día de pago */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2 text-green-700">💰 Día de Pago</h4>
                    <div className="grid grid-cols-3 gap-2">
                      {tiposPorCategoria.diaPago.map(t => (
                        <label key={t.valor} className="flex items-center gap-2 p-2 border rounded hover:bg-white cursor-pointer">
                          <input
                            type="checkbox"
                            checked={tiposSeleccionados.includes(t.valor)}
                            onChange={() => toggleTipo(t.valor)}
                            className="rounded"
                          />
                          <span className="text-sm">{t.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Retraso */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2 text-orange-700">⚠️ Días de Retraso</h4>
                    <div className="grid grid-cols-3 gap-2">
                      {tiposPorCategoria.retraso.map(t => (
                        <label key={t.valor} className="flex items-center gap-2 p-2 border rounded hover:bg-white cursor-pointer">
                          <input
                            type="checkbox"
                            checked={tiposSeleccionados.includes(t.valor)}
                            onChange={() => toggleTipo(t.valor)}
                            className="rounded"
                          />
                          <span className="text-sm">{t.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Prejudicial */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2 text-red-700">🚨 Prejudicial</h4>
                    <div className="grid grid-cols-3 gap-2">
                      {tiposPorCategoria.prejudicial.map(t => (
                        <label key={t.valor} className="flex items-center gap-2 p-2 border rounded hover:bg-white cursor-pointer">
                          <input
                            type="checkbox"
                            checked={tiposSeleccionados.includes(t.valor)}
                            onChange={() => toggleTipo(t.valor)}
                            className="rounded"
                          />
                          <span className="text-sm">{t.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              <input id="activa" type="checkbox" checked={activa} onChange={e=>setActiva(e.target.checked)} />
              <label htmlFor="activa" className="text-sm">Habilitar envío automático a las 3:00 AM</label>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-sm text-gray-600">Asunto</label>
              <Input ref={asuntoRef as any} value={asunto} onFocus={()=>setFocus('asunto')} onChange={e=>setAsunto(e.target.value)} placeholder="Asunto del correo" />
            </div>
            <div className="col-span-2">
              <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">Formato rápido (encabezado/cuerpo/firma):
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('b')}>B</Button>
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('i')}>I</Button>
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('u')}>U</Button>
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('ul')}>Lista</Button>
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('a')}>Enlace</Button>
              </div>
            </div>
            <div>
              <label className="text-sm text-gray-600">Encabezado</label>
              <Textarea ref={encRef} value={encabezado} onFocus={()=>setFocus('encabezado')} onChange={e=>setEncabezado(e.target.value)} rows={4} placeholder="Encabezado" />
            </div>
            <div>
              <label className="text-sm text-gray-600">Firma</label>
              <Textarea ref={firmaRef} value={firma} onFocus={()=>setFocus('firma')} onChange={e=>setFirma(e.target.value)} rows={4} placeholder="Firma" />
            </div>
            <div className="col-span-2">
              <label className="text-sm text-gray-600">Cuerpo</label>
              <Textarea ref={cuerpoRef} value={cuerpo} onFocus={()=>setFocus('cuerpo')} onChange={e=>setCuerpo(e.target.value)} rows={10} placeholder="Contenido principal" />
            </div>
          </div>

          {/* Panel de Variables Configuradas - Mejorado e Intuitivo */}
          <div className="border-2 border-blue-200 rounded-lg p-4 bg-gradient-to-br from-blue-50 to-white shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-blue-600" />
                <label className="text-base font-bold text-gray-800">Banco de Variables</label>
                <Badge variant="outline" className="text-xs bg-blue-100 text-blue-800 border-blue-300">
                  {variablesConfiguradas.length} disponibles
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setMostrarVariables(!mostrarVariables)
                  if (!mostrarVariables) {
                    cargarVariables() // Recargar al abrir
                  }
                }}
                className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
              >
                {mostrarVariables ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>

            {mostrarVariables && (
              <div className="space-y-4">
                {/* Filtros mejorados */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Filtro por tabla */}
                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-1 block">Filtrar por tabla:</label>
                    <select
                      value={filtroTablaVariable}
                      onChange={e => setFiltroTablaVariable(e.target.value)}
                      className="w-full px-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Todas las tablas</option>
                      {tablasUnicas.map(tabla => (
                        <option key={tabla} value={tabla}>{tabla}</option>
                      ))}
                    </select>
                  </div>
                  
                  {/* Búsqueda de variables */}
                  <div className="relative">
                    <label className="text-xs font-semibold text-gray-700 mb-1 block">Buscar variable:</label>
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" style={{ top: '60%' }} />
                    <Input
                      value={busquedaVariable}
                      onChange={e => setBusquedaVariable(e.target.value)}
                      placeholder="Nombre, tabla o campo..."
                      className="pl-10"
                    />
                  </div>
                </div>

                {/* Lista de variables agrupadas por tabla */}
                {variablesConfiguradas.length === 0 ? (
                  <div className="text-center py-8 text-sm text-gray-500 bg-white rounded-lg border-2 border-dashed border-gray-300">
                    <Database className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                    <p className="font-medium">No hay variables configuradas.</p>
                    <p className="text-xs mt-1 text-gray-400">Ve a la pestaña "Genera Variables" para crear variables personalizadas.</p>
                  </div>
                ) : variablesFiltradas.length === 0 ? (
                  <div className="text-center py-8 text-sm text-gray-500 bg-white rounded-lg border-2 border-dashed border-gray-300">
                    <p className="font-medium">No se encontraron variables con ese criterio.</p>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="mt-2"
                      onClick={() => {
                        setBusquedaVariable('')
                        setFiltroTablaVariable('')
                      }}
                    >
                      Limpiar filtros
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                    {Object.entries(variablesPorTabla).map(([tabla, variables]) => (
                      <div key={tabla} className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm">
                        <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-200">
                          <Badge variant="outline" className="text-xs font-semibold bg-gray-100 text-gray-700 border-gray-300">
                            {tabla}
                          </Badge>
                          <span className="text-xs text-gray-500">{variables.length} variable{variables.length !== 1 ? 's' : ''}</span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {variables.map(v => (
                            <div
                              key={v.id || v.nombre_variable}
                              className="group border-2 border-gray-200 rounded-lg p-3 bg-white hover:border-blue-400 hover:shadow-md cursor-pointer transition-all duration-200"
                              onClick={() => insertarVariable(v.nombre_variable)}
                              title={`Click para insertar {{${v.nombre_variable}}} en el campo activo`}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                  {/* Nombre de variable destacado */}
                                  <div className="mb-2">
                                    <code className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-mono font-semibold block w-fit">
                                      {'{{'}{v.nombre_variable}{'}}'}
                                    </code>
                                  </div>
                                  
                                  {/* Mapeo a BD - Destacado */}
                                  <div className="mb-1">
                                    <div className="text-xs text-gray-500 mb-0.5">Mapea a:</div>
                                    <div className="text-xs font-mono text-gray-700 bg-gray-50 px-2 py-1 rounded border border-gray-200">
                                      <span className="font-semibold text-gray-900">{v.tabla}</span>.<span className="text-blue-700">{v.campo_bd}</span>
                                    </div>
                                  </div>
                                  
                                  {/* Descripción si existe */}
                                  {v.descripcion && (
                                    <div className="text-xs text-gray-600 mt-2 italic border-l-2 border-blue-200 pl-2">
                                      {v.descripcion}
                                    </div>
                                  )}
                                </div>
                                
                                {/* Botón de inserción mejorado */}
                                <Button
                                  size="sm"
                                  className="shrink-0 bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    insertarVariable(v.nombre_variable)
                                    toast.success(`Variable {{${v.nombre_variable}}} insertada`, { duration: 1500 })
                                  }}
                                >
                                  +
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Método alternativo: campo de texto para variables rápidas */}
            <div className="mt-3 pt-3 border-t flex items-center gap-2">
              <Input
                value={variable}
                onChange={e => setVariable(e.target.value)}
                placeholder="Escriba nombre de variable..."
                className="max-w-xs"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    insertarVariable()
                  }
                }}
              />
              <Button onClick={() => insertarVariable()} disabled={!variable}>
                Insertar
              </Button>
              <div className="text-xs text-gray-500">
                O escriba manualmente: {variablesSugeridas.slice(0, 3).map(v => `{{${v}}}`).join(', ')}...
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={guardar}>{selected ? 'Actualizar' : 'Guardar'}</Button>
            {selected && <Button variant="destructive" onClick={eliminar}>Eliminar</Button>}
            {selected && (
              <>
                <Button variant="secondary" onClick={exportar} title="Exportar a JSON">
                  <FileText className="h-4 w-4 mr-1" />
                  Exportar
                </Button>
              </>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

export default PlantillasNotificaciones


