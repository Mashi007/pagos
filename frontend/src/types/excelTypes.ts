/**
 * Excel Upload Types and Interfaces
 */

export interface ExcelData {
  cedula: string
  nombres: string
  telefono: string
  email: string
  direccion: string
  fecha_nacimiento: string
  ocupacion: string
  estado: string
  activo: string
  notas: string
}

export interface ValidationResult {
  isValid: boolean
  message?: string
  normalizedValue?: string
}

export interface ExcelRow extends ExcelData {
  _rowIndex: number
  _validation: { [key: string]: ValidationResult }
  _hasErrors: boolean
}

export interface Toast {
  id: string
  type: 'error' | 'warning' | 'success'
  message: string
  suggestion?: string
  field: string
  rowIndex: number
}

export interface ViolationTracker {
  [key: string]: {
    violationCount: number
    lastRowData: string
  }
}

export interface ExcelUploaderProps {
  onClose: () => void
  onDataProcessed?: (data: ExcelRow[]) => void
  onSuccess?: () => void
}

export interface ExcelUploaderHookProps {
  onClose: () => void
  onDataProcessed?: (data: ExcelRow[]) => void
  onSuccess?: () => void
}

export interface ExcelUploaderHookReturn {
  // UI State
  isDragging: boolean
  setIsDragging: (value: boolean) => void
  uploadedFile: File | null
  isProcessing: boolean
  showPreview: boolean
  setShowPreview: (value: boolean) => void
  fileInputRef: React.RefObject<HTMLInputElement>

  // Excel Data
  excelData: ExcelRow[]
  setExcelData: (data: ExcelRow[]) => void
  showOnlyPending: boolean
  setShowOnlyPending: (value: boolean) => void

  // Saving State
  isSavingIndividual: boolean
  savingProgress: { [key: number]: boolean }
  savedClients: Set<number>
  serviceStatus: 'unknown' | 'online' | 'offline'

  // Validation & Modals
  showValidationModal: boolean
  setShowValidationModal: (value: boolean) => void
  showModalCedulasExistentes: boolean
  setShowModalCedulasExistentes: (value: boolean) => void
  cedulasExistentesEnBD: string[]

  // Toasts
  toasts: Toast[]
  removeToast: (toastId: string) => void

  // Duplicates
  cedulasDuplicadasEnArchivo: Set<string>
  nombresDuplicadosEnArchivo: Set<string>
  emailDuplicadosEnArchivo: Set<string>
  telefonoDuplicadosEnArchivo: Set<string>

  // Handlers
  handleDragOver: (e: React.DragEvent) => void
  handleDragLeave: (e: React.DragEvent) => void
  handleDrop: (e: React.DragEvent) => void
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void

  // Utility Functions
  updateCellValue: (rowIndex: number, field: string, value: string | null) => Promise<void>
  isClientValid: (row: ExcelRow) => boolean
  getDuplicadoMotivo: (row: ExcelRow) => string[]
  getValidClients: () => ExcelRow[]
  getDisplayData: () => ExcelRow[]
  getSavedClientsCount: () => number

  // Saving Functions
  saveIndividualClient: (row: ExcelRow) => Promise<boolean>
  saveAllValidClients: () => Promise<void>
  confirmSaveOmittingExistingCedulas: () => Promise<void>

  // Other
  blankIfNN: (value: string | null | undefined) => string
  formatNombres: (nombres: string) => string
}
