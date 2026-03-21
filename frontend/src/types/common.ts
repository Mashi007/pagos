/**
 * Tipos comunes reutilizables
 * Evita el uso de 'any' en toda la aplicaciÃ³n
 */

/**
 * Tipo genÃ©rico para objetos con claves string
 */
export type RecordString<T = unknown> = Record<string, T>

/**
 * Tipo para valores de formularios
 */
export type FormValue = string | number | boolean | Date | null | undefined

/**
 * Tipo para objetos de configuraciÃ³n genÃ©ricos
 */
export type ConfigObject = RecordString<FormValue>

/**
 * Tipo para respuestas de API genÃ©ricas
 */
export interface ApiErrorResponse {
  detail?: string
  message?: string
  errors?: RecordString<string[]>
}

/**
 * Tipo para funciones de actualizaciÃ³n genÃ©ricas
 */
export type UpdateHandler<T = FormValue> = (field: string, value: T) => void

/**
 * Tipo para callbacks genÃ©ricos
 */
export type Callback<T = void> = (value: T) => void

/**
 * Tipo para funciones async genÃ©ricas
 */
export type AsyncFunction<T = unknown, R = unknown> = (args: T) => Promise<R>

