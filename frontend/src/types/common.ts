/**
 * Tipos comunes reutilizables
 * Evita el uso de 'any' en toda la aplicaciÃÂ³n
 */

/**
 * Tipo genÃÂ©rico para objetos con claves string
 */
export type RecordString<T = unknown> = Record<string, T>

/**
 * Tipo para valores de formularios
 */
export type FormValue = string | number | boolean | Date | null | undefined

/**
 * Tipo para objetos de configuraciÃÂ³n genÃÂ©ricos
 */
export type ConfigObject = RecordString<FormValue>

/**
 * Tipo para respuestas de API genÃÂ©ricas
 */
export interface ApiErrorResponse {
  detail?: string
  message?: string
  errors?: RecordString<string[]>
}

/**
 * Tipo para funciones de actualizaciÃÂ³n genÃÂ©ricas
 */
export type UpdateHandler<T = FormValue> = (field: string, value: T) => void

/**
 * Tipo para callbacks genÃÂ©ricos
 */
export type Callback<T = void> = (value: T) => void

/**
 * Tipo para funciones async genÃÂ©ricas
 */
export type AsyncFunction<T = unknown, R = unknown> = (args: T) => Promise<R>

