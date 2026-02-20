import { useState, useEffect } from 'react'
import { logger } from '../../../utils/logger'
import { getErrorMessage, isAxiosError, getErrorDetail } from '../../../types/errors'
import { clienteService } from '../../../services/clienteService'
import type { ClienteForm } from '../../../types'
import { validadoresService } from '../../../services/validadoresService'
import { useSimpleAuth } from '../../../store/simpleAuthStore'
import { useEstadosCliente } from '../../../hooks/useEstadosCliente'

export interface FormData {
  cedula: string
  nombres: string
  telefono: string
  email: string
  callePrincipal: string
  calleTransversal: string
  descripcion: string
  parroquia: string
  municipio: string
  ciudad: string
  estadoDireccion: string
  fechaNacimiento: string
  ocupacion: string
  estado: string
  notas: string
}

export interface ValidationResult {
  field: string
  isValid: boolean
  message: string
}

export interface CrearClienteFormProps {
  cliente?: { id?: number; cedula?: string; nombre?: string; apellido?: string; telefono?: string; email?: string; [key: string]: unknown }
  onClose: () => void
  onSuccess: () => void
  onClienteCreated?: () => void
  onOpenEditExisting?: (clienteId: number) => void
}

const getTodayDate = () => {
  const today = new Date()
  const day = String(today.getDate()).padStart(2, '0')
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const year = today.getFullYear()
  return `${day}/${month}/${year}`
}

const blankIfNN = (value: string | null | undefined): string => {
  if (value == null) return ''
  const trimmed = value.trim()
  return trimmed.toLowerCase() === 'nn' ? '' : trimmed
}

const isNN = (value: string | null | undefined): boolean => {
  if (value == null) return false
  return value.trim().toLowerCase() === 'nn'
}

const convertirFechaAISO = (fechaDDMMYYYY: string): string => {
  if (fechaDDMMYYYY.match(/^\d{4}-\d{2}-\d{2}$/)) return fechaDDMMYYYY
  const partes = fechaDDMMYYYY.split('/')
  if (partes.length === 3) {
    const [dia, mes, ano] = partes
    return `${ano}-${mes}-${dia}`
  }
  return fechaDDMMYYYY
}

const toTitleCase = (text: string): string => {
  if (!text) return text
  const endsWithSpace = /\s$/.test(text)
  const formatted = text
    .toLowerCase()
    .split(/\s+/)
    .filter(w => w.length > 0)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
  return endsWithSpace ? formatted + ' ' : formatted
}

const extraerNumeroTelefono = (telefonoCompleto: string): string => {
  if (!telefonoCompleto) return ''
  if (telefonoCompleto.startsWith('+58')) return telefonoCompleto.substring(3)
  return telefonoCompleto.replace(/\D/g, '').slice(0, 10)
}

const normalizarTelefono = (telefono: string): string => {
  const digits = (telefono || '').replace(/\D/g, '')
  if (digits.length > 10) return '9999999999'
  return digits.slice(0, 10)
}

