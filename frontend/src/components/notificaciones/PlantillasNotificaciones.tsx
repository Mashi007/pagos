import { useEffect, useMemo, useRef, useState } from 'react'
import { notificacionService, NotificacionPlantilla, NotificacionVariable } from '@/services/notificacionService'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { Tabs } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { useSearchClientes } from '@/hooks/useClientes'
import { SearchableSelect } from '@/components/ui/searchable-select'
import toast from 'react-hot-toast'
import { Upload, Search, Eye, EyeOff, FileText, Database, ChevronDown, ChevronUp } from 'lucide-react'

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
  const [mostrarHTML, setMostrarHTML] = useState(true)
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
  const [clienteIdPrueba, setClienteIdPrueba] = useState<number | ''>('')
  const [variablesPrueba, setVariablesPrueba] = useState<Record<string, any>>({})
  const [variablesConfiguradas, setVariablesConfiguradas] = useState<NotificacionVariable[]>([])
  const [mostrarVariables, setMostrarVariables] = useState(false)
  const [busquedaVariable, setBusquedaVariable] = useState('')
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
    if (!busquedaVariable) return variablesConfiguradas
    return variablesConfiguradas.filter(v => 
      v.nombre_variable.toLowerCase().includes(busquedaVariable.toLowerCase()) ||
      v.descripcion?.toLowerCase().includes(busquedaVariable.toLowerCase()) ||
      v.tabla.toLowerCase().includes(busquedaVariable.toLowerCase()) ||
      v.campo_bd.toLowerCase().includes(busquedaVariable.toLowerCase())
    )
  }, [variablesConfiguradas, busquedaVariable])

  // Búsqueda clientes para prueba
  const [queryCliente, setQueryCliente] = useState('')
  const { data: resultadosClientes } = useSearchClientes(queryCliente)

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

  const enviarPrueba = async () => {
    if (!selected?.id && !nombre.trim()) {
      toast.error('Guarde o seleccione una plantilla primero')
      return
    }
    
    if (!clienteIdPrueba) {
      toast.error('Seleccione un cliente de prueba')
      return
    }

    try {
      if (!selected?.id) {
        // Guardar primero si es nueva
        const error = validarObligatorias()
        if (error) {
          toast.error(error)
          return
        }
        const nueva = await notificacionService.crearPlantilla({
          nombre,
          tipo,
          asunto,
          cuerpo: cuerpoFinal,
          activa: false, // No activar automáticamente al probar
        })
        await notificacionService.enviarConPlantilla(nueva.id, { 
          cliente_id: Number(clienteIdPrueba), 
          variables: variablesPrueba 
        })
        await cargar()
      } else {
        await notificacionService.enviarConPlantilla(selected.id, { 
          cliente_id: Number(clienteIdPrueba), 
          variables: variablesPrueba 
        })
      }
      toast.success('Email de prueba enviado exitosamente')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al enviar prueba')
    }
  }

  // Reemplazar variables en vista previa con datos de ejemplo
  const cuerpoPreview = useMemo(() => {
    let preview = cuerpoFinal
    const ejemplos: Record<string, string> = {
      nombre: 'Juan Pérez',
      monto: '500.00',
      fecha_vencimiento: '15/11/2025',
      numero_cuota: '3',
      credito_id: '123',
      cedula: 'V-12345678',
      dias_atraso: '2',
    }
    Object.entries(ejemplos).forEach(([key, val]) => {
      preview = preview.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), val)
    })
    return preview
  }, [cuerpoFinal])

  const asuntoPreview = useMemo(() => {
    let preview = asunto
    const ejemplos: Record<string, string> = {
      nombre: 'Juan Pérez',
      monto: '500.00',
      fecha_vencimiento: '15/11/2025',
      numero_cuota: '3',
      credito_id: '123',
      cedula: 'V-12345678',
      dias_atraso: '2',
    }
    Object.entries(ejemplos).forEach(([key, val]) => {
      preview = preview.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), val)
    })
    return preview
  }, [asunto])

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

          {/* Panel de Variables Configuradas */}
          <div className="border rounded-lg p-4 bg-gray-50">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-blue-600" />
                <label className="text-sm font-semibold">Variables Configuradas</label>
                <Badge variant="outline" className="text-xs">
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
              >
                {mostrarVariables ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>

            {mostrarVariables && (
              <div className="space-y-3">
                {/* Búsqueda de variables */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    value={busquedaVariable}
                    onChange={e => setBusquedaVariable(e.target.value)}
                    placeholder="Buscar variables por nombre, tabla o campo..."
                    className="pl-10"
                  />
                </div>

                {/* Lista de variables */}
                {variablesConfiguradas.length === 0 ? (
                  <div className="text-center py-4 text-sm text-gray-500">
                    <p>No hay variables configuradas.</p>
                    <p className="text-xs mt-1">Ve a la pestaña "Genera Variables" para crear variables personalizadas.</p>
                  </div>
                ) : variablesFiltradas.length === 0 ? (
                  <div className="text-center py-4 text-sm text-gray-500">
                    No se encontraron variables con ese criterio.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                    {variablesFiltradas.map(v => (
                      <div
                        key={v.id || v.nombre_variable}
                        className="border rounded p-2 bg-white hover:bg-gray-50 cursor-pointer transition-colors"
                        onClick={() => insertarVariable(v.nombre_variable)}
                        title={`Click para insertar {{${v.nombre_variable}}}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <code className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs font-mono">
                                {'{{'}{v.nombre_variable}{'}}'}
                              </code>
                              <Badge variant="outline" className="text-xs">{v.tabla}</Badge>
                            </div>
                            <div className="text-xs text-gray-600 truncate" title={v.campo_bd}>
                              <span className="font-mono">{v.tabla}.{v.campo_bd}</span>
                            </div>
                            {v.descripcion && (
                              <div className="text-xs text-gray-500 mt-1 line-clamp-1" title={v.descripcion}>
                                {v.descripcion}
                              </div>
                            )}
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="shrink-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              insertarVariable(v.nombre_variable)
                            }}
                          >
                            Insertar
                          </Button>
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

        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Vista previa</h3>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setMostrarHTML(!mostrarHTML)}
              title={mostrarHTML ? "Ver texto plano" : "Ver HTML renderizado"}
            >
              {mostrarHTML ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
          </div>
          <div className="border rounded p-3 bg-white">
            <div className="text-sm text-gray-600 mb-1">Asunto:</div>
            <div className="font-medium mb-3 text-sm">{asuntoPreview || '(sin asunto)'}</div>
            <hr className="mb-3" />
            {mostrarHTML ? (
              <div 
                className="text-sm prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: cuerpoPreview.replace(/\n/g, '<br>') }}
              />
            ) : (
              <pre className="whitespace-pre-wrap text-sm mt-2">{cuerpoFinal || '(sin contenido)'}</pre>
            )}
          </div>

          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="text-sm text-gray-600">Cliente de prueba</label>
              <SearchableSelect
                value={clienteIdPrueba ? String(clienteIdPrueba) : ''}
                onSearch={setQueryCliente}
                onChange={(val) => setClienteIdPrueba(val ? Number(val) : '')}
                options={(resultadosClientes || []).map((c: any) => ({
                  label: `${c.cedula} - ${c.nombres}`,
                  value: String(c.id ?? c.cliente_id ?? ''),
                }))}
                placeholder="Buscar por cédula o nombre..."
              />
            </div>
            <Button onClick={enviarPrueba}>Enviar prueba</Button>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default PlantillasNotificaciones


