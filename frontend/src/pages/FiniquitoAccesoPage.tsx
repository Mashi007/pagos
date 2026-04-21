import { useEffect, useState } from 'react'

import { Link, useNavigate } from 'react-router-dom'

import { CheckCircle2, ChevronLeft, Loader2 } from 'lucide-react'

import { toast } from 'sonner'

import { FiniquitoWorkspaceShell } from '../components/finiquito/FiniquitoWorkspaceShell'

import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'

import {
  finiquitoRegistro,
  finiquitoSolicitarCodigo,
  finiquitoVerificarCodigo,
  FiniquitoHttpError,
  setFiniquitoAccessToken,
} from '../services/finiquitoService'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

import { cn } from '../utils'

export function FiniquitoAccesoPage() {
  const navigate = useNavigate()

  const [cedula, setCedula] = useState('')

  const [email, setEmail] = useState('')

  const [codigo, setCodigo] = useState('')

  const [loading, setLoading] = useState<string | null>(null)

  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')

    sessionStorage.setItem(
      PUBLIC_FLOW_SESSION_KEY + '_path',
      'finiquitos/acceso'
    )
  }, [])

  const onRegistro = async () => {
    if (!cedula.trim() || !email.trim()) {
      toast.error('Ingrese cédula y correo.')

      return
    }

    setLoading('registro')

    try {
      const r = await finiquitoRegistro(cedula.trim(), email.trim())

      toast.success(r.message || 'Registro guardado.', {
        description: 'Ahora pulse «Enviar código» y revise su bandeja.',
      })
    } catch (e: unknown) {
      if (e instanceof FiniquitoHttpError && e.status === 429) {
        toast.error(e.message, {
          duration: 12000,
          description:
            'Límite de registros por hora desde su red. Intente más tarde.',
        })
      } else {
        const msg = e instanceof Error ? e.message : 'Error al registrar'

        toast.error(msg)
      }
    } finally {
      setLoading(null)
    }
  }

  const onSolicitar = async () => {
    if (!cedula.trim() || !email.trim()) {
      toast.error('Ingrese cédula y correo.')

      return
    }

    setLoading('solicitar')

    try {
      const r = await finiquitoSolicitarCodigo(cedula.trim(), email.trim())

      toast.success(r.message || 'Revise su correo.')
    } catch (e: unknown) {
      if (e instanceof FiniquitoHttpError && e.status === 429) {
        toast.error(e.message, {
          duration: 12000,

          description:
            'Límite de solicitudes por hora desde su red. Intente más tarde.',
        })
      } else {
        const msg = e instanceof Error ? e.message : 'Error al enviar código'

        toast.error(msg)
      }
    } finally {
      setLoading(null)
    }
  }

  const onVerificar = async () => {
    if (!cedula.trim() || !email.trim() || !codigo.trim()) {
      toast.error('Complete cédula, correo y código.')

      return
    }

    setLoading('verificar')

    try {
      const r = await finiquitoVerificarCodigo(
        cedula.trim(),

        email.trim(),

        codigo.trim()
      )

      if (!r.ok || !r.access_token) {
        toast.error(r.error || 'Código inválido.')

        return
      }

      setFiniquitoAccessToken(r.access_token)

      toast.success('Sesión iniciada.')

      navigate('/finiquitos/gestion', { replace: true })
    } catch (e: unknown) {
      if (e instanceof FiniquitoHttpError && e.status === 429) {
        toast.error(e.message, {
          duration: 12000,
          description:
            'Demasiados intentos de código. Espere unos minutos e intente de nuevo.',
        })
      } else {
        const msg = e instanceof Error ? e.message : 'Error al verificar'

        toast.error(msg)
      }
    } finally {
      setLoading(null)
    }
  }

  return (
    <FiniquitoWorkspaceShell
      description={
        <p>
          Primera vez: pulse <strong>Registrarme</strong>. Siguientes ingresos:
          mismo cédula y correo y pulse <strong>Enviar código</strong>. No use
          otro correo: el sistema rechaza el registro y no enviará código si la
          pareja no coincide. El correo del código es el mismo flujo que Estado
          de cuenta; revise spam.
        </p>
      }
      actions={
        <Button variant="outline" size="sm" className="gap-2" asChild>
          <Link to="/finiquitos">
            <ChevronLeft className="h-4 w-4" aria-hidden />
            Volver al inicio
          </Link>
        </Button>
      }
    >
      <section
        className={cn(
          'overflow-hidden rounded-2xl border border-emerald-200/90 bg-white shadow-md',

          'ring-1 ring-emerald-100/80'
        )}
        aria-labelledby="finiquito-acceso-titulo"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-200/80 bg-gradient-to-r from-emerald-800 to-emerald-600 px-4 py-3.5 text-white sm:px-5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 shadow-inner">
              <CheckCircle2 className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <h2
                id="finiquito-acceso-titulo"
                className="text-sm font-bold tracking-tight sm:text-base"
              >
                Acceso encargado Finiquito
              </h2>
              <p className="text-xs text-emerald-100">
                Portal colaboradores · cédula y código por correo
              </p>
            </div>
          </div>
        </div>
        <div className="space-y-4 bg-gradient-to-b from-emerald-50/50 to-white p-4 sm:p-6">
          <div className="space-y-2">
            <Label htmlFor="finiq-cedula">Cédula</Label>
            <Input
              id="finiq-cedula"
              value={cedula}
              onChange={e => setCedula(e.target.value)}
              placeholder="Ej: V12345678"
              autoComplete="username"
              className="border-slate-300"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="finiq-email">Correo personal</Label>
            <Input
              id="finiq-email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="correo@ejemplo.com"
              autoComplete="email"
              className="border-slate-300"
            />
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              type="button"
              variant="outline"
              className="flex-1 border-slate-300"
              disabled={loading !== null}
              onClick={onRegistro}
            >
              {loading === 'registro' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Registrarme (primera vez)'
              )}
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              disabled={loading !== null}
              onClick={onSolicitar}
            >
              {loading === 'solicitar' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Enviar código'
              )}
            </Button>
          </div>

          <div className="space-y-2 border-t border-emerald-200/60 pt-4">
            <Label htmlFor="finiq-codigo">Código del correo</Label>
            <Input
              id="finiq-codigo"
              value={codigo}
              onChange={e => setCodigo(e.target.value)}
              placeholder="6 dígitos"
              maxLength={10}
              autoComplete="one-time-code"
              className="border-slate-300 font-mono"
            />
            <Button
              type="button"
              className="w-full bg-[#1e3a5f] hover:bg-[#152a47]"
              disabled={loading !== null}
              onClick={onVerificar}
            >
              {loading === 'verificar' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Verificar e ingresar'
              )}
            </Button>
          </div>
        </div>
      </section>
    </FiniquitoWorkspaceShell>
  )
}
