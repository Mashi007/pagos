import { CreditCard } from 'lucide-react'

import { Link } from 'react-router-dom'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { PagosList } from '../components/pagos/PagosList'

import {
  SEGMENTO_REPORTE_COBROS,
  SEGMENTO_INFOPAGOS,
  SEGMENTO_GESTION_PAGOS,
} from '../constants/rutasIngresoPago'

function PagosPage() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/25">
            <CreditCard className="h-6 w-6" />
          </span>

          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
              Pagos
            </h1>

            <p className="mt-0.5 text-sm text-gray-500">
              Gestión de cobros y conciliación
            </p>
          </div>
        </div>
      </header>

      <Card className="overflow-hidden rounded-xl border border-blue-100/80 bg-gradient-to-br from-blue-50/80 to-white shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base font-semibold text-gray-800">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <CreditCard className="h-4 w-4" />
            </span>
            Gestión de pagos
          </CardTitle>
        </CardHeader>

        <CardContent className="text-sm leading-relaxed text-gray-600">
          <p>
            Registre pagos, consulte por cédula, estado o fecha y descargue
            reportes.
          </p>
        </CardContent>
      </Card>

      <Card className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold text-slate-800">
            Fuentes de reporte y dos monedas (Bs. / USD)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-600">
          <p>
            El mismo formulario de reporte (moneda, montos permitidos, tasa del
            día de la fecha de pago y recibo PDF) está en:
          </p>
          <ul className="list-inside list-disc space-y-1">
            <li>
              <Link
                className="font-medium text-blue-700 underline"
                to={`/${SEGMENTO_REPORTE_COBROS}`}
              >
                {`/${SEGMENTO_REPORTE_COBROS}`}
              </Link>{' '}
              (público, deudor).
            </li>
            <li>
              <Link
                className="font-medium text-blue-700 underline"
                to={`/${SEGMENTO_INFOPAGOS}`}
              >
                {`/${SEGMENTO_INFOPAGOS}`}
              </Link>{' '}
              (colaborador; en Agregar pago se enlaza aquí).
            </li>
            <li>
              <span className="font-medium text-slate-800">
                {`/${SEGMENTO_GESTION_PAGOS}`}
              </span>{' '}
              (esta pantalla: Excel, Gmail y revisión). La importación aplica la
              misma lógica de moneda y tasa cuando corresponde.
            </li>
          </ul>
          <p className="text-xs text-slate-500">
            Tras validar, los pagos reportados se encaminan al flujo normal de
            cobranza (revisión, conciliación y aplicación a cuotas) junto con el
            resto de fuentes.
          </p>
        </CardContent>
      </Card>

      <PagosList />
    </div>
  )
}

export default PagosPage
