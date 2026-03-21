/**
 * Hook personalizado para manejar funcionalidades de contraseÃÂ±as
 * Centraliza la lÃÂ³gica de generaciÃÂ³n, copiado y visibilidad de contraseÃÂ±as
 */
import { useState } from 'react'
import { toast } from 'sonner'

// Constantes de configuraciÃÂ³n
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

  // Generar contraseÃÂ±a automÃÂ¡tica segura
  const generatePassword = () => {
    const uppercaseChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    const lowercaseChars = 'abcdefghijklmnopqrstuvwxyz'
    const numberChars = '0123456789'
    const symbolChars = '!@#$%^&*'
    const allChars = uppercaseChars + lowercaseChars + numberChars + symbolChars

    let newPassword = ''

    // Asegurar al menos un carÃÂ¡cter de cada tipo
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
    toast.success('ContraseÃÂ±a generada automÃÂ¡ticamente')

    return shuffledPassword
  }

  // Copiar contraseÃÂ±a al portapapeles
  const copyPassword = async () => {
    if (!password) {
      toast.error('No hay contraseÃÂ±a para copiar')
      return false
    }

    try {
      await navigator.clipboard.writeText(password)
      toast.success('ContraseÃÂ±a copiada al portapapeles')
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
        toast.success('ContraseÃÂ±a copiada al portapapeles')
        return true
      } catch (fallbackErr) {
        toast.error('No se pudo copiar la contraseÃÂ±a')
        return false
      }
    }
  }

  // Alternar visibilidad de contraseÃÂ±a
  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  // Actualizar contraseÃÂ±a
  const updatePassword = (newPassword: string) => {
    setPassword(newPassword)
    options.onPasswordChange?.(newPassword)
  }

  // Validar fortaleza de contraseÃÂ±a
  const validatePassword = (pwd: string = password) => {
    const hasUppercase = /[A-Z]/.test(pwd)
    const hasLowercase = /[a-z]/.test(pwd)
    const hasNumbers = /\d/.test(pwd)
    // SÃÂ­mbolos permitidos: debe coincidir con el backend [!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]
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
