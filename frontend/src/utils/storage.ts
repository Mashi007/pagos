// frontend/src/utils/storage.ts
/**
 * Funciones de almacenamiento seguro unificadas
 * Evita inconsistencias entre diferentes archivos
 */

// Constantes de almacenamiento
const INVALID_VALUES = ['', 'undefined', 'null']

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
  } catch {
    return fallback
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
  } catch {
    return false
  }
}

// Función helper para remover item de storage
const removeStorageItem = (storage: Storage, key: string) => {
  try {
    storage.removeItem(key)
    return true
  } catch {
    return false
  }
}

// Funciones de localStorage
export const safeGetItem = (key: string, fallback: any = null) => {
  return getStorageItem(localStorage, key, fallback)
}

export const safeSetItem = (key: string, value: any) => {
  return setStorageItem(localStorage, key, value)
}

export const safeRemoveItem = (key: string) => {
  return removeStorageItem(localStorage, key)
}

// Funciones de sessionStorage
export const safeGetSessionItem = (key: string, fallback: any = null) => {
  return getStorageItem(sessionStorage, key, fallback)
}

export const safeSetSessionItem = (key: string, value: any) => {
  return setStorageItem(sessionStorage, key, value)
}

export const safeRemoveSessionItem = (key: string) => {
  return removeStorageItem(sessionStorage, key)
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