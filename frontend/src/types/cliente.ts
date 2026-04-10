/**
 * Tipos de cliente alineados con `Cliente` / `ClienteForm` en `./index`.
 * Importar desde `../types` en código nuevo; este archivo evita modelos duplicados (nombre/apellido legacy).
 */

import type { Cliente as ClienteCanonico } from './index'

export type Cliente = ClienteCanonico

export interface ClienteListItem extends ClienteCanonico {
  // Campos extra de listados (si en el futuro el API los agrega)
}
