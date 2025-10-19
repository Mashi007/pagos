/**
 * Componente reutilizable para campo de contraseña con funcionalidades avanzadas
 */
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Key, Copy, Eye, EyeOff } from 'lucide-react'
import { usePassword } from '@/hooks/usePassword'

interface PasswordFieldProps {
  value: string
  onChange: (password: string) => void
  placeholder?: string
  required?: boolean
  minLength?: number
  showGenerateButton?: boolean
  showCopyButton?: boolean
  showVisibilityToggle?: boolean
  className?: string
  disabled?: boolean
}

export const PasswordField = ({
  value,
  onChange,
  placeholder = 'Mínimo 8 caracteres',
  required = false,
  minLength = 8,
  showGenerateButton = true,
  showCopyButton = true,
  showVisibilityToggle = true,
  className = '',
  disabled = false
}: PasswordFieldProps) => {
  const {
    showPassword,
    generatePassword,
    copyPassword,
    togglePasswordVisibility,
    validatePassword
  } = usePassword({
    initialPassword: value,
    onPasswordChange: onChange
  })

  const validation = validatePassword(value)

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Input
            type={showPassword ? "text" : "password"}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            required={required}
            minLength={minLength}
            disabled={disabled}
            className="pr-10"
          />
          {showVisibilityToggle && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={togglePasswordVisibility}
              disabled={disabled}
              className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-gray-400" />
              ) : (
                <Eye className="h-4 w-4 text-gray-400" />
              )}
            </Button>
          )}
        </div>
        
        {showGenerateButton && (
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              const newPassword = generatePassword()
              onChange(newPassword)
            }}
            disabled={disabled}
            className="px-3"
            title="Generar contraseña automática"
          >
            <Key className="h-4 w-4" />
          </Button>
        )}
        
        {showCopyButton && value && (
          <Button
            type="button"
            variant="outline"
            onClick={copyPassword}
            disabled={disabled}
            className="px-3"
            title="Copiar contraseña"
          >
            <Copy className="h-4 w-4" />
          </Button>
        )}
      </div>
      
      {/* Indicador de fortaleza de contraseña */}
      {value && (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((level) => (
                <div
                  key={level}
                  className={`h-1 w-4 rounded ${
                    level <= validation.strength
                      ? validation.strength <= 2
                        ? 'bg-red-500'
                        : validation.strength <= 3
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                      : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
            <span className="text-xs text-gray-500">
              {validation.strength <= 2 ? 'Débil' : 
               validation.strength <= 3 ? 'Media' : 'Fuerte'}
            </span>
          </div>
          
          {/* Requisitos de contraseña */}
          <div className="text-xs text-gray-500 space-y-0.5">
            <div className={validation.hasMinLength ? 'text-green-600' : ''}>
              ✓ Mínimo 8 caracteres
            </div>
            <div className={validation.hasUppercase ? 'text-green-600' : ''}>
              ✓ Al menos una mayúscula
            </div>
            <div className={validation.hasLowercase ? 'text-green-600' : ''}>
              ✓ Al menos una minúscula
            </div>
            <div className={validation.hasNumbers ? 'text-green-600' : ''}>
              ✓ Al menos un número
            </div>
            <div className={validation.hasSymbols ? 'text-green-600' : ''}>
              ✓ Al menos un símbolo
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
