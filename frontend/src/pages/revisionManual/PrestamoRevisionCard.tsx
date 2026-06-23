import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import {
  Briefcase,
  Calendar,
  CreditCard,
  DollarSign,
  Loader2,
  RefreshCw,
  User,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
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
import {
  mergeCuotasParaMostrar,
  opcionesSelectEstadoPrestamoRevision,
  type CuotaData,
  type PrestamoData,
} from './EditarRevisionManual.helpers'

export type PrestamoRevisionCardProps = {
  prestamoData: Partial<PrestamoData>
  setPrestamoData: Dispatch<SetStateAction<Partial<PrestamoData>>>
  setCuotasData: Dispatch<SetStateAction<Partial<CuotaData>[]>>
  cambios: { cliente: boolean; prestamo: boolean; cuotas: boolean }
  setCambios: Dispatch<
    SetStateAction<{ cliente: boolean; prestamo: boolean; cuotas: boolean }>
  >
  errores: Record<string, string>
  setErrores: Dispatch<SetStateAction<Record<string, string>>>
  concesionarios: { id: number; nombre: string }[]
  analistas: { id: number; nombre: string }[]
  modelosVehiculos: { id: number; modelo: string }[]
  soloLectura: boolean
  formDirtyRef: MutableRefObject<boolean>
  recalculandoFechasCuotas: boolean
  handleGuardarFechaYRecalcularVencimientos: () => void | Promise<void>
  formatDateForInput: (isoDate: string | null | undefined) => string
}

export function PrestamoRevisionCard({
  prestamoData,
  setPrestamoData,
  setCuotasData,
  cambios,
  setCambios,
  errores,
  setErrores,
  concesionarios,
  analistas,
  modelosVehiculos,
  soloLectura,
  formDirtyRef,
  recalculandoFechasCuotas,
  handleGuardarFechaYRecalcularVencimientos,
  formatDateForInput,
}: PrestamoRevisionCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-green-600" />
          Datos del Préstamo
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Estado préstamo */}
        <div className="rounded-lg border-2 border-indigo-200 bg-indigo-50/80 p-4">
          <p className="mb-2 text-sm font-semibold text-indigo-900">
            Estado del préstamo
          </p>
          <Select
            value={prestamoData.estado || ''}
            onValueChange={v => {
              setPrestamoData({ ...prestamoData, estado: v })
              setCambios({ ...cambios, prestamo: true })
            }}
          >
            <SelectTrigger className="border-indigo-200 bg-white">
              <SelectValue placeholder="Seleccionar estado" />
            </SelectTrigger>
            <SelectContent>
              {opcionesSelectEstadoPrestamoRevision(prestamoData.estado).map(
                o => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                )
              )}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Total Financiamiento */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Total Financiamiento (USD) <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                type="number"
                step="0.01"
                min="0.01"
                value={prestamoData.total_financiamiento || ''}
                onChange={e => {
                  setPrestamoData({
                    ...prestamoData,
                    total_financiamiento: parseFloat(e.target.value) || 0,
                  })
                  setCambios({ ...cambios, prestamo: true })
                  if (errores['total_financiamiento'])
                    setErrores({ ...errores, total_financiamiento: '' })
                }}
                className={`pl-10 ${errores['total_financiamiento'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                placeholder="0.00"
              />
            </div>
            {errores['total_financiamiento'] && (
              <p className="text-xs text-red-600">
                {errores['total_financiamiento']}
              </p>
            )}
          </div>

          {/* Cuota Período */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Cuota por Período (USD)
            </label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                type="number"
                step="0.01"
                min="0"
                value={prestamoData.cuota_periodo ?? ''}
                onChange={e => {
                  setPrestamoData({
                    ...prestamoData,
                    cuota_periodo: parseFloat(e.target.value) || 0,
                  })
                  setCambios({ ...cambios, prestamo: true })
                  if (errores['cuota_periodo'])
                    setErrores({ ...errores, cuota_periodo: '' })
                }}
                className={`pl-10 ${errores['cuota_periodo'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                placeholder="0.00"
              />
            </div>
            {errores['cuota_periodo'] && (
              <p className="text-xs text-red-600">{errores['cuota_periodo']}</p>
            )}
          </div>

          {/* Número de Cuotas */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Número de Cuotas <span className="text-red-500">*</span>
            </label>
            <Input
              type="number"
              min="1"
              step="1"
              value={prestamoData.numero_cuotas || ''}
              onChange={e => {
                const nextN = parseInt(e.target.value, 10) || 0
                setPrestamoData({
                  ...prestamoData,
                  numero_cuotas: nextN,
                })
                setCuotasData(prev => mergeCuotasParaMostrar(prev, nextN))
                setCambios({ ...cambios, prestamo: true, cuotas: true })
                if (errores['numero_cuotas'])
                  setErrores({ ...errores, numero_cuotas: '' })
              }}
              title="En revisión manual puede ajustar el plazo; el servidor rechaza cambios inválidos (p. ej. préstamo liquidado con reglas de cuotas)."
              className={`${errores['numero_cuotas'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
              placeholder="0"
            />
            {errores['numero_cuotas'] && (
              <p className="text-xs text-red-600">{errores['numero_cuotas']}</p>
            )}
          </div>

          {/* Tasa de Interés - OCULTO (0% por defecto) */}

          {/* Modalidad Pago */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Modalidad de Pago
            </label>
            <Select
              value={prestamoData.modalidad_pago || '-'}
              onValueChange={v => {
                setPrestamoData({
                  ...prestamoData,
                  modalidad_pago: v === '-' ? '' : v,
                })
                setCambios({ ...cambios, prestamo: true })
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="-">-</SelectItem>
                <SelectItem value="MENSUAL">Mensual</SelectItem>
                <SelectItem value="QUINCENAL">Quincenal</SelectItem>
                <SelectItem value="SEMANAL">Semanal</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Valor Activo - OCULTO */}

          {/* Bloque: fecha de requerimiento (actualización manual en BD). */}
          <div className="rounded-lg border border-gray-200 bg-slate-50/80 p-3 md:col-span-2">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">
                Fecha de requerimiento
              </span>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                Actualización manual
              </span>
            </div>
            <p className="mb-2 text-xs text-gray-600">
              Fecha de solicitud/requerimiento del expediente (tabla{' '}
              <code className="rounded bg-white px-1">
                prestamos.fecha_requerimiento
              </code>
              ). Se muestra el valor cargado desde la base; corríjala aquí si
              debe alinearse con otros datos del expediente. No altera la tabla
              de cuotas por sí sola.
            </p>
            <div className="relative min-w-0 max-w-md">
              <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                type="date"
                disabled={soloLectura}
                value={formatDateForInput(prestamoData.fecha_requerimiento)}
                onChange={e => {
                  formDirtyRef.current = true
                  const v = e.target.value || null
                  setPrestamoData({
                    ...prestamoData,
                    fecha_requerimiento: v,
                  })
                  setCambios({ ...cambios, prestamo: true })
                }}
                className="pl-10"
              />
            </div>
          </div>

          {/* Bloque: fecha de aprobación (manual; en BD se guarda el día anterior al selector). */}
          <div className="rounded-lg border border-gray-200 bg-slate-50/80 p-3 md:col-span-2">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">Fecha de aprobación</span>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                Actualización manual
              </span>
            </div>
            <p className="mb-2 text-xs text-gray-600">
              Columna{' '}
              <code className="rounded bg-white px-1">
                prestamos.fecha_aprobacion
              </code>{' '}
              y{' '}
              <code className="rounded bg-white px-1">
                prestamos.fecha_base_calculo
              </code>
              . En esta pantalla, al guardar o al usar «Recalcular
              vencimientos», el valor persistido en base es el{' '}
              <strong className="font-medium">día calendario anterior</strong>{' '}
              al indicado en el selector (inicio de ese día). Es obligatoria si
              el estado es Aprobado, Desembolsado o Liquidado. «Recalcular
              vencimientos» usa esa fecha persistida junto con plazo, cuota por
              período y modalidad.
            </p>
            <div className="relative min-w-0 max-w-md">
              <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                type="date"
                disabled={soloLectura}
                value={formatDateForInput(prestamoData.fecha_aprobacion)}
                onChange={e => {
                  formDirtyRef.current = true
                  const v = e.target.value || null
                  setPrestamoData({
                    ...prestamoData,
                    fecha_aprobacion: v,
                  })
                  setCambios({ ...cambios, prestamo: true })
                  if (errores['fecha_aprobacion']) {
                    setErrores({
                      ...errores,
                      fecha_aprobacion: '',
                    })
                  }
                }}
                className={`pl-10 ${errores['fecha_aprobacion'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
              />
            </div>
            {errores['fecha_aprobacion'] && (
              <p className="mt-2 text-xs text-red-600">
                {errores['fecha_aprobacion']}
              </p>
            )}
            <Button
              type="button"
              variant="outline"
              className="mt-3 w-full max-w-md shrink-0 sm:w-auto"
              disabled={soloLectura || recalculandoFechasCuotas}
              onClick={handleGuardarFechaYRecalcularVencimientos}
              title="Persiste en BD las condiciones del préstamo (formulario) y reconstruye la tabla de cuotas (plazo, montos y vencimientos); luego reaplica pagos pendientes a cuotas."
            >
              {recalculandoFechasCuotas ? (
                <Loader2 className="mr-2 h-4 w-4 shrink-0 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4 shrink-0" />
              )}
              Recalcular vencimientos
            </Button>
          </div>

          {/* Fecha Base Cálculo - OCULTO */}
          {/* Sincronizada en servidor/BD con fecha_aprobacion cuando aplica; no se edita aquí. */}

          {/* Producto - OCULTO */}
          {/* Este campo se maneja en el módulo de gestión de préstamos, no en revisión manual */}

          {/* Concesionario */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Concesionario
            </label>
            <Select
              value={prestamoData.concesionario || '-'}
              onValueChange={v => {
                setPrestamoData({
                  ...prestamoData,
                  concesionario: v === '-' ? '' : v,
                })
                setCambios({ ...cambios, prestamo: true })
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="-" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="-">-</SelectItem>
                {prestamoData.concesionario &&
                  !concesionarios.some(
                    (c: any) => c.nombre === prestamoData.concesionario
                  ) && (
                    <SelectItem value={prestamoData.concesionario}>
                      {prestamoData.concesionario}
                    </SelectItem>
                  )}
                {concesionarios.map((c: any) => (
                  <SelectItem key={c.id} value={c.nombre}>
                    {c.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Analista */}
          <div>
            <label className="mb-1 block text-sm font-medium">Analista</label>
            <Select
              value={prestamoData.analista || '-'}
              onValueChange={v => {
                setPrestamoData({
                  ...prestamoData,
                  analista: v === '-' ? '' : v,
                })
                setCambios({ ...cambios, prestamo: true })
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="-" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="-">-</SelectItem>
                {prestamoData.analista &&
                  !analistas.some(
                    (a: any) => a.nombre === prestamoData.analista
                  ) && (
                    <SelectItem value={prestamoData.analista}>
                      {prestamoData.analista}
                    </SelectItem>
                  )}
                {analistas.map((a: any) => (
                  <SelectItem key={a.id} value={a.nombre}>
                    {a.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Modelo Vehículo */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Modelo de Vehículo
            </label>
            <Select
              value={prestamoData.modelo_vehiculo || '-'}
              onValueChange={v => {
                setPrestamoData({
                  ...prestamoData,
                  modelo_vehiculo: v === '-' ? '' : v,
                })
                setCambios({ ...cambios, prestamo: true })
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="-" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="-">-</SelectItem>
                {prestamoData.modelo_vehiculo &&
                  !modelosVehiculos.some(
                    (m: any) => m.modelo === prestamoData.modelo_vehiculo
                  ) && (
                    <SelectItem value={prestamoData.modelo_vehiculo}>
                      {prestamoData.modelo_vehiculo}
                    </SelectItem>
                  )}
                {modelosVehiculos.map((m: any) => (
                  <SelectItem key={m.id} value={m.modelo}>
                    {m.modelo}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Cédula préstamo */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Cédula (registro préstamo)
            </label>
            <div className="relative">
              <CreditCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                type="text"
                value={prestamoData.cedula || ''}
                onChange={e => {
                  setPrestamoData({
                    ...prestamoData,
                    cedula: e.target.value,
                  })
                  setCambios({ ...cambios, prestamo: true })
                }}
                className="pl-10"
                placeholder="Cédula"
              />
            </div>
          </div>

          {/* Nombres préstamo */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Nombres (registro préstamo)
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                type="text"
                value={prestamoData.nombres || ''}
                onChange={e => {
                  setPrestamoData({
                    ...prestamoData,
                    nombres: e.target.value,
                  })
                  setCambios({ ...cambios, prestamo: true })
                }}
                className="pl-10"
                placeholder="Nombres"
              />
            </div>
          </div>

          {/* Usuario Proponente */}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Usuario Proponente
            </label>
            <Input
              type="text"
              value={prestamoData.usuario_proponente || ''}
              onChange={e => {
                setPrestamoData({
                  ...prestamoData,
                  usuario_proponente: e.target.value,
                })
                setCambios({ ...cambios, prestamo: true })
              }}
              placeholder="Usuario proponente"
            />
          </div>

          {/* Usuario Aprobador - OCULTO */}
        </div>

        {/* Observaciones - ancho completo */}
        <div>
          <label className="mb-1 block text-sm font-medium">
            Observaciones
          </label>
          <Textarea
            value={prestamoData.observaciones || ''}
            onChange={e => {
              setPrestamoData({
                ...prestamoData,
                observaciones: e.target.value,
              })
              setCambios({ ...cambios, prestamo: true })
            }}
            placeholder="Ingresa observaciones del préstamo..."
            rows={3}
          />
        </div>
      </CardContent>
    </Card>
  )
}
