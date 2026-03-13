/**
 * Diálogo unificado para elegir el modo de carga de pagos desde Excel:
 * - Revisar y editar: previsualizar tabla, editar celdas, guardar por fila o enviar a Revisar Pagos.
 * - Subir y procesar todo: enviar archivo al servidor y procesar en bloque.
 * Mantiene ambas funcionalidades sin duplicar entradas en el menú.
 */

import { FileSpreadsheet, Upload, Edit } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../ui/dialog'

export interface ExcelModoSelectorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Al elegir "Revisar y editar": cierra el selector y abre el flujo de previsualización. */
  onPrevisualizar: () => void
  /** Al elegir "Subir y procesar todo": cierra el selector y abre el flujo de upload directo. */
  onSubirTodo: () => void
}

export function ExcelModoSelectorDialog({
  open,
  onOpenChange,
  onPrevisualizar,
  onSubirTodo,
}: ExcelModoSelectorDialogProps) {
  const handlePrevisualizar = () => {
    onOpenChange(false)
    onPrevisualizar()
  }
  const handleSubirTodo = () => {
    onOpenChange(false)
    onSubirTodo()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg rounded-xl shadow-xl border-0 overflow-hidden p-0 bg-gray-50/95 backdrop-blur-sm">
        {/* Header con acento */}
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 px-6 pt-6 pb-5">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-white text-xl font-semibold">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/20">
                <FileSpreadsheet className="h-5 w-5" />
              </span>
              Pagos desde Excel
            </DialogTitle>
            <DialogDescription className="text-emerald-100 text-sm mt-2 leading-relaxed">
              Elija cómo desea cargar el archivo: puede revisar y editar filas antes de guardar, o procesar todo el archivo de una vez en el servidor.
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="px-6 pb-6 pt-4 grid gap-3">
          <button
            type="button"
            onClick={handlePrevisualizar}
            className="group flex items-start gap-4 rounded-xl border-2 border-gray-200 bg-white p-4 text-left transition-all hover:border-emerald-400 hover:bg-emerald-50/50 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-400"
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600 group-hover:bg-emerald-200 transition-colors">
              <Edit className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <span className="font-semibold text-gray-900 block">Revisar y editar antes de guardar</span>
              <span className="text-sm text-gray-600 mt-0.5 block">
                Sube el Excel, ve la tabla, corrige celdas y guarda por fila o envía a Revisar Pagos.
              </span>
            </div>
          </button>

          <button
            type="button"
            onClick={handleSubirTodo}
            className="group flex items-start gap-4 rounded-xl border-2 border-gray-200 bg-white p-4 text-left transition-all hover:border-blue-400 hover:bg-blue-50/50 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400"
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-600 group-hover:bg-blue-200 transition-colors">
              <Upload className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <span className="font-semibold text-gray-900 block">Subir y procesar todo</span>
              <span className="text-sm text-gray-600 mt-0.5 block">
                El servidor procesa todo el archivo; los rechazados quedan en Revisar Pagos.
              </span>
            </div>
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
