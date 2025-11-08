/**
 * Hook personalizado para manejar funcionalidades de contraseñas
 * Centraliza la lógica de generación, copiado y visibilidad de contraseñas
 */
import { useState } from 'react'
import { toast } from 'sonner'

// Constantes de configuración
const PASSWORD_LENGTH = 12
const MIN_REQUIRED_CHARS = 4
const MIN_PASSWORD_LENGTH = 8

interface UsePasswordOptions {
  initialPassword?: string
  onPasswordChange?: (password: string) => void
}

export const usePassword = (options: UsePasswordOptions = {}) => {
  const [password, setPassword] = useState(options.initialPassword || '')
  const [showPassword, setShowPassword] = useState(false)

  // Generar contraseña automática segura
  const generatePassword = () => {
    const uppercaseChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    const lowercaseChars = 'abcdefghijklmnopqrstuvwxyz'
    const numberChars = '0123456789'
    const symbolChars = '!@#$%^&*'
    const allChars = uppercaseChars + lowercaseChars + numberChars + symbolChars
    
    let newPassword = ''
    
    // Asegurar al menos un carácter de cada tipo
    newPassword += uppercaseChars.charAt(Math.floor(Math.random() * uppercaseChars.length))
    newPassword += lowercaseChars.charAt(Math.floor(Math.random() * lowercaseChars.length))
    newPassword += numberChars.charAt(Math.floor(Math.random() * numberChars.length))
    newPassword += symbolChars.charAt(Math.floor(Math.random() * symbolChars.length))
    
    // Completar hasta longitud deseada
    for (let i = MIN_REQUIRED_CHARS; i < PASSWORD_LENGTH; i++) {
      newPassword += allChars.charAt(Math.floor(Math.random() * allChars.length))
    }
    
    // Mezclar los caracteres
    const shuffledPassword = newPassword.split('').sort(() => Math.random() - 0.5).join('')
    
    setPassword(shuffledPassword)
    options.onPasswordChange?.(shuffledPassword)
    toast.success('Contraseña generada automáticamente')
    
    return shuffledPassword
  }

  // Copiar contraseña al portapapeles
  const copyPassword = async () => {
    if (!password) {
      toast.error('No hay contraseña para copiar')
      return false
    }

    try {
      await navigator.clipboard.writeText(password)
      toast.success('Contraseña copiada al portapapeles')
      return true
    } catch (err) {
      // Fallback para navegadores que no soportan clipboard API
      try {
        const textArea = document.createElement('textarea')
        textArea.value = password
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        toast.success('Contraseña copiada al portapapeles')
        return true
      } catch (fallbackErr) {
        toast.error('No se pudo copiar la contraseña')
        return false
      }
    }
  }

  // Alternar visibilidad de contraseña
  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  // Actualizar contraseña
  const updatePassword = (newPassword: string) => {
    setPassword(newPassword)
    options.onPasswordChange?.(newPassword)
  }

  // Validar fortaleza de contraseña
  const validatePassword = (pwd: string = password) => {
    const hasUppercase = /[A-Z]/.test(pwd)
    const hasLowercase = /[a-z]/.test(pwd)
    const hasNumbers = /\d/.test(pwd)
    // Símbolos permitidos: debe coincidir con el backend [!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]
    const hasSymbols = /[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]/.test(pwd)
    const hasMinLength = pwd.length >= MIN_PASSWORD_LENGTH

    return {
      isValid: hasUppercase && hasLowercase && hasNumbers && hasSymbols && hasMinLength,
      hasUppercase,
      hasLowercase,
      hasNumbers,
      hasSymbols,
      hasMinLength,
      strength: [
        hasUppercase,
        hasLowercase,
        hasNumbers,
        hasSymbols,
        hasMinLength
      ].filter(Boolean).length
    }
  }

  return {
    password,
    showPassword,
    generatePassword,
    copyPassword,
    togglePasswordVisibility,
    updatePassword,
    validatePassword,
    setPassword: updatePassword
  }
}
