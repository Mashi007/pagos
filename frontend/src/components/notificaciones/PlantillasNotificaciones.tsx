import { useEffect, useMemo, useRef, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  notificacionService,
  NotificacionPlantilla,
  NotificacionVariable,
} from '../../services/notificacionService'

import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Textarea } from '../../components/ui/textarea'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../../components/ui/tabs'

import { Badge } from '../../components/ui/badge'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'

import { toast } from 'sonner'

import {
  Upload,
  Search,
  FileText,
  Database,
  ChevronDown,
  ChevronUp,
  Edit2,
  Trash2,
  Calendar,
  AlertCircle,
  Eye,
} from 'lucide-react'

import { EditorPlantillaHTML } from './EditorPlantillaHTML'

import { replaceBase64ImagesWithLogoUrl } from '../../utils/plantillaHtmlLogo'

import {
  etiquetaServicioPlantilla,
  bordeTarjetaServicioPlantilla,
} from '../../constants/notifPlantillaServicioContexto'

type EditorFocus = 'asunto' | 'encabezado' | 'cuerpo' | 'firma'

interface PlantillasNotificacionesProps {
  plantillaInicial?: NotificacionPlantilla | null

  onPlantillaCargada?: () => void

  /** Cuando el padre esta en la pestana "plantillas", se recargan las variables para integrar las creadas en Variables Personalizadas. */

  tabSeccionActiva?: string

  /**
   * Tipo de notificación (backend) para el que se crean plantillas nuevas y el panel amarillo.
   * Viene de ?notif_tipo= en Configuración → Plantillas o del submenú desde el que se abrió.
   */
  tipoServicioPlantilla?: string
}

