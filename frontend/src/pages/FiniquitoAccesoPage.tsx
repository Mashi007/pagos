import { useEffect, useState } from 'react'

import { Link, useNavigate } from 'react-router-dom'

import { Loader2, ChevronLeft } from 'lucide-react'

import { toast } from 'sonner'

import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Label } from '../components/ui/label'

import {
  finiquitoRegistro,
  finiquitoSolicitarCodigo,
  finiquitoVerificarCodigo,
  setFiniquitoAccessToken,
} from '../services/finiquitoService'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

export function FiniquitoAccesoPage() {
  const navigate = useNavigate()
  const [cedula, setCedula] = useState('')
  const [email, setEmail] = useState('')
  const [codigo, setCodigo] = useState('')
  const [loading, setLoading] = useState<string | null>(null)

  const LOGO_PUBLIC_SRC = `${(import.meta.env.BASE_URL || '/').replace(/\/?$/, '')}/logos/rapicredit-public.png`

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
      toast.success(r.message || 'Registro guardado.')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error al registrar'
      toast.error(msg)
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
      const msg = e instanceof Error ? e.message : 'Error al enviar código'
      toast.error(msg)
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
      navigate('/finiquitos/panel', { replace: true })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error al verificar'
      toast.error(msg)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-100 via-[#e0eaf2] to-[#c9d6e8] p-4 sm:p-6">
      <div className="mb-4 w-full max-w-md">
        <Button
          variant="ghost"
          size="sm"
          className="gap-2 text-slate-700"
          asChild
        >
          <Link to="/finiquitos">
            <ChevronLeft className="h-4 w-4" aria-hidden />
            Volver al inicio
          </Link>
        </Button>
      </div>

      <Card className="w-full max-w-lg overflow-hidden rounded-2xl border border-slate-200/90 shadow-2xl shadow-slate-300/40 ring-1 ring-slate-200/50">
        <div className="border-b border-slate-100 bg-gradient-to-b from-white to-slate-50/80 px-6 py-4 text-center">
          <img
            src={LOGO_PUBLIC_SRC}
            alt="RapiCredit"
            className="mx-auto h-14 object-contain drop-shadow-sm sm:h-16"
          />
          <p className="mt-2 text-xs font-semibold tracking-wide text-[#b8954a]">
            Finiquito - colaboradores
          </p>
        </div>
        <CardHeader>
          <CardTitle className="text-xl text-[#1e3a5f]">
            Acceso encargado Finiquito
          </CardTitle>
          <CardDescription>
            Regístrese la primera vez con su cédula y correo. Luego solicite el
            código y escríbalo para entrar.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="finiq-cedula">Cédula</Label>
            <Input
              id="finiq-cedula"
              value={cedula}
              onChange={e => setCedula(e.target.value)}
              placeholder="Ej: V12345678"
              autoComplete="username"
              className="rounded-xl"
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
              className="rounded-xl"
            />
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              type="button"
              variant="outline"
              className="flex-1"
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

          <div className="space-y-2 border-t border-slate-100 pt-4">
            <Label htmlFor="finiq-codigo">Código del correo</Label>
            <Input
              id="finiq-codigo"
              value={codigo}
              onChange={e => setCodigo(e.target.value)}
              placeholder="6 dígitos"
              maxLength={10}
              className="rounded-xl"
              autoComplete="one-time-code"
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
        </CardContent>
      </Card>
    </div>
  )
}
