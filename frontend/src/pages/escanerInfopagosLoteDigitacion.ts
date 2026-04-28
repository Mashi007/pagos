/**
 * Digitalización secuencial fuera del ciclo de vida del componente: sigue si el usuario
 * cambia de ruta dentro de la SPA; cede el hilo principal entre pasos (setTimeout).
 */
import toast from 'react-hot-toast'

import type { EscanerInfopagosExtraerResponse } from '../services/cobrosService'
import { escanerInfopagosExtraerComprobante } from '../services/cobrosService'
import { collectTokensSufijoVistoArchivoDesdeFilas } from '../utils/documentoSufijoVisto'

import { filaTrasExtraccion, type FilaLote } from './escanerInfopagosLoteModel'

/** Opciones de `runDigitacionLoteEnSegundoPlano` (re-escaneo lote desde modal, etc.). */
export type DigitacionLoteOpciones = {
  /** Solo las primeras N filas en el orden actual de la lista (p. ej. 10 visibles). */
  maxFilas?: number
  /** Si true, vuelve a llamar Gemini aunque la fila ya esté en `listo`. */
  forzarRescan?: boolean
}

function institucionPlantillaParaFila(f: FilaLote): string {
  const inst = (f.institucion || '').trim()
  const otro = (f.otroInstitucion || '').trim()
  if (inst && inst !== 'Otros') return inst
  return otro || inst
}

export type DigitacionLoteUiSnapshot = {
  running: boolean
  progressIndex: number | null
  total: number
}

let uiSnapshot: DigitacionLoteUiSnapshot = {
  running: false,
  progressIndex: null,
  total: 0,
}
const uiListeners = new Set<() => void>()

function emitUi() {
  uiListeners.forEach(l => l())
}

export function subscribeDigitacionLoteUi(listener: () => void): () => void {
  uiListeners.add(listener)
  return () => {
    uiListeners.delete(listener)
  }
}

export function getDigitacionLoteUiSnapshot(): DigitacionLoteUiSnapshot {
  return uiSnapshot
}

/** Recibe cada avance de filas (montado o no el componente). */
let filasSink: null | ((rows: FilaLote[]) => void) = null

/** Si no hay pantalla escuchando, último estado + contexto para hidratar al volver a la ruta. */
export type PendingDigitacionSession = {
  filas: FilaLote[]
  cedulaRaw: string
  nombreCliente: string
}

let pendingWhenNoSink: PendingDigitacionSession | null = null

export function setDigitacionLoteFilasSink(
  fn: null | ((rows: FilaLote[]) => void)
) {
  filasSink = fn
}

export function takePendingDigitacionSession(): PendingDigitacionSession | null {
  const p = pendingWhenNoSink
  pendingWhenNoSink = null
  return p
}

let abortController: AbortController | null = null

export function cancelDigitacionLote() {
  abortController?.abort()
}

function yieldToMain(): Promise<void> {
  return new Promise(resolve => {
    setTimeout(resolve, 0)
  })
}

function pushFilas(
  rows: FilaLote[],
  contexto: { cedulaRaw: string; nombreCliente: string }
) {
  if (filasSink) {
    filasSink(rows)
  } else {
    pendingWhenNoSink = {
      filas: rows,
      cedulaRaw: contexto.cedulaRaw,
      nombreCliente: contexto.nombreCliente,
    }
  }
}

/**
 * Ejecuta la cola de extracciones. Por defecto omite filas ya en `listo` (idempotente).
 * Con `forzarRescan`, vuelve a llamar Gemini usando la plantilla de banco de cada fila si existe.
 */
export async function runDigitacionLoteEnSegundoPlano(
  filas: FilaLote[],
  tipo: string,
  numero: string,
  onTokens: (tokens: Iterable<string>) => void,
  contexto: { cedulaRaw: string; nombreCliente: string },
  fuenteTasaCambio: string = 'euro',
  opciones?: DigitacionLoteOpciones
): Promise<void> {
  if (uiSnapshot.running) {
    toast.error('Ya hay una digitalización en curso.')
    return
  }
  if (!filas.length) {
    toast.error('No hay comprobantes para digitalizar.')
    return
  }

  abortController = new AbortController()
  const signal = abortController.signal
  const forzarRescan = Boolean(opciones?.forzarRescan)
  const maxFilas = opciones?.maxFilas
  const idsFull = filas.map(f => f.clientId)
  const ids =
    typeof maxFilas === 'number' && maxFilas > 0
      ? idsFull.slice(0, Math.min(maxFilas, idsFull.length))
      : idsFull
  const total = ids.length

  uiSnapshot = { running: true, progressIndex: null, total }
  emitUi()

  let working = filas.map(f => ({ ...f }))
  const prevTitle = document.title
  const toastId = toast.loading(
    forzarRescan
      ? 'Re-escaneando comprobantes (Gemini)… Puede cambiar de pantalla; el proceso sigue en segundo plano.'
      : 'Digitalizando comprobantes… Puede cambiar de pantalla; el proceso sigue en segundo plano.',
    { duration: 600_000 }
  )

  let aborted = false
  try {
    for (let i = 0; i < ids.length; i++) {
      if (signal.aborted) {
        aborted = true
        break
      }
      const clientId = ids[i]
      const filaActual = working.find(f => f.clientId === clientId)
      if (!filaActual) continue
      if (!forzarRescan && filaActual.extract === 'listo') continue

      uiSnapshot = { running: true, progressIndex: i, total }
      emitUi()
      document.title = `(${String(i + 1)}/${String(ids.length)}) Digitalizando…`

      working = working.map(f =>
        f.clientId === clientId
          ? { ...f, extract: 'extrayendo', errorExtraccion: undefined }
          : f
      )
      pushFilas(working, contexto)
      await yieldToMain()

      const fd = new FormData()
      fd.append('tipo_cedula', tipo)
      fd.append('numero_cedula', numero)
      fd.append('fuente_tasa_cambio', fuenteTasaCambio)
      fd.append('comprobante', filaActual.archivo)
      const plantilla = institucionPlantillaParaFila(filaActual)
      if (plantilla) {
        fd.append('institucion_plantilla', plantilla)
      }

      try {
        const res: EscanerInfopagosExtraerResponse =
          await escanerInfopagosExtraerComprobante(fd)
        working = working.map(f => {
          if (f.clientId !== clientId) return f
          const nextF = filaTrasExtraccion(f, res)
          if (nextF.extract === 'listo' && res.sugerencia) {
            const toks = collectTokensSufijoVistoArchivoDesdeFilas([
              { numero_documento: res.sugerencia.numero_operacion || '' },
            ])
            onTokens(toks)
          }
          return nextF
        })
      } catch {
        working = working.map(f =>
          f.clientId === clientId
            ? {
                ...f,
                extract: 'error',
                errorExtraccion: 'Error de red o del servidor al digitalizar.',
              }
            : f
        )
      }
      pushFilas(working, contexto)
      await yieldToMain()
    }

    toast.dismiss(toastId)
    if (aborted) {
      toast('Digitalización cancelada.')
    } else {
      toast.success(
        forzarRescan
          ? 'Re-escaneo finalizado. Revise cada fila antes de guardar.'
          : 'Digitalización finalizada. Revise cada fila antes de guardar.'
      )
    }
  } catch (e: unknown) {
    toast.dismiss(toastId)
    toast.error(
      e instanceof Error ? e.message : 'Error inesperado en digitalización.'
    )
  } finally {
    document.title = prevTitle
    uiSnapshot = { running: false, progressIndex: null, total: 0 }
    emitUi()
    abortController = null
  }
}
