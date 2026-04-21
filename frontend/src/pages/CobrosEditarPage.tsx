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

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog'

import toast from 'react-hot-toast'

import { Loader2, Eye } from 'lucide-react'
import {
  aplicarSufijoVistoADocumento,
  collectTokensSufijoVistoArchivoDesdeFilas,
  letterSufijoVistoDesdeMensajeDuplicado,
  mensajeEdicionManualSufijoVistoProhibida,
  SUFIJO_VISTO_ARCHIVO_RE,
  TOKEN_SUFIJO_VISTO_ARCHIVO_RE,
} from '../utils/documentoSufijoVisto'

import { normalizarNumeroDocumento } from '../utils/pagoExcelValidation'

const INSTITUCIONES_FINANCIERAS = [
  'BINANCE',

  'BNC',

  'Banco de Venezuela',

  'Mercantil',

  'Recibos',
]

function baseYTokenNumeroOperacion(raw: string): { base: string; token: string } {
  const s = (raw || '').trim()
  const m = s.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
  if (m) {
    return {
      base: s.replace(SUFIJO_VISTO_ARCHIVO_RE, '').trim(),
      token: m[1].toUpperCase(),
    }
  }
  return { base: s, token: '' }
}

function detalleErrorApi(e: unknown): string {
  const any = e as { message?: string; response?: { data?: { detail?: unknown } } }
  const d = any?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    try {
      return JSON.stringify(d)
    } catch {
      return 'Error al guardar.'
    }
  }
  return any?.message || 'Error al guardar.'
}

