/**
 * Editar pago reportado: modificar valores para que cumplan con los validadores (cédula, fecha, monto, etc.).
 * Solo disponible cuando estado es pendiente o en_revision.
 */
import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getPagoReportadoDetalle, updatePagoReportado, type PagoReportadoDetalleResponse } from '../services/cobrosService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import toast from 'react-hot-toast'
import { Loader2 } from 'lucide-react'

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
  const [detalle, setDetalle] = useState<PagoReportadoDetalleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [otroInstitucion, setOtroInstitucion] = useState('')
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
      const montoRaw = res.monto != null ? String(res.monto) : ''
      setForm({
        nombres: res.nombres || '',
        apellidos: res.apellidos || '',
        tipo_cedula: (res.tipo_cedula || 'V').trim(),
        numero_cedula: (res.numero_cedula || '').trim(),
        fecha_pago: (res.fecha_pago || '').toString().slice(0, 10),
        institucion_financiera: res.institucion_financiera || '',
        numero_operacion: res.numero_operacion || '',
        monto: montoRaw,
        moneda: res.moneda || 'BS',
        correo_enviado_a: res.correo_enviado_a || '',
        observacion: res.observacion || res.gemini_comentario || '',
      })
      const inst = res.institucion_financiera || ''
      setOtroInstitucion(INSTITUCIONES_FINANCIERAS.includes(inst) ? '' : inst)
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar.')
      navigate('/cobros/pagos-reportados')
    } finally {
      setLoading(false)
    }
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
      await updatePagoReportado(Number(id), {
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
      toast.success('Datos actualizados. Los cambios cumplen con los validadores.')
      navigate(`/cobros/pagos-reportados/${id}`)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || e?.message || 'Error al guardar.')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !detalle) {
    return (
      <div className="p-6 flex items-center gap-2">
        <Loader2 className="h-5 w-5 animate-spin" /> Cargando...
      </div>
    )
  }

  const formatMontoDisplay = (val: string) => {
    const num = parseFloat(val.replace(/,/g, '.').replace(/\s/g, ''))
    if (Number.isNaN(num)) return ''
    return num.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  const parseMontoInput = (val: string) => {
    const cleaned = val.replace(/[^\d.,]/g, '')
    const lastSep = Math.max(cleaned.lastIndexOf('.'), cleaned.lastIndexOf(','))
    if (lastSep === -1) return cleaned
    const before = cleaned.slice(0, lastSep).replace(/[.,]/g, '')
    const after = cleaned.slice(lastSep + 1).replace(/\D/g, '').slice(0, 2)
    return after ? `${before || '0'}.${after}` : (before || '0')
  }

  if (detalle.estado === 'aprobado' || detalle.estado === 'rechazado') {
    return (
      <div className="p-6 space-y-4">
        <p className="text-muted-foreground">
          No se puede editar un pago ya {detalle.estado === 'aprobado' ? 'aprobado' : 'rechazado'}.
        </p>
        <Button variant="outline" onClick={() => navigate(`/cobros/pagos-reportados/${id}`)}>
          Volver al detalle
        </Button>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate('/cobros/pagos-reportados')}>
          ← Volver al listado
        </Button>
        <Button variant="outline" onClick={() => navigate(`/cobros/pagos-reportados/${id}`)}>
          Ver detalle
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Editar reporte #{detalle.referencia_interna}</CardTitle>
          <p className="text-sm text-muted-foreground">
            Modifica los valores para que cumplan con los validadores (cédula, fecha, monto, etc.).
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Nombres</label>
                <Input
                  value={form.nombres}
                  onChange={(e) => setForm((f) => ({ ...f, nombres: e.target.value }))}
                  placeholder="Nombres"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Apellidos</label>
                <Input
                  value={form.apellidos}
                  onChange={(e) => setForm((f) => ({ ...f, apellidos: e.target.value }))}
                  placeholder="Apellidos"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Tipo cédula</label>
                <select
                  className="w-full border rounded-md px-3 py-2"
                  value={form.tipo_cedula}
                  onChange={(e) => setForm((f) => ({ ...f, tipo_cedula: e.target.value }))}
                >
                  <option value="V">V</option>
                  <option value="E">E</option>
                  <option value="J">J</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Número cédula</label>
                <Input
                  value={form.numero_cedula}
                  onChange={(e) => setForm((f) => ({ ...f, numero_cedula: e.target.value.replace(/\D/g, '').slice(0, 11) }))}
                  placeholder="Solo dígitos"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Fecha de pago</label>
              <Input
                type="date"
                value={form.fecha_pago}
                onChange={(e) => setForm((f) => ({ ...f, fecha_pago: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Institución financiera</label>
              <select
                className="w-full border rounded-md px-3 py-2 min-h-[40px] bg-white"
                value={INSTITUCIONES_FINANCIERAS.includes(form.institucion_financiera) ? form.institucion_financiera : 'Otros'}
                onChange={(e) => {
                  const v = e.target.value
                  if (v === 'Otros') {
                    setForm((f) => ({ ...f, institucion_financiera: otroInstitucion }))
                  } else {
                    setForm((f) => ({ ...f, institucion_financiera: v }))
                    setOtroInstitucion('')
                  }
                }}
              >
                <option value="">Seleccione...</option>
                {INSTITUCIONES_FINANCIERAS.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
                <option value="Otros">Otros</option>
              </select>
              {!INSTITUCIONES_FINANCIERAS.includes(form.institucion_financiera) && (
                <Input
                  className="mt-2"
                  value={form.institucion_financiera || otroInstitucion}
                  onChange={(e) => {
                    const val = e.target.value
                    setOtroInstitucion(val)
                    setForm((f) => ({ ...f, institucion_financiera: val }))
                  }}
                  placeholder="Nombre del banco o entidad"
                />
              )}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Número de operación</label>
              <Input
                value={form.numero_operacion}
                onChange={(e) => setForm((f) => ({ ...f, numero_operacion: e.target.value }))}
                placeholder="Referencia / serial"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Monto</label>
                <Input
                  type="text"
                  inputMode="decimal"
                  value={form.monto ? formatMontoDisplay(form.monto) : ''}
                  onChange={(e) => setForm((f) => ({ ...f, monto: parseMontoInput(e.target.value) }))}
                  placeholder="0,00"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Moneda</label>
                <Input
                  value={form.moneda}
                  onChange={(e) => setForm((f) => ({ ...f, moneda: e.target.value }))}
                  placeholder="BS, USD, USDT ($)"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Correo (para envío de recibo)</label>
              <Input
                type="email"
                value={form.correo_enviado_a}
                onChange={(e) => setForm((f) => ({ ...f, correo_enviado_a: e.target.value }))}
                placeholder="email@ejemplo.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Observación (opcional)</label>
              <Input
                value={form.observacion}
                onChange={(e) => setForm((f) => ({ ...f, observacion: e.target.value }))}
                placeholder="Nota interna"
              />
            </div>
            <div className="flex gap-2 pt-4">
              <Button type="submit" disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Guardar cambios
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate(`/cobros/pagos-reportados/${id}`)}>
                Cancelar
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