export function PlantillasNotificaciones({
  plantillaInicial,
  onPlantillaCargada,
  tabSeccionActiva,
  tipoServicioPlantilla = 'PAGO_1_DIA_ATRASADO',
}: PlantillasNotificacionesProps = {}) {
  const queryClient = useQueryClient()

  const { data: plantillas = [], isLoading: loading } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,

    queryFn: () => notificacionService.listarPlantillas(undefined, false),

    staleTime: 1 * 60 * 1000,

    placeholderData: [] as NotificacionPlantilla[],
  })

  const [plantillasFiltradas, setPlantillasFiltradas] = useState<
    NotificacionPlantilla[]
  >([])

  const [selected, setSelected] = useState<NotificacionPlantilla | null>(null)

  const [busqueda, setBusqueda] = useState('')

  const [filtroTipo, setFiltroTipo] = useState('')

  const [filtroActiva, setFiltroActiva] = useState<boolean | null>(null)

  const [activeTab, setActiveTab] = useState('armar')

  const fileInputRef = useRef<HTMLInputElement>(null)

  const [nombre, setNombre] = useState('')

  const [tipo, setTipo] = useState('') // Mantener para compatibilidad con edicion individual

  const [tiposSeleccionados, setTiposSeleccionados] = useState<string[]>([
    tipoServicioPlantilla,
  ])

  const [activa, setActiva] = useState(true)

  const [asunto, setAsunto] = useState('')

  const [encabezado, setEncabezado] = useState('')

  const [cuerpo, setCuerpo] = useState('')

  const [firma, setFirma] = useState('')

  const [variable, setVariable] = useState('')

  const [focus, setFocus] = useState<EditorFocus>('cuerpo')

  const [variablesConfiguradas, setVariablesConfiguradas] = useState<
    NotificacionVariable[]
  >([])

  const [mostrarVariables, setMostrarVariables] = useState(true) // Por defecto visible

  const [busquedaVariable, setBusquedaVariable] = useState('')

  const [filtroTablaVariable, setFiltroTablaVariable] = useState<string>('') // Filtro por tabla

  const asuntoRef = useRef<HTMLTextAreaElement | HTMLInputElement>(null)

  const encRef = useRef<HTMLTextAreaElement>(null)

  const cuerpoRef = useRef<HTMLTextAreaElement>(null)

  const firmaRef = useRef<HTMLTextAreaElement>(null)

  const cuerpoFinal = useMemo(() => {
    const parts = [encabezado, cuerpo, firma].filter(Boolean)

    return replaceBase64ImagesWithLogoUrl(parts.join('\n\n'))
  }, [encabezado, cuerpo, firma])

  /** Variables que el sistema sustituye al enviar (sin burocracia de tablas/BD). Insertar en asunto/cuerpo. */

  const VARIABLES_NOTIFICACION = [
    { key: 'nombre', label: 'Nombre' },

    { key: 'cedula', label: 'Cedula' },

    { key: 'fecha_vencimiento', label: 'Fecha venc.' },

    {
      key: 'fecha_vencimiento_display',
      label: 'Fecha venc. (texto, ej. 5 de abril de 2026)',
    },

    { key: 'numero_cuota', label: 'Nº cuota' },

    { key: 'monto', label: 'Monto' },

    {
      key: 'dias_atraso',
      label: 'Dias desde vencimiento cuota de referencia',
    },

    {
      key: 'cuotas_atrasadas',
      label: 'Cuotas atrasadas (estado de cuenta)',
    },
  ]

  // Generar variables precargadas desde los campos de las tablas

  const generarVariablesPrecargadas = (): NotificacionVariable[] => {
    const CAMPOS_DISPONIBLES = {
      clientes: [
        { campo: 'id', descripcion: 'ID ?nico del cliente' },

        { campo: 'cedula', descripcion: 'C?dula de identidad' },

        { campo: 'nombres', descripcion: 'Nombres completos' },

        { campo: 'telefono', descripcion: 'Tel?fono de contacto' },

        { campo: 'email', descripcion: 'Correo electr?nico' },

        { campo: 'direccion', descripcion: 'Direcci?n de residencia' },

        { campo: 'fecha_nacimiento', descripcion: 'Fecha de nacimiento' },

        { campo: 'ocupacion', descripcion: 'Ocupaci?n del cliente' },

        {
          campo: 'estado',
          descripcion: 'Estado (ACTIVO, INACTIVO, FINALIZADO)',
        },

        { campo: 'activo', descripcion: 'Estado activo (true/false)' },

        { campo: 'fecha_registro', descripcion: 'Fecha de registro' },

        {
          campo: 'fecha_actualizacion',
          descripcion: 'Fecha de ?ltima actualizaci?n',
        },

        { campo: 'usuario_registro', descripcion: 'Usuario que registr?' },

        { campo: 'notas', descripcion: 'Notas adicionales' },
      ],

      prestamos: [
        { campo: 'id', descripcion: 'ID del pr?stamo' },

        { campo: 'cliente_id', descripcion: 'ID del cliente' },

        { campo: 'cedula', descripcion: 'C?dula del cliente' },

        { campo: 'nombres', descripcion: 'Nombres del cliente' },

        { campo: 'valor_activo', descripcion: 'Valor del activo (veh?culo)' },

        {
          campo: 'total_financiamiento',
          descripcion: 'Monto total financiado',
        },

        {
          campo: 'fecha_requerimiento',
          descripcion: 'Fecha requerida del pr?stamo',
        },

        {
          campo: 'modalidad_pago',
          descripcion: 'Modalidad (MENSUAL, QUINCENAL, SEMANAL)',
        },

        { campo: 'numero_cuotas', descripcion: 'N?mero total de cuotas' },

        { campo: 'cuota_periodo', descripcion: 'Monto de cuota por per?odo' },

        { campo: 'tasa_interes', descripcion: 'Tasa de inter?s (%)' },

        { campo: 'fecha_base_calculo', descripcion: 'Fecha base para c?lculo' },

        { campo: 'producto', descripcion: 'Producto financiero' },

        { campo: 'concesionario', descripcion: 'Concesionario' },

        { campo: 'analista', descripcion: 'Analista asignado' },

        { campo: 'modelo_vehiculo', descripcion: 'Modelo del veh?culo' },

        { campo: 'estado', descripcion: 'Estado del pr?stamo' },

        { campo: 'usuario_proponente', descripcion: 'Usuario proponente' },

        { campo: 'usuario_aprobador', descripcion: 'Usuario aprobador' },

        { campo: 'fecha_registro', descripcion: 'Fecha de registro' },

        { campo: 'fecha_aprobacion', descripcion: 'Fecha de aprobaci?n' },
      ],

      cuotas: [
        { campo: 'id', descripcion: 'ID de la cuota' },

        { campo: 'prestamo_id', descripcion: 'ID del pr?stamo' },

        { campo: 'numero_cuota', descripcion: 'N?mero de cuota' },

        { campo: 'fecha_vencimiento', descripcion: 'Fecha de vencimiento' },

        { campo: 'fecha_pago', descripcion: 'Fecha de pago' },

        { campo: 'monto_cuota', descripcion: 'Monto total de la cuota' },

        { campo: 'monto_capital', descripcion: 'Monto de capital' },

        { campo: 'monto_interes', descripcion: 'Monto de inter?s' },

        {
          campo: 'saldo_capital_inicial',
          descripcion: 'Saldo capital inicial',
        },

        { campo: 'saldo_capital_final', descripcion: 'Saldo capital final' },

        { campo: 'capital_pagado', descripcion: 'Capital pagado' },

        { campo: 'interes_pagado', descripcion: 'Inter?s pagado' },

        { campo: 'mora_pagada', descripcion: 'Mora pagada' },

        { campo: 'total_pagado', descripcion: 'Total pagado' },

        { campo: 'capital_pendiente', descripcion: 'Capital pendiente' },

        { campo: 'interes_pendiente', descripcion: 'Inter?s pendiente' },

        { campo: 'dias_mora', descripcion: 'D?as de mora' },

        { campo: 'monto_mora', descripcion: 'Monto de mora' },

        { campo: 'tasa_mora', descripcion: 'Tasa de mora (%)' },

        { campo: 'dias_morosidad', descripcion: 'D?as de morosidad' },

        { campo: 'monto_morosidad', descripcion: 'Monto de morosidad' },

        { campo: 'estado', descripcion: 'Estado de la cuota' },
      ],

      pagos: [
        { campo: 'id', descripcion: 'ID del pago' },

        { campo: 'cedula', descripcion: 'C?dula del cliente' },

        { campo: 'prestamo_id', descripcion: 'ID del pr?stamo' },

        { campo: 'numero_cuota', descripcion: 'N?mero de cuota' },

        { campo: 'fecha_pago', descripcion: 'Fecha de pago' },

        { campo: 'fecha_registro', descripcion: 'Fecha de registro' },

        { campo: 'monto_pagado', descripcion: 'Monto pagado' },

        { campo: 'numero_documento', descripcion: 'N?mero de documento' },

        { campo: 'institucion_bancaria', descripcion: 'Instituci?n bancaria' },

        { campo: 'estado', descripcion: 'Estado del pago' },

        { campo: 'conciliado', descripcion: 'Si est? conciliado' },

        { campo: 'fecha_conciliacion', descripcion: 'Fecha de conciliaci?n' },
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

      const nombresVariablesUsuario = new Set(
        variablesUsuario.map(v => v.nombre_variable)
      )

      const variablesPrecargadasFiltradas = variablesPrecargadas.filter(
        v => !nombresVariablesUsuario.has(v.nombre_variable)
      )

      // Combinar ambas listas

      const todasLasVariables = [
        ...variablesUsuario,
        ...variablesPrecargadasFiltradas,
      ]

      setVariablesConfiguradas(todasLasVariables)
    } catch (error: any) {
      // Si falla, usar solo variables precargadas

      const variablesPrecargadas = generarVariablesPrecargadas()

      setVariablesConfiguradas(variablesPrecargadas)
    }
  }

  useEffect(() => {
    cargarVariables()
  }, [])

  // Recargar variables cuando el usuario vuelve a la pesta?a Plantillas (tras crear/editar en Variables Personalizadas)

  useEffect(() => {
    if (tabSeccionActiva === 'plantillas') {
      cargarVariables()
    }
  }, [tabSeccionActiva])

  // Cargar plantilla inicial si se proporciona (para edici?n desde Resumen)

  useEffect(() => {
    if (plantillaInicial && plantillas.length > 0) {
      // Buscar la plantilla en la lista cargada para asegurar que est? actualizada

      const plantillaEncontrada = plantillas.find(
        p => p.id === plantillaInicial.id
      )

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

      // Cambiar a la pesta?a de armar plantilla

      setActiveTab('armar')

      // Notificar que la plantilla fue cargada

      if (onPlantillaCargada) {
        onPlantillaCargada()
      }
    }
  }, [plantillaInicial, plantillas, onPlantillaCargada])

  useEffect(() => {
    if (selected) return
    setTiposSeleccionados([tipoServicioPlantilla])
  }, [tipoServicioPlantilla, selected])

  // Filtrar plantillas

  useEffect(() => {
    let filtradas = [...plantillas]

    if (busqueda) {
      filtradas = filtradas.filter(
        p =>
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

    setTiposSeleccionados([tipoServicioPlantilla])

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

    setCuerpo(replaceBase64ImagesWithLogoUrl(p.cuerpo || ''))

    setFirma('')
  }

  const insertarVariable = (nombreVariable?: string) => {
    const varName = nombreVariable || variable

    if (!varName) return

    const token = `{{${varName}}}`

    const insertInto = (
      el: HTMLTextAreaElement | HTMLInputElement | null,
      setter: (v: string) => void,
      current: string
    ) => {
      if (!el) {
        setter(current + token)

        return
      }

      const start = (el as any).selectionStart ?? current.length

      const end = (el as any).selectionEnd ?? current.length

      const next = current.slice(0, start) + token + current.slice(end)

      setter(next)

      queueMicrotask(() => {
        try {
          ;(el as any).focus()
          ;(el as any).setSelectionRange(
            start + token.length,
            start + token.length
          )
        } catch {}
      })
    }

    if (focus === 'asunto')
      return insertInto(asuntoRef.current, setAsunto, asunto)

    if (focus === 'encabezado')
      return insertInto(encRef.current, setEncabezado, encabezado)

    if (focus === 'cuerpo')
      return insertInto(cuerpoRef.current, setCuerpo, cuerpo)

    if (focus === 'firma') return insertInto(firmaRef.current, setFirma, firma)
  }

  const variablesFiltradas = useMemo(() => {
    let filtradas = variablesConfiguradas

    // Filtrar por tabla

    if (filtroTablaVariable) {
      filtradas = filtradas.filter(v => v.tabla === filtroTablaVariable)
    }

    // Filtrar por b?squeda

    if (busquedaVariable) {
      filtradas = filtradas.filter(
        v =>
          v.nombre_variable
            .toLowerCase()
            .includes(busquedaVariable.toLowerCase()) ||
          (v.descripcion ?? '')
            .toLowerCase()
            .includes(busquedaVariable.toLowerCase()) ||
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

  // Obtener tablas ?nicas

  const tablasUnicas = useMemo(() => {
    return Array.from(new Set(variablesConfiguradas.map(v => v.tabla))).sort()
  }, [variablesConfiguradas])

  const aplicarFormato = (tag: 'b' | 'i' | 'u' | 'ul' | 'a') => {
    const wrap = (
      el: HTMLTextAreaElement | null,
      setter: (v: string) => void,
      current: string
    ) => {
      if (!el) return

      const start = el.selectionStart ?? 0

      const end = el.selectionEnd ?? 0

      const selected = current.slice(start, end)

      let before = '',
        after = ''

      if (tag === 'a') {
        before = '<a href="https://">'

        after = '</a>'
      } else if (tag === 'ul') {
        const lines = selected || 'Elemento 1\nElemento 2'

        const wrapped = lines
          .split('\n')
          .map(l => `<li>${l || 'Elemento'}</li>`)
          .join('\n')

        const next =
          current.slice(0, start) +
          `<ul>\n${wrapped}\n</ul>` +
          current.slice(end)

        setter(next)

        return
      } else {
        before = `<${tag}>`

        after = `</${tag}>`
      }

      const next =
        current.slice(0, start) +
        before +
        (selected || 'texto') +
        after +
        current.slice(end)

      setter(next)

      queueMicrotask(() => {
        try {
          el.focus()
        } catch {}
      })
    }

    if (focus === 'encabezado')
      return wrap(encRef.current, setEncabezado, encabezado)

    if (focus === 'cuerpo') return wrap(cuerpoRef.current, setCuerpo, cuerpo)

    if (focus === 'firma') return wrap(firmaRef.current, setFirma, firma)

    if (focus === 'asunto') return // no aplicar html al asunto
  }

  const guardar = async () => {
    // Si estamos editando una plantilla existente, guardar solo esa

    if (selected?.id) {
      if (!nombre.trim() || !asunto.trim() || !cuerpoFinal.trim()) {
        toast.error('Complete todos los campos obligatorios')

        return
      }

      if (tiposSeleccionados.length === 0) {
        toast.error('Seleccione al menos un caso para esta plantilla')

        return
      }

      const tipoActual = selected.tipo

      try {
        await notificacionService.actualizarPlantilla(selected.id, {
          nombre,
          tipo: tipoActual,
          asunto,
          cuerpo: cuerpoFinal,
          activa,
        })

        toast.success('Plantilla actualizada exitosamente')

        await queryClient.invalidateQueries({
          queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,
        })

        limpiar()

        // Cambiar a la pesta?a de resumen despu?s de guardar

        setActiveTab('resumen')
      } catch (error: any) {
        toast.error(
          error?.response?.data?.detail || 'Error al guardar plantilla'
        )
      }

      return
    }

    if (!nombre.trim() || !asunto.trim() || !cuerpoFinal.trim()) {
      toast.error('Complete todos los campos obligatorios')

      return
    }

    try {
      const tipoNuevo = tipoServicioPlantilla

      await notificacionService.crearPlantilla({
        nombre: nombre.trim(),
        tipo: tipoNuevo,
        asunto,
        cuerpo: cuerpoFinal,
        activa,
      })

      toast.success('Plantilla creada exitosamente')

      setActiveTab('resumen')

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,
      })

      limpiar()
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || 'Error al guardar la plantilla'
      )
    }
  }

  const eliminar = async () => {
    if (!selected?.id) {
      toast.error('Seleccione una plantilla para eliminar')

      return
    }

    if (!window.confirm(`?Eliminar plantilla "${selected.nombre}"?`)) return

    try {
      await notificacionService.eliminarPlantilla(selected.id)

      toast.success('Plantilla eliminada exitosamente')

      limpiar()

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,
      })
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || 'Error al eliminar plantilla'
      )
    }
  }

  const exportar = async () => {
    if (!selected?.id) {
      toast.error('Seleccione una plantilla para exportar')

      return
    }

    try {
      const data = await notificacionService.exportarPlantilla(selected.id)

      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      })

      const url = URL.createObjectURL(blob)

      const a = document.createElement('a')

      a.href = url

      a.download = `plantilla_${selected.nombre.replace(/[^a-z0-9]/gi, '_')}.json`

      a.click()

      URL.revokeObjectURL(url)

      toast.success('Plantilla exportada exitosamente')
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || 'Error al exportar plantilla'
      )
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
        toast.error('Archivo JSON inv?lido: faltan campos obligatorios')

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

      setTiposSeleccionados([tipoServicioPlantilla])

      setActiveTab('armar')

      toast.success(
        `Plantilla importada. Al guardar se creará solo para: ${etiquetaServicioPlantilla(tipoServicioPlantilla)}.`
      )
    } catch (error: any) {
      toast.error(
        'Error al leer el archivo JSON: ' +
          (error.message || 'Formato inv?lido')
      )
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

  const handleEliminarDesdeResumen = async (
    plantilla: NotificacionPlantilla
  ) => {
    if (
      !window.confirm(
        `?Est? seguro de eliminar la plantilla "${plantilla.nombre}"?`
      )
    ) {
      return
    }

    try {
      await notificacionService.eliminarPlantilla(plantilla.id)

      toast.success('Plantilla eliminada exitosamente')

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,
      })
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || 'Error al eliminar plantilla'
      )
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

  // Mapeo de tipos a categor?as y casos (para el resumen)

  const mapeoTipos = {
    PAGO_5_DIAS_ANTES: {
      categoria: 'Notificación previa (heredada)',
      caso: '5 días antes',
    },

    PAGO_3_DIAS_ANTES: {
      categoria: 'Notificación previa (heredada)',
      caso: '3 días antes',
    },

    PAGO_1_DIA_ANTES: {
      categoria: 'Notificación previa (heredada)',
      caso: '1 día antes',
    },

    PAGO_2_DIAS_ANTES_PENDIENTE: {
      categoria: 'Notificación previa (heredada)',
      caso: '2 días antes (pendiente, vence en 2 días)',
    },

    PAGO_DIA_0: {
      categoria: 'Día de pago (heredado)',
      caso: 'Día de pago',
    },

    PAGO_1_DIA_ATRASADO: {
      categoria: 'Notificación retrasada',
      caso: 'Día siguiente al vencimiento',
    },

    PAGO_10_DIAS_ATRASADO: {
      categoria: 'Notificación retrasada',
      caso: '10 días de retraso',
    },

    PREJUDICIAL: { categoria: 'Prejudicial', caso: 'Prejudicial' },

    MASIVOS: {
      categoria: 'Comunicaciones masivas',
      caso: 'Comunicaciones masivas',
    },

    COBRANZA: { categoria: 'Cobranza', caso: 'Carta de cobranza' },
  }

  /** Un solo bloque "servicio activo" según submenú / ?notif_tipo= */

  const ordenCasos = useMemo(
    () => [
      {
        tipo: tipoServicioPlantilla,
        label: etiquetaServicioPlantilla(tipoServicioPlantilla),
        borderColor: bordeTarjetaServicioPlantilla(tipoServicioPlantilla),
      },
    ],
    [tipoServicioPlantilla]
  )

  const tiposPlantillaHeredados = useMemo(() => {
    const u = new Set<string>()
    plantillas.forEach(p => {
      if (p.tipo !== tipoServicioPlantilla) u.add(p.tipo)
    })
    return Array.from(u).sort()
  }, [plantillas, tipoServicioPlantilla])

  /** Banco por caso: plantillas agrupadas por tipo */

  const plantillasPorCaso = useMemo(() => {
    const porTipo: Record<string, NotificacionPlantilla[]> = {}

    ordenCasos.forEach(({ tipo }) => {
      porTipo[tipo] = []
    })

    plantillasFiltradas.forEach(plantilla => {
      if (porTipo[plantilla.tipo]) {
        porTipo[plantilla.tipo].push(plantilla)
      } else {
        porTipo[plantilla.tipo] = [plantilla]
      }
    })

    return porTipo
  }, [plantillasFiltradas, ordenCasos])

  const categoriasOrden = [
    {
      key: 'Notificación retrasada',
      color: 'orange',
      borderColor: 'border-orange-500',
      icon: '⚠️',
    },

    {
      key: 'Prejudicial',
      color: 'red',
      borderColor: 'border-red-500',
      icon: '🚨',
    },

    {
      key: 'Comunicaciones masivas',
      color: 'teal',
      borderColor: 'border-teal-500',
      icon: 'mail',
    },

    {
      key: 'Cobranza',
      color: 'violet',
      borderColor: 'border-violet-500',
      icon: '📧',
    },

    {
      key: 'Notificación previa (heredada)',
      color: 'blue',
      borderColor: 'border-blue-500',
      icon: '🔔',
    },

    {
      key: 'Día de pago (heredado)',
      color: 'green',
      borderColor: 'border-green-500',
      icon: '📅',
    },
  ]

  // Organizar plantillas por categor?a (para el resumen)

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

    // Ordenar plantillas dentro de cada categor?a por caso

    Object.keys(organizadas).forEach(categoria => {
      organizadas[categoria].sort((a, b) => {
        const casoA = mapeoTipos[a.tipo as keyof typeof mapeoTipos]?.caso || ''

        const casoB = mapeoTipos[b.tipo as keyof typeof mapeoTipos]?.caso || ''

        return casoA.localeCompare(casoB)
      })
    })

    return organizadas
  }, [plantillasFiltradas])

  const handleVistaPreviaHtml = () => {
    const ejemplo: Record<string, string> = {
      nombre: 'Juan Perez',

      cedula: 'V-12345678',

      fecha_vencimiento: '15/03/2025',

      fecha_vencimiento_display: '15 de marzo de 2025',

      numero_cuota: '3',

      monto: '150.00',

      dias_atraso: '2',

      cuotas_atrasadas: '2',

      'CLIENTES.TRATAMIENTO': 'Sr.',

      'CLIENTES.NOMBRE_COMPLETO': 'Juan Perez',

      'PRESTAMOS.ID': 'CR-2024-001',

      FECHA_CARTA: new Date().toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      }),

      LOGO_URL:
        typeof window !== 'undefined' && window.location.origin
          ? `${window.location.origin}/logos/rapicredit-public.png`
          : '',
    }

    let html = cuerpoFinal || ''

    if (!html.trim()) {
      html =
        cuerpo ||
        encabezado ||
        firma ||
        '<p>Sin contenido para previsualizar.</p>'
    }

    Object.entries(ejemplo).forEach(([key, val]) => {
      const token = `{{${key}}}`

      html = html.split(token).join(val)
    })

    html = html.replace(
      /\{\{#CUOTAS\.VENCIMIENTOS\}\}[\s\S]*?\{\{\/CUOTAS\.VENCIMIENTOS\}\}/g,
      '<p>Cuota N? 1 - Vencimiento: 10/01/2025 - Monto: 150.00</p><p>Cuota N? 2 - Vencimiento: 10/02/2025 - Monto: 150.00</p>'
    )

    // Siempre renderizar como HTML (encabezado, cuerpo y firma pueden contener código HTML)

    const doc = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Vista previa</title></head><body style="margin:0; padding:12px; font-family: sans-serif;">${html}</body></html>`

    const blob = new Blob([doc], { type: 'text/html;charset=utf-8' })

    const url = URL.createObjectURL(blob)

    window.open(url, '_blank', 'noopener,noreferrer')

    requestAnimationFrame(() => {
      requestAnimationFrame(() => URL.revokeObjectURL(url))
    })

    toast.success('Vista previa abierta en nueva pesta?a')
  }

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="armar" className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Armar plantilla
        </TabsTrigger>

        <TabsTrigger value="resumen" className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Resumen
        </TabsTrigger>

        <TabsTrigger value="html-editor" className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Editor HTML
        </TabsTrigger>
      </TabsList>

      <TabsContent value="armar" className="space-y-4">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Armar plantilla</h2>

            <p className="text-sm text-gray-500">
              Un solo servicio activo: día siguiente al vencimiento. Escriba
              asunto y cuerpo, inserte variables y guarde. Luego asígnela en
              Notificaciones → Configuración.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              onClick={importar}
              variant="outline"
              size="sm"
              title="Importar plantilla"
            >
              <Upload className="mr-1 h-4 w-4" />
              Importar
            </Button>

            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleImportFile}
              className="hidden"
            />

            <Button onClick={limpiar} variant="secondary" size="sm">
              Nueva plantilla
            </Button>
          </div>
        </div>

        <Card className="space-y-3 p-4">
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="text-sm text-gray-600">Nombre</label>

              <Input
                value={nombre}
                onChange={e => setNombre(e.target.value)}
                placeholder="Recordatorio de pago"
              />
            </div>

            <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/40 p-4">
              <p className="text-sm font-semibold text-amber-900">
                Servicio de notificación
              </p>
              <p className="text-sm text-gray-800">
                {etiquetaServicioPlantilla(tipoServicioPlantilla)}
              </p>
              <p className="text-xs text-gray-600">
                Las plantillas nuevas se guardan solo para este caso (
                <code className="rounded bg-white px-1">
                  {tipoServicioPlantilla}
                </code>
                ).
              </p>
              {selected && selected.tipo !== tipoServicioPlantilla ? (
                <p className="rounded border border-amber-300 bg-amber-100 px-2 py-1.5 text-xs text-amber-950">
                  Esta plantilla es de un tipo heredado ({selected.tipo}). Puede
                  editarla o eliminarla; no se ofrecen nuevos tipos desde esta
                  pantalla.
                </p>
              ) : null}
            </div>
          </div>

          {/* Variables listas para insertar: por tipo de plantilla */}

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
            <p className="mb-1 text-xs font-semibold text-blue-900">
              Insertar variable en asunto o cuerpo (clic en la variable):
            </p>

            <>
              <p className="mb-2 text-xs text-blue-700">
                Las variables de la pestaña{' '}
                <strong>Variables Personalizadas</strong> aparecen abajo en el
                Banco de Variables y se copian aquí al hacer clic.
              </p>

              <div className="flex flex-wrap gap-2">
                {VARIABLES_NOTIFICACION.map(({ key, label }) => (
                  <Button
                    key={key}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="border-blue-300 bg-white font-mono text-xs text-blue-800 hover:bg-blue-100"
                    onClick={() => {
                      insertarVariable(key)

                      toast.success(`{{${key}}} insertado`, {
                        duration: 1200,
                      })
                    }}
                  >
                    {`{{${key}}}`}
                  </Button>
                ))}
              </div>
            </>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-sm text-gray-600">Asunto</label>

              <Input
                ref={asuntoRef as any}
                value={asunto}
                onFocus={() => setFocus('asunto')}
                onChange={e => setAsunto(e.target.value)}
                placeholder="Asunto del correo"
              />
            </div>

            <div className="col-span-2">
              <p className="mb-1 text-xs text-gray-500">
                Puede usar código HTML en encabezado, cuerpo y firma. Use el
                botón «Vista previa (datos de ejemplo)» para ver cómo queda el
                resultado.
              </p>

              <div className="mb-1 flex items-center gap-2 text-sm text-gray-600">
                Formato rápido (encabezado/cuerpo/firma):
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => aplicarFormato('b')}
                >
                  B
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => aplicarFormato('i')}
                >
                  I
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => aplicarFormato('u')}
                >
                  U
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => aplicarFormato('ul')}
                >
                  Lista
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => aplicarFormato('a')}
                >
                  Enlace
                </Button>
              </div>
            </div>

            <div>
              <label className="text-sm text-gray-600">
                Encabezado (puede incluir HTML)
              </label>

              <Textarea
                ref={encRef}
                value={encabezado}
                onFocus={() => setFocus('encabezado')}
                onChange={e => setEncabezado(e.target.value)}
                rows={4}
                placeholder="Encabezado (ej. <p>Texto</p>)"
              />
            </div>

            <div>
              <label className="text-sm text-gray-600">
                Firma (puede incluir HTML)
              </label>

              <Textarea
                ref={firmaRef}
                value={firma}
                onFocus={() => setFocus('firma')}
                onChange={e => setFirma(e.target.value)}
                rows={4}
                placeholder="Firma (ej. <p>Atentamente,</p>)"
              />
            </div>

            <div className="col-span-2">
              <label className="text-sm text-gray-600">
                Cuerpo (puede incluir HTML)
              </label>

              <Textarea
                ref={cuerpoRef}
                value={cuerpo}
                onFocus={() => setFocus('cuerpo')}
                onChange={e =>
                  setCuerpo(replaceBase64ImagesWithLogoUrl(e.target.value))
                }
                rows={10}
                placeholder="Contenido principal (ej. <p>Hola <b>{{nombre}}</b></p>)"
              />
            </div>
          </div>

          {/* Panel de Variables Configuradas: incluye Variables Personalizadas (pesta?a hom?nima) */}

          <div className="rounded-lg border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-white p-4 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-blue-600" />

                <label className="text-base font-bold text-gray-800">
                  Banco de Variables
                </label>

                <Badge
                  variant="outline"
                  className="border-blue-300 bg-blue-100 text-xs text-blue-800"
                >
                  {variablesConfiguradas.length} disponibles
                </Badge>

                <span className="text-xs text-gray-600">
                  (incluye Variables Personalizadas)
                </span>
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
                className="text-blue-600 hover:bg-blue-50 hover:text-blue-700"
              >
                {mostrarVariables ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </div>

            {mostrarVariables && (
              <div className="space-y-4">
                {/* Filtros mejorados */}

                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {/* Filtro por tabla */}

                  <div>
                    <label className="mb-1 block text-xs font-semibold text-gray-700">
                      Filtrar por tabla:
                    </label>

                    <select
                      value={filtroTablaVariable}
                      onChange={e => setFiltroTablaVariable(e.target.value)}
                      className="w-full rounded-md border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Todas las tablas</option>

                      {tablasUnicas.map(tabla => (
                        <option key={tabla} value={tabla}>
                          {tabla}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* B?squeda de variables */}

                  <div className="relative">
                    <label className="mb-1 block text-xs font-semibold text-gray-700">
                      Buscar variable:
                    </label>

                    <Search
                      className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400"
                      style={{ top: '60%' }}
                    />

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
                  <div className="rounded-lg border-2 border-dashed border-gray-300 bg-white py-8 text-center text-sm text-gray-500">
                    <Database className="mx-auto mb-2 h-8 w-8 text-gray-400" />

                    <p className="font-medium">Cargando variables...</p>
                  </div>
                ) : variablesFiltradas.length === 0 ? (
                  <div className="rounded-lg border-2 border-dashed border-gray-300 bg-white py-8 text-center text-sm text-gray-500">
                    <p className="font-medium">
                      No se encontraron variables con ese criterio.
                    </p>

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
                  <div className="max-h-96 space-y-4 overflow-y-auto pr-2">
                    {Object.entries(variablesPorTabla).map(
                      ([tabla, variables]) => (
                        <div
                          key={tabla}
                          className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm"
                        >
                          <div className="mb-3 flex items-center gap-2 border-b border-gray-200 pb-2">
                            <Badge
                              variant="outline"
                              className="border-gray-300 bg-gray-100 text-xs font-semibold text-gray-700"
                            >
                              {tabla}
                            </Badge>

                            <span className="text-xs text-gray-500">
                              {variables.length} variable
                              {variables.length !== 1 ? 's' : ''}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                            {variables.map(v => (
                              <div
                                key={v.id || v.nombre_variable}
                                className="group cursor-pointer rounded-lg border-2 border-gray-200 bg-white p-3 transition-all duration-200 hover:border-blue-400 hover:shadow-md"
                                onClick={() =>
                                  insertarVariable(v.nombre_variable)
                                }
                                title={`Click para insertar {{${v.nombre_variable}}} en el campo activo`}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="min-w-0 flex-1">
                                    {/* Nombre de variable destacado */}

                                    <div className="mb-2">
                                      <code className="block w-fit rounded bg-blue-100 px-2 py-1 font-mono text-sm font-semibold text-blue-800">
                                        {'{{'}
                                        {v.nombre_variable}
                                        {'}}'}
                                      </code>
                                    </div>

                                    {/* Mapeo a BD - Destacado */}

                                    <div className="mb-1">
                                      <div className="mb-0.5 text-xs text-gray-500">
                                        Mapea a:
                                      </div>

                                      <div className="rounded border border-gray-200 bg-gray-50 px-2 py-1 font-mono text-xs text-gray-700">
                                        <span className="font-semibold text-gray-900">
                                          {v.tabla}
                                        </span>
                                        .
                                        <span className="text-blue-700">
                                          {v.campo_bd}
                                        </span>
                                      </div>
                                    </div>

                                    {/* Descripci?n si existe */}

                                    {v.descripcion && (
                                      <div className="mt-2 border-l-2 border-blue-200 pl-2 text-xs italic text-gray-600">
                                        {v.descripcion}
                                      </div>
                                    )}
                                  </div>

                                  {/* Bot?n de inserci?n mejorado */}

                                  <Button
                                    size="sm"
                                    className="shrink-0 bg-blue-600 text-white shadow-sm hover:bg-blue-700"
                                    onClick={e => {
                                      e.stopPropagation()

                                      insertarVariable(v.nombre_variable)

                                      toast.success(
                                        `Variable {{${v.nombre_variable}}} insertada`,
                                        { duration: 1500 }
                                      )
                                    }}
                                  >
                                    +
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}
              </div>
            )}

            {/* M?todo alternativo: campo de texto para variables r?pidas */}

            <div className="mt-3 flex items-center gap-2 border-t pt-3">
              <Input
                value={variable}
                onChange={e => setVariable(e.target.value)}
                placeholder="Escriba nombre de variable..."
                className="max-w-xs"
                onKeyDown={e => {
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
                O escriba manualmente:{' '}
                {VARIABLES_NOTIFICACION.slice(0, 3)
                  .map(v => `{{${v.key}}}`)
                  .join(', ')}
                ...
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={guardar}>
              {selected ? 'Actualizar' : 'Guardar'}
            </Button>

            {selected && (
              <Button variant="destructive" onClick={eliminar}>
                Eliminar
              </Button>
            )}

            {selected && (
              <>
                <Button
                  variant="secondary"
                  onClick={exportar}
                  title="Exportar a JSON"
                >
                  <FileText className="mr-1 h-4 w-4" />
                  Exportar
                </Button>
              </>
            )}

            <Button
              type="button"
              variant="outline"
              onClick={handleVistaPreviaHtml}
              title="Ver c?mo quedar? el cuerpo del email con datos de ejemplo"
            >
              <Eye className="mr-2 h-4 w-4" />
              Vista previa (datos de ejemplo)
            </Button>
          </div>
        </Card>
      </TabsContent>

      <TabsContent value="html-editor" className="space-y-4">
        <EditorPlantillaHTML tipoServicioPorDefecto={tipoServicioPlantilla} />
      </TabsContent>

      <TabsContent value="resumen" className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              Banco de plantillas por caso
            </CardTitle>

            <CardDescription>
              Servicio activo:{' '}
              {etiquetaServicioPlantilla(tipoServicioPlantilla)}. Las plantillas
              de otros tipos, si existen, aparecen como heredadas para revisión
              o eliminación.
            </CardDescription>
          </CardHeader>

          <CardContent>
            {/* B?squeda y filtros para el resumen */}

            <div className="mb-6 space-y-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

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
                  className="flex-1 rounded border px-2 py-1 text-sm"
                >
                  <option value="">Todos los casos</option>

                  {ordenCasos.map(c => (
                    <option key={c.tipo} value={c.tipo}>
                      {c.label}
                    </option>
                  ))}

                  {tiposPlantillaHeredados.map(ht => (
                    <option key={ht} value={ht}>
                      {mapeoTipos[ht as keyof typeof mapeoTipos]?.caso ?? ht}{' '}
                      (heredado)
                    </option>
                  ))}
                </select>

                <select
                  value={filtroActiva === null ? '' : String(filtroActiva)}
                  onChange={e =>
                    setFiltroActiva(
                      e.target.value === '' ? null : e.target.value === 'true'
                    )
                  }
                  className="rounded border px-2 py-1 text-sm"
                >
                  <option value="">Todas</option>

                  <option value="true">Solo activas</option>

                  <option value="false">Solo inactivas</option>
                </select>
              </div>
            </div>

            {loading ? (
              <div className="py-8 text-center text-gray-500">
                Cargando plantillas...
              </div>
            ) : plantillasFiltradas.length === 0 ? (
              <div className="py-8 text-center text-gray-500">
                <AlertCircle className="mx-auto mb-4 h-12 w-12 text-gray-400" />

                <p>No hay plantillas configuradas.</p>

                <p className="mt-2 text-sm">
                  Vaya a la pestaña &quot;Armar plantilla&quot; para crear
                  nuevas plantillas.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {ordenCasos.map(({ tipo, label, borderColor }) => {
                  const lista = plantillasPorCaso[tipo] || []

                  if (lista.length === 0) return null

                  return (
                    <Card key={tipo} className={`border-l-4 ${borderColor}`}>
                      <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-lg">
                          <FileText className="h-5 w-5 text-gray-500" />
                          Banco: {label}
                          <Badge variant="outline" className="ml-2">
                            {lista.length} plantilla(s)
                          </Badge>
                        </CardTitle>
                      </CardHeader>

                      <CardContent>
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Nombre</TableHead>

                                <TableHead>Asunto</TableHead>

                                <TableHead>Fecha actualización</TableHead>

                                <TableHead>Estado</TableHead>

                                <TableHead className="text-right">
                                  Acciones
                                </TableHead>
                              </TableRow>
                            </TableHeader>

                            <TableBody>
                              {lista.map(plantilla => (
                                <TableRow key={plantilla.id}>
                                  <TableCell
                                    className="font-medium"
                                    title={plantilla.nombre}
                                  >
                                    {plantilla.nombre}
                                  </TableCell>

                                  <TableCell
                                    className="max-w-xs truncate text-sm text-gray-600"
                                    title={plantilla.asunto || ''}
                                  >
                                    {plantilla.asunto || 'Sin asunto'}
                                  </TableCell>

                                  <TableCell>
                                    <div className="flex items-center gap-1 text-sm text-gray-600">
                                      <Calendar className="h-3 w-3" />

                                      {formatearFecha(
                                        plantilla.fecha_actualizacion
                                      )}
                                    </div>
                                  </TableCell>

                                  <TableCell>
                                    {plantilla.activa ? (
                                      <Badge
                                        variant="default"
                                        className="bg-green-600"
                                      >
                                        Activa
                                      </Badge>
                                    ) : (
                                      <Badge variant="secondary">
                                        Inactiva
                                      </Badge>
                                    )}
                                  </TableCell>

                                  <TableCell className="text-right">
                                    <div className="flex justify-end gap-2">
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() =>
                                          handleEditarDesdeResumen(plantilla)
                                        }
                                        title="Editar plantilla"
                                      >
                                        <Edit2 className="h-4 w-4" />
                                      </Button>

                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="hover:bg-red-100 hover:text-red-600"
                                        onClick={() =>
                                          handleEliminarDesdeResumen(plantilla)
                                        }
                                        title="Eliminar plantilla"
                                      >
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}

                {tiposPlantillaHeredados.map(tipoH => {
                  const lista = plantillasPorCaso[tipoH] || []

                  if (lista.length === 0) return null

                  const etiqueta =
                    mapeoTipos[tipoH as keyof typeof mapeoTipos]?.caso ?? tipoH

                  return (
                    <Card key={tipoH} className="border-l-4 border-slate-400">
                      <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-lg">
                          <FileText className="h-5 w-5 text-gray-500" />
                          Banco heredado: {etiqueta}
                          <Badge variant="outline" className="ml-2">
                            {lista.length} plantilla(s)
                          </Badge>
                        </CardTitle>
                        <p className="text-xs text-amber-800">
                          Tipo descontinuado en esta pantalla; puede editar o
                          eliminar.
                        </p>
                      </CardHeader>

                      <CardContent>
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Nombre</TableHead>

                                <TableHead>Asunto</TableHead>

                                <TableHead>Fecha actualización</TableHead>

                                <TableHead>Estado</TableHead>

                                <TableHead className="text-right">
                                  Acciones
                                </TableHead>
                              </TableRow>
                            </TableHeader>

                            <TableBody>
                              {lista.map(plantilla => (
                                <TableRow key={plantilla.id}>
                                  <TableCell
                                    className="font-medium"
                                    title={plantilla.nombre}
                                  >
                                    {plantilla.nombre}
                                  </TableCell>

                                  <TableCell
                                    className="max-w-xs truncate text-sm text-gray-600"
                                    title={plantilla.asunto || ''}
                                  >
                                    {plantilla.asunto || 'Sin asunto'}
                                  </TableCell>

                                  <TableCell>
                                    <div className="flex items-center gap-1 text-sm text-gray-600">
                                      <Calendar className="h-3 w-3" />

                                      {formatearFecha(
                                        plantilla.fecha_actualizacion
                                      )}
                                    </div>
                                  </TableCell>

                                  <TableCell>
                                    {plantilla.activa ? (
                                      <Badge
                                        variant="default"
                                        className="bg-green-600"
                                      >
                                        Activa
                                      </Badge>
                                    ) : (
                                      <Badge variant="secondary">
                                        Inactiva
                                      </Badge>
                                    )}
                                  </TableCell>

                                  <TableCell className="text-right">
                                    <div className="flex justify-end gap-2">
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() =>
                                          handleEditarDesdeResumen(plantilla)
                                        }
                                        title="Editar plantilla"
                                      >
                                        <Edit2 className="h-4 w-4" />
                                      </Button>

                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="hover:bg-red-100 hover:text-red-600"
                                        onClick={() =>
                                          handleEliminarDesdeResumen(plantilla)
                                        }
                                        title="Eliminar plantilla"
                                      >
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              ))}
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
