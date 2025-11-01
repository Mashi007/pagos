import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Mail, Lock } from 'lucide-react'
import { motion } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertWithIcon } from '@/components/ui/alert'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { LoginForm as LoginFormType } from '@/types'

// Constantes de configuración
const MIN_PASSWORD_LENGTH = 6
const ANIMATION_DURATION = 0.5
const SPRING_DELAY = 0.2
const SPRING_STIFFNESS = 200
const LOGO_SIZE_LARGE = 24
const LOGO_SIZE_SMALL = 16
const TEXT_SIZE_LARGE = 3
const TEXT_SIZE_MEDIUM = 1
const SPACING_SMALL = 4
const SPACING_MEDIUM = 6
const BUTTON_HEIGHT = 12
const ICON_SIZE = 4

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

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false)
  const { login, isLoading, error, clearError } = useSimpleAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from = location.state?.from?.pathname || '/dashboard'

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      remember: true, // Por defecto activado para persistencia
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
    } catch (error: any) {
      // Manejar diferentes tipos de errores
      if (error.code === 'NETWORK_ERROR' || !error.response) {
        setError('root', { 
          message: 'Error de conexión. Verifica que el servidor esté funcionando.' 
        })
        return
      }
      
      if (error.response?.status === 422) {
        // Errores de validación del servidor
        const details = error.response.data.detail
        if (Array.isArray(details)) {
          details.forEach((err: any) => {
            if (err.loc?.includes('email')) {
              setError('email', { message: err.msg })
            } else if (err.loc?.includes('password')) {
              setError('password', { message: err.msg })
            }
          })
        }
      } else if (error.response?.status === 401) {
        setError('root', { 
          message: 'Credenciales incorrectas. Verifica tu email y contraseña.' 
        })
      } else {
        setError('root', { 
          message: `Error del servidor: ${error.response?.status || 'Desconocido'}` 
        })
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: ANIMATION_DURATION }}
        className="w-full max-w-md"
      >
        <Card className="shadow-2xl border-0">
          <CardHeader className="space-y-4 text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: SPRING_DELAY, type: "spring", stiffness: SPRING_STIFFNESS }}
          className="mx-auto"
        >
          {/* Logo de Rapicredit */}
          <div className={`w-${LOGO_SIZE_LARGE} h-${LOGO_SIZE_LARGE} mx-auto mb-${SPACING_SMALL} bg-white rounded-2xl flex items-center justify-center shadow-2xl p-4 border-4 border-white/80 ring-4 ring-gray-100/50`}>
            <img 
              src="/logo-compact.svg" 
              alt="RAPICREDIT Logo" 
              className={`w-${LOGO_SIZE_SMALL} h-${LOGO_SIZE_SMALL} drop-shadow-lg`}
            />
          </div>
        </motion.div>
            
            <div>
              <CardTitle className={`text-${TEXT_SIZE_LARGE}xl font-bold text-gradient text-center`}>
                RAPICREDIT
              </CardTitle>
              <CardDescription className={`text-lg mt-${SPACING_SMALL} text-center font-medium`}>
                Sistema de Préstamos y Cobranza
              </CardDescription>
              <CardDescription className={`text-sm mt-${TEXT_SIZE_MEDIUM} text-center text-gray-500`}>
                Ingrese sus credenciales para acceder
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className={`space-y-${SPACING_MEDIUM}`}>
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

            <form onSubmit={handleSubmit(onSubmit)} className={`space-y-${SPACING_SMALL}`}>
              <div className={`space-y-${SPACING_SMALL}`}>
                <Input
                  {...register('email')}
                  type="email"
                  label="Correo electrónico"
                  placeholder="usuario@empresa.com"
                  leftIcon={<Mail className={`w-${ICON_SIZE} h-${ICON_SIZE}`} />}
                  error={errors.email?.message}
                  autoComplete="email"
                  autoFocus
                />

                <Input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  label="Contraseña"
                  placeholder="••••••••"
                  leftIcon={<Lock className={`w-${ICON_SIZE} h-${ICON_SIZE}`} />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="hover:text-primary transition-colors"
                    >
                      {showPassword ? (
                        <EyeOff className={`w-${ICON_SIZE} h-${ICON_SIZE}`} />
                      ) : (
                        <Eye className={`w-${ICON_SIZE} h-${ICON_SIZE}`} />
                      )}
                    </button>
                  }
                  error={errors.password?.message}
                  autoComplete="current-password"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    {...register('remember')}
                    type="checkbox"
                    className="rounded border-gray-300 text-primary focus:ring-primary"
                  />
                  <span className="text-sm text-muted-foreground">
                    Recordarme
                  </span>
                </label>

                <button
                  type="button"
                  className="text-sm text-primary hover:underline"
                  onClick={() => {
                    // TODO: Implementar recuperación de contraseña
                    alert('Funcionalidad próximamente disponible')
                  }}
                >
                  ¿Olvidó su contraseña?
                </button>
              </div>

              <Button
                type="submit"
                className={`w-full h-${BUTTON_HEIGHT} text-base font-semibold`}
                loading={isLoading}
                disabled={isLoading}
              >
                {isLoading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
              </Button>
            </form>

        <div className="text-center text-sm text-muted-foreground">
          <p className="font-semibold text-blue-600">RAPICREDIT v1.0</p>
          <p className="mt-1">© 2024 - Todos los derechos reservados</p>
          <p className="text-xs mt-1 text-gray-400">Sistema de préstamos y cobranza</p>
        </div>
          </CardContent>
        </Card>

      </motion.div>
    </div>
  )
}
