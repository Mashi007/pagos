// frontend/src/utils/safeStorage.ts
// Utilidades seguras para localStorage/sessionStorage

/**
 * Guarda datos de forma segura en localStorage
 */
export function safeSetItem(key: string, value: any): boolean {
  try {
    // Validar que el valor no sea undefined
    if (value === undefined) {
      console.warn(`safeSetItem: Intentando guardar undefined para clave '${key}'`)
      return false
    }

    // Convertir a string de forma segura
    const stringValue = typeof value === 'string' ? value : JSON.stringify(value)
    
    // Verificar que el string no sea "undefined"
    if (stringValue === 'undefined') {
      console.warn(`safeSetItem: Valor serializado es 'undefined' para clave '${key}'`)
      return false
    }

    localStorage.setItem(key, stringValue)
    return true
  } catch (error) {
    console.error(`safeSetItem: Error al guardar '${key}':`, error)
    return false
  }
}

/**
 * Obtiene datos de forma segura de localStorage
 */
export function safeGetItem<T = any>(key: string, fallback: T | null = null): T | null {
  try {
    const item = localStorage.getItem(key)
    
    // Si no existe, retornar fallback
    if (item === null) {
      return fallback
    }

    // Si es string vacío, retornar fallback
    if (item === '') {
      return fallback
    }

    // Si es literalmente "undefined", retornar fallback
    if (item === 'undefined') {
      console.warn(`safeGetItem: Valor 'undefined' encontrado para clave '${key}'`)
      return fallback
    }

    // Si es literalmente "null", retornar fallback
    if (item === 'null') {
      return fallback
    }

    // Intentar parsear JSON
    try {
      return JSON.parse(item)
    } catch (parseError) {
      // Si no es JSON válido, retornar como string
      return item as T
    }
  } catch (error) {
    console.error(`safeGetItem: Error al obtener '${key}':`, error)
    return fallback
  }
}

/**
 * Elimina un item de forma segura
 */
export function safeRemoveItem(key: string): boolean {
  try {
    localStorage.removeItem(key)
    return true
  } catch (error) {
    console.error(`safeRemoveItem: Error al eliminar '${key}':`, error)
    return false
  }
}

/**
 * Limpia localStorage de forma segura
 */
export function safeClear(): boolean {
  try {
    localStorage.clear()
    return true
  } catch (error) {
    console.error('safeClear: Error al limpiar localStorage:', error)
    return false
  }
}

// Funciones similares para sessionStorage
export function safeSetSessionItem(key: string, value: any): boolean {
  try {
    if (value === undefined) {
      console.warn(`safeSetSessionItem: Intentando guardar undefined para clave '${key}'`)
      return false
    }

    const stringValue = typeof value === 'string' ? value : JSON.stringify(value)
    
    if (stringValue === 'undefined') {
      console.warn(`safeSetSessionItem: Valor serializado es 'undefined' para clave '${key}'`)
      return false
    }

    sessionStorage.setItem(key, stringValue)
    return true
  } catch (error) {
    console.error(`safeSetSessionItem: Error al guardar '${key}':`, error)
    return false
  }
}

export function safeGetSessionItem<T = any>(key: string, fallback: T | null = null): T | null {
  try {
    const item = sessionStorage.getItem(key)
    
    if (item === null || item === '' || item === 'undefined' || item === 'null') {
      return fallback
    }

    try {
      return JSON.parse(item)
    } catch (parseError) {
      return item as T
    }
  } catch (error) {
    console.error(`safeGetSessionItem: Error al obtener '${key}':`, error)
    return fallback
  }
}

export function safeRemoveSessionItem(key: string): boolean {
  try {
    sessionStorage.removeItem(key)
    return true
  } catch (error) {
    console.error(`safeRemoveSessionItem: Error al eliminar '${key}':`, error)
    return false
  }
}

export function safeClearSession(): boolean {
  try {
    sessionStorage.clear()
    return true
  } catch (error) {
    console.error('safeClearSession: Error al limpiar sessionStorage:', error)
    return false
  }
}