export default function CobrosEditarPage() {
  const { id } = useParams<{ id: string }>()

  const navigate = useNavigate()

  const [detalle, setDetalle] = useState<PagoReportadoDetalleResponse | null>(
    null
  )

  const [loading, setLoading] = useState(true)

  const [saving, setSaving] = useState(false)

  const [vistoSaving, setVistoSaving] = useState(false)

  const [vistoAyudaOpen, setVistoAyudaOpen] = useState(false)

  const ultimoErrorVistoRef = useRef('')

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

  const handleVistoRellenarSufijoYGuardar = async () => {
    if (!id || vistoSaving || saving) return

    const trimmed = form.numero_operacion.trim()
    const { base } = baseYTokenNumeroOperacion(trimmed)
    if (!base) {
      toast.error('Primero indique el número de operación / referencia bancaria.')
      return
    }

    const montoNum = form.monto ? parseFloat(form.monto) : undefined
    if (montoNum !== undefined && (isNaN(montoNum) || montoNum < 0)) {
      toast.error('Monto debe ser un número mayor o igual a 0.')
      return
    }

    setVistoSaving(true)
    try {
      const letter = letterSufijoVistoDesdeMensajeDuplicado(
        ultimoErrorVistoRef.current
      )
      const hadSuffix = SUFIJO_VISTO_ARCHIVO_RE.test(trimmed)
      const nuevo = aplicarSufijoVistoADocumento(
        base,
        letter,
        tokensSufijoUsadosRef.current,
        { reemplazarSufijoAdmin: hadSuffix }
      )
      if (!nuevo || nuevo === trimmed) {
        toast.error('No se pudo asignar sufijo. Revise el número de operación.')
        return
      }

      const res = await updatePagoReportado(Number(id), {
        nombres: form.nombres.trim() || undefined,
        apellidos: form.apellidos.trim() || undefined,
        tipo_cedula: form.tipo_cedula.trim() || undefined,
        numero_cedula: form.numero_cedula.trim() || undefined,
        fecha_pago: form.fecha_pago || undefined,
        institucion_financiera: form.institucion_financiera.trim() || undefined,
        numero_operacion: nuevo,
        monto: montoNum,
        moneda: form.moneda.trim() || undefined,
        correo_enviado_a: form.correo_enviado_a.trim() || undefined,
        observacion: form.observacion.trim() || undefined,
      })

      ultimoErrorVistoRef.current = ''
      toast.success(res.mensaje || 'Código asignado y datos guardados.')
      await load()
    } catch (e: unknown) {
      const msg = detalleErrorApi(e)
      ultimoErrorVistoRef.current = msg
      toast.error(msg)
    } finally {
      setVistoSaving(false)
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

      ultimoErrorVistoRef.current = ''
      toast.success(res.mensaje || 'Cambios guardados.')

      navigate(`/cobros/pagos-reportados/${id}`)
    } catch (e: unknown) {
      const msg = detalleErrorApi(e)
      if (/duplicad|DUPLICADO|ya est[aá]/i.test(msg)) {
        ultimoErrorVistoRef.current = msg
      }
      toast.error(msg)
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
            disabled={loading || saving || vistoSaving}
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

      {detalle.duplicado_en_pagos && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          <p>
            Este reporte ya tiene un pago en cartera.
            {typeof detalle.prestamo_existente_id === 'number' && (
              <>
                {' '}
                Préstamo aplicado: <strong>#{detalle.prestamo_existente_id}</strong>.
              </>
            )}
            {typeof detalle.pago_existente_id === 'number' && (
              <>
                {' '}
                Pago existente: <strong>#{detalle.pago_existente_id}</strong>
                {detalle.pago_existente_estado
                  ? ` (${detalle.pago_existente_estado})`
                  : ''}
                .
              </>
            )}
          </p>
          {typeof detalle.prestamo_objetivo_id === 'number' && (
            <p className="mt-1">
              Préstamo objetivo del caso (actual):{' '}
              <strong>#{detalle.prestamo_objetivo_id}</strong>
              {detalle.prestamo_objetivo_multiple ? (
                <span className="ml-1 text-amber-700">
                  (hay más de un préstamo APROBADO para la cédula)
                </span>
              ) : null}
              .
            </p>
          )}
          {typeof detalle.prestamo_existente_id === 'number' &&
          typeof detalle.prestamo_objetivo_id === 'number' ? (
            <p className="mt-1">
              Diagnóstico:{' '}
              {detalle.prestamo_duplicado_es_objetivo ? (
                <strong className="text-emerald-700">
                  ya fue cargado al préstamo actual.
                </strong>
              ) : (
                <strong className="text-amber-700">
                  fue cargado a otro préstamo (distinto al actual).
                </strong>
              )}
            </p>
          ) : null}
          {typeof detalle.prestamo_existente_id === 'number' && (
            <div className="mt-2 flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  navigate(
                    `/prestamos?filtro_prestamo_id=${detalle.prestamo_existente_id}`
                  )
                }
              >
                Abrir préstamo #{detalle.prestamo_existente_id}
              </Button>
              {typeof detalle.prestamo_objetivo_id === 'number' &&
              detalle.prestamo_objetivo_id !== detalle.prestamo_existente_id ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    navigate(
                      `/prestamos?filtro_prestamo_id=${detalle.prestamo_objetivo_id}`
                    )
                  }
                >
                  Abrir préstamo actual #{detalle.prestamo_objetivo_id}
                </Button>
              ) : null}
            </div>
          )}
        </div>
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

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="mb-1 block text-sm font-medium">
                  Número de operación{' '}
                  <span className="text-red-500">*</span>
                </label>

                <Input
                  value={baseYTokenNumeroOperacion(form.numero_operacion).base}
                  onChange={e => {
                    const v = e.target.value
                    const prevBase = baseYTokenNumeroOperacion(
                      form.numero_operacion
                    ).base
                    const msg = mensajeEdicionManualSufijoVistoProhibida(
                      prevBase,
                      v
                    )
                    if (msg) {
                      toast.error(msg)
                      return
                    }
                    const token = baseYTokenNumeroOperacion(
                      form.numero_operacion
                    ).token
                    const compuesto = token ? `${v.trim()}_${token}` : v
                    setForm(f => ({ ...f, numero_operacion: compuesto }))
                  }}
                  onBlur={() => {
                    setForm(prev => {
                      const { base, token } = baseYTokenNumeroOperacion(
                        prev.numero_operacion
                      )
                      const raw = base.trim()
                      const n =
                        normalizarNumeroDocumento(raw) || raw
                      const msg = mensajeEdicionManualSufijoVistoProhibida(
                        raw,
                        n
                      )
                      if (msg) {
                        toast.error(msg)
                        return prev
                      }
                      const nextOp = token ? `${n}_${token}` : n
                      if (nextOp === prev.numero_operacion) return prev
                      return { ...prev, numero_operacion: nextOp }
                    })
                  }}
                  placeholder="Referencia / serial del banco"
                />
                <p className="text-xs text-muted-foreground">
                  No escriba manualmente el sufijo <code className="rounded bg-muted px-1">_A####</code> ni{' '}
                  <code className="rounded bg-muted px-1">_P####</code>: use{' '}
                  <strong>Visto</strong> o los botones de sufijo (borrador) y luego Guardar.
                </p>
              </div>

              <div className="space-y-2">
                <label className="mb-1 block text-sm font-medium">
                  Código{' '}
                  <span className="text-xs font-normal text-muted-foreground">
                    (solo lectura; lo asigna Visto)
                  </span>
                </label>

                <Input
                  readOnly
                  aria-readonly="true"
                  title="Este campo no se escribe a mano. Se rellena con el botón Visto (revisión manual / Cobros)."
                  value={baseYTokenNumeroOperacion(form.numero_operacion).token}
                  placeholder="Pendiente: use Visto"
                  className="cursor-default bg-slate-50 text-slate-800"
                />
                <p className="text-xs text-muted-foreground">
                  Token <strong>A####</strong> / <strong>P####</strong> al final del número de operación (mismo criterio
                  que en revisión manual y carga masiva).
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-violet-200/70 bg-violet-50 px-3 py-2">
              <p className="min-w-0 flex-1 text-xs text-violet-900">
                <span className="font-medium">Revisión manual:</span> Visto asigna el código
                (_A#### / _P####) y guarda en el servidor de inmediato.
              </p>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  className="text-[11px] font-medium text-violet-700 underline underline-offset-2 hover:text-violet-950"
                  onClick={() => setVistoAyudaOpen(true)}
                >
                  Sin cambiar doc.
                </button>
                <Button
                  type="button"
                  size="sm"
                  disabled={saving || vistoSaving}
                  className="h-8 min-w-[4.5rem] bg-violet-600 px-3 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50"
                  onClick={() => void handleVistoRellenarSufijoYGuardar()}
                >
                  {vistoSaving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    'Visto'
                  )}
                </Button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleAplicarSufijoOperacion('A')}
                title="Sufijo en borrador: _A#### (luego Guardar y continuar)"
              >
                <Eye className="mr-2 h-4 w-4" />
                Agregar sufijo A
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleAplicarSufijoOperacion('P')}
                title="Sufijo en borrador: _P#### (luego Guardar y continuar)"
              >
                <Eye className="mr-2 h-4 w-4" />
                Agregar sufijo P
              </Button>
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
              <Button type="submit" disabled={saving || vistoSaving}>
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

      <Dialog open={vistoAyudaOpen} onOpenChange={setVistoAyudaOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Duplicado u observación (Cobros)</DialogTitle>
            <div className="space-y-2 text-sm text-gray-600">
              <p>
                El botón <strong>Visto</strong> añade un token <strong>_A####</strong> /{' '}
                <strong>_P####</strong> al <strong>número de operación</strong> y{' '}
                <strong>guarda de inmediato</strong> en el servidor. Así puede desambiguar la misma
                referencia bancaria sin reescribir el comprobante a mano.
              </p>
              <p className="text-xs">
                No está permitido pegar manualmente <code className="rounded bg-gray-100 px-1">_A####</code> ni{' '}
                <code className="rounded bg-gray-100 px-1">_P####</code> en el número de operación: use{' '}
                <strong>Visto</strong> o los botones de sufijo en borrador y luego Guardar.
              </p>
            </div>
          </DialogHeader>
          <DialogFooter className="flex flex-col gap-2 sm:flex-col sm:justify-stretch">
            <button
              type="button"
              className="w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
              onClick={() => {
                ultimoErrorVistoRef.current = ''
                toast.success(
                  'Listo. Si al guardar persiste aviso de duplicado en pagos, pulse Visto para asignar código automáticamente.'
                )
                setVistoAyudaOpen(false)
              }}
            >
              Entendido: continuar sin cambiar el documento
            </button>
            <button
              type="button"
              className="w-full rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
              onClick={() => setVistoAyudaOpen(false)}
            >
              Cerrar
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
