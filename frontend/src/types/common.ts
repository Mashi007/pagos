/**
 * Tipos comunes reutilizables
 * Evita el uso de 'any' en toda la aplicación
 */

/**
 * Tipo genérico para objetos con claves string
 */
export type RecordString<T = unknown> = Record<string, T>

/**
 * Tipo para valores de formularios
 */
export type FormValue = string | number | boolean | Date | null | undefined

/**
 * Tipo para objetos de configuración genéricos
 */
export type ConfigObject = RecordString<FormValue>

/**
 * Tipo para respuestas de API genéricas
 */
export interface ApiErrorResponse {
  detail?: string
  message?: string
  errors?: RecordString<string[]>
}

/**
 * Tipo para funciones de actualización genéricas
 */
export type UpdateHandler<T = FormValue> = (field: string, value: T) => void

/**
 * Tipo para callbacks genéricos
 */
export type Callback<T = void> = (value: T) => void

/**
 * Tipo para funciones async genéricas
 */
export type AsyncFunction<T = unknown, R = unknown> = (args: T) => Promise<R>