export function useCrearCliente({
  cliente,
  onClose,
  onSuccess,
  onClienteCreated,
  onOpenEditExisting,
}: CrearClienteFormProps) {
  const { user } = useSimpleAuth()
  const { opciones: opcionesEstado } = useEstadosCliente()
  const usuarioRegistro = user?.email ?? 'formulario'

  const [formData, setFormData] = useState<FormData>({
    cedula: '',
    nombres: '',
    telefono: '',
    email: '',
    callePrincipal: '',
    calleTransversal: '',
    descripcion: '',
    parroquia: '',
    municipio: '',
    ciudad: '',
    estadoDireccion: '',
    fechaNacimiento: getTodayDate(),
    ocupacion: '',
    estado: 'ACTIVO',
    notas: 'No hay observacion',
  })

  const [datosOriginales, setDatosOriginales] = useState<Partial<FormData> | null>(null)
  const [validations, setValidations] = useState<ValidationResult[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const formatCedula = (text: string): string => {
    if (!text || text.trim() === '') return text
    const firstChar = text.charAt(0).toUpperCase()
    const validLetters = ['E', 'J', 'V', 'Z']
    if (validLetters.includes(firstChar)) return firstChar + text.slice(1)
    return text
  }

  const formatNombres = (text: string): string => toTitleCase(text ?? '')
  const formatOcupacion = (text: string): string => (text?.trim() ? toTitleCase(text) : text)
  const formatEmail = (text: string): string => (text ? text.toLowerCase() : text)

  const validateNombres = (nombres: string): ValidationResult => {
    if (isNN(nombres)) return { field: 'nombres', isValid: true, message: 'Valor omitido por NN' }
    if (!nombres || nombres.trim() === '') return { field: 'nombres', isValid: false, message: 'Nombres y apellidos requeridos' }
    const words = nombres.trim().split(/\s+/).filter(w => w.length > 0)
    const wordCount = words.length
    const textEndsWithSpace = nombres.trim().endsWith(' ')
    if (wordCount < 2 && textEndsWithSpace) return { field: 'nombres', isValid: false, message: 'Mínimo 2 palabras requeridas (nombre + apellido)' }
    if (wordCount > 7) return { field: 'nombres', isValid: false, message: `Máximo 7 palabras permitidas (tienes ${wordCount})` }
    if (wordCount >= 2 && wordCount <= 7) {
      const invalidWords = words.filter(w => w.length < 2)
      if (invalidWords.length > 0) return { field: 'nombres', isValid: false, message: 'Cada palabra debe tener mínimo 2 caracteres' }
      return { field: 'nombres', isValid: true, message: `${wordCount} palabra${wordCount > 1 ? 's' : ''} - Válido` }
    }
    if (wordCount === 1 && !textEndsWithSpace) return { field: 'nombres', isValid: false, message: 'Agrega más palabras (mínimo 2, máximo 7)' }
    return { field: 'nombres', isValid: false, message: 'Mínimo 2 palabras requeridas (nombre + apellido)' }
  }

  const validateOcupacion = (ocupacion: string): ValidationResult => {
    if (isNN(ocupacion)) return { field: 'ocupacion', isValid: true, message: 'Valor omitido por NN' }
    if (!ocupacion || ocupacion.trim() === '') return { field: 'ocupacion', isValid: false, message: 'Ocupación requerida' }
    if (ocupacion.trim().length < 2) return { field: 'ocupacion', isValid: false, message: 'Mínimo 2 caracteres' }
    const words = ocupacion.trim().split(/\s+/).filter(w => w.length > 0)
    if (words.length > 2) return { field: 'ocupacion', isValid: false, message: 'Máximo 2 palabras permitidas en ocupación' }
    return { field: 'ocupacion', isValid: true, message: 'Ocupación válida' }
  }

  const validateDescripcion = (descripcion: string): ValidationResult => {
    if (isNN(descripcion)) return { field: 'descripcion', isValid: true, message: 'Valor omitido por NN' }
    if (!descripcion || descripcion.trim() === '') return { field: 'descripcion', isValid: true, message: '' }
    const words = descripcion.trim().split(/\s+/).filter(w => w.length > 0)
    if (words.length < 5) return { field: 'descripcion', isValid: false, message: `Mínimo 5 palabras requeridas (tienes ${words.length})` }
    return { field: 'descripcion', isValid: true, message: `${words.length} palabras - Válido` }
  }

  const validateDireccion = (): ValidationResult => {
    if ((!formData.callePrincipal || formData.callePrincipal.trim() === '') && !isNN(formData.callePrincipal))
      return { field: 'direccion', isValid: false, message: 'Calle Principal es requerida' }
    if ((!formData.parroquia || formData.parroquia.trim() === '') && !isNN(formData.parroquia))
      return { field: 'direccion', isValid: false, message: 'Parroquia es requerida' }
    if ((!formData.municipio || formData.municipio.trim() === '') && !isNN(formData.municipio))
      return { field: 'direccion', isValid: false, message: 'Municipio es requerido' }
    if ((!formData.ciudad || formData.ciudad.trim() === '') && !isNN(formData.ciudad))
      return { field: 'direccion', isValid: false, message: 'Ciudad es requerida' }
    if ((!formData.estadoDireccion || formData.estadoDireccion.trim() === '') && !isNN(formData.estadoDireccion))
      return { field: 'direccion', isValid: false, message: 'Estado es requerido' }
    return { field: 'direccion', isValid: true, message: 'Dirección válida' }
  }

  const validateTelefono = (telefono: string): ValidationResult => {
    if (isNN(telefono)) return { field: 'telefono', isValid: true, message: 'Valor omitido por NN' }
    if (!telefono || telefono.trim() === '') return { field: 'telefono', isValid: false, message: 'Teléfono requerido' }
    const numeroLimpio = telefono.replace(/\D/g, '')
    if (numeroLimpio.length > 10) return { field: 'telefono', isValid: true, message: 'Se usará 9999999999 por defecto (>10 dígitos)' }
    if (numeroLimpio.length !== 10) return { field: 'telefono', isValid: false, message: 'El teléfono debe tener exactamente 10 dígitos' }
    if (numeroLimpio.startsWith('0')) return { field: 'telefono', isValid: false, message: 'El teléfono no puede empezar por 0' }
    if (!/^[1-9]\d{9}$/.test(numeroLimpio)) return { field: 'telefono', isValid: false, message: 'El teléfono solo puede contener números (0-9)' }
    return { field: 'telefono', isValid: true, message: 'Teléfono válido' }
  }

  const validateFechaNacimiento = (fecha: string): ValidationResult => {
    if (isNN(fecha)) return { field: 'fechaNacimiento', isValid: true, message: 'Valor omitido por NN' }
    if (!fecha || fecha.trim() === '') return { field: 'fechaNacimiento', isValid: false, message: 'Fecha de nacimiento requerida' }
    const fechaFormatRegex = /^(\d{2})\/(\d{2})\/(\d{4})$/
    if (!fechaFormatRegex.test(fecha.trim())) return { field: 'fechaNacimiento', isValid: false, message: 'Formato inválido. Use: DD/MM/YYYY' }
    const [, dia, mes, ano] = fecha.trim().match(fechaFormatRegex)!
    const diaNum = parseInt(dia, 10)
    const mesNum = parseInt(mes, 10)
    const anoNum = parseInt(ano, 10)
    if (diaNum < 1 || diaNum > 31) return { field: 'fechaNacimiento', isValid: false, message: 'Día inválido (1-31)' }
    if (mesNum < 1 || mesNum > 12) return { field: 'fechaNacimiento', isValid: false, message: 'Mes inválido (1-12)' }
    if (anoNum < 1900 || anoNum > 2100) return { field: 'fechaNacimiento', isValid: false, message: 'Año inválido (1900-2100)' }
    const fechaNac = new Date(anoNum, mesNum - 1, diaNum)
    if (fechaNac.getDate() !== diaNum || fechaNac.getMonth() !== mesNum - 1 || fechaNac.getFullYear() !== anoNum)
      return { field: 'fechaNacimiento', isValid: false, message: 'Fecha inválida (ej: 31/02 no existe)' }
    const hoy = new Date()
    hoy.setHours(0, 0, 0, 0)
    if (fechaNac >= hoy) return { field: 'fechaNacimiento', isValid: false, message: 'La fecha de nacimiento no puede ser futura o de hoy' }
    const fecha21 = new Date(anoNum + 21, mesNum - 1, diaNum)
    if (fecha21 > hoy) return { field: 'fechaNacimiento', isValid: false, message: 'Debe tener al menos 21 años cumplidos' }
    const fecha60 = new Date(anoNum + 60, mesNum - 1, diaNum)
    if (fecha60 <= hoy) return { field: 'fechaNacimiento', isValid: false, message: 'No puede tener más de 60 años cumplidos' }
    return { field: 'fechaNacimiento', isValid: true, message: 'Fecha válida' }
  }

  const validateEmail = (email: string): ValidationResult => {
    if (isNN(email)) return { field: 'email', isValid: true, message: 'Valor omitido por NN' }
    if (!email || email.trim() === '') return { field: 'email', isValid: false, message: 'Email requerido' }
    const emailTrimmed = email.trim()
    if (emailTrimmed.includes(' ')) return { field: 'email', isValid: false, message: 'El email no puede contener espacios' }
    if (emailTrimmed.includes(',')) return { field: 'email', isValid: false, message: 'El email no puede contener comas' }
    if (!emailTrimmed.includes('@')) return { field: 'email', isValid: false, message: 'El email debe contener un @' }
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    if (!emailPattern.test(emailTrimmed)) return { field: 'email', isValid: false, message: 'El email debe tener una extensión válida (.com, .edu, .gob, etc.)' }
    return { field: 'email', isValid: true, message: 'Email válido' }
  }

  const validateFieldWithBackend = async (field: string, value: string): Promise<ValidationResult> => {
    if (field === 'cedula' && !(value || '').trim()) return { field: 'cedula', isValid: true, message: 'Se usará Z999999999 por defecto' }
    const campoMapper: Record<string, string> = {
      cedula: 'cedula_venezuela',
      nombres: 'nombre',
      telefono: 'telefono_venezuela',
      email: 'email',
      fechaNacimiento: 'fecha',
    }
    const tipoValidador = campoMapper[field]
    if (!tipoValidador) {
      if (!value) return { field, isValid: false, message: `${field} es obligatorio` }
      return { field, isValid: true, message: '' }
    }
    try {
      const resultado = await validadoresService.validarCampo(tipoValidador, value, 'VENEZUELA')
      if (resultado.validacion.valido) return { field, isValid: true, message: resultado.validacion.mensaje || 'Campo válido' }
      const errorMsg = resultado.validacion.error || 'Campo inválido'
      const sugerencia = resultado.validacion.sugerencia || ''
      return { field, isValid: false, message: sugerencia ? `${errorMsg}. ${sugerencia}` : errorMsg }
    } catch {
      if (!value) return { field, isValid: false, message: `${field} es obligatorio` }
      return { field, isValid: true, message: '' }
    }
  }

  const handleInputChange = async (field: keyof FormData, value: string) => {
    let formattedValue = value
    if (field === 'cedula') formattedValue = formatCedula(value)
    else if (field === 'nombres') formattedValue = formatNombres(value)
    else if (field === 'ocupacion') formattedValue = formatOcupacion(value)
    else if (field === 'email') formattedValue = formatEmail(value)

    setFormData(prev => ({ ...prev, [field]: formattedValue }))

    let validation: ValidationResult
    if (field === 'nombres') validation = validateNombres(formattedValue)
    else if (field === 'ocupacion') validation = validateOcupacion(formattedValue)
    else if (field === 'fechaNacimiento') validation = validateFechaNacimiento(formattedValue)
    else if (field === 'telefono') validation = validateTelefono(formattedValue)
    else if (field === 'email') validation = validateEmail(formattedValue)
    else if (field === 'descripcion') validation = validateDescripcion(formattedValue)
    else if (['callePrincipal', 'calleTransversal', 'parroquia', 'municipio', 'ciudad', 'estadoDireccion'].includes(field)) {
      setTimeout(() => {
        const direccionValidation = validateDireccion()
        setValidations(prev => [...prev.filter(v => v.field !== 'direccion'), direccionValidation])
      }, 100)
      validation = { field: 'direccion', isValid: true, message: '' }
    } else {
      validation = !cliente ? await validateFieldWithBackend(field, formattedValue) : { field, isValid: true, message: '' }
    }

    setValidations(prev => [...prev.filter(v => v.field !== field), validation])
  }

  const isFormValid = () => {
    if (cliente) return true
    const requiredFields: (keyof FormData)[] = [
      'cedula', 'nombres', 'telefono', 'email',
      'callePrincipal', 'parroquia', 'municipio', 'ciudad', 'estadoDireccion',
      'fechaNacimiento', 'ocupacion',
    ]
    const nombresValidation = validateNombres(formData.nombres)
    const ocupacionValidation = validateOcupacion(formData.ocupacion)
    const direccionValidation = validateDireccion()
    const fechaNacimientoValidation = validateFechaNacimiento(formData.fechaNacimiento)
    const telefonoValidation = validateTelefono(formData.telefono)
    const emailValidation = validateEmail(formData.email)

    const direccionValida = direccionValidation.isValid && formData.callePrincipal && formData.parroquia && formData.municipio && formData.ciudad && formData.estadoDireccion

    return requiredFields.every(field => {
      if (field === 'nombres') return nombresValidation.isValid && formData[field]
      if (field === 'ocupacion') return ocupacionValidation.isValid && formData[field]
      if (field === 'fechaNacimiento') return fechaNacimientoValidation.isValid && formData[field]
      if (field === 'telefono') return telefonoValidation.isValid && formData[field]
      if (field === 'email') return emailValidation.isValid && formData[field]
      if (field === 'cedula') {
        const cedulaVal = (formData.cedula || '').trim()
        if (!cedulaVal) return true
        const validation = validations.find(v => v.field === 'cedula')
        return validation?.isValid ?? false
      }
      if (['callePrincipal', 'parroquia', 'municipio', 'ciudad', 'estadoDireccion'].includes(field)) return direccionValida && formData[field]
      const validation = validations.find(v => v.field === field)
      return validation?.isValid && formData[field]
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if ((!formData.callePrincipal || !formData.callePrincipal.trim()) && !isNN(formData.callePrincipal)) { alert('ERROR: Debe completar el campo Calle Principal'); return }
    if ((!formData.parroquia || !formData.parroquia.trim()) && !isNN(formData.parroquia)) { alert('ERROR: Debe completar el campo Parroquia'); return }
    if ((!formData.municipio || !formData.municipio.trim()) && !isNN(formData.municipio)) { alert('ERROR: Debe completar el campo Municipio'); return }
    if ((!formData.ciudad || !formData.ciudad.trim()) && !isNN(formData.ciudad)) { alert('ERROR: Debe completar el campo Ciudad'); return }
    if ((!formData.estadoDireccion || !formData.estadoDireccion.trim()) && !isNN(formData.estadoDireccion)) { alert('ERROR: Debe completar el campo Estado'); return }
    if ((!formData.fechaNacimiento || !formData.fechaNacimiento.trim()) && !isNN(formData.fechaNacimiento)) { alert('ERROR: Debe completar el campo Fecha de Nacimiento'); return }
    if ((!formData.ocupacion || !formData.ocupacion.trim()) && !isNN(formData.ocupacion)) { alert('ERROR: Debe completar el campo Ocupación'); return }
    if (formData.descripcion && formData.descripcion.trim() && !isNN(formData.descripcion)) {
      const descripcionValidation = validateDescripcion(formData.descripcion)
      if (!descripcionValidation.isValid) { alert(`ERROR: ${descripcionValidation.message}`); return }
    }
    if (!isFormValid()) return

    setIsSubmitting(true)
    try {
      const telefonoLimpio = normalizarTelefono(blankIfNN(formData.telefono))
      const telefonoCompleto = `+58${telefonoLimpio}`
      const nombresFormateado = toTitleCase(blankIfNN(formData.nombres))
      const ocupacionFormateada = toTitleCase(blankIfNN(formData.ocupacion))
      const direccionCompleta = JSON.stringify({
        callePrincipal: toTitleCase(blankIfNN(formData.callePrincipal)),
        calleTransversal: blankIfNN(formData.calleTransversal) ? toTitleCase(blankIfNN(formData.calleTransversal)) : null,
        descripcion: blankIfNN(formData.descripcion) || null,
        parroquia: toTitleCase(blankIfNN(formData.parroquia)),
        municipio: toTitleCase(blankIfNN(formData.municipio)),
        ciudad: toTitleCase(blankIfNN(formData.ciudad)),
        estado: toTitleCase(blankIfNN(formData.estadoDireccion)),
      })

      const todosLosDatos = {
        cedula: formatCedula(blankIfNN(formData.cedula)) || 'Z999999999',
        nombres: nombresFormateado,
        telefono: telefonoCompleto,
        email: blankIfNN(formData.email),
        direccion: direccionCompleta,
        fecha_nacimiento: convertirFechaAISO(blankIfNN(formData.fechaNacimiento)),
        ocupacion: ocupacionFormateada,
        estado: formData.estado,
        notas: blankIfNN(formData.notas) || 'No hay observacion',
        usuario_registro: usuarioRegistro,
      }

      if (cliente && typeof cliente.id === 'number') {
        logger.info('Editando cliente existente', { clienteId: cliente.id })
        const valoresIguales = (valor1: unknown, valor2: unknown): boolean => {
          if ((valor1 == null || valor1 === '') && (valor2 == null || valor2 === '')) return true
          if (valor1 == null || valor2 == null) return false
          const v1 = String(valor1).trim().toLowerCase().replace(/\s+/g, ' ')
          const v2 = String(valor2).trim().toLowerCase().replace(/\s+/g, ' ')
          return v1 === v2
        }
        const clienteData: Record<string, unknown> = {}
        if (datosOriginales) {
          const reconstruirDireccionOriginal = () => {
            try {
              return JSON.stringify({
                callePrincipal: toTitleCase(blankIfNN(datosOriginales.callePrincipal || '')),
                calleTransversal: blankIfNN(datosOriginales.calleTransversal || '') ? toTitleCase(blankIfNN(datosOriginales.calleTransversal || '')) : null,
                descripcion: blankIfNN(datosOriginales.descripcion || '') || null,
                parroquia: toTitleCase(blankIfNN(datosOriginales.parroquia || '')),
                municipio: toTitleCase(blankIfNN(datosOriginales.municipio || '')),
                ciudad: toTitleCase(blankIfNN(datosOriginales.ciudad || '')),
                estado: toTitleCase(blankIfNN(datosOriginales.estadoDireccion || '')),
              })
            } catch { return '' }
          }
          const direccionOriginal = reconstruirDireccionOriginal()
          const telefonoOriginal = datosOriginales.telefono ? `+58${extraerNumeroTelefono(datosOriginales.telefono)}` : ''
          if (!valoresIguales(todosLosDatos.cedula, datosOriginales.cedula)) clienteData.cedula = todosLosDatos.cedula
          if (!valoresIguales(todosLosDatos.nombres, datosOriginales.nombres)) clienteData.nombres = todosLosDatos.nombres
          if (!valoresIguales(todosLosDatos.telefono, telefonoOriginal)) clienteData.telefono = todosLosDatos.telefono
          if (!valoresIguales(todosLosDatos.email, datosOriginales.email)) clienteData.email = todosLosDatos.email
          if (!valoresIguales(todosLosDatos.direccion, direccionOriginal)) clienteData.direccion = todosLosDatos.direccion
          if (!valoresIguales(todosLosDatos.fecha_nacimiento, convertirFechaAISO(datosOriginales.fechaNacimiento || ''))) clienteData.fecha_nacimiento = todosLosDatos.fecha_nacimiento
          if (!valoresIguales(todosLosDatos.ocupacion, datosOriginales.ocupacion)) clienteData.ocupacion = todosLosDatos.ocupacion
          if (!valoresIguales(todosLosDatos.estado, datosOriginales.estado)) clienteData.estado = todosLosDatos.estado
          if (!valoresIguales(todosLosDatos.notas, datosOriginales.notas)) clienteData.notas = todosLosDatos.notas
        } else {
          Object.assign(clienteData, todosLosDatos)
        }
        if (Object.keys(clienteData).length === 0) {
          logger.info('No hay cambios detectados')
          alert('No se detectaron cambios en el cliente')
          setIsSubmitting(false)
          return
        }
        await clienteService.updateCliente(String(cliente.id), clienteData as Partial<ClienteForm>)
        logger.info('Cliente actualizado exitosamente', { clienteId: cliente.id })
      } else {
        logger.info('Creando nuevo cliente', { cedula: todosLosDatos.cedula })
        await clienteService.createCliente(todosLosDatos as ClienteForm & { estado?: string; usuario_registro?: string })
        logger.info('Cliente creado exitosamente', { cedula: todosLosDatos.cedula })
      }
      onSuccess()
      onClienteCreated?.()
      onClose()
    } catch (error: unknown) {
      const errorMessage = getErrorMessage(error)
      const status = isAxiosError(error) ? error.response?.status : undefined
      const detail = getErrorDetail(error)
      const responseData = isAxiosError(error) ? error.response?.data as { message?: string } | undefined : undefined
      logger.error('Error creando cliente', { action: 'create_client_error', component: 'CrearClienteForm', error: errorMessage, status, detail, message: responseData?.message })

      let _errorMessageUser = 'Error al crear el cliente. Por favor, intente nuevamente.'
      let tipoDuplicado = ''
      if (isAxiosError(error)) {
        const errorDetail = getErrorDetail(error)
        const respData = error.response?.data as { message?: string } | undefined
        const statusCode = error.response?.status
        if (statusCode === 400 || statusCode === 409) {
          const detailText = errorDetail || ''
          if (detailText.includes('misma cédula')) { tipoDuplicado = 'cedula'; _errorMessageUser = errorDetail || 'Ya existe un cliente con esa cédula.' }
          else if (detailText.includes('mismo nombre completo')) { tipoDuplicado = 'nombre'; _errorMessageUser = errorDetail || 'Ya existe un cliente con ese nombre.' }
          else if (detailText.includes('mismo email')) { tipoDuplicado = 'email'; _errorMessageUser = errorDetail || 'Ya existe un cliente con ese email.' }
          else if (detailText.includes('mismo teléfono')) { tipoDuplicado = 'telefono'; _errorMessageUser = errorDetail || 'Ya existe un cliente con ese teléfono.' }
          else if (detailText.includes('cédula') || detailText.includes('nombre') || detailText.includes('email') || detailText.includes('teléfono')) { tipoDuplicado = 'datos'; _errorMessageUser = errorDetail || 'Cédula, nombre, email o teléfono ya pertenecen a otro cliente.' }
          else { _errorMessageUser = errorDetail || 'Datos duplicados (cédula, nombre, email o teléfono).' }
        } else if (errorDetail) _errorMessageUser = errorDetail
        else if (respData?.message) _errorMessageUser = respData.message
      }
      let existingId: number | null = null
      const detailText: string = getErrorDetail(error) || ''
      const match = detailText.match(/ID:\s*(\d+)/i)
      if (match?.[1]) existingId = Number(match[1])

      if (isAxiosError(error) && (error.response?.status === 400 || error.response?.status === 409)) {
        const mensajes: Record<string, string> = { cedula: 'la misma cédula', nombre: 'el mismo nombre completo', email: 'el mismo email', telefono: 'el mismo teléfono', datos: 'la misma cédula, nombre, email o teléfono' }
        const mensajeDuplicado = mensajes[tipoDuplicado] || 'la misma cédula, nombre, email o teléfono'
        const friendly = existingId
          ? `ADVERTENCIA: Ya existe un cliente con ${mensajeDuplicado}.\n\nCliente existente ID: ${existingId}\n\n¿Deseas abrir el cliente existente para editarlo?`
          : `ADVERTENCIA: Ya existe un cliente con ${mensajeDuplicado}.\n\n¿Deseas buscar el cliente existente?`
        const wantsEdit = window.confirm(friendly)
        if (wantsEdit) {
          onClose()
          if (existingId && onOpenEditExisting) onOpenEditExisting(existingId)
        }
      } else {
        alert(`ERROR: ${errorMessage}`)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const getFieldValidation = (field: string) => (cliente ? null : validations.find(v => v.field === field))

  useEffect(() => {
    if (cliente) {
      const convertirFechaLocal = (fechaISO: string): string => {
        if (fechaISO.match(/^\d{2}\/\d{2}\/\d{4}$/)) return fechaISO
        if (fechaISO.match(/^\d{4}-\d{2}-\d{2}$/)) {
          const partes = fechaISO.split('-')
          if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`
        }
        return fechaISO
      }
      const decodeHtmlEntities = (text: string): string => {
        if (!text) return ''
        const textarea = document.createElement('textarea')
        textarea.innerHTML = text
        return textarea.value
      }
      const parsearDireccion = (direccionCompleta: string) => {
        if (!direccionCompleta) return { callePrincipal: '', calleTransversal: '', descripcion: '', parroquia: '', municipio: '', ciudad: '', estadoDireccion: '' }
        let direccionLimpia = decodeHtmlEntities(direccionCompleta.trim())
          .replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'")
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
        if (direccionLimpia.trim().startsWith('{') && direccionLimpia.trim().endsWith('}')) {
          try {
            const parsed = JSON.parse(direccionLimpia)
            return {
              callePrincipal: String(parsed.callePrincipal || '').trim(),
              calleTransversal: String(parsed.calleTransversal || '').trim(),
              descripcion: String(parsed.descripcion || '').trim(),
              parroquia: String(parsed.parroquia || '').trim(),
              municipio: String(parsed.municipio || '').trim(),
              ciudad: String(parsed.ciudad || '').trim(),
              estadoDireccion: String(parsed.estado || parsed.estadoDireccion || '').trim(),
            }
          } catch {
            const calleMatch = direccionLimpia.match(/"callePrincipal"\s*:\s*"([^"]*)"/i)
            const parroquiaMatch = direccionLimpia.match(/"parroquia"\s*:\s*"([^"]*)"/i)
            const municipioMatch = direccionLimpia.match(/"municipio"\s*:\s*"([^"]*)"/i)
            const ciudadMatch = direccionLimpia.match(/"ciudad"\s*:\s*"([^"]*)"/i)
            const estadoMatch = direccionLimpia.match(/"estado"\s*:\s*"([^"]*)"/i)
            return {
              callePrincipal: calleMatch?.[1]?.trim() ?? '',
              calleTransversal: '',
              descripcion: '',
              parroquia: parroquiaMatch?.[1]?.trim() ?? '',
              municipio: municipioMatch?.[1]?.trim() ?? '',
              ciudad: ciudadMatch?.[1]?.trim() ?? '',
              estadoDireccion: estadoMatch?.[1]?.trim() ?? '',
            }
          }
        }
        const partes = direccionLimpia.split('|')
        if (partes.length >= 7) {
          return {
            callePrincipal: partes[0]?.trim() || '',
            calleTransversal: partes[1]?.trim() || '',
            descripcion: partes[2]?.trim() || '',
            parroquia: partes[3]?.trim() || '',
            municipio: partes[4]?.trim() || '',
            ciudad: partes[5]?.trim() || '',
            estadoDireccion: partes[6]?.trim() || '',
          }
        }
        if (!direccionLimpia.includes('{') && !direccionLimpia.includes('}') && !direccionLimpia.includes('&quot;')) {
          return { callePrincipal: direccionLimpia, calleTransversal: '', descripcion: '', parroquia: '', municipio: '', ciudad: '', estadoDireccion: '' }
        }
        return { callePrincipal: '', calleTransversal: '', descripcion: '', parroquia: '', municipio: '', ciudad: '', estadoDireccion: '' }
      }
      const direccionRaw = typeof cliente.direccion === 'string' ? cliente.direccion : ''
      const direccionData = parsearDireccion(direccionRaw)
      const nombresValue = cliente.nombres || ''
      const newFormData: FormData = {
        cedula: typeof cliente.cedula === 'string' ? cliente.cedula : '',
        nombres: typeof nombresValue === 'string' ? nombresValue : '',
        telefono: extraerNumeroTelefono(typeof cliente.telefono === 'string' ? cliente.telefono : ''),
        email: typeof cliente.email === 'string' ? cliente.email : '',
        ...direccionData,
        fechaNacimiento: convertirFechaLocal(typeof cliente.fecha_nacimiento === 'string' ? cliente.fecha_nacimiento : ''),
        ocupacion: typeof cliente.ocupacion === 'string' ? cliente.ocupacion : '',
        estado: (typeof cliente.estado === 'string' && cliente.estado) ? cliente.estado : 'ACTIVO',
        notas: typeof cliente.notas === 'string' ? cliente.notas : 'No hay observacion',
      }
      setDatosOriginales({ ...newFormData })
      setFormData(newFormData)
      setValidations([])
    } else {
      setFormData({
        cedula: '', nombres: '', telefono: '', email: '',
        callePrincipal: '', calleTransversal: '', descripcion: '', parroquia: '', municipio: '', ciudad: '', estadoDireccion: '',
        fechaNacimiento: getTodayDate(), ocupacion: '', estado: 'ACTIVO', notas: 'No hay observacion',
      })
      setDatosOriginales(null)
    }
  }, [cliente])

  return {
    formData,
    handleInputChange,
    handleSubmit,
    getFieldValidation,
    isFormValid,
    isSubmitting,
    opcionesEstado,
    cliente,
  }
}
