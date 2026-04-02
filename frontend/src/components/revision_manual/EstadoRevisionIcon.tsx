import {
  AlertTriangle,
  HelpCircle,
  X,
  CheckCircle,
  Loader2,
} from 'lucide-react'
import { Button } from '../ui/button'
import { toast } from 'sonner'
import { revisionManualService } from '../../services/revisionManualService'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

interface EstadoRevisionIconProps {
  prestamoId: number
  estadoActual: string
  nombreCliente: string
  onStateChange?: () => void
}

/**
 * Componente que muestra el estado visual de la revisión manual.
 * Estados: pendiente (⚠️), revisando (❓), en_espera (❌), revisado (✓)
 *
 * Comportamiento:
 * - ⚠️ Pendiente: Clickeable, inicia revisión → pasa a ❓
 * - ❓ Revisando: Clickeable, abre diálogo para cambiar a ❌ o ✓
 * - ❌ En espera: Clickeable, regresa a ❓ o marca ✓
 * - ✓ Revisado: No clickeable, finalizado (solo admin puede hacer esto)
 */
export function EstadoRevisionIcon({
  prestamoId,
  estadoActual,
  nombreCliente,
  onStateChange,
}: EstadoRevisionIconProps) {
  const queryClient = useQueryClient()
  const [isLoading, setIsLoading] = useState(false)

  const estadoNorm = (estadoActual || 'pendiente').toLowerCase().trim()

  const handleChangeState = async (nuevoEstado: string) => {
    const confirmMsgs: Record<string, string> = {
      revisando: `🔍 Iniciar revisión de ${nombreCliente}?`,
      en_espera: `⚠️ Marcar como EN ESPERA (requiere más revisión): ${nombreCliente}?\n\nNo se guardarán cambios, solo se marca para revisión posterior.`,
      revisado: `✅ FINALIZAR REVISIÓN de ${nombreCliente}?\n\n⚠️ Esta acción NO se puede deshacer. Solo admin.\n\nTodos los cambios se guardarán en las tablas originales.`,
    }

    const confirmar = window.confirm(
      confirmMsgs[nuevoEstado] || 'Confirmar cambio?'
    )
    if (!confirmar) return

    setIsLoading(true)
    try {
      await revisionManualService.cambiarEstadoRevision(prestamoId, {
        nuevo_estado: nuevoEstado,
        observaciones: undefined,
      })

      toast.success(`✅ Estado actualizado a: ${nuevoEstado}`)

      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      onStateChange?.()
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Error al cambiar estado'
      toast.error(`❌ ${errorMsg}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleShowDialog = () => {
    if (estadoNorm === 'pendiente') {
      handleChangeState('revisando')
    } else if (estadoNorm === 'revisando' || estadoNorm === 'en_espera') {
      const seleccion = window.prompt(
        `Selecciona la acción:\n\n1. ❓ REVISANDO - Continuar revisando\n2. ✅ REVISADO - Finalizar (solo admin)\n3. Cancelar`,
        ''
      )
      if (seleccion === '1') {
        handleChangeState('revisando')
      } else if (seleccion === '2') {
        handleChangeState('revisado')
      }
    } else if (estadoNorm === 'rechazado') {
      // Desde rechazado se puede reabrir para corrección
      const confirmar = window.confirm(
        `Este préstamo está RECHAZADO.\n\n¿Deseas reabrirlo para continuar la revisión?`
      )
      if (confirmar) {
        handleChangeState('revisando')
      }
    } else if (estadoNorm === 'revisado') {
      // Desde revisado (visto) se puede reabrir → vuelve a revisando (? es el nuevo inicio)
      const confirmar = window.confirm(
        `Este préstamo está REVISADO ✓.\n\n¿Deseas reabrirlo para continuar revisando?`
      )
      if (confirmar) {
        handleChangeState('revisando')
      }
    }
  }

  // Renderizar icono según estado
  const renderIcon = () => {
    switch (estadoNorm) {
      case 'pendiente':
        return (
          <div
            className="flex cursor-pointer items-center justify-center gap-1 rounded-lg bg-amber-100 px-2 py-1 transition-all hover:bg-amber-200"
            onClick={handleShowDialog}
            title="Click para iniciar revisión"
          >
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span className="text-xs font-semibold text-amber-700">
              Pendiente
            </span>
          </div>
        )

      case 'revisando':
        return (
          <div
            className="flex cursor-pointer items-center justify-center gap-1 rounded-lg bg-orange-100 px-2 py-1 transition-all hover:bg-orange-200"
            onClick={handleShowDialog}
            title="Click para cambiar estado"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-orange-600" />
            ) : (
              <HelpCircle className="h-4 w-4 text-orange-600" />
            )}
            <span className="text-xs font-semibold text-orange-700">
              Revisando
            </span>
          </div>
        )

      case 'en_espera':
        return (
          <div
            className="flex cursor-pointer items-center justify-center gap-1 rounded-lg bg-orange-100 px-2 py-1 transition-all hover:bg-orange-200"
            onClick={handleShowDialog}
            title="Click para cambiar estado"
          >
            <X className="h-4 w-4 text-orange-600" />
            <span className="text-xs font-semibold text-orange-700">
              En Espera
            </span>
          </div>
        )

      case 'rechazado':
        return (
          <div
            className="flex cursor-pointer items-center justify-center gap-1 rounded-lg bg-red-100 px-2 py-1 transition-all hover:bg-red-200"
            onClick={handleShowDialog}
            title="Rechazado - click para reabrir"
          >
            <X className="h-4 w-4 text-red-600" />
            <span className="text-xs font-semibold text-red-700">
              Rechazado
            </span>
          </div>
        )

      case 'revisado':
        return (
          <div className="flex items-center justify-center gap-1 rounded-lg bg-green-100 px-2 py-1">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span className="text-xs font-semibold text-green-700">
              Revisado
            </span>
          </div>
        )

      default:
        return <span className="text-xs text-gray-500">Estado desconocido</span>
    }
  }

  return <>{renderIcon()}</>
}
