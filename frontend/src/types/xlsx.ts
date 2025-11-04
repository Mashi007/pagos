/**
 * Tipos para xlsx (CommonJS module)
 * Evita el uso de 'as any' cuando se importa xlsx
 */

// Tipo para el módulo xlsx completo
export interface XLSXModule {
  utils: {
    json_to_sheet: (data: unknown[]) => unknown
    sheet_to_json: <T = unknown>(sheet: unknown, options?: { header?: string[]; defval?: string }) => T[]
    book_new: () => unknown
    book_append_sheet: (wb: unknown, ws: unknown, name?: string) => void
  }
  writeFile: (wb: unknown, filename: string, options?: { bookType?: string }) => void
  read: (data: unknown, options?: { type?: string }) => unknown
}

// Helper para importar xlsx de forma type-safe
export async function importXLSX(): Promise<XLSXModule> {
  const module = await import('xlsx')
  return module as unknown as XLSXModule
}

