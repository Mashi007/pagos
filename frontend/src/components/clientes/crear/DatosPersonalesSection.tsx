import { User, CreditCard, Calendar, Briefcase, CheckCircle, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Input } from '../../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select'
import type { FormData, ValidationResult } from './useCrearCliente'

interface DatosPersonalesSectionProps {
  formData: FormData
  onInputChange: (field: keyof FormData, value: string) => void
  getFieldValidation: (field: string) => ValidationResult | null | undefined
  opcionesEstado: Array<{ valor: string; etiqueta: string }>
}

export function DatosPersonalesSection({
  formData,
  onInputChange,
  getFieldValidation,
  opcionesEstado,
}: DatosPersonalesSectionProps) {
  return (
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
              onChange={(e) => onInputChange('cedula', e.target.value)}
              className={`pl-10 ${getFieldValidation('cedula')?.isValid === false ? 'border-red-500' : ''}`}
              placeholder="12345678"
            />
          </div>
          {getFieldValidation('cedula') && (
            <div className={`text-xs flex items-center gap-1 ${getFieldValidation('cedula')?.isValid ? 'text-green-600' : 'text-red-600'}`}>
              {getFieldValidation('cedula')?.isValid ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
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
              onChange={(e) => onInputChange('nombres', e.target.value)}
              className={`pl-10 ${getFieldValidation('nombres')?.isValid === false ? 'border-red-500' : getFieldValidation('nombres')?.isValid ? 'border-green-500' : ''}`}
              placeholder="Ejemplo: Juan Carlos Pérez González"
              autoComplete="name"
            />
          </div>
          {getFieldValidation('nombres') && (
            <div className={`text-xs flex items-center gap-1 ${getFieldValidation('nombres')?.isValid ? 'text-green-600' : 'text-red-600'}`}>
              {getFieldValidation('nombres')?.isValid ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {getFieldValidation('nombres')?.message}
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
              onChange={(e) => onInputChange('fechaNacimiento', e.target.value)}
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

        <div className="space-y-2 min-h-[80px]">
          <label className="text-sm font-medium text-gray-700">
            Ocupación <span className="text-red-500">*</span> <span className="text-gray-500 text-xs">(máximo 2 palabras)</span>
          </label>
          <div className="relative">
            <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              type="text"
              value={formData.ocupacion}
              onChange={(e) => onInputChange('ocupacion', e.target.value)}
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

        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            Estado <span className="text-red-500">*</span>
          </label>
          <Select value={formData.estado} onValueChange={(value: string) => onInputChange('estado', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Seleccionar estado" />
            </SelectTrigger>
            <SelectContent>
              {(opcionesEstado.length > 0 ? opcionesEstado : [
                { valor: 'ACTIVO', etiqueta: 'Activo' },
                { valor: 'INACTIVO', etiqueta: 'Inactivo' },
                { valor: 'FINALIZADO', etiqueta: 'Finalizado' },
                { valor: 'LEGACY', etiqueta: 'Legacy' },
              ]).map((opt) => (
                <SelectItem key={opt.valor} value={opt.valor}>{opt.etiqueta}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  )
}
