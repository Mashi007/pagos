import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { logger } from '@/utils/logger'
import { getErrorMessage, isAxiosError, getErrorDetail } from '@/types/errors'
import {
  User,
  CreditCard,
  Phone,
  Mail,
  DollarSign,
  Calendar,
  Users,
  Building,
  Save,
  X,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Download,
  FileSpreadsheet,
  MapPin,
  Briefcase,
  FileText,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { clienteService } from '@/services/clienteService'
import { validadoresService } from '@/services/validadoresService'
import { ExcelUploader } from './ExcelUploader'
import { useEscapeClose } from '@/hooks/useEscapeClose'

interface FormData {
  // Datos personales - OBLIGATORIOS
  cedula: string
  nombres: string  // ✅ UNIFICA nombres + apellidos (2-4 palabras)
  telefono: string
  email: string
  // Dirección estructurada
  callePrincipal: string
  calleTransversal: string
  descripcion: string  // Lugar cercano, color de casa
  parroquia: string
  municipio: string
  ciudad: string
  estadoDireccion: string  // Estado (nuevo campo)
  fechaNacimiento: string
  ocupacion: string  // ✅ MÁXIMO 2 palabras

  // Estado - OBLIGATORIO
  estado: 'ACTIVO' | 'INACTIVO' | 'FINALIZADO'

  // Notas - OBLIGATORIO (default 'NA')
  notas: string
}

interface ValidationResult {
  field: string
  isValid: boolean
  message: string
}

interface CrearClienteFormProps {
  cliente?: { id?: number; cedula?: string; nombre?: string; apellido?: string; [key: string]: unknown } // Cliente existente para edición
  onClose: () => void
  onSuccess: () => void
  onClienteCreated?: () => void
  // Opcional: abrir edición desde el listado cuando detectamos duplicado
  onOpenEditExisting?: (clienteId: number) => void
}

export function CrearClienteForm({ cliente, onClose, onSuccess, onClienteCreated, onOpenEditExisting }: CrearClienteFormProps) {
  // Cierre global con ESC
  useEscapeClose(onClose, true)
  // Normalizador: si el usuario coloca 'nn' (cualquier caso/espacios), convertir a vacío
  const blankIfNN = (value: string | null | undefined): string => {
    if (value == null) return ''
    const trimmed = value.trim()
    return trimmed.toLowerCase() === 'nn' ? '' : trimmed
  }
  // ✅ Función para convertir DD/MM/YYYY a YYYY-MM-DD
  const convertirFechaAISO = (fechaDDMMYYYY: string): string => {
    // Si la fecha ya está en formato ISO (YYYY-MM-DD), devolverla tal cual
    if (fechaDDMMYYYY.match(/^\d{4}-\d{2}-\d{2}$/)) {
      return fechaDDMMYYYY
    }
    // Si está en formato DD/MM/YYYY, convertir
    const partes = fechaDDMMYYYY.split('/')
    if (partes.length === 3) {
      const [dia, mes, ano] = partes
      return `${ano}-${mes}-${dia}`
    }
    return fechaDDMMYYYY
  }

  // Función para convertir fecha de ISO a DD/MM/YYYY
  const convertirFechaDeISO = (fechaISO: string): string => {
    // Si ya está en formato DD/MM/YYYY, devolverla tal cual
    if (fechaISO.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
      return fechaISO
    }
    // Si está en formato ISO (YYYY-MM-DD), convertir
    if (fechaISO.match(/^\d{4}-\d{2}-\d{2}$/)) {
      const partes = fechaISO.split('-')
      if (partes.length === 3) {
        const [ano, mes, dia] = partes
        return `${dia}/${mes}/${ano}`
      }
    }
    return fechaISO
  }

  // ✅ Función para obtener fecha de hoy en formato DD/MM/YYYY
  const getTodayDate = () => {
    const today = new Date()
    const day = String(today.getDate()).padStart(2, '0')
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const year = today.getFullYear()
    return `${day}/${month}/${year}`
  }

  // Helper: detectar 'nn' (cualquier caso/espacios)
  const isNN = (value: string | null | undefined): boolean => {
    if (value == null) return false
    return value.trim().toLowerCase() === 'nn'
  }

  const [formData, setFormData] = useState<FormData>({
    cedula: '',
    nombres: '',  // ✅ UNIFICA nombres + apellidos
    telefono: '',
    email: '',
    // Dirección estructurada
    callePrincipal: '',
    calleTransversal: '',
    descripcion: '',
    parroquia: '',
    municipio: '',
    ciudad: '',
    estadoDireccion: '',
    fechaNacimiento: getTodayDate(), // ✅ Fecha por defecto: hoy
    ocupacion: '',
    estado: 'ACTIVO',
    notas: 'No hay observacion'  // ✅ Default 'No hay observacion'
  })

  // ✅ Estado para almacenar los datos originales del cliente (para comparación en edición)
  const [datosOriginales, setDatosOriginales] = useState<Partial<FormData> | null>(null)

  const [validations, setValidations] = useState<ValidationResult[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showExcelUploader, setShowExcelUploader] = useState(false)

  // ✅ Función para extraer el número de teléfono de la BD (+581234567890 → 1234567890)
  const extraerNumeroTelefono = (telefonoCompleto: string): string => {
    if (!telefonoCompleto) return ''

    // Si empieza con +58, eliminar el prefijo
    if (telefonoCompleto.startsWith('+58')) {
      return telefonoCompleto.substring(3)
    }

    // Si ya es solo el número, devolverlo
    return telefonoCompleto.replace(/\D/g, '').slice(0, 10)
  }

  // Pre-cargar datos del cliente si se está editando
  useEffect(() => {
    if (cliente) {
      console.log('📝 MODO EDITAR - Cargando datos del cliente:', cliente)
      console.log('📝 Datos completos del cliente recibidos:', JSON.stringify(cliente, null, 2))

      // Dividir nombres si vienen unificados de la BD
      let nombresValue = cliente.nombres || ''

      // Función local para convertir fecha
      const convertirFechaLocal = (fechaISO: string): string => {
        // Si ya está en formato DD/MM/YYYY, devolverla tal cual
        if (fechaISO.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
          return fechaISO
        }
        // Si está en formato ISO (YYYY-MM-DD), convertir
        if (fechaISO.match(/^\d{4}-\d{2}-\d{2}$/)) {
          const partes = fechaISO.split('-')
          if (partes.length === 3) {
            const [ano, mes, dia] = partes
            return `${dia}/${mes}/${ano}`
          }
        }
        return fechaISO
      }

      // ✅ Función para parsear dirección estructurada desde la BD
      const parsearDireccion = (direccionCompleta: string) => {
        if (!direccionCompleta) {
          return {
            callePrincipal: '',
            calleTransversal: '',
            descripcion: '',
            parroquia: '',
            municipio: '',
            ciudad: '',
            estadoDireccion: ''
          }
        }

        // Intentar parsear si está en formato JSON
        try {
          const parsed = JSON.parse(direccionCompleta)
          return {
            callePrincipal: parsed.callePrincipal || '',
            calleTransversal: parsed.calleTransversal || '',
            descripcion: parsed.descripcion || '',
            parroquia: parsed.parroquia || '',
            municipio: parsed.municipio || '',
            ciudad: parsed.ciudad || '',
            estadoDireccion: parsed.estado || parsed.estadoDireccion || ''
          }
        } catch {
          // Si no es JSON, dividir por separadores comunes o dejarlo en callePrincipal
          const partes = direccionCompleta.split('|')
          if (partes.length >= 7) {
            return {
              callePrincipal: partes[0] || '',
              calleTransversal: partes[1] || '',
              descripcion: partes[2] || '',
              parroquia: partes[3] || '',
              municipio: partes[4] || '',
              ciudad: partes[5] || '',
              estadoDireccion: partes[6] || ''
            }
          }
          // Si es un texto simple, dejar todo en callePrincipal
          return {
            callePrincipal: direccionCompleta,
            calleTransversal: '',
            descripcion: '',
            parroquia: '',
            municipio: '',
            ciudad: '',
            estadoDireccion: ''
          }
        }
      }

      const direccionData = parsearDireccion(typeof cliente.direccion === 'string' ? cliente.direccion : '')

      const newFormData: FormData = {
        cedula: typeof cliente.cedula === 'string' ? cliente.cedula : '',
        nombres: typeof nombresValue === 'string' ? nombresValue : '',  // ✅ nombres unificados
        telefono: extraerNumeroTelefono(typeof cliente.telefono === 'string' ? cliente.telefono : ''),  // ✅ Extraer solo el número (sin +58)
        email: typeof cliente.email === 'string' ? cliente.email : '',
        ...direccionData,
        fechaNacimiento: convertirFechaLocal(typeof cliente.fecha_nacimiento === 'string' ? cliente.fecha_nacimiento : ''), // ✅ Convertir ISO a DD/MM/YYYY
        ocupacion: typeof cliente.ocupacion === 'string' ? cliente.ocupacion : '',
        estado: (typeof cliente.estado === 'string' && ['ACTIVO', 'INACTIVO', 'FINALIZADO'].includes(cliente.estado)) ? cliente.estado as 'ACTIVO' | 'INACTIVO' | 'FINALIZADO' : 'ACTIVO',  // ✅ Mantener estado del cliente existente en edición
        notas: typeof cliente.notas === 'string' ? cliente.notas : 'No hay observacion'
      }

      console.log('📝 MODO EDITAR - Datos formateados para cargar:', newFormData)

      // ✅ Guardar datos originales para comparación posterior
      setDatosOriginales({ ...newFormData })

      // ✅ Asegurar que los datos se carguen correctamente
      setFormData(newFormData)

      // ✅ Limpiar validaciones previas al cargar datos de edición
      setValidations([])

      console.log('✅ MODO EDITAR - Formulario cargado con datos del cliente')
    } else {
      // ✅ Si no hay cliente, resetear el formulario a valores por defecto
      setFormData({
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
        estado: 'ACTIVO',  // ✅ Estado por defecto SOLO para clientes nuevos
        notas: 'No hay observacion'  // ✅ Default 'No hay observacion'
      })
      // ✅ Limpiar datos originales cuando no hay cliente (modo creación)
      setDatosOriginales(null)
    }
  }, [cliente])


  // ✅ Validaciones personalizadas para nombres y ocupacion
  // Regla: Mínimo 2 palabras, máximo 7 palabras en nombres+apellidos
  const validateNombres = (nombres: string): ValidationResult => {
    if (isNN(nombres)) {
      return { field: 'nombres', isValid: true, message: 'Valor omitido por NN' }
    }
    if (!nombres || nombres.trim() === '') {
      return { field: 'nombres', isValid: false, message: 'Nombres y apellidos requeridos' }
    }

    // Dividir en palabras, filtrando espacios vacíos y espacios múltiples
    const words = nombres.trim().split(/\s+/).filter(w => w.length > 0)
    const wordCount = words.length

    // Si está escribiendo (palabra incompleta al final), no contar esa última palabra si no tiene espacio después
    // Esto permite escribir libremente hasta 7 palabras completas
    const textEndsWithSpace = nombres.trim().endsWith(' ')

    // Validar mínimo 2 palabras (solo cuando el usuario ha terminado de escribir)
    // Si está escribiendo la primera o segunda palabra, permitir continuar
    if (wordCount < 2 && textEndsWithSpace) {
      return { field: 'nombres', isValid: false, message: 'Mínimo 2 palabras requeridas (nombre + apellido)' }
    }

    // Validar máximo 7 palabras
    // Solo mostrar error si hay más de 7 palabras completas (con espacios)
    if (wordCount > 7) {
      return { field: 'nombres', isValid: false, message: `Máximo 7 palabras permitidas (tienes ${wordCount})` }
    }

    // Si hay exactamente 7 palabras o menos y cumple mínimo, validar estructura
    if (wordCount >= 2 && wordCount <= 7) {
      // Validar que cada palabra tenga mínimo 2 caracteres
      const invalidWords = words.filter(w => w.length < 2)
      if (invalidWords.length > 0) {
        return { field: 'nombres', isValid: false, message: 'Cada palabra debe tener mínimo 2 caracteres' }
      }

      // Si tiene entre 2 y 7 palabras válidas, está correcto
      return { field: 'nombres', isValid: true, message: `${wordCount} palabra${wordCount > 1 ? 's' : ''} - Válido` }
    }

    // Si está escribiendo la primera palabra, solo mostrar mensaje informativo, no error
    if (wordCount === 1 && !textEndsWithSpace) {
      return { field: 'nombres', isValid: false, message: 'Agrega más palabras (mínimo 2, máximo 7)' }
    }

    return { field: 'nombres', isValid: false, message: 'Mínimo 2 palabras requeridas (nombre + apellido)' }
  }

  const validateOcupacion = (ocupacion: string): ValidationResult => {
    if (isNN(ocupacion)) {
      return { field: 'ocupacion', isValid: true, message: 'Valor omitido por NN' }
    }
    if (!ocupacion || ocupacion.trim() === '') {
      return { field: 'ocupacion', isValid: false, message: 'Ocupación requerida' }
    }

    // Validar longitud mínima
    if (ocupacion.trim().length < 2) {
      return { field: 'ocupacion', isValid: false, message: 'Mínimo 2 caracteres' }
    }

    const words = ocupacion.trim().split(/\s+/).filter(w => w.length > 0)

    if (words.length > 2) {
      return { field: 'ocupacion', isValid: false, message: 'Máximo 2 palabras permitidas en ocupación' }
    }

    return { field: 'ocupacion', isValid: true, message: 'Ocupación válida' }
  }

  // ✅ Validación para descripción (mínimo 5 palabras)
  const validateDescripcion = (descripcion: string): ValidationResult => {
    if (isNN(descripcion)) {
      return { field: 'descripcion', isValid: true, message: 'Valor omitido por NN' }
    }
    if (!descripcion || descripcion.trim() === '') {
      return { field: 'descripcion', isValid: true, message: '' }  // Descripción es opcional
    }

    // Dividir en palabras, filtrando espacios vacíos
    const words = descripcion.trim().split(/\s+/).filter(w => w.length > 0)
    const wordCount = words.length

    // Validar mínimo 5 palabras
    if (wordCount < 5) {
      return { field: 'descripcion', isValid: false, message: `Mínimo 5 palabras requeridas (tienes ${wordCount})` }
    }

    return { field: 'descripcion', isValid: true, message: `${wordCount} palabras - Válido` }
  }

  // ✅ Validación para dirección estructurada
  const validateDireccion = (): ValidationResult => {
    if ((!formData.callePrincipal || formData.callePrincipal.trim() === '') && !isNN(formData.callePrincipal)) {
      return { field: 'direccion', isValid: false, message: 'Calle Principal es requerida' }
    }
    if ((!formData.parroquia || formData.parroquia.trim() === '') && !isNN(formData.parroquia)) {
      return { field: 'direccion', isValid: false, message: 'Parroquia es requerida' }
    }
    if ((!formData.municipio || formData.municipio.trim() === '') && !isNN(formData.municipio)) {
      return { field: 'direccion', isValid: false, message: 'Municipio es requerido' }
    }
    if ((!formData.ciudad || formData.ciudad.trim() === '') && !isNN(formData.ciudad)) {
      return { field: 'direccion', isValid: false, message: 'Ciudad es requerida' }
    }
    if ((!formData.estadoDireccion || formData.estadoDireccion.trim() === '') && !isNN(formData.estadoDireccion)) {
      return { field: 'direccion', isValid: false, message: 'Estado es requerido' }
    }

    return { field: 'direccion', isValid: true, message: 'Dirección válida' }
  }

  // ✅ Validación personalizada para teléfono (10 dígitos, sin empezar por 0)
  const validateTelefono = (telefono: string): ValidationResult => {
    if (isNN(telefono)) {
      return { field: 'telefono', isValid: true, message: 'Valor omitido por NN' }
    }
    if (!telefono || telefono.trim() === '') {
      return { field: 'telefono', isValid: false, message: 'Teléfono requerido' }
    }

    // Remover espacios y caracteres no numéricos
    const numeroLimpio = telefono.replace(/\D/g, '')

    // Validar que tenga exactamente 10 dígitos
    if (numeroLimpio.length !== 10) {
      return { field: 'telefono', isValid: false, message: 'El teléfono debe tener exactamente 10 dígitos' }
    }

    // Validar que no empiece por 0
    if (numeroLimpio.startsWith('0')) {
      return { field: 'telefono', isValid: false, message: 'El teléfono no puede empezar por 0' }
    }

    // Validar que todos los caracteres sean dígitos (0-9)
    if (!/^\d{10}$/.test(numeroLimpio)) {
      return { field: 'telefono', isValid: false, message: 'El teléfono solo puede contener números (0-9)' }
    }

    return { field: 'telefono', isValid: true, message: 'Teléfono válido' }
  }

  const validateFechaNacimiento = (fecha: string): ValidationResult => {
    if (isNN(fecha)) {
      return { field: 'fechaNacimiento', isValid: true, message: 'Valor omitido por NN' }
    }
    if (!fecha || fecha.trim() === '') {
      return { field: 'fechaNacimiento', isValid: false, message: 'Fecha de nacimiento requerida' }
    }

    // Validar formato DD/MM/YYYY
    const fechaFormatRegex = /^(\d{2})\/(\d{2})\/(\d{4})$/
    if (!fechaFormatRegex.test(fecha.trim())) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Formato inválido. Use: DD/MM/YYYY' }
    }

    // Extraer día, mes y año
    const [, dia, mes, ano] = fecha.trim().match(fechaFormatRegex)!
    const diaNum = parseInt(dia, 10)
    const mesNum = parseInt(mes, 10)
    const anoNum = parseInt(ano, 10)

    // Validar rangos
    if (diaNum < 1 || diaNum > 31) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Día inválido (1-31)' }
    }
    if (mesNum < 1 || mesNum > 12) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Mes inválido (1-12)' }
    }
    if (anoNum < 1900 || anoNum > 2100) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Año inválido (1900-2100)' }
    }

    // Validar que la fecha sea válida (ej: no 31/02/2025)
    const fechaNac = new Date(anoNum, mesNum - 1, diaNum)
    if (fechaNac.getDate() !== diaNum || fechaNac.getMonth() !== mesNum - 1 || fechaNac.getFullYear() !== anoNum) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Fecha inválida (ej: 31/02 no existe)' }
    }

    // ✅ Validar que la fecha sea pasada (no futura ni hoy)
    const hoy = new Date()
    hoy.setHours(0, 0, 0, 0)
    if (fechaNac >= hoy) {
      return { field: 'fechaNacimiento', isValid: false, message: 'La fecha de nacimiento no puede ser futura o de hoy' }
    }

    // ✅ Validar que tenga al menos 21 años cumplidos
    const fecha21 = new Date(anoNum + 21, mesNum - 1, diaNum)
    if (fecha21 > hoy) {
      return { field: 'fechaNacimiento', isValid: false, message: 'Debe tener al menos 21 años cumplidos' }
    }

    // ✅ Validar que tenga como máximo 60 años cumplidos
    const fecha60 = new Date(anoNum + 60, mesNum - 1, diaNum)
    if (fecha60 <= hoy) {
      return { field: 'fechaNacimiento', isValid: false, message: 'No puede tener más de 60 años cumplidos' }
    }

    return { field: 'fechaNacimiento', isValid: true, message: 'Fecha válida' }
  }

  // ✅ Función para formatear texto a Title Case preservando espacio final mientras se escribe
  const toTitleCase = (text: string): string => {
    if (!text) return text

    // Detectar si el usuario dejó un espacio al final (para agregar otra palabra)
    const endsWithSpace = /\s$/.test(text)

    // Normalizar múltiples espacios internos a uno, y capitalizar palabras
    const formatted = text
      .toLowerCase()
      .split(/\s+/)
      .filter(w => w.length > 0)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')

    // Preservar un espacio al final si el usuario lo tecleó
    return endsWithSpace ? formatted + ' ' : formatted
  }

  // ✅ Función para formatear nombres a Title Case en tiempo real (primera letra mayúscula)
  const formatNombres = (text: string): string => {
    if (!text) return text
    // Aplicar Title Case preservando espacio final (no hacer trim aquí)
    return toTitleCase(text)
  }

  const formatOcupacion = (text: string): string => {
    if (!text || text.trim() === '') return text

    // Aplicar Title Case a ocupación también
    return toTitleCase(text)
  }

  // ✅ Función para formatear cédula: convertir letra inicial (E, J, V, Z) a mayúscula
  const formatCedula = (text: string): string => {
    if (!text || text.trim() === '') return text

    // Si el primer carácter es una letra (e, j, v, z), convertirla a mayúscula
    const firstChar = text.charAt(0).toUpperCase()
    const validLetters = ['E', 'J', 'V', 'Z']

    // Si la primera letra es E, J, V o Z (en minúscula o mayúscula), convertirla a mayúscula
    if (validLetters.includes(firstChar)) {
      return firstChar + text.slice(1)
    }

    // Si no es una letra válida al inicio, devolver tal cual (puede ser solo números)
    return text
  }

  // ✅ Función para formatear email: convertir a minúsculas en tiempo real
  const formatEmail = (text: string): string => {
    if (!text || text.trim() === '') return text
    // Convertir a minúsculas automáticamente
    return text.toLowerCase()
  }

  // ✅ Validación personalizada para email
  const validateEmail = (email: string): ValidationResult => {
    if (isNN(email)) {
      return { field: 'email', isValid: true, message: 'Valor omitido por NN' }
    }
    if (!email || email.trim() === '') {
      return { field: 'email', isValid: false, message: 'Email requerido' }
    }

    const emailTrimmed = email.trim()

    // Validar que no tenga espacios intermedios
    if (emailTrimmed.includes(' ')) {
      return { field: 'email', isValid: false, message: 'El email no puede contener espacios' }
    }

    // Validar que no tenga comas
    if (emailTrimmed.includes(',')) {
      return { field: 'email', isValid: false, message: 'El email no puede contener comas' }
    }

    // Validar que tenga arroba
    if (!emailTrimmed.includes('@')) {
      return { field: 'email', isValid: false, message: 'El email debe contener un @' }
    }

    // Validar que tenga extensión válida (.com, .edu, .gob, etc.)
    // Extensión debe ser de al menos 2 caracteres alfabéticos después del último punto
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    if (!emailPattern.test(emailTrimmed)) {
      return { field: 'email', isValid: false, message: 'El email debe tener una extensión válida (.com, .edu, .gob, etc.)' }
    }

    return { field: 'email', isValid: true, message: 'Email válido' }
  }

  // Validaciones usando el servicio de validadores del backend
  const validateField = async (field: string, value: string): Promise<ValidationResult> => {
    // Mapeo de campos del formulario a tipos de validadores del backend
    const campoMapper: Record<string, string> = {
      'cedula': 'cedula_venezuela',
      'nombres': 'nombre',  // ✅ Ahora unifica nombres + apellidos
      'telefono': 'telefono_venezuela',
      'email': 'email',
      'fechaNacimiento': 'fecha',
    }

    const tipoValidador = campoMapper[field]

    // Si no hay validador del backend para este campo, usar validación local simple
    if (!tipoValidador) {
      if (!value) {
        return { field, isValid: false, message: `${field} es obligatorio` }
      }
      return { field, isValid: true, message: '' }
    }

    // Validar con el backend
    try {
      const resultado = await validadoresService.validarCampo(tipoValidador, value, 'VENEZUELA')

      if (resultado.validacion.valido) {
        return {
          field,
          isValid: true,
          message: resultado.validacion.mensaje || 'Campo válido'
        }
      } else {
        // Incluir sugerencia en el mensaje de error
        const errorMsg = resultado.validacion.error || 'Campo inválido'
        const sugerencia = resultado.validacion.sugerencia || ''
        const mensajeCompleto = sugerencia ? `${errorMsg}. ${sugerencia}` : errorMsg

        return {
          field,
          isValid: false,
          message: mensajeCompleto
        }
      }
    } catch (error) {
      // Si el servicio falla, usar validación básica como fallback
      if (!value) {
        return { field, isValid: false, message: `${field} es obligatorio` }
      }
      return { field, isValid: true, message: '' }
    }
  }

  const handleInputChange = async (field: keyof FormData, value: string) => {
    console.log(`🔧 Cambio en campo: ${field}, nuevo valor: ${value}`)
    console.log(`🔧 Modo edición: ${cliente ? 'SÍ' : 'NO'}`)

    let formattedValue = value

    // ✅ Aplicar autoformato en tiempo real (tanto creación como edición)
    if (field === 'cedula') {
      formattedValue = formatCedula(value)
    } else if (field === 'nombres') {
      formattedValue = formatNombres(value)
    } else if (field === 'ocupacion') {
      formattedValue = formatOcupacion(value)
    } else if (field === 'email') {
      // ✅ Autoformato email a minúsculas en tiempo real
      formattedValue = formatEmail(value)
    }

    // ✅ Actualizar el estado del formulario
    setFormData(prev => ({ ...prev, [field]: formattedValue }))

    // ✅ Validar con funciones personalizadas o backend según el campo (TANTO creación como edición)
    let validation: ValidationResult

    if (field === 'nombres') {
      // ✅ Validar nombres DESPUÉS del formateo para verificar 2-7 palabras
      validation = validateNombres(formattedValue)
    } else if (field === 'ocupacion') {
      validation = validateOcupacion(formattedValue)
    } else if (field === 'fechaNacimiento') {
      validation = validateFechaNacimiento(formattedValue)
    } else if (field === 'telefono') {
      validation = validateTelefono(formattedValue)
    } else if (field === 'email') {
      // ✅ Validar email con función personalizada (rechaza comas, espacios, sin @, sin extensión)
      validation = validateEmail(formattedValue)
    } else if (field === 'descripcion') {
      // ✅ Validar descripción (mínimo 5 palabras)
      validation = validateDescripcion(formattedValue)
    } else {
      // Para campos de dirección, validar cuando cambie cualquier campo
      if (['callePrincipal', 'calleTransversal', 'parroquia', 'municipio', 'ciudad', 'estadoDireccion'].includes(field)) {
        // Validar dirección completa cuando cambie cualquier campo de dirección
        setTimeout(() => {
          const direccionValidation = validateDireccion()
          setValidations(prev => {
            const filtered = prev.filter(v => v.field !== 'direccion')
            return [...filtered, direccionValidation]
          })
        }, 100)
        // Retornar validación temporal
        validation = { field: 'direccion', isValid: true, message: '' }
      } else {
        // Solo validar con backend en modo creación
        if (!cliente) {
          validation = await validateField(field, formattedValue)
        } else {
          validation = { field, isValid: true, message: '' }
        }
      }
    }

    // ✅ Agregar validación al estado (tanto creación como edición)
    setValidations(prev => {
      const filtered = prev.filter(v => v.field !== field)
      return [...filtered, validation]
    })
  }

  const isFormValid = () => {
    // ✅ En modo edición, permitir guardar sin validar campos
    if (cliente) {
      return true
    }

    const requiredFields: (keyof FormData)[] = [
      'cedula', 'nombres', 'telefono', 'email',
      'callePrincipal', 'parroquia', 'municipio', 'ciudad', 'estadoDireccion',
      'fechaNacimiento', 'ocupacion'
    ]

    // ✅ Solo en modo creación: validar nombres, ocupacion, direccion, fechaNacimiento, telefono y email con funciones personalizadas
    const nombresValidation = validateNombres(formData.nombres)
    const ocupacionValidation = validateOcupacion(formData.ocupacion)
    const direccionValidation = validateDireccion()
    const fechaNacimientoValidation = validateFechaNacimiento(formData.fechaNacimiento)
    const telefonoValidation = validateTelefono(formData.telefono)
    const emailValidation = validateEmail(formData.email)

    // Agregar validaciones personalizadas al estado
    const nombresValidationResult = validations.find(v => v.field === 'nombres')
    const ocupacionValidationResult = validations.find(v => v.field === 'ocupacion')
    const direccionValidationResult = validations.find(v => v.field === 'direccion')
    const fechaNacimientoValidationResult = validations.find(v => v.field === 'fechaNacimiento')
    const telefonoValidationResult = validations.find(v => v.field === 'telefono')
    const emailValidationResult = validations.find(v => v.field === 'email')

    if (!nombresValidationResult || nombresValidationResult.isValid !== nombresValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'nombres')
        return [...filtered, nombresValidation]
      })
    }

    if (!ocupacionValidationResult || ocupacionValidationResult.isValid !== ocupacionValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'ocupacion')
        return [...filtered, ocupacionValidation]
      })
    }

    if (!direccionValidationResult || direccionValidationResult.isValid !== direccionValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'direccion')
        return [...filtered, direccionValidation]
      })
    }

    if (!fechaNacimientoValidationResult || fechaNacimientoValidationResult.isValid !== fechaNacimientoValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'fechaNacimiento')
        return [...filtered, fechaNacimientoValidation]
      })
    }

    if (!telefonoValidationResult || telefonoValidationResult.isValid !== telefonoValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'telefono')
        return [...filtered, telefonoValidation]
      })
    }

    if (!emailValidationResult || emailValidationResult.isValid !== emailValidation.isValid) {
      setValidations(prev => {
        const filtered = prev.filter(v => v.field !== 'email')
        return [...filtered, emailValidation]
      })
    }

    // Validar campos de dirección
    const direccionValida = direccionValidation.isValid &&
      formData.callePrincipal &&
      formData.parroquia &&
      formData.municipio &&
      formData.ciudad &&
      formData.estadoDireccion

    return requiredFields.every(field => {
      // Usar validaciones personalizadas para nombres, ocupacion, direccion, fechaNacimiento y telefono
      if (field === 'nombres') {
        return nombresValidation.isValid && formData[field]
      }
      if (field === 'ocupacion') {
        return ocupacionValidation.isValid && formData[field]
      }
      if (field === 'fechaNacimiento') {
        return fechaNacimientoValidation.isValid && formData[field]
      }
      if (field === 'telefono') {
        return telefonoValidation.isValid && formData[field]
      }
      if (field === 'email') {
        return emailValidation.isValid && formData[field]
      }
      // Validar campos de dirección
      if (['callePrincipal', 'parroquia', 'municipio', 'ciudad', 'estadoDireccion'].includes(field)) {
        return direccionValida && formData[field]
      }

      const validation = validations.find(v => v.field === field)
      return validation?.isValid && formData[field]
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // ✅ VALIDACIÓN: Permitir vacío solo si el usuario ingresó 'NN'
    if ((!formData.callePrincipal || !formData.callePrincipal.trim()) && !isNN(formData.callePrincipal)) {
      alert('⚠️ ERROR: Debe completar el campo Calle Principal')
      return
    }
    if ((!formData.parroquia || !formData.parroquia.trim()) && !isNN(formData.parroquia)) {
      alert('⚠️ ERROR: Debe completar el campo Parroquia')
      return
    }
    if ((!formData.municipio || !formData.municipio.trim()) && !isNN(formData.municipio)) {
      alert('⚠️ ERROR: Debe completar el campo Municipio')
      return
    }
    if ((!formData.ciudad || !formData.ciudad.trim()) && !isNN(formData.ciudad)) {
      alert('⚠️ ERROR: Debe completar el campo Ciudad')
      return
    }
    if ((!formData.estadoDireccion || !formData.estadoDireccion.trim()) && !isNN(formData.estadoDireccion)) {
      alert('⚠️ ERROR: Debe completar el campo Estado')
      return
    }
    if ((!formData.fechaNacimiento || !formData.fechaNacimiento.trim()) && !isNN(formData.fechaNacimiento)) {
      alert('⚠️ ERROR: Debe completar el campo Fecha de Nacimiento')
      return
    }
    if ((!formData.ocupacion || !formData.ocupacion.trim()) && !isNN(formData.ocupacion)) {
      alert('⚠️ ERROR: Debe completar el campo Ocupación')
      return
    }

    // ✅ Validar descripción: si tiene contenido, debe tener mínimo 5 palabras
    if (formData.descripcion && formData.descripcion.trim() && !isNN(formData.descripcion)) {
      const descripcionValidation = validateDescripcion(formData.descripcion)
      if (!descripcionValidation.isValid) {
        alert(`⚠️ ERROR: ${descripcionValidation.message}`)
        return
      }
    }

    if (!isFormValid()) {
      return
    }

    setIsSubmitting(true)

    try {
      // ✅ Normalizar 'nn'→'' y concatenar +58 con el número de teléfono
      const telefonoLimpio = blankIfNN(formData.telefono).replace(/\D/g, '').slice(0, 10)
      const telefonoCompleto = `+58${telefonoLimpio}`

      // ✅ Normalizar 'nn'→'' y formatear campos a Title Case antes de guardar
      const nombresFormateado = toTitleCase(blankIfNN(formData.nombres))
      const ocupacionFormateada = toTitleCase(blankIfNN(formData.ocupacion))

      // ✅ Construir dirección como JSON estructurado con formateo Title Case
      const direccionCompleta = JSON.stringify({
        callePrincipal: toTitleCase(blankIfNN(formData.callePrincipal)),
        calleTransversal: blankIfNN(formData.calleTransversal) ? toTitleCase(blankIfNN(formData.calleTransversal)) : null,
        descripcion: blankIfNN(formData.descripcion) || null,  // ✅ Descripción sin formatear si queda vacía
        parroquia: toTitleCase(blankIfNN(formData.parroquia)),
        municipio: toTitleCase(blankIfNN(formData.municipio)),
        ciudad: toTitleCase(blankIfNN(formData.ciudad)),
        estado: toTitleCase(blankIfNN(formData.estadoDireccion))
      })

      // ✅ Preparar todos los datos formateados
      const todosLosDatos = {
        cedula: formatCedula(blankIfNN(formData.cedula)),  // ✅ Cédula con letra inicial en mayúscula
        nombres: nombresFormateado,  // ✅ nombres formateados con Title Case
        telefono: telefonoCompleto,  // ✅ Formato: +581234567890
        email: blankIfNN(formData.email),  // ✅ Email ya está en minúsculas por autoformato
        direccion: direccionCompleta,  // ✅ Dirección estructurada como JSON con Title Case
        fecha_nacimiento: convertirFechaAISO(blankIfNN(formData.fechaNacimiento)), // ✅ Convertir DD/MM/YYYY → YYYY-MM-DD
        ocupacion: ocupacionFormateada,  // ✅ Ocupación formateada con Title Case
        estado: formData.estado,
        notas: blankIfNN(formData.notas) || 'No hay observacion'
      }

      if (cliente && typeof cliente.id === 'number') {
        // ✅ MODO EDICIÓN: Solo enviar campos que cambiaron
        logger.info('Editando cliente existente', { clienteId: cliente.id })
        
        // ✅ Función para comparar valores normalizados (ignora espacios, mayúsculas/minúsculas)
        const valoresIguales = (valor1: any, valor2: any): boolean => {
          // Manejar null/undefined
          if ((valor1 == null || valor1 === '') && (valor2 == null || valor2 === '')) {
            return true
          }
          if (valor1 == null || valor2 == null) {
            return false
          }
          // Normalizar ambos valores para comparación (trim, lowercase, sin espacios múltiples)
          const v1 = String(valor1).trim().toLowerCase().replace(/\s+/g, ' ')
          const v2 = String(valor2).trim().toLowerCase().replace(/\s+/g, ' ')
          return v1 === v2
        }

        // ✅ Comparar con datos originales y construir objeto solo con cambios
        const clienteData: Partial<typeof todosLosDatos> = {}
        
        if (datosOriginales) {
          // ✅ Función para reconstruir dirección original desde datos originales
          const reconstruirDireccionOriginal = () => {
            try {
              return JSON.stringify({
                callePrincipal: toTitleCase(blankIfNN(datosOriginales.callePrincipal || '')),
                calleTransversal: blankIfNN(datosOriginales.calleTransversal || '') ? toTitleCase(blankIfNN(datosOriginales.calleTransversal || '')) : null,
                descripcion: blankIfNN(datosOriginales.descripcion || '') || null,
                parroquia: toTitleCase(blankIfNN(datosOriginales.parroquia || '')),
                municipio: toTitleCase(blankIfNN(datosOriginales.municipio || '')),
                ciudad: toTitleCase(blankIfNN(datosOriginales.ciudad || '')),
                estado: toTitleCase(blankIfNN(datosOriginales.estadoDireccion || ''))
              })
            } catch {
              return ''
            }
          }

          const direccionOriginal = reconstruirDireccionOriginal()
          const telefonoOriginal = datosOriginales.telefono ? `+58${extraerNumeroTelefono(datosOriginales.telefono)}` : ''

          // Comparar cada campo y solo incluir si cambió
          if (!valoresIguales(todosLosDatos.cedula, datosOriginales.cedula)) {
            clienteData.cedula = todosLosDatos.cedula
          }
          if (!valoresIguales(todosLosDatos.nombres, datosOriginales.nombres)) {
            clienteData.nombres = todosLosDatos.nombres
          }
          if (!valoresIguales(todosLosDatos.telefono, telefonoOriginal)) {
            clienteData.telefono = todosLosDatos.telefono
          }
          if (!valoresIguales(todosLosDatos.email, datosOriginales.email)) {
            clienteData.email = todosLosDatos.email
          }
          if (!valoresIguales(todosLosDatos.direccion, direccionOriginal)) {
            clienteData.direccion = todosLosDatos.direccion
          }
          if (!valoresIguales(todosLosDatos.fecha_nacimiento, convertirFechaAISO(datosOriginales.fechaNacimiento || ''))) {
            clienteData.fecha_nacimiento = todosLosDatos.fecha_nacimiento
          }
          if (!valoresIguales(todosLosDatos.ocupacion, datosOriginales.ocupacion)) {
            clienteData.ocupacion = todosLosDatos.ocupacion
          }
          if (!valoresIguales(todosLosDatos.estado, datosOriginales.estado)) {
            clienteData.estado = todosLosDatos.estado
          }
          if (!valoresIguales(todosLosDatos.notas, datosOriginales.notas)) {
            clienteData.notas = todosLosDatos.notas
          }

          logger.debug('Campos modificados detectados', { 
            camposModificados: Object.keys(clienteData),
            clienteData,
            datosOriginales: {
              cedula: datosOriginales.cedula,
              nombres: datosOriginales.nombres,
              telefono: telefonoOriginal,
              email: datosOriginales.email,
              direccion: direccionOriginal.substring(0, 100) + '...'
            }
          })
        } else {
          // Si no hay datos originales (no debería pasar en modo edición), enviar todos los datos
          logger.warning('No hay datos originales para comparar, enviando todos los campos')
          Object.assign(clienteData, todosLosDatos)
        }

        // ✅ Solo actualizar si hay cambios
        if (Object.keys(clienteData).length === 0) {
          logger.info('No hay cambios detectados, no se actualizará el cliente')
          alert('No se detectaron cambios en el cliente')
          setIsSubmitting(false)
          return
        }

        logger.debug('Datos a enviar al backend (solo campos modificados)', { clienteData })
        await clienteService.updateCliente(String(cliente.id), clienteData)
        logger.info('Cliente actualizado exitosamente', { clienteId: cliente.id, camposActualizados: Object.keys(clienteData) })
      } else {
        // Crear nuevo cliente - enviar todos los datos
        logger.info('Creando nuevo cliente', { cedula: todosLosDatos.cedula })
        await clienteService.createCliente(todosLosDatos)
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
      const message = responseData?.message
      logger.error('Error creando cliente', {
        action: 'create_client_error',
        component: 'CrearClienteForm',
        error: errorMessage,
        status,
        detail,
        message
      })

      // Mostrar mensaje de error al usuario
      let errorMessageUser = 'Error al crear el cliente. Por favor, intente nuevamente.'
      let tipoDuplicado = ''

      if (isAxiosError(error)) {
        const errorDetail = getErrorDetail(error)
        const responseData = error.response?.data as { message?: string } | undefined
        if (error.response?.status === 400) {
          // Detectar qué tipo de duplicado es
          const detailText = errorDetail || ''
          if (detailText.includes('cédula') && detailText.includes('nombre')) {
            tipoDuplicado = 'cedula_nombre'
            errorMessageUser = errorDetail || 'No se puede crear un cliente con la misma cédula y el mismo nombre completo. Ya existe un cliente con esos datos.'
          } else if (detailText.includes('email')) {
            tipoDuplicado = 'email'
            errorMessageUser = errorDetail || 'No se puede crear un cliente con el mismo email. Ya existe un cliente con ese email.'
          } else {
            // Error de cliente duplicado genérico
            errorMessageUser = errorDetail || 'No se puede crear un cliente con datos duplicados. Ya existe un cliente con estos datos.'
          }
        } else if (errorDetail) {
          errorMessageUser = errorDetail
        } else if (responseData?.message) {
          errorMessageUser = responseData.message
        }
      }

      // Intentar extraer ID existente del mensaje
      let existingId: number | null = null
      const detailText: string = getErrorDetail(error) || ''
      const match = detailText.match(/ID:\s*(\d+)/i)
      if (match && match[1]) {
        existingId = Number(match[1])
      }

      // Notificar y ofrecer abrir en edición
      if (isAxiosError(error) && error.response?.status === 400) {
        // Mensaje amigable específico según el tipo de duplicado
        let mensajeDuplicado = ''
        if (tipoDuplicado === 'cedula_nombre') {
          mensajeDuplicado = 'la misma cédula y el mismo nombre completo'
        } else if (tipoDuplicado === 'email') {
          mensajeDuplicado = 'el mismo email'
        } else {
          mensajeDuplicado = 'los mismos datos (cédula y nombre, o email)'
        }

        const friendly = existingId
          ? `⚠️ ADVERTENCIA: Ya existe un cliente con ${mensajeDuplicado}.\n\nCliente existente ID: ${existingId}\n\nNo se puede crear un nuevo cliente con datos duplicados.\n\n¿Deseas abrir el cliente existente para editarlo?`
          : `⚠️ ADVERTENCIA: Ya existe un cliente con ${mensajeDuplicado}.\n\nNo se puede crear un nuevo cliente con datos duplicados.\n\n¿Deseas buscar el cliente existente?`
        
        const wantsEdit = window.confirm(friendly)
        if (wantsEdit) {
          // Cerrar el modal de creación antes de abrir edición
          onClose()
          if (existingId && onOpenEditExisting) {
            onOpenEditExisting(existingId)
          }
        }
      } else {
        alert(`⚠️ ${errorMessage}`)
      }
    } finally {
      // ✅ CORRECCIÓN: Siempre ejecutar setIsSubmitting(false) en finally
      // El manejo específico de duplicados ya se hizo en el catch block
      setIsSubmitting(false)
    }
  }


  const getFieldValidation = (field: string) => {
    // ✅ En modo edición, no mostrar mensajes de validación
    if (cliente) {
      return null
    }
    return validations.find(v => v.field === field)
  }

  if (showExcelUploader) {
    return (
      <ExcelUploader
        onClose={() => {
          setShowExcelUploader(false)
          // Solo cerrar ExcelUploader, mantener CrearClienteForm abierto
        }}
        onSuccess={() => {
          setShowExcelUploader(false)
          // ✅ Solo cerrar ExcelUploader, NO cerrar formulario Nuevo Cliente
          // El usuario debe decidir qué hacer después
        }}
      />
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        <div className="sticky top-0 bg-white border-b p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {cliente ? 'Editar Cliente' : 'Nuevo Cliente'}
          </h2>
          <div className="flex gap-2">
            {/* Solo mostrar "Cargar Excel" en modo crear, no en modo editar */}
            {!cliente && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowExcelUploader(true)}
                className="flex items-center gap-2"
              >
                <FileSpreadsheet className="w-4 h-4" />
                Cargar Excel
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              className="flex items-center gap-2"
              title="Cerrar formulario"
            >
              <X className="w-4 h-4" />
              <span className="sr-only">Cerrar</span>
            </Button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Datos Personales */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Datos Personales
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Cédula <span className="text-red-500">*</span>
                  </label>
                <div className="relative">
                  <CreditCard className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.cedula}
                    onChange={(e) => handleInputChange('cedula', e.target.value)}
                    className={`pl-10 ${getFieldValidation('cedula')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="12345678"
                  />
                </div>
                {getFieldValidation('cedula') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('cedula')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('cedula')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('cedula')?.message}
                  </div>
                )}
                </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Nombres y Apellidos <span className="text-red-500">*</span> <span className="text-gray-500 text-xs">(2-7 palabras)</span>
                  </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.nombres}
                    onChange={(e) => handleInputChange('nombres', e.target.value)}
                    className={`pl-10 ${getFieldValidation('nombres')?.isValid === false ? 'border-red-500' : getFieldValidation('nombres')?.isValid ? 'border-green-500' : ''}`}
                    placeholder="Ejemplo: Juan Carlos Pérez González"
                    autoComplete="name"
                  />
                </div>
                {getFieldValidation('nombres') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('nombres')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('nombres')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('nombres')?.message}
                    </div>
                  )}
              </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Teléfono <span className="text-red-500">*</span>
                  </label>
                <div className="flex items-center gap-2">
                  {/* Prefijo fijo +58 */}
                  <div className="flex items-center px-3 py-2 bg-gray-100 border border-gray-300 rounded-md text-gray-700 font-medium">
                    <Phone className="w-4 h-4 mr-2 text-gray-600" />
                    +58
                  </div>
                  {/* Input para el número (10 dígitos) */}
                  <div className="flex-1 relative">
                    <Input
                      type="text"
                      inputMode="numeric"
                      value={formData.telefono}
                      onChange={(e) => {
                        // Solo permitir números
                        const value = e.target.value.replace(/\D/g, '').slice(0, 10)
                        handleInputChange('telefono', value)
                      }}
                      className={`${getFieldValidation('telefono')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                      placeholder="1234567890"
                      maxLength={10}
                    />
                  </div>
                </div>
                {getFieldValidation('telefono') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('telefono')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('telefono')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('telefono')?.message}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Email <span className="text-red-500">*</span>
                  </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    className={`pl-10 ${getFieldValidation('email')?.isValid === false ? 'border-red-500' : ''}`}
                    placeholder="juan@email.com"
                  />
                </div>
                {getFieldValidation('email') && (
                  <div className={`text-xs flex items-center gap-1 ${
                    getFieldValidation('email')?.isValid ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {getFieldValidation('email')?.isValid ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {getFieldValidation('email')?.message}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Fecha de Nacimiento <span className="text-red-500">*</span> <span className="text-gray-500 text-xs">(DD/MM/YYYY)</span>
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.fechaNacimiento}
                    onChange={(e) => handleInputChange('fechaNacimiento', e.target.value)}
                    placeholder="DD/MM/YYYY"
                    className={`pl-10 ${getFieldValidation('fechaNacimiento')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                  />
                </div>
                {getFieldValidation('fechaNacimiento') && getFieldValidation('fechaNacimiento')?.isValid === false && (
                  <div className="text-xs flex items-center gap-1 text-red-600 font-medium">
                    <XCircle className="w-3 h-3" />
                    <span className="font-semibold">{getFieldValidation('fechaNacimiento')?.message}</span>
                  </div>
                )}
                {getFieldValidation('fechaNacimiento')?.isValid && (
                  <div className="text-xs flex items-center gap-1 text-green-600">
                    <CheckCircle className="w-3 h-3" />
                    {getFieldValidation('fechaNacimiento')?.message}
                  </div>
                )}
              </div>

              {/* Sección de Dirección Estructurada */}
              <div className="md:col-span-2 space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b">
                  <MapPin className="w-5 h-5 text-gray-600" />
                  <label className="text-sm font-semibold text-gray-700">
                    Dirección <span className="text-red-500">*</span>
                  </label>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">
                      Calle Principal <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="text"
                      value={formData.callePrincipal}
                      onChange={(e) => handleInputChange('callePrincipal', e.target.value)}
                      className={`${getFieldValidation('direccion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                      placeholder="Ej: Av. Bolívar"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">
                      Calle Transversal
                    </label>
                    <Input
                      type="text"
                      value={formData.calleTransversal}
                      onChange={(e) => handleInputChange('calleTransversal', e.target.value)}
                      placeholder="Ej: Calle 5 de Julio"
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <label className="text-sm font-medium text-gray-700">
                      Descripción (Lugar cercano, color de casa) <span className="text-gray-500 text-xs">(mínimo 5 palabras)</span>
                    </label>
                    <Textarea
                      value={formData.descripcion}
                      onChange={(e) => handleInputChange('descripcion', e.target.value)}
                      placeholder="Ej: Cerca del mercado central, casa color azul claro, portón verde"
                      rows={3}
                      className={getFieldValidation('descripcion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}
                    />
                    {getFieldValidation('descripcion') && (
                      <div className={`text-xs flex items-center gap-1 ${
                        getFieldValidation('descripcion')?.isValid ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {getFieldValidation('descripcion')?.isValid ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        {getFieldValidation('descripcion')?.message}
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">
                      Parroquia <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="text"
                      value={formData.parroquia}
                      onChange={(e) => handleInputChange('parroquia', e.target.value)}
                      className={`${getFieldValidation('direccion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                      placeholder="Ej: San Juan"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">
                      Municipio <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="text"
                      value={formData.municipio}
                      onChange={(e) => handleInputChange('municipio', e.target.value)}
                      className={`${getFieldValidation('direccion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                      placeholder="Ej: Libertador"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">
                      Ciudad <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="text"
                      value={formData.ciudad}
                      onChange={(e) => handleInputChange('ciudad', e.target.value)}
                      className={`${getFieldValidation('direccion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                      placeholder="Ej: Caracas"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">
                      Estado <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="text"
                      value={formData.estadoDireccion}
                      onChange={(e) => handleInputChange('estadoDireccion', e.target.value)}
                      className={`${getFieldValidation('direccion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                      placeholder="Ej: Distrito Capital"
                    />
                  </div>
                </div>

                {getFieldValidation('direccion') && getFieldValidation('direccion')?.isValid === false && (
                  <div className="text-xs flex items-center gap-1 text-red-600 font-medium">
                    <XCircle className="w-3 h-3" />
                    <span className="font-semibold">{getFieldValidation('direccion')?.message}</span>
                  </div>
                )}
                {getFieldValidation('direccion')?.isValid && (
                  <div className="text-xs flex items-center gap-1 text-green-600">
                    <CheckCircle className="w-3 h-3" />
                    {getFieldValidation('direccion')?.message}
                  </div>
                )}
              </div>

              <div className="space-y-2 min-h-[80px]"> {/* ✅ Estabilizar altura del campo */}
                <label className="text-sm font-medium text-gray-700">
                  Ocupación <span className="text-red-500">*</span> <span className="text-gray-500 text-xs">(máximo 2 palabras)</span>
                </label>
                <div className="relative">
                  <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    value={formData.ocupacion}
                    onChange={(e) => handleInputChange('ocupacion', e.target.value)}
                    className={`pl-10 w-full ${getFieldValidation('ocupacion')?.isValid === false ? 'border-red-500 border-2 bg-red-50' : ''}`}
                    placeholder="Ejemplo: Ingeniero, Gerente General"
                  />
                </div>
                {getFieldValidation('ocupacion') && getFieldValidation('ocupacion')?.isValid === false && (
                  <div className="text-xs flex items-center gap-1 text-red-600 font-medium">
                    <XCircle className="w-3 h-3" />
                    <span className="font-semibold">{getFieldValidation('ocupacion')?.message}</span>
                  </div>
                )}
                {getFieldValidation('ocupacion')?.isValid && (
                  <div className="text-xs flex items-center gap-1 text-green-600">
                    <CheckCircle className="w-3 h-3" />
                    {getFieldValidation('ocupacion')?.message}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Estado y Notas */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Estado y Notas
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Estado <span className="text-red-500">*</span>
                  </label>
                <Select
                  value={formData.estado}
                  onValueChange={(value: 'ACTIVO' | 'INACTIVO' | 'FINALIZADO') => handleInputChange('estado', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar estado" />
                    </SelectTrigger>
                    <SelectContent>
                    <SelectItem value="ACTIVO">Activo</SelectItem>
                    <SelectItem value="INACTIVO">Inactivo</SelectItem>
                    <SelectItem value="FINALIZADO">Finalizado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Notas <span className="text-gray-500 text-xs">(Por defecto: "No hay observacion")</span>
                  </label>
                <Textarea
                  value={formData.notas}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleInputChange('notas', e.target.value)}
                  placeholder="No hay observacion"
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {/* Botones */}
          <div className="flex justify-end gap-4 pt-6 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={!isFormValid() || isSubmitting}
              className="flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {isSubmitting ? 'Guardando...' : 'Guardar Cliente'}
            </Button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}
