import { useState } from 'react'
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
import { useAuth } from '@/store/authStore'
import { LoginForm as LoginFormType } from '@/types'
import { ConnectionTest } from '@/components/debug/ConnectionTest'
import { BackendStatus } from '@/components/debug/BackendStatus'

// Schema de validación
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es requerido')
    .email('Formato de email inválido'),
  password: z
    .string()
    .min(1, 'La contraseña es requerida')
    .min(6, 'La contraseña debe tener al menos 6 caracteres'),
  remember: z.boolean().optional(),
})

type LoginFormData = z.infer<typeof loginSchema>

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false)
  const { login, isLoading, error, clearError } = useAuth()
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
      remember: false,
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      clearError()
      console.log('Intentando login con:', data)
      await login(data)
      navigate(from, { replace: true })
    } catch (error: any) {
      console.error('Error en login:', error)
      
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
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Card className="shadow-2xl border-0">
          <CardHeader className="space-y-4 text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          className="mx-auto"
        >
          {/* Logo de Rapicredit */}
          <div className="w-24 h-24 mx-auto mb-4 bg-gradient-to-br from-blue-600 to-purple-700 rounded-2xl flex items-center justify-center shadow-2xl">
            <img 
              src="/logo-compact.svg" 
              alt="RAPICREDIT Logo" 
              className="w-16 h-16"
            />
          </div>
        </motion.div>
            
            <div>
              <CardTitle className="text-3xl font-bold text-gradient text-center">
                RAPICREDIT
              </CardTitle>
              <CardDescription className="text-lg mt-2 text-center font-medium">
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
                className="w-full h-12 text-base font-semibold"
                loading={isLoading}
                disabled={isLoading}
              >
                {isLoading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
              </Button>
            </form>

        <div className="text-center text-sm text-muted-foreground">
          <p className="font-semibold text-blue-600">RAPICREDIT v1.0</p>
          <p className="mt-1">© 2024 - Todos los derechos reservados</p>
          <p className="text-xs mt-1 text-gray-400">Soluciones financieras rápidas y confiables</p>
        </div>
        
        {/* Componente de prueba de conexión */}
        <div className="mt-6">
          <ConnectionTest />
        </div>
        
        {/* Estado del backend */}
        <div className="mt-4">
          <BackendStatus />
        </div>
          </CardContent>
        </Card>

        {/* Información de usuarios demo */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          className="mt-6 p-4 bg-white/50 backdrop-blur-sm rounded-lg border border-white/20"
        >
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            Usuarios de demostración:
          </h3>
          <div className="text-xs text-gray-600 space-y-1">
            <p><strong>Admin:</strong> admin@sistema.com / admin123</p>
            <p><strong>Gerente:</strong> gerente@sistema.com / gerente123</p>
            <p><strong>Asesor:</strong> asesor@sistema.com / asesor123</p>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
