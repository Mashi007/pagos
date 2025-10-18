// frontend/src/utils/storage.ts
/**
 * Funciones de almacenamiento seguro unificadas
 * Evita inconsistencias entre diferentes archivos
 */

// Funciones de localStorage
export const safeGetItem = (key: string, fallback: any = null) => {
  try {
    const item = localStorage.getItem(key)
    if (item === null || item === '' || item === 'undefined' || item === 'null') {
      return fallback
    }
    try {
      return JSON.parse(item)
    } catch {
      return item
    }
  } catch {
    return fallback
  }
}

export const safeSetItem = (key: string, value: any) => {
  try {
    if (value === undefined) return false
    const stringValue = typeof value === 'string' ? value : JSON.stringify(value)
    if (stringValue === 'undefined') return false
    localStorage.setItem(key, stringValue)
    return true
  } catch {
    return false
  }
}

export const safeRemoveItem = (key: string) => {
  try {
    localStorage.removeItem(key)
    return true
  } catch {
    return false
  }
}

// Funciones de sessionStorage
export const safeGetSessionItem = (key: string, fallback: any = null) => {
  try {
    const item = sessionStorage.getItem(key)
    if (item === null || item === '' || item === 'undefined' || item === 'null') {
      return fallback
    }
    try {
      return JSON.parse(item)
    } catch {
      return item
    }
  } catch {
    return fallback
  }
}

export const safeSetSessionItem = (key: string, value: any) => {
  try {
    if (value === undefined) return false
    const stringValue = typeof value === 'string' ? value : JSON.stringify(value)
    if (stringValue === 'undefined') return false
    sessionStorage.setItem(key, stringValue)
    return true
  } catch {
    return false
  }
}

export const safeRemoveSessionItem = (key: string) => {
  try {
    sessionStorage.removeItem(key)
    return true
  } catch {
    return false
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
