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
import { Button } from '../ui/button'

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
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-green-600" />
            Pagos desde Excel
          </DialogTitle>
          <DialogDescription>
            Elija cómo desea cargar el archivo: puede revisar y editar filas antes de guardar, o procesar todo el archivo de una vez en el servidor.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 py-2">
          <Button
            type="button"
            variant="outline"
            className="h-auto flex items-start gap-3 px-4 py-3 text-left"
            onClick={handlePrevisualizar}
          >
            <Edit className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
            <div>
              <span className="font-medium block">Revisar y editar antes de guardar</span>
              <span className="text-sm text-muted-foreground">
                Sube el Excel, ve la tabla, corrige celdas y guarda por fila o envía a Revisar Pagos.
              </span>
            </div>
          </Button>
          <Button
            type="button"
            variant="outline"
            className="h-auto flex items-start gap-3 px-4 py-3 text-left"
            onClick={handleSubirTodo}
          >
            <Upload className="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
            <div>
              <span className="font-medium block">Subir y procesar todo</span>
              <span className="text-sm text-muted-foreground">
                El servidor procesa todo el archivo; los rechazados quedan en Revisar Pagos.
              </span>
            </div>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
