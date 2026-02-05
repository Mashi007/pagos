import { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Mail, Lock, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'

import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { AlertWithIcon } from '../../components/ui/alert'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog'
import { Logo } from '../../components/ui/Logo'
import { useSimpleAuth } from '../../store/simpleAuthStore'
import { isAxiosError } from '../../types/errors'
import { authService } from '../../services/authService'

// Constantes de configuración
const MIN_PASSWORD_LENGTH = 6
const ANIMATION_DURATION = 0.5
const SPRING_DELAY = 0.2
const SPRING_STIFFNESS = 200

// Schema de validación
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es requerido')
    .email('Formato de email inválido'),
  password: z
    .string()
    .min(1, 'La contraseña es requerida')
    .min(MIN_PASSWORD_LENGTH, `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres`),
  remember: z.boolean().optional(),
})

type LoginFormData = z.infer<typeof loginSchema>

const FORGOT_EMAIL_DESTINO = 'itmaster@rapicreditca.com'

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false)
  const [forgotOpen, setForgotOpen] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotLoading, setForgotLoading] = useState(false)
  const [forgotSuccess, setForgotSuccess] = useState(false)
  const [forgotError, setForgotError] = useState<string | null>(null)
  const { login, isLoading, error, clearError } = useSimpleAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from = location.state?.from?.pathname || '/dashboard/menu'

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      remember: true, // Recordarme activo por defecto (localStorage)
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      clearError()

      // Asegurar que remember sea boolean y email en minúsculas
      const loginData = {
        ...data,
        email: data.email.toLowerCase().trim(), // Convertir a minúsculas
        remember: Boolean(data.remember)
      }

      await login(loginData)
      navigate(from, { replace: true })
    } catch (error: unknown) {
      // Manejar diferentes tipos de errores
      if (!isAxiosError(error) || !error.response) {
        setError('root', {
          message: 'Error de conexión. Verifica que el servidor esté funcionando.'
        })
        return
      }

      if (isAxiosError(error) && error.response?.status === 422) {
        // Errores de validación del servidor
        const responseData = error.response.data as { detail?: Array<{ loc?: string[]; msg?: string }> | string } | undefined
        const details = responseData?.detail
        if (Array.isArray(details)) {
          details.forEach((err: { loc?: string[]; msg?: string }) => {
            if (err.loc?.includes('email')) {
              setError('email', { message: err.msg })
            } else if (err.loc?.includes('password')) {
              setError('password', { message: err.msg })
            }
          })
        }
      } else if (error.response?.status === 401) {
        // Extraer mensaje del backend (puede estar en detail)
        const responseData = error.response?.data as { detail?: string; message?: string } | undefined
        const errorDetail = responseData?.detail || responseData?.message
        const errorMessage = errorDetail || 'Credenciales incorrectas. Verifica tu email y contraseña.'
        setError('root', {
          message: errorMessage
        })
      } else if (error.response?.status === 429) {
        setError('root', {
          message: 'Demasiados intentos de inicio de sesión. Espere un minuto e intente de nuevo.'
        })
      } else {
        // Extraer mensaje del backend para otros errores
        const responseData = error.response?.data as { detail?: string; message?: string } | undefined
        const errorDetail = responseData?.detail || responseData?.message
        const errorMessage = errorDetail || `Error del servidor: ${error.response?.status || 'Desconocido'}`
        setError('root', {
          message: errorMessage
        })
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4 overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: ANIMATION_DURATION }}
        className="w-full max-w-md my-4"
      >
        <Card className="shadow-2xl border-0 overflow-visible">
          <CardHeader className="space-y-4 text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: SPRING_DELAY, type: "spring", stiffness: SPRING_STIFFNESS }}
          className="mx-auto"
        >
          {/* Logo RapiCredit: forceDefault para no llamar a /api en login (público) y branding consistente */}
          <div className="w-24 h-24 mx-auto mb-4 bg-white rounded-2xl flex items-center justify-center shadow-2xl p-3 border-4 border-white/90 ring-4 ring-gray-100/60">
            <Logo size="lg" forceDefault className="drop-shadow-xl brightness-110 contrast-125" />
          </div>
        </motion.div>

            <div>
              <CardTitle className="text-3xl font-bold text-gradient text-center">
                RAPICREDIT
              </CardTitle>
              <CardDescription className="text-lg mt-4 text-center font-medium">
                Sistema de Préstamos y Cobranza
              </CardDescription>
              <CardDescription className="text-sm mt-1 text-center text-gray-500">
                Ingrese sus credenciales para acceder
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {error && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <AlertWithIcon
                  variant="destructive"
                  title="Error de autenticación"
                  description={error}
                />
              </motion.div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-4">
                <Input
                  {...register('email')}
                  type="email"
                  label="Correo electrónico"
                  placeholder="usuario@empresa.com"
                  leftIcon={<Mail className="w-4 h-4" />}
                  error={errors.email?.message}
                  autoComplete="email"
                  autoFocus
                />

                <Input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  label="Contraseña"
                  placeholder="••••••••"
                  leftIcon={<Lock className="w-4 h-4" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="hover:text-primary transition-colors"
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  }
                  error={errors.password?.message}
                  autoComplete="current-password"
                />
              </div>

              <div className="flex items-center justify-between">
                <Controller
                  name="remember"
                  control={control}
                  render={({ field }) => (
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={field.value === true}
                        onChange={(e) => field.onChange(e.target.checked)}
                        onBlur={field.onBlur}
                        ref={field.ref}
                        className="rounded border-gray-300 text-primary focus:ring-primary"
                        aria-checked={field.value === true}
                      />
                      <span className="text-sm text-muted-foreground">
                        Recordarme
                      </span>
                    </label>
                  )}
                />

                <button
                  type="button"
                  className="text-sm text-primary hover:underline"
                  onClick={() => {
                    setForgotOpen(true)
                    setForgotSuccess(false)
                    setForgotError(null)
                    setForgotEmail('')
                  }}
                >
                  ¿Olvidó su contraseña?
                </button>
              </div>

              <Button
                type="submit"
                className="w-full h-12 text-base font-semibold"
                loading={isLoading}
                disabled={isLoading}
              >
                {isLoading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
              </Button>
            </form>

            {/* Modal Olvidó su contraseña: envía notificación a itmaster@rapicreditca.com */}
            <Dialog open={forgotOpen} onOpenChange={setForgotOpen}>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Restablecer contraseña</DialogTitle>
                  <DialogDescription>
                    Indique su correo electrónico. Se enviará una notificación a {FORGOT_EMAIL_DESTINO} para el envío de una nueva contraseña.
                  </DialogDescription>
                </DialogHeader>
                {forgotSuccess ? (
                  <p className="text-sm text-green-700 py-2">
                    Solicitud enviada. Se ha notificado al administrador. Recibirá un correo en {FORGOT_EMAIL_DESTINO} para gestionar el restablecimiento de su contraseña.
                  </p>
                ) : (
                  <>
                    <div className="py-2">
                      <Input
                        type="email"
                        placeholder="su@correo.com"
                        value={forgotEmail}
                        onChange={(e) => setForgotEmail(e.target.value)}
                        label="Correo electrónico"
                        leftIcon={<Mail className="w-4 h-4" />}
                        disabled={forgotLoading}
                      />
                    </div>
                    {forgotError && (
                      <p className="text-sm text-red-600 mt-2">{forgotError}</p>
                    )}
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setForgotOpen(false)}
                        disabled={forgotLoading}
                      >
                        Cerrar
                      </Button>
                      <Button
                        onClick={async () => {
                          const email = forgotEmail.trim()
                          if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                            setForgotError('Indique un correo válido.')
                            return
                          }
                          setForgotError(null)
                          setForgotLoading(true)
                          try {
                            await authService.forgotPassword(email)
                            setForgotSuccess(true)
                          } catch (e: any) {
                            setForgotError(e?.response?.data?.detail || e?.message || 'Error al enviar la solicitud.')
                          } finally {
                            setForgotLoading(false)
                          }
                        }}
                        disabled={forgotLoading || !forgotEmail.trim()}
                      >
                        {forgotLoading ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Enviando...
                          </>
                        ) : (
                          'Enviar solicitud'
                        )}
                      </Button>
                    </DialogFooter>
                  </>
                )}
              </DialogContent>
            </Dialog>

        <div className="text-center text-sm text-muted-foreground">
          <p className="font-semibold text-blue-600">RAPICREDIT v1.0</p>
          <p className="mt-1">Â© 2024 - Todos los derechos reservados</p>
          <p className="text-xs mt-1 text-gray-400">Sistema de préstamos y cobranza</p>
        </div>
          </CardContent>
        </Card>

      </motion.div>
    </div>
  )
}
