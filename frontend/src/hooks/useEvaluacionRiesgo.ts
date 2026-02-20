import { useState, useEffect } from 'react'
import { prestamoService } from '../services/prestamoService'
import { clienteService } from '../services/clienteService'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { toast } from 'sonner'
import type { Prestamo } from '../types'

export interface EvaluacionFormData {
  // Criterio 1: Capacidad de Pago
  ingresos_mensuales: number
  gastos_fijos_mensuales: number
  otras_deudas: number

  // Criterio 2: Estabilidad Laboral
  meses_trabajo: number
  tipo_empleo: string
  sector_economico: string

  // Criterio 3: Referencias
  referencia1_observaciones: string
  referencia1_calificacion: number
  referencia2_observaciones: string
  referencia2_calificacion: number
  referencia3_observaciones: string
  referencia3_calificacion: number

  // Criterio 4: Arraigo Geográfico
  familia_cercana: boolean
  familia_pais: boolean
  minutos_trabajo: number

  // Criterio 5: Perfil Sociodemográfico
  tipo_vivienda_detallado: string
  zona_urbana: boolean
  servicios_nombre: boolean
  zona_rural: boolean
  personas_casa: number
  estado_civil: string
  pareja_trabaja: boolean
  pareja_aval: boolean
  pareja_desempleada: boolean
  relacion_conflictiva: boolean
  situacion_hijos: string
  todos_estudian: boolean
  viven_con_cliente: boolean
  necesidades_especiales: boolean
  viven_con_ex: boolean
  embarazo_actual: boolean

  // Criterio 6: Edad
  edad: number

  // Criterio 7: Capacidad de Maniobra (calculado automáticamente)
}

const INITIAL_FORM_DATA: EvaluacionFormData = {
  ingresos_mensuales: 0,
  gastos_fijos_mensuales: 0,
  otras_deudas: 0,
  meses_trabajo: 0,
  tipo_empleo: 'empleado_formal',
  sector_economico: 'servicios_esenciales',
  referencia1_observaciones: '',
  referencia1_calificacion: 0,
  referencia2_observaciones: '',
  referencia2_calificacion: 0,
  referencia3_observaciones: '',
  referencia3_calificacion: 0,
  familia_cercana: false,
  familia_pais: false,
  minutos_trabajo: 0,
  tipo_vivienda_detallado: 'alquiler_1_3',
  zona_urbana: false,
  servicios_nombre: false,
  zona_rural: false,
  personas_casa: 1,
  estado_civil: 'soltero_sin_pareja',
  pareja_trabaja: false,
  pareja_aval: false,
  pareja_desempleada: false,
  relacion_conflictiva: false,
  situacion_hijos: 'sin_hijos_no_planea',
  todos_estudian: false,
  viven_con_cliente: false,
  necesidades_especiales: false,
  viven_con_ex: false,
  embarazo_actual: false,
  edad: 0,
}

export interface UseEvaluacionRiesgoOptions {
  prestamo: Prestamo
  onSuccess: () => void
  onClose: () => void
}

