import { useState, useEffect, useRef } from 'react'
import {
  FileSpreadsheet,
  Search,
  CheckCircle,
  XCircle,
  Plus,
  Trash2,
  Upload,
  Loader2,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import { pagoService } from '../../services/pagoService'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'

/**
 * Lista blanca de cédulas que pueden reportar en Bs (RapiCredit Cobros / Infopagos).
 * Antes vivía arriba de PagosList; también se usa en la página dedicada «Pago Bs.».
 */
export function CedulasReportarBsPanel() {
  const [cedulasReportarBsTotal, setCedulasReportarBsTotal] = useState<
    number | null
  >(null)
  const [isUploadingCedulasBs, setIsUploadingCedulasBs] = useState(false)
  const [isAgregandoCedulaBs, setIsAgregandoCedulaBs] = useState(false)
  const [isEliminandoCedulaBs, setIsEliminandoCedulaBs] = useState(false)
  const [nuevaCedulaBs, setNuevaCedulaBs] = useState('')
  const [consultaCedulaBs, setConsultaCedulaBs] = useState('')
  const [consultaCedulaBsResultado, setConsultaCedulaBsResultado] = useState<{
    en_lista: boolean
    cedula_normalizada: string | null
    total_en_lista: number
  } | null>(null)
  const [isConsultandoCedulaBs, setIsConsultandoCedulaBs] = useState(false)
  const fileInputCedulasBsRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    pagoService
      .getCedulasReportarBs()
      .then(r => setCedulasReportarBsTotal(r.total))
      .catch(() => setCedulasReportarBsTotal(0))
  }, [])

  return (
    <Card className="border-blue-200 bg-blue-50/80 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base font-semibold text-gray-800">
          <FileSpreadsheet className="h-5 w-5 text-blue-600" />
          Cédulas que pueden reportar en Bs (Bolívares)
        </CardTitle>
        <p className="mt-1 text-sm text-gray-600">
          Solo las cédulas de esta lista pueden elegir «Bs» en RapiCredit Cobros e
          Infopagos. Arriba puede consultar si una cédula está en la lista; abajo,
          cargue un Excel con columna <strong>cedula</strong> o agregue una cédula
          (ej. nuevo cliente que paga en bolívares).
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-slate-800">
            Consultar si la cédula está en la lista
          </p>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            <Input
              placeholder="Ej: V12345678"
              value={consultaCedulaBs}
              onChange={e => {
                setConsultaCedulaBs(e.target.value)
                setConsultaCedulaBsResultado(null)
              }}
              className="w-full min-w-0 border-blue-300 sm:min-w-[220px] sm:max-w-md sm:flex-1"
              maxLength={20}
              aria-label="Cédula a consultar"
              onKeyDown={e =>
                e.key === 'Enter' &&
                (e.preventDefault(),
                document.getElementById('btn-consultar-cedula-bs')?.click())
              }
            />
            <Button
              id="btn-consultar-cedula-bs"
              variant="outline"
              size="sm"
              className="border-blue-400 text-blue-800 hover:bg-blue-100 sm:shrink-0"
              disabled={isConsultandoCedulaBs || !consultaCedulaBs.trim()}
              onClick={async () => {
                const ced = consultaCedulaBs.trim()
                if (!ced) return
                setIsConsultandoCedulaBs(true)
                try {
                  const res = await pagoService.consultarCedulaReportarBs(ced)
                  setConsultaCedulaBsResultado(res)
                  setCedulasReportarBsTotal(res.total_en_lista)
                } catch (err) {
                  setConsultaCedulaBsResultado(null)
                  toast.error(getErrorMessage(err))
                } finally {
                  setIsConsultandoCedulaBs(false)
                }
              }}
            >
              {isConsultandoCedulaBs ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-1 h-4 w-4" />
              )}
              Consultar
            </Button>
            {consultaCedulaBsResultado && (
              <div className="flex w-full flex-col gap-1 sm:w-auto sm:min-w-[220px]">
                {consultaCedulaBsResultado.en_lista ? (
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-800">
                    <CheckCircle className="h-4 w-4 shrink-0" />
                    En lista: puede elegir Bs
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-800">
                    <XCircle className="h-4 w-4 shrink-0" />
                    No está en la lista
                  </span>
                )}
                {consultaCedulaBsResultado.cedula_normalizada && (
                  <span className="text-xs text-slate-600">
                    Normalizada:{' '}
                    <strong>
                      {consultaCedulaBsResultado.cedula_normalizada}
                    </strong>
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-blue-200/80 pt-4">
          <p className="mb-2 text-sm font-semibold text-slate-800">
            Agregar cédula o cargar Excel
          </p>
          <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center">
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center">
              <Input
                placeholder="Ej: V12345678"
                value={nuevaCedulaBs}
                onChange={e => setNuevaCedulaBs(e.target.value)}
                className="w-full min-w-0 border-blue-300 sm:w-44 sm:max-w-xs"
                maxLength={20}
                aria-label="Cédula a agregar a la lista"
                onKeyDown={e =>
                  e.key === 'Enter' &&
                  (e.preventDefault(),
                  document.getElementById('btn-agregar-cedula-bs')?.click())
                }
              />
              <Button
                id="btn-agregar-cedula-bs"
                variant="outline"
                size="sm"
                className="border-blue-400 text-blue-800 hover:bg-blue-100"
                disabled={isAgregandoCedulaBs || !nuevaCedulaBs.trim()}
                onClick={async () => {
                  const ced = nuevaCedulaBs.trim()
                  if (!ced) return
                  setIsAgregandoCedulaBs(true)
                  try {
                    const res = await pagoService.addCedulaReportarBs(ced)
                    setCedulasReportarBsTotal(res.total)
                    setNuevaCedulaBs('')
                    toast.success(res.mensaje)
                  } catch (err) {
                    toast.error(getErrorMessage(err))
                  } finally {
                    setIsAgregandoCedulaBs(false)
                  }
                }}
              >
                {isAgregandoCedulaBs ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-1 h-4 w-4" />
                )}
                Agregar cédula
              </Button>
            </div>
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center">
              <Input
                placeholder="Ej: V12345678 (eliminar)"
                value={consultaCedulaBs}
                onChange={e => setConsultaCedulaBs(e.target.value)}
                className="w-full min-w-0 border-red-300 sm:w-44 sm:max-w-xs"
                maxLength={20}
                aria-label="Cédula a eliminar de la lista"
                onKeyDown={e =>
                  e.key === 'Enter' &&
                  (e.preventDefault(),
                  document.getElementById('btn-eliminar-cedula-bs')?.click())
                }
              />
              <Button
                id="btn-eliminar-cedula-bs"
                variant="outline"
                size="sm"
                className="border-red-400 text-red-800 hover:bg-red-100"
                disabled={isEliminandoCedulaBs || !consultaCedulaBs.trim()}
                onClick={async () => {
                  const ced = consultaCedulaBs.trim()
                  if (!ced) return
                  setIsEliminandoCedulaBs(true)
                  try {
                    const res = await pagoService.removeCedulaReportarBs(ced)
                    setCedulasReportarBsTotal(res.total)
                    setConsultaCedulaBs('')
                    toast.success(res.mensaje)
                  } catch (err) {
                    toast.error(getErrorMessage(err))
                  } finally {
                    setIsEliminandoCedulaBs(false)
                  }
                }}
              >
                {isEliminandoCedulaBs ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="mr-1 h-4 w-4" />
                )}
                Eliminar cédula
              </Button>
            </div>
            <input
              ref={fileInputCedulasBsRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={async e => {
                const file = e.target.files?.[0]
                if (!file) return
                setIsUploadingCedulasBs(true)
                try {
                  const res = await pagoService.uploadCedulasReportarBs(file)
                  setCedulasReportarBsTotal(res.total)
                  toast.success(res.mensaje)
                  if (fileInputCedulasBsRef.current)
                    fileInputCedulasBsRef.current.value = ''
                } catch (err) {
                  toast.error(getErrorMessage(err))
                } finally {
                  setIsUploadingCedulasBs(false)
                }
              }}
            />
            <Button
              variant="outline"
              size="sm"
              className="border-blue-400 text-blue-800 hover:bg-blue-100"
              onClick={() => fileInputCedulasBsRef.current?.click()}
              disabled={isUploadingCedulasBs}
            >
              {isUploadingCedulasBs ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              Cargar Excel (columna cedula)
            </Button>
            {cedulasReportarBsTotal !== null && (
              <span className="text-sm text-gray-700">
                <strong>{cedulasReportarBsTotal}</strong> cédula(s) cargada(s)
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
