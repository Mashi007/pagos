/**
 * Estado de Cuenta PÚBLICO - Sin código ni verificación
 * 
 * Flujo: bienvenida → ingresar cédula → ver datos cliente → descargar PDF
 * 
 * SIN login. SIN código. Acceso directo.
 * Cualquier persona con una cédula puede ver el estado de cuenta.
 * 
 * Rate limit: igual que EstadoCuentaPublicoPage
 * Seguridad: validación de cédula, rate limiting por IP
 */

import React, { useState, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import {
  validarCedulaEstadoCuenta,
  solicitarEstadoCuenta,
  type ReciboCuotaItem,
} from '../services/estadoCuentaService'
import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Download, Loader2, ChevronLeft } from 'lucide-react'

const CEDULA_REGEX = /^[VEGJ]\d{6,11}$/i

function normalizarCedulaParaProcesar(val: string): {
  valido: boolean
  valorParaEnviar?: string
  error?: string
} {
  const s = val
    .trim()
    .toUpperCase()
    .replace(/[\s.\-]/g, '')

  if (!s) return { valido: false, error: 'Ingrese el número de cédula.' }

  if (!/^[VEGJ]?\d+$/.test(s)) {
    return {
      valido: false,
      error: 'No use puntos ni signos intermedios. Solo letra y dígitos.',
    }
  }

  if (/^\d{6,11}$/.test(s)) return { valido: true, valorParaEnviar: 'V' + s }

  if (CEDULA_REGEX.test(s)) return { valido: true, valorParaEnviar: s }

  return {
    valido: false,
    error: 'Cédula inválida. Use letra V, E, G o J seguida de 6 a 11 dígitos.',
  }
}

type NotificationState = { type: 'error' | 'success'; message: string } | null

function NotificationBanner({
  notification,
  onDismiss,
}: {
  notification: NotificationState
  onDismiss: () => void
}) {
  if (!notification) return null

  const isError = notification.type === 'error'
  return (
    <div
      className={`rounded-lg border px-4 py-3 text-sm ${
        isError
          ? 'border-red-300 bg-red-50 text-red-800'
          : 'border-green-300 bg-green-50 text-green-800'
      }`}
    >
      <div className="flex items-center justify-between">
        <span>{notification.message}</span>
        <button onClick={onDismiss} className="ml-4 font-bold">
          ✕
        </button>
      </div>
    </div>
  )
}

