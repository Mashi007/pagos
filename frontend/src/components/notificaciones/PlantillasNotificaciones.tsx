import { useEffect, useMemo, useRef, useState } from 'react'
import { notificacionService, NotificacionPlantilla, NotificacionVariable } from '../../services/notificacionService'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import toast from 'react-hot-toast'
import { Upload, Search, FileText, Database, ChevronDown, ChevronUp, Edit2, Trash2, Calendar, AlertCircle } from 'lucide-react'

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
  const [activeTab, setActiveTab] = useState('armar')
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

  /** Variables que el sistema sustituye al enviar (sin burocracia de tablas/BD). Insertar en asunto/cuerpo. */
  const VARIABLES_NOTIFICACION = [
    { key: 'nombre', label: 'Nombre' },
    { key: 'cedula', label: 'Cédula' },
    { key: 'fecha_vencimiento', label: 'Fecha venc.' },
    { key: 'numero_cuota', label: 'Nº cuota' },
    { key: 'monto', label: 'Monto' },
    { key: 'dias_atraso', label: 'Días atraso' },
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
    mora61: [
      { valor: 'MORA_61', label: '61+ días de mora' },
    ],
  }

  const tiposSugeridos = [
    'PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES', 'PAGO_DIA_0',
    'PAGO_1_DIA_ATRASADO', 'PAGO_3_DIAS_ATRASADO', 'PAGO_5_DIAS_ATRASADO', 'PREJUDICIAL', 'MORA_61'
  ]

  const todosLosTipos = [
    ...tiposPorCategoria.antes,
    ...tiposPorCategoria.diaPago,
    ...tiposPorCategoria.retraso,
    ...tiposPorCategoria.prejudicial,
    ...tiposPorCategoria.mora61,
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

  // Generar variables precargadas desde los campos de las tablas
  const generarVariablesPrecargadas = (): NotificacionVariable[] => {
    const CAMPOS_DISPONIBLES = {
      clientes: [
        { campo: 'id', descripcion: 'ID único del cliente' },
        { campo: 'cedula', descripcion: 'Cédula de identidad' },
        { campo: 'nombres', descripcion: 'Nombres completos' },
        { campo: 'telefono', descripcion: 'Teléfono de contacto' },
        { campo: 'email', descripcion: 'Correo electrónico' },
        { campo: 'direccion', descripcion: 'Dirección de residencia' },
        { campo: 'fecha_nacimiento', descripcion: 'Fecha de nacimiento' },
        { campo: 'ocupacion', descripcion: 'Ocupación del cliente' },
        { campo: 'estado', descripcion: 'Estado (ACTIVO, INACTIVO, FINALIZADO)' },
        { campo: 'activo', descripcion: 'Estado activo (true/false)' },
        { campo: 'fecha_registro', descripcion: 'Fecha de registro' },
        { campo: 'fecha_actualizacion', descripcion: 'Fecha de última actualización' },
        { campo: 'usuario_registro', descripcion: 'Usuario que registró' },
        { campo: 'notas', descripcion: 'Notas adicionales' },
      ],
      prestamos: [
        { campo: 'id', descripcion: 'ID del préstamo' },
        { campo: 'cliente_id', descripcion: 'ID del cliente' },
        { campo: 'cedula', descripcion: 'Cédula del cliente' },
        { campo: 'nombres', descripcion: 'Nombres del cliente' },
        { campo: 'valor_activo', descripcion: 'Valor del activo (vehículo)' },
        { campo: 'total_financiamiento', descripcion: 'Monto total financiado' },
        { campo: 'fecha_requerimiento', descripcion: 'Fecha requerida del préstamo' },
        { campo: 'modalidad_pago', descripcion: 'Modalidad (MENSUAL, QUINCENAL, SEMANAL)' },
        { campo: 'numero_cuotas', descripcion: 'Número total de cuotas' },
        { campo: 'cuota_periodo', descripcion: 'Monto de cuota por período' },
        { campo: 'tasa_interes', descripcion: 'Tasa de interés (%)' },
        { campo: 'fecha_base_calculo', descripcion: 'Fecha base para cálculo' },
        { campo: 'producto', descripcion: 'Producto financiero' },
        { campo: 'concesionario', descripcion: 'Concesionario' },
        { campo: 'analista', descripcion: 'Analista asignado' },
        { campo: 'modelo_vehiculo', descripcion: 'Modelo del vehículo' },
        { campo: 'estado', descripcion: 'Estado del préstamo' },
        { campo: 'usuario_proponente', descripcion: 'Usuario proponente' },
        { campo: 'usuario_aprobador', descripcion: 'Usuario aprobador' },
        { campo: 'fecha_registro', descripcion: 'Fecha de registro' },
        { campo: 'fecha_aprobacion', descripcion: 'Fecha de aprobación' },
      ],
      cuotas: [
        { campo: 'id', descripcion: 'ID de la cuota' },
        { campo: 'prestamo_id', descripcion: 'ID del préstamo' },
        { campo: 'numero_cuota', descripcion: 'Número de cuota' },
        { campo: 'fecha_vencimiento', descripcion: 'Fecha de vencimiento' },
        { campo: 'fecha_pago', descripcion: 'Fecha de pago' },
        { campo: 'monto_cuota', descripcion: 'Monto total de la cuota' },
        { campo: 'monto_capital', descripcion: 'Monto de capital' },
        { campo: 'monto_interes', descripcion: 'Monto de interés' },
        { campo: 'saldo_capital_inicial', descripcion: 'Saldo capital inicial' },
        { campo: 'saldo_capital_final', descripcion: 'Saldo capital final' },
        { campo: 'capital_pagado', descripcion: 'Capital pagado' },
        { campo: 'interes_pagado', descripcion: 'Interés pagado' },
        { campo: 'mora_pagada', descripcion: 'Mora pagada' },
        { campo: 'total_pagado', descripcion: 'Total pagado' },
        { campo: 'capital_pendiente', descripcion: 'Capital pendiente' },
        { campo: 'interes_pendiente', descripcion: 'Interés pendiente' },
        { campo: 'dias_mora', descripcion: 'Días de mora' },
        { campo: 'monto_mora', descripcion: 'Monto de mora' },
        { campo: 'tasa_mora', descripcion: 'Tasa de mora (%)' },
        { campo: 'dias_morosidad', descripcion: 'Días de morosidad' },
        { campo: 'monto_morosidad', descripcion: 'Monto de morosidad' },
        { campo: 'estado', descripcion: 'Estado de la cuota' },
      ],
      pagos: [
        { campo: 'id', descripcion: 'ID del pago' },
        { campo: 'cedula', descripcion: 'Cédula del cliente' },
        { campo: 'prestamo_id', descripcion: 'ID del préstamo' },
        { campo: 'numero_cuota', descripcion: 'Número de cuota' },
        { campo: 'fecha_pago', descripcion: 'Fecha de pago' },
        { campo: 'fecha_registro', descripcion: 'Fecha de registro' },
        { campo: 'monto_pagado', descripcion: 'Monto pagado' },
        { campo: 'numero_documento', descripcion: 'Número de documento' },
        { campo: 'institucion_bancaria', descripcion: 'Institución bancaria' },
        { campo: 'estado', descripcion: 'Estado del pago' },
        { campo: 'conciliado', descripcion: 'Si está conciliado' },
        { campo: 'fecha_conciliacion', descripcion: 'Fecha de conciliación' },
      ],
    }

    const variablesPrecargadas: NotificacionVariable[] = []

    Object.entries(CAMPOS_DISPONIBLES).forEach(([tabla, campos]) => {
      campos.forEach(({ campo, descripcion }) => {
        // Generar nombre de variable: tabla_campo (ej: cliente_nombres, cuota_monto_cuota)
        const nombreVariable = `${tabla.slice(0, tabla.length - 1)}_${campo}` // Remover 's' final

        variablesPrecargadas.push({
          id: undefined, // Variables precargadas no tienen ID
          nombre_variable: nombreVariable,
          tabla: tabla,
          campo_bd: campo,
          descripcion: descripcion,
          activa: true,
        } as NotificacionVariable)
      })
    })

    return variablesPrecargadas
  }

  const cargarVariables = async () => {
    try {
      const vars = await notificacionService.listarVariables(true) // Solo variables activas
      const variablesUsuario = vars || []

      // Generar variables precargadas y combinarlas con las del usuario
      const variablesPrecargadas = generarVariablesPrecargadas()

      // Combinar: las variables del usuario tienen prioridad (por nombre_variable)
      const nombresVariablesUsuario = new Set(variablesUsuario.map(v => v.nombre_variable))
      const variablesPrecargadasFiltradas = variablesPrecargadas.filter(
        v => !nombresVariablesUsuario.has(v.nombre_variable)
      )

      // Combinar ambas listas
      const todasLasVariables = [...variablesUsuario, ...variablesPrecargadasFiltradas]
      setVariablesConfiguradas(todasLasVariables)
    } catch (error: any) {
      // Si falla, usar solo variables precargadas
      const variablesPrecargadas = generarVariablesPrecargadas()
      setVariablesConfiguradas(variablesPrecargadas)
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

      // Cambiar a la pestaña de armar plantilla
      setActiveTab('armar')

      // Notificar que la plantilla fue cargada
      if (onPlantillaCargada) {
        onPlantillaCargada()
      }
    }
  }, [plantillaInicial, plantillas, onPlantillaCargada])

  // Recargar plantillas cuando se cambia a la pestaña de resumen
  useEffect(() => {
    if (activeTab === 'resumen') {
      cargar()
    }
  }, [activeTab])

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
        // Cambiar a la pestaña de resumen después de guardar
        setActiveTab('resumen')
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
        // Cambiar a la pestaña de resumen después de guardar
        setActiveTab('resumen')
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
      setActiveTab('armar')

      toast.success('Plantilla importada. Revise y guarde cuando esté lista.')
    } catch (error: any) {
      toast.error('Error al leer el archivo JSON: ' + (error.message || 'Formato inválido'))
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Funciones para el resumen
  const handleEditarDesdeResumen = (plantilla: NotificacionPlantilla) => {
    seleccionar(plantilla)
    setActiveTab('armar')
  }

  const handleEliminarDesdeResumen = async (plantilla: NotificacionPlantilla) => {
    if (!window.confirm(`¿Está seguro de eliminar la plantilla "${plantilla.nombre}"?`)) {
      return
    }

    try {
      await notificacionService.eliminarPlantilla(plantilla.id)
      toast.success('Plantilla eliminada exitosamente')
      await cargar()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al eliminar plantilla')
    }
  }

  const formatearFecha = (fecha: string | null | undefined) => {
    if (!fecha) return '-'
    try {
      const date = new Date(fecha)
      return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return fecha
    }
  }

  // Mapeo de tipos a categorías y casos (para el resumen)
  const mapeoTipos = {
    'PAGO_5_DIAS_ANTES': { categoria: 'Notificación Previa', caso: '5 días antes' },
    'PAGO_3_DIAS_ANTES': { categoria: 'Notificación Previa', caso: '3 días antes' },
    'PAGO_1_DIA_ANTES': { categoria: 'Notificación Previa', caso: '1 día antes' },
    'PAGO_DIA_0': { categoria: 'Día de Pago', caso: 'Día de pago' },
    'PAGO_1_DIA_ATRASADO': { categoria: 'Notificación Retrasada', caso: '1 día de retraso' },
    'PAGO_3_DIAS_ATRASADO': { categoria: 'Notificación Retrasada', caso: '3 días de retraso' },
    'PAGO_5_DIAS_ATRASADO': { categoria: 'Notificación Retrasada', caso: '5 días de retraso' },
    'PREJUDICIAL': { categoria: 'Prejudicial', caso: 'Prejudicial' },
  }

  const categoriasOrden = [
    { key: 'Notificación Previa', color: 'blue', borderColor: 'border-blue-500', icon: 'ðŸ“…' },
    { key: 'Día de Pago', color: 'green', borderColor: 'border-green-500', icon: 'ðŸ’°' },
    { key: 'Notificación Retrasada', color: 'orange', borderColor: 'border-orange-500', icon: 'âš ï¸' },
    { key: 'Prejudicial', color: 'red', borderColor: 'border-red-500', icon: 'ðŸš¨' },
  ]

  // Organizar plantillas por categoría (para el resumen)
  const plantillasPorCategoria = useMemo(() => {
    const organizadas: Record<string, NotificacionPlantilla[]> = {}

    plantillasFiltradas.forEach(plantilla => {
      const mapeo = mapeoTipos[plantilla.tipo as keyof typeof mapeoTipos]
      if (mapeo) {
        const categoria = mapeo.categoria
        if (!organizadas[categoria]) {
          organizadas[categoria] = []
        }
        organizadas[categoria].push(plantilla)
      }
    })

    // Ordenar plantillas dentro de cada categoría por caso
    Object.keys(organizadas).forEach(categoria => {
      organizadas[categoria].sort((a, b) => {
        const casoA = mapeoTipos[a.tipo as keyof typeof mapeoTipos]?.caso || ''
        const casoB = mapeoTipos[b.tipo as keyof typeof mapeoTipos]?.caso || ''
        return casoA.localeCompare(casoB)
      })
    })

    return organizadas
  }, [plantillasFiltradas])


  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="armar" className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Armar plantilla
        </TabsTrigger>
        <TabsTrigger value="resumen" className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Resumen
        </TabsTrigger>
      </TabsList>

      <TabsContent value="armar" className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">Armar plantilla</h2>
            <p className="text-sm text-gray-500">Elige el caso, escribe asunto y cuerpo, inserta variables y guarda. Luego asígnala en Notificaciones → Configuración.</p>
          </div>
          <div className="flex gap-2">
            <Button onClick={importar} variant="outline" size="sm" title="Importar plantilla">
              <Upload className="h-4 w-4 mr-1" />
              Importar
            </Button>
            <input ref={fileInputRef} type="file" accept=".json" onChange={handleImportFile} className="hidden" />
            <Button onClick={limpiar} variant="secondary" size="sm">
              Nueva plantilla
            </Button>
          </div>
        </div>

        <Card className="p-4 space-y-3">
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="text-sm text-gray-600">Nombre</label>
              <Input value={nombre} onChange={e=>setNombre(e.target.value)} placeholder="Recordatorio de pago" />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-2 block">
                Aplicar al caso
              </label>

              {selected ? (
                <select value={tipo} onChange={e=>setTipo(e.target.value)} className="w-full border rounded px-3 py-2 text-sm bg-white">
                  <option value="">Seleccione...</option>
                  {todosLosTipos.map(t => <option key={t.valor} value={t.valor}>{t.label}</option>)}
                </select>
              ) : (
                <select
                  value={tiposSeleccionados[0] || ''}
                  onChange={e => setTiposSeleccionados(e.target.value ? [e.target.value] : [])}
                  className="w-full border rounded px-3 py-2 text-sm bg-white"
                >
                  <option value="">Seleccione un caso...</option>
                  {todosLosTipos.map(t => <option key={t.valor} value={t.valor}>{t.label}</option>)}
                </select>
              )}
            </div>
            <div className="sr-only">
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
                    <h4 className="text-sm font-semibold mb-2 text-blue-700">ðŸ“… Antes de Fecha de Vencimiento</h4>
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
                    <h4 className="text-sm font-semibold mb-2 text-green-700">ðŸ’° Día de Pago</h4>
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
                    <h4 className="text-sm font-semibold mb-2 text-orange-700">âš ï¸ Días de Retraso</h4>
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
                    <h4 className="text-sm font-semibold mb-2 text-red-700">Prejudicial</h4>
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

                  {/* Mora 61+ */}
                  {tiposPorCategoria.mora61 && (
                    <div>
                      <h4 className="text-sm font-semibold mb-2 text-slate-700">61+ días de mora</h4>
                      <div className="grid grid-cols-3 gap-2">
                        {tiposPorCategoria.mora61.map(t => (
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
                  )}
                </div>
            </div>
            <div className="flex items-center gap-2">
              <input id="activa" type="checkbox" checked={activa} onChange={e=>setActiva(e.target.checked)} />
              <label htmlFor="activa" className="text-sm">Habilitar envío automático a las 3:00 AM</label>
            </div>
          </div>

          {/* Variables listas para insertar (sin burocracia) */}
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-3">
            <p className="text-xs font-semibold text-blue-900 mb-2">Insertar variable en asunto o cuerpo (clic):</p>
            <div className="flex flex-wrap gap-2">
              {VARIABLES_NOTIFICACION.map(({ key, label }) => (
                <Button
                  key={key}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="bg-white border-blue-300 text-blue-800 hover:bg-blue-100 font-mono text-xs"
                  onClick={() => {
                    insertarVariable(key)
                    toast.success(`{{${key}}} insertado`, { duration: 1200 })
                  }}
                >
                  {`{{${key}}}`}
                </Button>
              ))}
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
                    <p className="font-medium">Cargando variables...</p>
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
                O escriba manualmente: {VARIABLES_NOTIFICACION.slice(0, 3).map(v => `{{${v.key}}}`).join(', ')}...
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
      </TabsContent>

      <TabsContent value="resumen" className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              Resumen de Plantillas por Caso
            </CardTitle>
            <CardDescription>
              Visualización organizada de todas las plantillas almacenadas, clasificadas por tipo de notificación y caso.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Búsqueda y filtros para el resumen */}
            <div className="mb-6 space-y-2">
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

            {loading ? (
              <div className="text-center py-8 text-gray-500">Cargando plantillas...</div>
            ) : plantillasFiltradas.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p>No hay plantillas configuradas.</p>
                <p className="text-sm mt-2">Vaya a la pestaña "Armar plantilla" para crear nuevas plantillas.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {categoriasOrden.map(categoriaInfo => {
                  const categoria = categoriaInfo.key
                  const plantillasCategoria = plantillasPorCategoria[categoria] || []

                  if (plantillasCategoria.length === 0) return null

                  return (
                    <Card key={categoria} className={`border-l-4 ${categoriaInfo.borderColor}`}>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg flex items-center gap-2">
                          <span>{categoriaInfo.icon}</span>
                          {categoria}
                          <Badge variant="outline" className="ml-2">
                            {plantillasCategoria.length} plantilla(s)
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Tipo</TableHead>
                                <TableHead>Caso</TableHead>
                                <TableHead>Fecha Actualización</TableHead>
                                <TableHead>Archivo / Plantilla</TableHead>
                                <TableHead>Estado</TableHead>
                                <TableHead className="text-right">Acciones</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {plantillasCategoria.map(plantilla => {
                                const mapeo = mapeoTipos[plantilla.tipo as keyof typeof mapeoTipos]
                                return (
                                  <TableRow key={plantilla.id}>
                                    <TableCell className="font-medium">
                                      {mapeo?.categoria || plantilla.tipo}
                                    </TableCell>
                                    <TableCell>
                                      <Badge variant="outline">{mapeo?.caso || plantilla.tipo}</Badge>
                                    </TableCell>
                                    <TableCell>
                                      <div className="flex items-center gap-1 text-sm text-gray-600">
                                        <Calendar className="h-3 w-3" />
                                        {formatearFecha(plantilla.fecha_actualizacion)}
                                      </div>
                                    </TableCell>
                                    <TableCell>
                                      <div className="max-w-xs">
                                        <div className="font-medium text-sm truncate" title={plantilla.nombre}>
                                          {plantilla.nombre}
                                        </div>
                                        <div className="text-xs text-gray-500 truncate" title={plantilla.asunto}>
                                          {plantilla.asunto || 'Sin asunto'}
                                        </div>
                                      </div>
                                    </TableCell>
                                    <TableCell>
                                      {plantilla.activa ? (
                                        <Badge variant="success">Activa</Badge>
                                      ) : (
                                        <Badge variant="secondary">Inactiva</Badge>
                                      )}
                                    </TableCell>
                                    <TableCell className="text-right">
                                      <div className="flex justify-end gap-2">
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={() => handleEditarDesdeResumen(plantilla)}
                                          title="Editar plantilla"
                                        >
                                          <Edit2 className="h-4 w-4" />
                                        </Button>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={() => handleEliminarDesdeResumen(plantilla)}
                                          title="Eliminar plantilla"
                                        >
                                          <Trash2 className="h-4 w-4 text-red-500" />
                                        </Button>
                                      </div>
                                    </TableCell>
                                  </TableRow>
                                )
                              })}
                            </TableBody>
                          </Table>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}

export default PlantillasNotificaciones

