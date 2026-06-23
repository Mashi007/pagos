import type { Dispatch, SetStateAction } from 'react'
import {
  Briefcase,
  Calendar,
  CreditCard,
  FileText,
  Mail,
  MapPin,
  Phone,
  User,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'
import type {
  ClienteData,
  EstadoValidadorCierreContacto,
} from './EditarRevisionManual.helpers'

export type ClienteRevisionCardProps = {
  clienteData: Partial<ClienteData>
  setClienteData: Dispatch<SetStateAction<Partial<ClienteData>>>
  cambios: { cliente: boolean; prestamo: boolean; cuotas: boolean }
  setCambios: Dispatch<
    SetStateAction<{ cliente: boolean; prestamo: boolean; cuotas: boolean }>
  >
  errores: Record<string, string>
  setErrores: Dispatch<SetStateAction<Record<string, string>>>
  opcionesEstado: { value: string; label: string }[]
  emailValidadorCierre: EstadoValidadorCierreContacto
  telValidadorCierre: EstadoValidadorCierreContacto
}

export function ClienteRevisionCard({
  clienteData,
  setClienteData,
  cambios,
  setCambios,
  errores,
  setErrores,
  opcionesEstado,
  emailValidadorCierre,
  telValidadorCierre,
}: ClienteRevisionCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="h-5 w-5 text-blue-600" />
          Datos del Cliente
        </CardTitle>
      </CardHeader>

      <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Cédula - solo lectura */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Cédula</label>
          <div className="relative">
            <CreditCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              value={clienteData.cedula || ''}
              disabled
              className="cursor-not-allowed bg-gray-100 pl-10"
            />
          </div>
        </div>

        {/* Nombres */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            Nombres y Apellidos <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              type="text"
              value={clienteData.nombres || ''}
              onChange={e => {
                setClienteData({
                  ...clienteData,
                  nombres: e.target.value,
                })
                setCambios({ ...cambios, cliente: true })
                if (errores['nombres']) setErrores({ ...errores, nombres: '' })
              }}
              placeholder="Juan Carlos Pérez González"
              className={`pl-10 ${errores['nombres'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
            />
          </div>
          {errores['nombres'] && (
            <p className="text-xs text-red-600">{errores['nombres']}</p>
          )}
        </div>

        {/* Teléfono */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Teléfono</label>
          <div className="flex items-center gap-2">
            <div className="flex items-center rounded-md border border-gray-300 bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700">
              <Phone className="mr-1 h-4 w-4 text-gray-500" />
              +58
            </div>
            <Input
              type="text"
              inputMode="numeric"
              value={(clienteData.telefono || '').replace(/^\+?58/, '')}
              onChange={e => {
                const digits = e.target.value.replace(/\D/g, '')
                setClienteData({
                  ...clienteData,
                  telefono: digits ? `+58${digits}` : '',
                })
                setCambios({ ...cambios, cliente: true })
                if (errores['telefono'])
                  setErrores({ ...errores, telefono: '' })
              }}
              placeholder="4141234567"
              className={
                errores['telefono']
                  ? 'border-red-500 focus-visible:ring-red-400'
                  : (clienteData.telefono || '').trim() &&
                      telValidadorCierre.validando
                    ? 'border-slate-300 ring-1 ring-slate-200'
                    : (clienteData.telefono || '').trim() &&
                        !telValidadorCierre.validando &&
                        !telValidadorCierre.listo
                      ? 'border-amber-500 focus-visible:ring-amber-400'
                      : ''
              }
            />
          </div>
          {errores['telefono'] && (
            <p className="text-xs text-red-600">{errores['telefono']}</p>
          )}
          {(clienteData.telefono || '').trim() &&
            telValidadorCierre.validando && (
              <p className="text-xs text-muted-foreground">
                Validando teléfono con el sistema…
              </p>
            )}
          {(clienteData.telefono || '').trim() &&
            !telValidadorCierre.validando &&
            !telValidadorCierre.listo && (
              <p className="text-xs text-amber-800">
                <span className="font-medium">
                  No se puede «Guardar y cerrar»
                </span>{' '}
                hasta que el teléfono cumpla los validadores. Puede usar
                «Guardar cambios» para seguir editando.
                {telValidadorCierre.mensaje
                  ? ` Detalle: ${telValidadorCierre.mensaje}`
                  : ''}
              </p>
            )}
        </div>

        {/* Email */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              type="email"
              value={clienteData.email || ''}
              onChange={e => {
                setClienteData({
                  ...clienteData,
                  email: e.target.value,
                })
                setCambios({ ...cambios, cliente: true })
                if (errores['email']) setErrores({ ...errores, email: '' })
              }}
              placeholder="juan@email.com"
              className={`pl-10 ${
                errores['email']
                  ? 'border-red-500 focus-visible:ring-red-400'
                  : (clienteData.email || '').trim() &&
                      emailValidadorCierre.validando
                    ? 'border-slate-300 ring-1 ring-slate-200'
                    : (clienteData.email || '').trim() &&
                        !emailValidadorCierre.validando &&
                        !emailValidadorCierre.listo
                      ? 'border-amber-500 focus-visible:ring-amber-400'
                      : ''
              }`}
            />
          </div>
          {errores['email'] && (
            <p className="text-xs text-red-600">{errores['email']}</p>
          )}
          {(clienteData.email || '').trim() &&
            emailValidadorCierre.validando && (
              <p className="text-xs text-muted-foreground">
                Validando correo con el sistema…
              </p>
            )}
          {(clienteData.email || '').trim() &&
            !emailValidadorCierre.validando &&
            !emailValidadorCierre.listo && (
              <p className="text-xs text-amber-800">
                <span className="font-medium">
                  No se puede «Guardar y cerrar»
                </span>{' '}
                hasta que el correo cumpla los validadores. Puede usar «Guardar
                cambios» para seguir editando.
                {emailValidadorCierre.mensaje
                  ? ` Detalle: ${emailValidadorCierre.mensaje}`
                  : ''}
              </p>
            )}
        </div>

        {/* Fecha Nacimiento */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            Fecha de Nacimiento
          </label>
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              type="date"
              value={clienteData.fecha_nacimiento || ''}
              max={new Date(
                new Date().setFullYear(new Date().getFullYear() - 18)
              )
                .toISOString()
                .slice(0, 10)}
              onChange={e => {
                setClienteData({
                  ...clienteData,
                  fecha_nacimiento: e.target.value || null,
                })
                setCambios({ ...cambios, cliente: true })
                if (errores['fecha_nacimiento'])
                  setErrores({ ...errores, fecha_nacimiento: '' })
              }}
              className={`pl-10 ${errores['fecha_nacimiento'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
            />
          </div>
          {errores['fecha_nacimiento'] && (
            <p className="text-xs text-red-600">
              {errores['fecha_nacimiento']}
            </p>
          )}
        </div>

        {/* Ocupación */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Ocupación</label>
          <div className="relative">
            <Briefcase className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              type="text"
              value={clienteData.ocupacion || ''}
              onChange={e => {
                setClienteData({
                  ...clienteData,
                  ocupacion: e.target.value,
                })
                setCambios({ ...cambios, cliente: true })
              }}
              placeholder="Ingeniero, Gerente..."
              className="pl-10"
            />
          </div>
        </div>

        {/* Estado */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            Estado del cliente
          </label>
          <Select
            value={clienteData.estado || ''}
            onValueChange={val => {
              setClienteData({ ...clienteData, estado: val })
              setCambios({ ...cambios, cliente: true })
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Seleccionar estado" />
            </SelectTrigger>
            <SelectContent>
              {opcionesEstado.map(est => (
                <SelectItem key={est.value} value={est.value}>
                  {est.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Dirección - Desglosada en campos */}
        <div className="space-y-4 md:col-span-2">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
            <MapPin className="h-5 w-5 text-blue-600" />
            Dirección Completa
          </h3>

          {(() => {
            const getDireccionObj = () => {
              try {
                return typeof clienteData.direccion === 'string' &&
                  clienteData.direccion.startsWith('{')
                  ? JSON.parse(clienteData.direccion)
                  : {}
              } catch {
                return {}
              }
            }

            const updateDireccionField = (field: string, value: string) => {
              try {
                const obj = getDireccionObj()
                const updated = { ...obj, [field]: value }
                setClienteData({
                  ...clienteData,
                  direccion: JSON.stringify(updated),
                })
                setCambios({ ...cambios, cliente: true })
              } catch {
                setClienteData({
                  ...clienteData,
                  direccion: JSON.stringify({ [field]: value }),
                })
                setCambios({ ...cambios, cliente: true })
              }
            }

            const dirObj = getDireccionObj()

            return (
              <div className="grid grid-cols-2 gap-3">
                {/* Calle Principal */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">
                    Calle Principal
                  </label>
                  <Input
                    type="text"
                    value={dirObj.callePrincipal || ''}
                    onChange={e =>
                      updateDireccionField('callePrincipal', e.target.value)
                    }
                    placeholder="Av. Principal, Calle 5..."
                    className="text-xs"
                  />
                </div>

                {/* Calle Transversal */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">
                    Calle Transversal
                  </label>
                  <Input
                    type="text"
                    value={dirObj.calleTransversal || ''}
                    onChange={e =>
                      updateDireccionField('calleTransversal', e.target.value)
                    }
                    placeholder="Calle 10, Entre..."
                    className="text-xs"
                  />
                </div>

                {/* Parroquia */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">
                    Parroquia
                  </label>
                  <Input
                    type="text"
                    value={dirObj.parroquia || ''}
                    onChange={e =>
                      updateDireccionField('parroquia', e.target.value)
                    }
                    placeholder="Los Robles..."
                    className="text-xs"
                  />
                </div>

                {/* Municipio */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">
                    Municipio
                  </label>
                  <Input
                    type="text"
                    value={dirObj.municipio || ''}
                    onChange={e =>
                      updateDireccionField('municipio', e.target.value)
                    }
                    placeholder="Chacao, Baruta..."
                    className="text-xs"
                  />
                </div>

                {/* Ciudad */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">
                    Ciudad
                  </label>
                  <Input
                    type="text"
                    value={dirObj.ciudad || ''}
                    onChange={e =>
                      updateDireccionField('ciudad', e.target.value)
                    }
                    placeholder="Caracas..."
                    className="text-xs"
                  />
                </div>

                {/* Estado (Región) */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">
                    Estado (Región)
                  </label>
                  <Input
                    type="text"
                    value={dirObj.estado || ''}
                    onChange={e =>
                      updateDireccionField('estado', e.target.value)
                    }
                    placeholder="Miranda, Caracas..."
                    className="text-xs"
                  />
                </div>

                {/* Descripción (ancho completo) */}
                <div className="col-span-2 space-y-1">
                  <label className="text-xs font-medium text-gray-600">
                    Descripción Adicional
                  </label>
                  <Textarea
                    value={dirObj.descripcion || ''}
                    onChange={e =>
                      updateDireccionField('descripcion', e.target.value)
                    }
                    placeholder="Casa de color blanco, entre Av. A y B, próximo a esquina..."
                    rows={2}
                    className="text-xs"
                  />
                </div>
              </div>
            )
          })()}
        </div>

        {/* Notas */}
        <div className="space-y-2 md:col-span-2">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <FileText className="h-4 w-4 text-gray-500" />
            Notas
          </label>
          <Textarea
            value={clienteData.notas || ''}
            onChange={e => {
              setClienteData({ ...clienteData, notas: e.target.value })
              setCambios({ ...cambios, cliente: true })
            }}
            placeholder="Observaciones adicionales del cliente..."
            rows={2}
          />
        </div>
      </CardContent>
    </Card>
  )
}
