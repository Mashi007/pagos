import { useState, useMemo, useCallback } from 'react'

export interface ChartWithDateRangeSliderProps<T extends Record<string, unknown>> {
  /** Datos completos del gráfico (cada item debe tener la clave dataKey para etiquetas) */
  data: T[]
  /** Clave del objeto que contiene la etiqueta de período (ej. "mes", "nombre_fecha") */
  dataKey: string
  /** Contenido del gráfico: recibe solo los datos filtrados por el rango */
  children: (filteredData: T[]) => React.ReactNode
  /** Altura del contenedor del gráfico (sin contar la regleta) */
  chartHeight?: number
  /** Clase adicional para el contenedor de la regleta */
  sliderClassName?: string
}

/**
 * Envuelve un gráfico y añade una regleta (slider de rango) al pie para filtrar
 * los datos entre dos extremos. Cada gráfico muestra solo el segmento seleccionado.
 */
export function ChartWithDateRangeSlider<T extends Record<string, unknown>>({
  data,
  dataKey,
  children,
  chartHeight = 320,
  sliderClassName = '',
}: ChartWithDateRangeSliderProps<T>) {
  const count = data.length
  const maxIndex = Math.max(0, count - 1)

  const [minIndex, setMinIndex] = useState(0)
  const [maxIndexState, setMaxIndexState] = useState(maxIndex)

  const fromIndex = Math.min(minIndex, maxIndexState)
  const toIndex = Math.max(minIndex, maxIndexState)

  const filteredData = useMemo(
    () => (count === 0 ? [] : data.slice(fromIndex, toIndex + 1)),
    [data, fromIndex, toIndex, count]
  )

  const handleMinChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = Number(e.target.value)
      setMinIndex(v)
      if (v > maxIndexState) setMaxIndexState(v)
    },
    [maxIndexState]
  )

  const handleMaxChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = Number(e.target.value)
      setMaxIndexState(v)
      if (v < minIndex) setMinIndex(v)
    },
    [minIndex]
  )

  const labelFrom = data[fromIndex]?.[dataKey] ?? ''
  const labelTo = data[toIndex]?.[dataKey] ?? ''

  if (count === 0) {
    return <>{children([])}</>
  }

  const showSlider = count > 1

  return (
    <div className="w-full">
      <div style={{ height: chartHeight }} className="w-full">
        {children(filteredData)}
      </div>
      {showSlider && (
        <div
          className={`mt-4 pt-4 border-t border-gray-200/80 ${sliderClassName}`}
          role="group"
          aria-label="Rango de fechas del gráfico"
        >
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Rango visible
            </span>
            <span className="text-xs font-semibold text-gray-700 tabular-nums">
              {String(labelFrom)} → {String(labelTo)}
            </span>
          </div>
          {/* Una sola regleta: pista única con dos thumbs que recorren los extremos */}
          <div className="relative h-8 flex items-center">
            <div className="absolute left-0 right-0 h-2 rounded-full bg-gradient-to-r from-gray-200 to-gray-300" aria-hidden />
            <input
              type="range"
              min={0}
              max={maxIndex}
              step={1}
              value={fromIndex}
              onChange={handleMinChange}
              className="chart-range-input absolute left-0 right-0 w-full h-8 cursor-pointer z-20"
              style={{ opacity: 0.01 }}
              aria-label="Inicio del rango"
            />
            <input
              type="range"
              min={0}
              max={maxIndex}
              step={1}
              value={toIndex}
              onChange={handleMaxChange}
              className="chart-range-input absolute left-0 right-0 w-full h-8 cursor-pointer z-30"
              style={{ opacity: 0.01 }}
              aria-label="Fin del rango"
            />
            {/* Thumbs visibles posicionados según valores (maxIndex puede ser 0, evitar /0) */}
            <div className="absolute inset-0 pointer-events-none flex items-center" aria-hidden>
              <div
                className="absolute w-4 h-4 rounded-full bg-cyan-500 border-2 border-white shadow-md -translate-x-1/2"
                style={{ left: maxIndex > 0 ? `${(fromIndex / maxIndex) * 100}%` : 0 }}
              />
              <div
                className="absolute w-4 h-4 rounded-full bg-cyan-500 border-2 border-white shadow-md -translate-x-1/2"
                style={{ left: maxIndex > 0 ? `${(toIndex / maxIndex) * 100}%` : 0 }}
              />
            </div>
          </div>
          <div className="flex justify-between mt-1 text-[10px] text-gray-400">
            <span>{String(data[0]?.[dataKey] ?? '')}</span>
            <span>{String(data[maxIndex]?.[dataKey] ?? '')}</span>
          </div>
        </div>
      )}
    </div>
  )
}
