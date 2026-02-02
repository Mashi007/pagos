// frontend/src/utils/storage.ts
/**
 * Funciones de almacenamiento seguro unificadas
 * Evita inconsistencias entre diferentes archivos
 */

// Constantes de almacenamiento
const INVALID_VALUES = ['', 'undefined', 'null']

// Detectar error de seguridad/almacenamiento no disponible ("The operation is insecure")
function isStorageError(e: unknown): boolean {
  if (e instanceof DOMException) return true
  if (e instanceof Error && (e.name === 'SecurityError' || e.name === 'QuotaExceededError')) return true
  return false
}

// Función helper para obtener item de storage
const getStorageItem = (storage: Storage, key: string, fallback: any = null) => {
  try {
    const item = storage.getItem(key)
    if (item === null || INVALID_VALUES.includes(item)) {
      return fallback
    }
    try {
      return JSON.parse(item)
    } catch {
      return item
    }
  } catch (e) {
    if (isStorageError(e)) return fallback
    throw e
  }
}

// Función helper para establecer item en storage
const setStorageItem = (storage: Storage, key: string, value: any) => {
  try {
    if (value === undefined) return false
    const stringValue = typeof value === 'string' ? value : JSON.stringify(value)
    if (stringValue === 'undefined') return false
    storage.setItem(key, stringValue)
    return true
  } catch (e) {
    if (isStorageError(e)) return false
    throw e
  }
}

// Función helper para remover item de storage
const removeStorageItem = (storage: Storage, key: string) => {
  try {
    storage.removeItem(key)
    return true
  } catch (e) {
    if (isStorageError(e)) return false
    throw e
  }
}

// Cache de disponibilidad para no llamar a setItem/removeItem en cada acceso
// (reduce "demasiadas llamadas" a la API de almacenamiento)
let _localStorageAvailable: boolean | null = null
let _sessionStorageAvailable: boolean | null = null

function checkLocalStorageOnce(): boolean {
  if (_localStorageAvailable !== null) return _localStorageAvailable
  try {
    const test = '__localStorage_test__'
    localStorage.setItem(test, test)
    localStorage.removeItem(test)
    _localStorageAvailable = true
  } catch (e) {
    if (isStorageError(e)) {
      _localStorageAvailable = false
    } else {
      throw e
    }
  }
  return _localStorageAvailable
}

function checkSessionStorageOnce(): boolean {
  if (_sessionStorageAvailable !== null) return _sessionStorageAvailable
  try {
    const test = '__sessionStorage_test__'
    sessionStorage.setItem(test, test)
    sessionStorage.removeItem(test)
    _sessionStorageAvailable = true
  } catch (e) {
    if (isStorageError(e)) {
      _sessionStorageAvailable = false
    } else {
      throw e
    }
  }
  return _sessionStorageAvailable
}

// Funciones de localStorage con verificación de disponibilidad (una sola prueba por tipo)
export const safeGetItem = (key: string, fallback: any = null) => {
  if (!checkLocalStorageOnce()) return fallback
  try {
    return getStorageItem(localStorage, key, fallback)
  } catch (e) {
    if (isStorageError(e)) return fallback
    throw e
  }
}

export const safeSetItem = (key: string, value: any) => {
  if (!checkLocalStorageOnce()) return false
  try {
    return setStorageItem(localStorage, key, value)
  } catch (e) {
    if (isStorageError(e)) return false
    throw e
  }
}

export const safeRemoveItem = (key: string) => {
  if (!checkLocalStorageOnce()) return false
  try {
    return removeStorageItem(localStorage, key)
  } catch (e) {
    if (isStorageError(e)) return false
    throw e
  }
}

// Funciones de sessionStorage con verificación de disponibilidad (una sola prueba por tipo)
export const safeGetSessionItem = (key: string, fallback: any = null) => {
  if (!checkSessionStorageOnce()) return fallback
  try {
    return getStorageItem(sessionStorage, key, fallback)
  } catch (e) {
    if (isStorageError(e)) return fallback
    throw e
  }
}

export const safeSetSessionItem = (key: string, value: any) => {
  if (!checkSessionStorageOnce()) return false
  try {
    return setStorageItem(sessionStorage, key, value)
  } catch (e) {
    if (isStorageError(e)) return false
    throw e
  }
}

export const safeRemoveSessionItem = (key: string) => {
  if (!checkSessionStorageOnce()) return false
  try {
    return removeStorageItem(sessionStorage, key)
  } catch (e) {
    if (isStorageError(e)) return false
    throw e
  }
}

// Función para limpiar todo el almacenamiento de autenticación
export const clearAuthStorage = () => {
  safeRemoveItem('access_token')
  safeRemoveItem('refresh_token')
  safeRemoveItem('user')
  safeRemoveItem('remember_me')
  safeRemoveSessionItem('access_token')
  safeRemoveSessionItem('refresh_token')
  safeRemoveSessionItem('user')
}