export function useEvaluacionRiesgo({ prestamo, onSuccess, onClose }: UseEvaluacionRiesgoOptions) {
  const { user } = useSimpleAuth()
  const [formData, setFormData] = useState<EvaluacionFormData>(INITIAL_FORM_DATA)
  const [isLoading, setIsLoading] = useState(false)
  const [resultado, setResultado] = useState<any>(null)
  const [showSection, setShowSection] = useState<string>('criterio1')
  const [clienteEdad, setClienteEdad] = useState<number>(0)
  const [showFormularioAprobacion, setShowFormularioAprobacion] = useState(false)
  const [resumenPrestamos, setResumenPrestamos] = useState<any | null>(null)
  const [bloqueadoPorMora, setBloqueadoPorMora] = useState<boolean>(false)
  const [condicionesAprobacion, setCondicionesAprobacion] = useState({
    tasa_interes: 0.0,
    plazo_maximo: 36,
    fecha_base_calculo: new Date().toISOString().split('T')[0],
    observaciones: '',
  })

  const handleChange = <K extends keyof EvaluacionFormData>(
    field: K,
    value: EvaluacionFormData[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const loadPrestamoData = async () => {
    try {
      const [clienteRes, resumenRes] = await Promise.all([
        clienteService.getClientes({ cedula: prestamo.cedula }),
        prestamoService.getResumenPrestamos(prestamo.cedula),
      ])

      if (clienteRes?.data?.length > 0 && clienteRes.data[0].fecha_nacimiento) {
        const hoy = new Date()
        const nacimiento = new Date(clienteRes.data[0].fecha_nacimiento)
        let años = hoy.getFullYear() - nacimiento.getFullYear()
        const diferenciaMeses = hoy.getMonth() - nacimiento.getMonth()
        if (diferenciaMeses < 0 || (diferenciaMeses === 0 && hoy.getDate() < nacimiento.getDate())) {
          años -= 1
        }
        let meses = 0
        if (hoy.getMonth() >= nacimiento.getMonth()) {
          meses = hoy.getMonth() - nacimiento.getMonth()
          if (hoy.getDate() < nacimiento.getDate()) meses -= 1
        } else {
          meses = 12 - nacimiento.getMonth() + hoy.getMonth()
          if (hoy.getDate() < nacimiento.getDate()) meses -= 1
        }
        setClienteEdad(años + meses / 12)
      }

      setResumenPrestamos(resumenRes ?? { error: true, tiene_prestamos: false, prestamos: [] })
      const tieneMora = (resumenRes?.total_cuotas_mora || 0) > 0
      setBloqueadoPorMora(tieneMora)
      if (tieneMora) setShowSection('situacion')
    } catch (e) {
      setResumenPrestamos({ error: true, tiene_prestamos: false, prestamos: [] })
      console.error('Error cargando datos del préstamo:', e)
    }
  }

  const loadEvaluacionExistente = async () => {
    try {
      const ev = await prestamoService.getEvaluacionRiesgo(prestamo.id)
      if (ev?.datos_evaluacion) {
        setFormData((prev) => ({ ...prev, ...ev.datos_evaluacion }))
      }
    } catch {
      // No hay evaluación previa, ignorar
    }
  }

  useEffect(() => {
    loadPrestamoData()
  }, [prestamo.cedula])

  useEffect(() => {
    if (resultado?.sugerencias) {
      setCondicionesAprobacion({
        tasa_interes: resultado.sugerencias.tasa_interes_sugerida || 8.0,
        plazo_maximo: resultado.sugerencias.plazo_maximo_sugerido || 36,
        fecha_base_calculo: new Date().toISOString().split('T')[0],
        observaciones: `Aprobado después de evaluación de riesgo. Puntuación: ${resultado.puntuacion_total?.toFixed(2)}/100, Riesgo: ${resultado.clasificacion_riesgo}`,
      })
      setShowFormularioAprobacion(true)
    }
  }, [resultado])

  const seccion1Completa =
    (formData.ingresos_mensuales ?? 0) > 0 &&
    (formData.gastos_fijos_mensuales ?? 0) >= 0 &&
    (formData.otras_deudas ?? 0) >= 0

  const seccion2Completa =
    (formData.meses_trabajo ?? 0) >= 0 &&
    !!formData.tipo_empleo &&
    !!formData.sector_economico

  const seccion3Completa =
    !!formData.referencia1_observaciones?.trim() &&
    (formData.referencia1_calificacion ?? 0) > 0 &&
    !!formData.referencia2_observaciones?.trim() &&
    (formData.referencia2_calificacion ?? 0) > 0 &&
    !!formData.referencia3_observaciones?.trim() &&
    (formData.referencia3_calificacion ?? 0) > 0

  const seccion4Completa =
    typeof formData.familia_cercana === 'boolean' &&
    typeof formData.familia_pais === 'boolean' &&
    (formData.minutos_trabajo ?? 0) >= 0

  const seccion5Completa =
    !!formData.tipo_vivienda_detallado &&
    !!formData.estado_civil &&
    !!formData.situacion_hijos &&
    (formData.personas_casa ?? 0) > 0

  const seccion6Completa = (clienteEdad ?? 0) > 0
  const seccion7Completa = seccion1Completa

  const todasSeccionesCompletas =
    seccion1Completa &&
    seccion2Completa &&
    seccion3Completa &&
    seccion4Completa &&
    seccion5Completa &&
    seccion6Completa &&
    seccion7Completa

  const criteriosFaltantes: string[] = []
  if (!seccion1Completa) criteriosFaltantes.push('Criterio 1: Capacidad de Pago')
  if (!seccion2Completa) criteriosFaltantes.push('Criterio 2: Estabilidad Laboral')
  if (!seccion3Completa) criteriosFaltantes.push('Criterio 3: Referencias Personales')
  if (!seccion4Completa) criteriosFaltantes.push('Criterio 4: Arraigo Geográfico')
  if (!seccion5Completa) criteriosFaltantes.push('Criterio 5: Perfil Sociodemográfico')
  if (!seccion6Completa) criteriosFaltantes.push('Criterio 6: Edad del Cliente')
  if (!seccion7Completa) criteriosFaltantes.push('Criterio 7: Capacidad de Maniobra')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!todasSeccionesCompletas) {
      toast.error(
        `Debe completar todos los 7 criterios antes de evaluar. Faltan: ${criteriosFaltantes.join(', ')}`,
        { duration: 5000 }
      )
      return
    }
    if (bloqueadoPorMora) {
      toast.error('No puede continuar: el cliente tiene cuotas en mora.')
      setShowSection('situacion')
      return
    }

    const correo = user?.email || 'usuario@dominio'
    const confirmacion = window.confirm(
      '⚠️ CONFIRMACIÓN IMPORTANTE\n\n' +
        `Yo (correo: ${correo}) declaro que he revisado los documentos y que los mismos respaldan:\n` +
        '• Los ingresos coinciden con documentos\n' +
        '• Los gastos son verificables\n' +
        '• La información de empleo es correcta\n' +
        '• Los valores de anticipo son reales\n\n' +
        '¿Desea proceder con la evaluación?'
    )
    if (!confirmacion) {
      toast('Evaluación cancelada')
      return
    }

    setIsLoading(true)
    try {
      const datosEvaluacion = {
        ingresos_mensuales: formData.ingresos_mensuales,
        gastos_fijos_mensuales: formData.gastos_fijos_mensuales,
        otras_deudas: formData.otras_deudas,
        meses_trabajo: formData.meses_trabajo,
        tipo_empleo: formData.tipo_empleo,
        sector_economico: formData.sector_economico,
        referencia1_observaciones: formData.referencia1_observaciones,
        referencia1_calificacion: formData.referencia1_calificacion,
        referencia2_observaciones: formData.referencia2_observaciones,
        referencia2_calificacion: formData.referencia2_calificacion,
        referencia3_observaciones: formData.referencia3_observaciones,
        referencia3_calificacion: formData.referencia3_calificacion,
        familia_cercana: formData.familia_cercana,
        familia_pais: formData.familia_pais,
        minutos_trabajo: formData.minutos_trabajo,
        tipo_vivienda_detallado: formData.tipo_vivienda_detallado,
        zona_urbana: formData.zona_urbana,
        servicios_nombre: formData.servicios_nombre,
        zona_rural: formData.zona_rural,
        personas_casa: formData.personas_casa,
        estado_civil: formData.estado_civil,
        pareja_trabaja: formData.pareja_trabaja,
        pareja_aval: formData.pareja_aval,
        pareja_desempleada: formData.pareja_desempleada,
        relacion_conflictiva: formData.relacion_conflictiva,
        situacion_hijos: formData.situacion_hijos,
        todos_estudian: formData.todos_estudian,
        viven_con_cliente: formData.viven_con_cliente,
        necesidades_especiales: formData.necesidades_especiales,
        viven_con_ex: formData.viven_con_ex,
        embarazo_actual: formData.embarazo_actual,
        edad: clienteEdad || 0,
      }

      const response = await prestamoService.evaluarRiesgo(prestamo.id, datosEvaluacion)
      setResultado(response)
      setTimeout(() => setShowSection('resultado'), 100)
      toast.success('[OK] Fase 1 Completada: Evaluación de Riesgo guardada. El préstamo ahora está en estado EVALUADO.')

      setTimeout(() => {
        onSuccess()
        onClose()
        toast.info('✓ Ahora puede usar el nuevo icono en el dashboard para proceder con la Aprobación (Fase 2)')
      }, 2000)
    } catch (error: any) {
      toast.error(error.message || 'Error al evaluar riesgo')
    } finally {
      setIsLoading(false)
    }
  }

  const seccionCompleta = (id: string) => {
    switch (id) {
      case 'criterio1': return seccion1Completa
      case 'criterio2': return seccion2Completa
      case 'criterio3': return seccion3Completa
      case 'criterio4': return seccion4Completa
      case 'criterio5': return seccion5Completa
      case 'criterio6': return seccion6Completa
      case 'criterio7': return seccion7Completa
      default: return true
    }
  }

  return {
    formData,
    setFormData,
    handleChange,
    handleSubmit,
    loadPrestamoData,
    loadEvaluacionExistente,
    isLoading,
    resultado,
    showSection,
    setShowSection,
    clienteEdad,
    showFormularioAprobacion,
    setShowFormularioAprobacion,
    resumenPrestamos,
    bloqueadoPorMora,
    condicionesAprobacion,
    setCondicionesAprobacion,
    seccion1Completa,
    seccion2Completa,
    seccion3Completa,
    seccion4Completa,
    seccion5Completa,
    seccion6Completa,
    seccion7Completa,
    todasSeccionesCompletas,
    criteriosFaltantes,
    seccionCompleta,
    prestamo,
  }
}