export function EstadoCuentaPublicoSinCodigoPage() {
  const location = useLocation()

  // Session marker para indicar que vino de flujo público
  React.useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY + '_path', 'rapicredit-estadocuenta-publico')
  }, [])

  const [paso, setPaso] = useState<'cedula' | 'cliente' | 'error'>('cedula')
  const [cedula, setCedula] = useState('')
  const [cedulaValidada, setCedulaValidada] = useState('')
  const [cliente, setCliente] = useState<{ nombres?: string; email?: string } | null>(null)
  const [recibos, setRecibos] = useState<ReciboCuotaItem[]>([])

  const [loading, setLoading] = useState(false)
  const [notification, setNotification] = useState<NotificationState>(null)
  const [descargando, setDescargando] = useState(false)

  const cedulaInputRef = useRef<HTMLInputElement>(null)

  const handleValidarCedula = async () => {
    setNotification(null)

    const norm = normalizarCedulaParaProcesar(cedula)
    if (!norm.valido) {
      setNotification({ type: 'error', message: norm.error || 'Cédula inválida' })
      return
    }

    setLoading(true)
    try {
      const resultado = await validarCedulaEstadoCuenta(norm.valorParaEnviar!)

      if (!resultado.ok) {
        setNotification({ type: 'error', message: resultado.error || 'Error al validar cédula' })
        setPaso('error')
        setLoading(false)
        return
      }

      setCedulaValidada(norm.valorParaEnviar!)
      setCliente({ nombres: resultado.nombre, email: resultado.email })
      setPaso('cliente')
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Error al validar'
      setNotification({ type: 'error', message: msg })
      setPaso('error')
    } finally {
      setLoading(false)
    }
  }

  const handleDescargarPDF = async () => {
    setDescargando(true)
    try {
      const res = await solicitarEstadoCuenta(cedulaValidada)

      if (!res.ok) {
        setNotification({
          type: 'error',
          message: res.error || 'Error al descargar estado de cuenta',
        })
        setDescargando(false)
        return
      }

      // Si tiene PDF en base64, descargar
      if (res.pdf_base64) {
        const bin = atob(res.pdf_base64)
        const bytes = new Uint8Array(bin.length)
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
        const blob = new Blob([bytes], { type: 'application/pdf' })
        const url = URL.createObjectURL(blob)

        const link = document.createElement('a')
        link.href = url
        link.download = `estado_cuenta_${cedulaValidada}.pdf`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)

        setNotification({
          type: 'success',
          message: 'Estado de cuenta descargado. También se envió a tu email.',
        })
      } else {
        setNotification({
          type: 'success',
          message: 'Estado de cuenta enviado a tu email.',
        })
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Error al descargar'
      setNotification({ type: 'error', message: msg })
    } finally {
      setDescargando(false)
    }
  }

  const handleVolver = () => {
    setPaso('cedula')
    setCedula('')
    setCedulaValidada('')
    setCliente(null)
    setRecibos([])
    setNotification(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-md">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-slate-900">Estado de Cuenta</h1>
          <p className="mt-2 text-sm text-slate-600">
            Acceso público - Sin clave requerida
          </p>
        </div>

        {/* Notification */}
        {notification && (
          <div className="mb-4">
            <NotificationBanner
              notification={notification}
              onDismiss={() => setNotification(null)}
            />
          </div>
        )}

        {/* Paso 1: Ingreso de cédula */}
        {paso === 'cedula' && (
          <Card>
            <CardHeader>
              <CardTitle>Consultar Estado de Cuenta</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700">
                  Número de Cédula
                </label>
                <Input
                  ref={cedulaInputRef}
                  type="text"
                  placeholder="V12345678 o solo 12345678"
                  value={cedula}
                  onChange={(e) => setCedula(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleValidarCedula()}
                  className="mt-1"
                  autoFocus
                />
                <p className="mt-1 text-xs text-slate-500">
                  Ingresa tu cédula: V, E, G o J seguido de números
                </p>
              </div>

              <Button
                onClick={handleValidarCedula}
                disabled={loading || !cedula.trim()}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Validando...
                  </>
                ) : (
                  'Consultar'
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Paso 2: Datos del cliente */}
        {paso === 'cliente' && cliente && (
          <Card>
            <CardHeader>
              <CardTitle>Datos Encontrados</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-slate-600">Cliente</p>
                <p className="text-lg font-semibold text-slate-900">
                  {cliente.nombres || 'No especificado'}
                </p>
              </div>

              <div>
                <p className="text-sm text-slate-600">Email</p>
                <p className="font-mono text-sm text-slate-900">
                  {cliente.email || 'No especificado'}
                </p>
              </div>

              <div className="space-y-2">
                <Button
                  onClick={handleDescargarPDF}
                  disabled={descargando}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {descargando ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Descargando...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Descargar Estado de Cuenta
                    </>
                  )}
                </Button>

                <Button
                  onClick={handleVolver}
                  variant="outline"
                  className="w-full"
                >
                  <ChevronLeft className="mr-2 h-4 w-4" />
                  Consultar otra cédula
                </Button>
              </div>

              <p className="text-xs text-slate-500">
                El estado de cuenta también será enviado a tu email registrado.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Paso 3: Error */}
        {paso === 'error' && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <p className="text-sm text-red-800">
                No se pudo validar la cédula. Verifica que esté correcta e intenta de nuevo.
              </p>
              <Button onClick={handleVolver} variant="outline" className="mt-4 w-full">
                <ChevronLeft className="mr-2 h-4 w-4" />
                Volver
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <div className="mt-8 text-center text-xs text-slate-600">
          <p>
            Este es un portal público. No requiere login ni código de verificación.
          </p>
        </div>
      </div>
    </div>
  )
}
