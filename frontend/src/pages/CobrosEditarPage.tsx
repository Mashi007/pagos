/**





 * Editar pago reportado: modificar valores para que cumplan con los validadores (cédula, fecha, monto, etc.).





 * Editable si no está aprobado ni importado a pagos (incluye rechazado y en revisión).





 */

import React, { useState, useEffect, useRef } from 'react'

import { useParams, useNavigate } from 'react-router-dom'

import {
  getPagoReportadoDetalle,
  updatePagoReportado,
  type PagoReportadoDetalleResponse,
} from '../services/cobrosService'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import toast from 'react-hot-toast'

import { Loader2, Eye } from 'lucide-react'
import {
  aplicarSufijoVistoADocumento,
  collectTokensSufijoVistoArchivoDesdeFilas,
  SUFIJO_VISTO_ARCHIVO_RE,
} from '../utils/documentoSufijoVisto'

const INSTITUCIONES_FINANCIERAS = [
  'BINANCE',

  'BNC',

  'Banco de Venezuela',

  'Mercantil',

  'Recibos',
]

export default function CobrosEditarPage() {
  const { id } = useParams<{ id: string }>()

  const navigate = useNavigate()

  const [detalle, setDetalle] = useState<PagoReportadoDetalleResponse | null>(
    null
  )

  const [loading, setLoading] = useState(true)

  const [saving, setSaving] = useState(false)

  const [otroInstitucion, setOtroInstitucion] = useState('')
  const tokensSufijoUsadosRef = useRef<Set<string>>(new Set())

  const [form, setForm] = useState({
    nombres: '',

    apellidos: '',

    tipo_cedula: 'V',

    numero_cedula: '',

    fecha_pago: '',

    institucion_financiera: '',

    numero_operacion: '',

    monto: '',

    moneda: 'BS',

    correo_enviado_a: '',

    observacion: '',
  })

  const load = async () => {
    if (!id) return

    setLoading(true)

    try {
      const res = await getPagoReportadoDetalle(Number(id))

      setDetalle(res)

      // Monto como texto plano para <input type="number"> (evita miles es-VE que bloquean la edición)
      const montoRaw =
        typeof res.monto === 'number' && !Number.isNaN(res.monto)
          ? String(res.monto)
          : ''

      setForm({
        nombres: res.nombres || '',

        apellidos: res.apellidos || '',

        tipo_cedula: (res.tipo_cedula || 'V').trim(),

        numero_cedula: (res.numero_cedula || '').trim(),

        fecha_pago: (res.fecha_pago || '').toString().slice(0, 10),

        institucion_financiera: res.institucion_financiera || '',

        numero_operacion: res.numero_operacion || '',

        monto: montoRaw,

        moneda: (() => {
          const m = (res.moneda || 'BS').toUpperCase()
          return ['BS', 'USD', 'USDT'].includes(m) ? m : 'BS'
        })(),

        correo_enviado_a: res.correo_enviado_a || '',

        observacion: res.observacion || res.gemini_comentario || '',
      })
      tokensSufijoUsadosRef.current = collectTokensSufijoVistoArchivoDesdeFilas(
        [{ numero_documento: res.numero_operacion || '' }]
      )

      const inst = res.institucion_financiera || ''

      setOtroInstitucion(INSTITUCIONES_FINANCIERAS.includes(inst) ? '' : inst)
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar.')

      navigate('/cobros/pagos-reportados')
    } finally {
      setLoading(false)
    }
  }

  const handleAplicarSufijoOperacion = (letter: 'A' | 'P') => {
    const actual = form.numero_operacion.trim()
    if (!actual) {
      toast.error('Primero escriba un número de operación.')
      return
    }
    if (SUFIJO_VISTO_ARCHIVO_RE.test(actual)) {
      toast.error('Este número de operación ya tiene sufijo admin.')
      return
    }
    const nuevo = aplicarSufijoVistoADocumento(
      actual,
      letter,
      tokensSufijoUsadosRef.current
    )
    if (!nuevo || nuevo === actual) {
      toast.error('No se pudo asignar sufijo.')
      return
    }
    setForm(f => ({ ...f, numero_operacion: nuevo }))
    toast.success(`Sufijo _${letter}#### aplicado al número de operación.`)
  }

  useEffect(() => {
    load()
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!id) return

    setSaving(true)

    try {
      const montoNum = form.monto ? parseFloat(form.monto) : undefined

      if (montoNum !== undefined && (isNaN(montoNum) || montoNum < 0)) {
        toast.error('Monto debe ser un número mayor o igual a 0.')

        setSaving(false)

        return
      }

      const res = await updatePagoReportado(Number(id), {
        nombres: form.nombres.trim() || undefined,

        apellidos: form.apellidos.trim() || undefined,

        tipo_cedula: form.tipo_cedula.trim() || undefined,

        numero_cedula: form.numero_cedula.trim() || undefined,

        fecha_pago: form.fecha_pago || undefined,

        institucion_financiera: form.institucion_financiera.trim() || undefined,

        numero_operacion: form.numero_operacion.trim() || undefined,

        monto: montoNum,

        moneda: form.moneda.trim() || undefined,

        correo_enviado_a: form.correo_enviado_a.trim() || undefined,

        observacion: form.observacion.trim() || undefined,
      })

      toast.success(res.mensaje || 'Cambios guardados.')

      navigate(`/cobros/pagos-reportados/${id}`)
    } catch (e: any) {
      toast.error(
        e?.message || e?.response?.data?.detail || 'Error al guardar.'
      )
    } finally {
      setSaving(false)
    }
  }

  if (loading || !detalle) {
    return (
      <div className="flex items-center gap-2 p-6">
        <Loader2 className="h-5 w-5 animate-spin" /> Cargando...
      </div>
    )
  }

  if (detalle.estado === 'aprobado' || detalle.estado === 'importado') {
    return (
      <div className="space-y-4 p-6">
        <p className="text-muted-foreground">
          No se puede editar un pago ya{' '}
          {detalle.estado === 'aprobado' ? 'aprobado' : 'importado a pagos'}.
        </p>

        <Button
          variant="outline"
          onClick={() => navigate(`/cobros/pagos-reportados/${id}`)}
        >
          Volver al detalle
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={() => navigate('/cobros/pagos-reportados')}
        >
          ← Volver al listado
        </Button>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={loading || saving}
            onClick={() => load()}
          >
            Recargar datos
          </Button>

          <Button
            variant="outline"
            onClick={() => navigate(`/cobros/pagos-reportados/${id}`)}
          >
            Ver detalle
          </Button>
        </div>
      </div>

      {detalle.estado === 'rechazado' && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Este reporte está <strong>rechazado</strong>. Puede corregir montos,
          referencia y demás datos; luego cambie el estado a «En revisión» desde
          el detalle si corresponde.
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>
            Editar reporte{' '}
            {detalle.referencia_interna?.startsWith('#')
              ? detalle.referencia_interna
              : `#${detalle.referencia_interna}`}
          </CardTitle>

          <p className="text-sm text-muted-foreground">
            Los datos se cargan al abrir la página o con «Recargar datos». Al
            guardar se pasa al <strong>detalle del reporte</strong> (siguiente
            paso: aprobar, rechazar o revisar comprobante).
          </p>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Nombres
                </label>

                <Input
                  value={form.nombres}
                  onChange={e =>
                    setForm(f => ({ ...f, nombres: e.target.value }))
                  }
                  placeholder="Nombres"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Apellidos
                </label>

                <Input
                  value={form.apellidos}
                  onChange={e =>
                    setForm(f => ({ ...f, apellidos: e.target.value }))
                  }
                  placeholder="Apellidos"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Tipo cédula
                </label>

                <select
                  className="w-full rounded-md border px-3 py-2"
                  value={form.tipo_cedula}
                  onChange={e =>
                    setForm(f => ({ ...f, tipo_cedula: e.target.value }))
                  }
                >
                  <option value="V">V</option>

                  <option value="E">E</option>

                  <option value="J">J</option>

                  <option value="G">G</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Número cédula
                </label>

                <Input
                  value={form.numero_cedula}
                  onChange={e =>
                    setForm(f => ({
                      ...f,
                      numero_cedula: e.target.value
                        .replace(/\D/g, '')
                        .slice(0, 13),
                    }))
                  }
                  placeholder="Solo dígitos"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">
                Fecha de pago
              </label>

              <Input
                type="date"
                value={form.fecha_pago}
                onChange={e =>
                  setForm(f => ({ ...f, fecha_pago: e.target.value }))
                }
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">
                Institución financiera
              </label>

              <select
                className="min-h-[40px] w-full rounded-md border bg-white px-3 py-2"
                value={
                  INSTITUCIONES_FINANCIERAS.includes(
                    form.institucion_financiera
                  )
                    ? form.institucion_financiera
                    : 'Otros'
                }
                onChange={e => {
                  const v = e.target.value

                  if (v === 'Otros') {
                    setForm(f => ({
                      ...f,
                      institucion_financiera: otroInstitucion,
                    }))
                  } else {
                    setForm(f => ({ ...f, institucion_financiera: v }))

                    setOtroInstitucion('')
                  }
                }}
              >
                <option value="">Seleccione...</option>

                {INSTITUCIONES_FINANCIERAS.map(opt => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}

                <option value="Otros">Otros</option>
              </select>

              {!INSTITUCIONES_FINANCIERAS.includes(
                form.institucion_financiera
              ) && (
                <Input
                  className="mt-2"
                  value={form.institucion_financiera || otroInstitucion}
                  onChange={e => {
                    const val = e.target.value

                    setOtroInstitucion(val)

                    setForm(f => ({ ...f, institucion_financiera: val }))
                  }}
                  placeholder="Nombre del banco o entidad"
                />
              )}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">
                Número de operación
              </label>

              <div className="space-y-2">
                <Input
                  value={form.numero_operacion}
                  onChange={e =>
                    setForm(f => ({ ...f, numero_operacion: e.target.value }))
                  }
                  placeholder="Referencia / serial"
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleAplicarSufijoOperacion('A')}
                    title="Asignar sufijo único _A#### (mismo crédito/carga)"
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    Agregar sufijo A
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleAplicarSufijoOperacion('P')}
                    title="Asignar sufijo único _P#### (otro préstamo)"
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    Agregar sufijo P
                  </Button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">Monto</label>

                <Input
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min={0}
                  value={form.monto}
                  onChange={e =>
                    setForm(f => ({ ...f, monto: e.target.value }))
                  }
                  placeholder="0.00"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  Use punto como decimal (ej. 94.01). Editable en todos los
                  estados permitidos.
                </p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Moneda</label>

                <select
                  className="w-full rounded-md border bg-white px-3 py-2"
                  value={
                    ['BS', 'USD', 'USDT'].includes(form.moneda)
                      ? form.moneda
                      : 'BS'
                  }
                  onChange={e =>
                    setForm(f => ({ ...f, moneda: e.target.value }))
                  }
                >
                  <option value="BS">BS (Bolívares)</option>
                  <option value="USD">USD (Dólares)</option>
                  <option value="USDT">USDT (equivale a USD al guardar)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">
                Correo (para envío de recibo)
              </label>

              <Input
                type="email"
                value={form.correo_enviado_a}
                onChange={e =>
                  setForm(f => ({ ...f, correo_enviado_a: e.target.value }))
                }
                placeholder="email@ejemplo.com"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">
                Observación (opcional)
              </label>

              <textarea
                className="min-h-[88px] w-full rounded-md border px-3 py-2 text-sm"
                value={form.observacion}
                onChange={e =>
                  setForm(f => ({ ...f, observacion: e.target.value }))
                }
                placeholder="Nota interna"
                maxLength={500}
              />
            </div>

            <div className="flex flex-wrap gap-2 pt-4">
              <Button type="submit" disabled={saving}>
                {saving ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Guardar y continuar
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={() => navigate(`/cobros/pagos-reportados/${id}`)}
              >
                Volver al detalle
              </Button>

              <Button
                type="button"
                variant="ghost"
                onClick={() => navigate('/cobros/pagos-reportados')}
              >
                Listado
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
