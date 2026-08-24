import React, { useEffect, useRef, useState } from 'react'

import { useLocation } from 'react-router-dom'

import { AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'

import { TasaCambioModal } from './TasaCambioModal'
import {
  getEstadoTasa,
  getTasaHoy,
  getTasaPorFecha,
  guardarTasaPorFecha,
  invalidateTasaLecturaClientCache,
  type TasaCambioResponse,
} from '../services/tasaCambioService'

const STORAGE_PREFIX = 'rapicredit_tasa_vigente_toast_'
const TASA_CHECK_SESSION_KEY = 'rapicredit_tasa_estado_checked_at'
const TASA_DEFER_MS_COBROS = 12_000
const TASA_DEFER_MS_DEFAULT = 4_000

function tasaDeferMsForPath(pathname: string): number {
  if (
    pathname.includes('/cobros/') ||
    pathname.includes('/pagos/pagos') ||
    pathname.endsWith('/pagos')
  ) {
    return TASA_DEFER_MS_COBROS
  }
  return TASA_DEFER_MS_DEFAULT
}

function formatTasaBsUsd(val: number): string {
  if (!Number.isFinite(val)) return String(val)
  return new Intl.NumberFormat('es-VE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(val)
}

/**
 * Toast informativo para todos. Bloqueo de pantalla SOLO si el backend marca
 * debe_ingresar (itmaster@rapicreditca.com, tarde hábil, BCV automático falló).
 */
export const TasaCambioNotificacion: React.FC = () => {
  const location = useLocation()
  const ultimaFechaToastRef = useRef<string | null>(null)
  const verificarEnCursoRef = useRef(false)
  const [debeIngresar, setDebeIngresar] = useState(false)
  const [mostrarModal, setMostrarModal] = useState(false)
  const [tasaFila, setTasaFila] = useState<TasaCambioResponse | null>(null)
  const [fechaBcvEsperada, setFechaBcvEsperada] = useState<string | null>(null)

  useEffect(() => {
    const verificarTasa = async () => {
      if (typeof document !== 'undefined' && document.hidden) return
      if (verificarEnCursoRef.current) return
      verificarEnCursoRef.current = true
      try {
        const estado = await getEstadoTasa()
        const bloquear = Boolean(estado.debe_ingresar)
        setDebeIngresar(bloquear)
        setFechaBcvEsperada(estado.fecha_bcv_esperada || null)

        if (bloquear) {
          const fecha = (estado.fecha_bcv_esperada || '').slice(0, 10)
          let fila: TasaCambioResponse | null = null
          if (fecha) {
            try {
              fila = await getTasaPorFecha(fecha)
            } catch {
              fila = null
            }
          }
          if (!fila) {
            try {
              fila = await getTasaHoy()
            } catch {
              fila = null
            }
          }
          setTasaFila(fila)
          setMostrarModal(true)
          return
        }

        try {
          const checkedAt = Number(
            sessionStorage.getItem(TASA_CHECK_SESSION_KEY) || '0'
          )
          if (checkedAt > 0 && Date.now() - checkedAt < 5 * 60 * 1000) {
            return
          }
        } catch {
          /* ignore */
        }

        if (!estado.tasa_ya_ingresada && !estado.bcv_ok && !estado.euro_ok) {
          return
        }
        const tasa = await getTasaHoy()
        if (!tasa) return
        const fechaKey = (tasa.fecha || '').slice(0, 10)
        const storageKey = STORAGE_PREFIX + fechaKey
        const yaMostrada =
          typeof sessionStorage !== 'undefined' &&
          sessionStorage.getItem(storageKey) === '1'
        if (!fechaKey || yaMostrada || ultimaFechaToastRef.current === fechaKey) {
          return
        }
        ultimaFechaToastRef.current = fechaKey
        try {
          sessionStorage.setItem(storageKey, '1')
          sessionStorage.setItem(TASA_CHECK_SESSION_KEY, String(Date.now()))
        } catch {
          /* ignore */
        }
        const b =
          tasa.tasa_bcv != null ? formatTasaBsUsd(tasa.tasa_bcv) : '-'
        toast.info(
          `Tasas del día (${fechaKey}): Euro ${formatTasaBsUsd(tasa.tasa_oficial)} · BCV ${b} Bs./USD.`,
          { duration: 8000 }
        )
      } catch (err: unknown) {
        if (import.meta.env.DEV) {
          console.error('Error verificando tasa:', err)
        }
      } finally {
        verificarEnCursoRef.current = false
      }
    }

    const deferMs = tasaDeferMsForPath(location.pathname)
    const startTimer = window.setTimeout(() => {
      void verificarTasa()
    }, deferMs)

    const interval = setInterval(() => {
      void verificarTasa()
    }, 5 * 60 * 1000)

    return () => {
      window.clearTimeout(startTimer)
      clearInterval(interval)
    }
  }, [location.pathname])

  const handleGuardarTasa = async (p: {
    tasa_oficial: number
    tasa_bcv?: number
  }) => {
    const fecha = (fechaBcvEsperada || '').slice(0, 10)
    if (!fecha) {
      throw new Error('No hay fecha valor BCV para guardar')
    }
    const resultado = await guardarTasaPorFecha(fecha, p.tasa_oficial, {
      tasa_bcv: p.tasa_bcv,
    })
    invalidateTasaLecturaClientCache()
    setTasaFila(resultado)
    setDebeIngresar(false)
    setMostrarModal(false)
    toast.success(
      `BCV cargado a mano para ${fecha}: ${formatTasaBsUsd(p.tasa_bcv ?? 0)} Bs./USD.`,
      { duration: 8000 }
    )
  }

  if (!debeIngresar) {
    return null
  }

  return (
    <>
      <div className="sticky top-0 z-40 border-b-2 border-amber-300 bg-amber-50 p-4 shadow-md">
        <div className="mx-auto flex max-w-7xl items-center gap-3">
          <AlertTriangle className="h-6 w-6 flex-shrink-0 text-amber-600" />
          <div className="flex-1">
            <p className="font-bold text-amber-900">
              Carga manual de BCV (solo su usuario)
            </p>
            <p className="mt-1 text-sm text-amber-800">
              El bot no pudo leer el recuadro BCV esta tarde. Registre Euro y BCV
              para la fecha valor
              {fechaBcvEsperada ? ` ${fechaBcvEsperada.slice(0, 10)}` : ''}. El
              resto del equipo no está bloqueado.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setMostrarModal(true)}
            className="whitespace-nowrap rounded-lg bg-amber-600 px-4 py-2 font-semibold text-white transition hover:bg-amber-700"
          >
            Cargar tasas
          </button>
        </div>
      </div>

      <TasaCambioModal
        isOpen={mostrarModal}
        cannotClose
        requireBcv
        fechaValorLabel={fechaBcvEsperada}
        tasaHoyRow={tasaFila}
        onSave={handleGuardarTasa}
      />
    </>
  )
}
