# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\components\pagos\PagosList.tsx")
t = p.read_text(encoding="utf-8")

if "CircleDollarSign" not in t:
    t = t.replace(
        "  Upload,\n} from 'lucide-react'",
        "  Upload,\n  CircleDollarSign,\n} from 'lucide-react'",
        1,
    )

if "getTasaHoy" not in t:
    t = t.replace(
        "import { useGmailPipeline } from '../../hooks/useGmailPipeline'\n\n",
        "import { useGmailPipeline } from '../../hooks/useGmailPipeline'\n"
        "import { getTasaHoy } from '../../services/tasaCambioService'\n\n",
        1,
    )

needle = "  const queryClient = useQueryClient()\n"
if "queryKey: ['tasa-hoy-banner-pagos']" not in t:
    if needle not in t:
        raise SystemExit("queryClient needle missing")
    t = t.replace(
        needle,
        needle
        + "\n  const { data: tasaHoyBanner, isLoading: tasaHoyBannerLoading } = useQuery({\n"
        "    queryKey: ['tasa-hoy-banner-pagos'],\n"
        "    queryFn: async () => {\n"
        "      try {\n"
        "        return await getTasaHoy()\n"
        "      } catch {\n"
        "        return null\n"
        "      }\n"
        "    },\n"
        "    staleTime: 60_000,\n"
        "    refetchOnWindowFocus: true,\n"
        "  })\n",
        1,
    )

marker = (
    "        </CardContent>\n"
    "      </Card>\n"
    '      <div className="flex flex-wrap items-center justify-end gap-3 rounded-xl border border-gray-200/80 bg-gray-50/50 px-4 py-3 sm:px-5 sm:py-4">'
)

banner = (
    "        </CardContent>\n"
    "      </Card>\n"
    '      <Card className="border-emerald-200 bg-emerald-50/90 shadow-sm">\n'
    '        <CardContent className="flex flex-wrap items-center gap-3 py-4">\n'
    "          {tasaHoyBannerLoading ? (\n"
    '            <div className="flex items-center gap-2 text-sm text-emerald-800">\n'
    '              <Loader2 className="h-5 w-5 animate-spin text-emerald-600" />\n'
    "              Consultando tasa del dia (Caracas)...\n"
    "            </div>\n"
    "          ) : tasaHoyBanner ? (\n"
    "            <>\n"
    '              <CircleDollarSign className="h-6 w-6 shrink-0 text-emerald-700" />\n'
    '              <div className="min-w-0">\n'
    '                <p className="text-sm font-semibold text-emerald-900">\n'
    "                  Tasa de cambio vigente del dia\n"
    "                </p>\n"
    '                <p className="mt-0.5 text-sm text-emerald-800">\n'
    "                  Fecha{' '}\n"
    "                  <strong>{(tasaHoyBanner.fecha || '').slice(0, 10)}</strong>\n"
    "                  :{' '}\n"
    "                  <strong>\n"
    "                    {new Intl.NumberFormat('es-VE', {\n"
    "                      minimumFractionDigits: 2,\n"
    "                      maximumFractionDigits: 2,\n"
    "                    }).format(tasaHoyBanner.tasa_oficial)}\n"
    "                  </strong>{' '}\n"
    "                  Bs. por 1 USD. Es la tasa oficial ingresada diariamente; se usa\n"
    "                  para reportes en bolivares segun la fecha de pago.\n"
    "                </p>\n"
    "              </div>\n"
    "            </>\n"
    "          ) : (\n"
    '            <div className="flex items-start gap-2 text-sm text-amber-900">\n'
    '              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />\n'
    "              <span>\n"
    "                No hay tasa cargada para hoy (Caracas) o no tiene permisos para\n"
    "                verla. Ingrese la tasa en Administracion (tasa de cambio) para\n"
    "                poder operar pagos en bolivares.\n"
    "              </span>\n"
    "            </div>\n"
    "          )}\n"
    "        </CardContent>\n"
    "      </Card>\n"
    '      <div className="flex flex-wrap items-center justify-end gap-3 rounded-xl border border-gray-200/80 bg-gray-50/50 px-4 py-3 sm:px-5 sm:py-4">'
)

if "border-emerald-200 bg-emerald-50/90" in t:
    print("banner already present")
else:
    if marker not in t:
        raise SystemExit("marker missing - check whitespace")
    t = t.replace(marker, banner, 1)

p.write_text(t, encoding="utf-8")
print("ok")
