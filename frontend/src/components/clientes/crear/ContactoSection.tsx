import { Phone, Mail, MapPin, CheckCircle, XCircle } from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../../components/ui/card'

import { Input } from '../../../components/ui/input'

import { Textarea } from '../../../components/ui/textarea'

import type { FormData, ValidationResult } from './useCrearCliente'

interface ContactoSectionProps {
  formData: FormData

  onInputChange: (field: keyof FormData, value: string) => void

  getFieldValidation: (field: string) => ValidationResult | null | undefined
}

export function ContactoSection({
  formData,

  onInputChange,

  getFieldValidation,
}: ContactoSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Phone className="h-5 w-5" />
          Contacto y Dirección
        </CardTitle>
      </CardHeader>

      <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            Teléfono <span className="text-red-500">*</span>
          </label>

          <div className="flex items-center gap-2">
            <div className="flex items-center rounded-md border border-gray-300 bg-gray-100 px-3 py-2 font-medium text-gray-700">
              <Phone className="mr-2 h-4 w-4 text-gray-600" />
              +58
            </div>

            <div className="relative flex-1">
              <Input
                type="text"
                inputMode="numeric"
                value={formData.telefono}
                onChange={e => {
                  const digits = e.target.value.replace(/\D/g, '')

                  const value =
                    digits.length > 10 ? '9999999999' : digits.slice(0, 10)

                  onInputChange('telefono', value)
                }}
                className={`${getFieldValidation('telefono')?.isValid === false ? 'border-2 border-red-500 bg-red-50' : ''}`}
                placeholder="1234567890"
                maxLength={10}
              />
            </div>
          </div>

          {getFieldValidation('telefono') && (
            <div
              className={`flex items-center gap-1 text-xs ${getFieldValidation('telefono')?.isValid ? 'text-green-600' : 'text-red-600'}`}
            >
              {getFieldValidation('telefono')?.isValid ? (
                <CheckCircle className="h-3 w-3" />
              ) : (
                <XCircle className="h-3 w-3" />
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
            <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

            <Input
              type="email"
              value={formData.email}
              onChange={e => onInputChange('email', e.target.value)}
              className={`pl-10 ${getFieldValidation('email')?.isValid === false ? 'border-red-500' : ''}`}
              placeholder="juan@email.com"
            />
          </div>

          {getFieldValidation('email') && (
            <div
              className={`flex items-center gap-1 text-xs ${getFieldValidation('email')?.isValid ? 'text-green-600' : 'text-red-600'}`}
            >
              {getFieldValidation('email')?.isValid ? (
                <CheckCircle className="h-3 w-3" />
              ) : (
                <XCircle className="h-3 w-3" />
              )}

              {getFieldValidation('email')?.message}
            </div>
          )}
        </div>

        <div className="space-y-4 md:col-span-2">
          <div className="flex items-center gap-2 border-b pb-2">
            <MapPin className="h-5 w-5 text-gray-600" />

            <label className="text-sm font-semibold text-gray-700">
              Dirección <span className="text-red-500">*</span>
            </label>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Calle Principal <span className="text-red-500">*</span>
              </label>

              <Input
                type="text"
                value={formData.callePrincipal}
                onChange={e => onInputChange('callePrincipal', e.target.value)}
                className={`${getFieldValidation('direccion')?.isValid === false ? 'border-2 border-red-500 bg-red-50' : ''}`}
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
                onChange={e =>
                  onInputChange('calleTransversal', e.target.value)
                }
                placeholder="Ej: Calle 5 de Julio"
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium text-gray-700">
                Descripción (Lugar cercano, color de casa){' '}
                <span className="text-xs text-gray-500">
                  (mínimo 5 palabras)
                </span>
              </label>

              <Textarea
                value={formData.descripcion}
                onChange={e => onInputChange('descripcion', e.target.value)}
                placeholder="Ej: Cerca del mercado central, casa color azul claro, portón verde"
                rows={3}
                className={
                  getFieldValidation('descripcion')?.isValid === false
                    ? 'border-2 border-red-500 bg-red-50'
                    : ''
                }
              />

              {getFieldValidation('descripcion') && (
                <div
                  className={`flex items-center gap-1 text-xs ${getFieldValidation('descripcion')?.isValid ? 'text-green-600' : 'text-red-600'}`}
                >
                  {getFieldValidation('descripcion')?.isValid ? (
                    <CheckCircle className="h-3 w-3" />
                  ) : (
                    <XCircle className="h-3 w-3" />
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
                onChange={e => onInputChange('parroquia', e.target.value)}
                className={`${getFieldValidation('direccion')?.isValid === false ? 'border-2 border-red-500 bg-red-50' : ''}`}
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
                onChange={e => onInputChange('municipio', e.target.value)}
                className={`${getFieldValidation('direccion')?.isValid === false ? 'border-2 border-red-500 bg-red-50' : ''}`}
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
                onChange={e => onInputChange('ciudad', e.target.value)}
                className={`${getFieldValidation('direccion')?.isValid === false ? 'border-2 border-red-500 bg-red-50' : ''}`}
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
                onChange={e => onInputChange('estadoDireccion', e.target.value)}
                className={`${getFieldValidation('direccion')?.isValid === false ? 'border-2 border-red-500 bg-red-50' : ''}`}
                placeholder="Ej: Distrito Capital"
              />
            </div>
          </div>

          {getFieldValidation('direccion') &&
            getFieldValidation('direccion')?.isValid === false && (
              <div className="flex items-center gap-1 text-xs font-medium text-red-600">
                <XCircle className="h-3 w-3" />

                <span className="font-semibold">
                  {getFieldValidation('direccion')?.message}
                </span>
              </div>
            )}

          {getFieldValidation('direccion')?.isValid && (
            <div className="flex items-center gap-1 text-xs text-green-600">
              <CheckCircle className="h-3 w-3" />

              {getFieldValidation('direccion')?.message}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
