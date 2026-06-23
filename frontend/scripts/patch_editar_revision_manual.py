from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "pages"
MAIN = ROOT / "EditarRevisionManual.tsx"
OUT_DIR = ROOT / "revisionManual"

cliente_lines = (2549, 2994)
prestamo_lines = (2998, 3489)

main_text = MAIN.read_text(encoding="utf-8")
lines = main_text.splitlines(keepends=True)

cliente_body = "".join(lines[cliente_lines[0] - 1 : cliente_lines[1]])
prestamo_body = "".join(lines[prestamo_lines[0] - 1 : prestamo_lines[1]])

cliente_ts = '''import {
  Calendar,
  CreditCard,
  FileText,
  Mail,
  MapPin,
  Phone,
  User,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'
import type { ClienteData, EstadoValidadorCierreContacto } from './EditarRevisionManual.helpers'

export type ClienteRevisionCardProps = {
  clienteData: ClienteData
  setClienteData: React.Dispatch<React.SetStateAction<ClienteData>>
  cambios: { cliente: boolean; prestamo: boolean; cuotas: boolean }
  setCambios: React.Dispatch<
    React.SetStateAction<{ cliente: boolean; prestamo: boolean; cuotas: boolean }>
  >
  errores: Record<string, string>
  setErrores: React.Dispatch<React.SetStateAction<Record<string, string>>>
  opcionesEstado: { value: string; label: string }[]
  emailValidadorCierre: EstadoValidadorCierreContacto
}

export function ClienteRevisionCard({
  clienteData,
  setClienteData,
  cambios,
  setCambios,
  errores,
  setErrores,
  opcionesEstado,
  emailValidadorCierre,
}: ClienteRevisionCardProps) {
  return (
''' + cliente_body.rstrip() + "\n  )\n}\n"

prestamo_ts = '''import {
  Briefcase,
  Calendar,
  CreditCard,
  DollarSign,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'
import {
  opcionesSelectEstadoPrestamoRevision,
  type PrestamoData,
} from './EditarRevisionManual.helpers'

export type PrestamoRevisionCardProps = {
  prestamoData: PrestamoData
  setPrestamoData: React.Dispatch<React.SetStateAction<PrestamoData>>
  cambios: { cliente: boolean; prestamo: boolean; cuotas: boolean }
  setCambios: React.Dispatch<
    React.SetStateAction<{ cliente: boolean; prestamo: boolean; cuotas: boolean }>
  >
  errores: Record<string, string>
  setErrores: React.Dispatch<React.SetStateAction<Record<string, string>>>
  concesionarios: { id: number; nombre: string }[]
  analistas: { id: number; nombre: string }[]
  modelosVehiculos: { id: number; modelo: string }[]
  applyFechaAprobacionAlPayload: (payload: Record<string, unknown>) => void
  formatDateForInput: (value: unknown) => string
}

export function PrestamoRevisionCard({
  prestamoData,
  setPrestamoData,
  cambios,
  setCambios,
  errores,
  setErrores,
  concesionarios,
  analistas,
  modelosVehiculos,
  applyFechaAprobacionAlPayload,
  formatDateForInput,
}: PrestamoRevisionCardProps) {
  return (
''' + prestamo_body.rstrip() + "\n  )\n}\n"

(OUT_DIR / "ClienteRevisionCard.tsx").write_text(cliente_ts, encoding="utf-8")
(OUT_DIR / "PrestamoRevisionCard.tsx").write_text(prestamo_ts, encoding="utf-8")

replacement_cliente = """            <ClienteRevisionCard
              clienteData={clienteData}
              setClienteData={setClienteData}
              cambios={cambios}
              setCambios={setCambios}
              errores={errores}
              setErrores={setErrores}
              opcionesEstado={opcionesEstado}
              emailValidadorCierre={emailValidadorCierre}
            />
"""
replacement_prestamo = """            <PrestamoRevisionCard
              prestamoData={prestamoData}
              setPrestamoData={setPrestamoData}
              cambios={cambios}
              setCambios={setCambios}
              errores={errores}
              setErrores={setErrores}
              concesionarios={concesionarios}
              analistas={analistas}
              modelosVehiculos={modelosVehiculos}
              applyFechaAprobacionAlPayload={applyFechaAprobacionAlPayload}
              formatDateForInput={formatDateForInput}
            />
"""

new_main = (
    "".join(lines[: cliente_lines[0] - 1])
    + replacement_cliente
    + "".join(lines[cliente_lines[1] : prestamo_lines[0] - 1])
    + replacement_prestamo
    + "".join(lines[prestamo_lines[1] :])
)

import_line = "import { reescanearComprobantesCarteraPrestamo } from './revisionManual/reescanearComprobantesCarteraRevision'\n"
insert = (
    "import { ClienteRevisionCard } from './revisionManual/ClienteRevisionCard'\n"
    "import { PrestamoRevisionCard } from './revisionManual/PrestamoRevisionCard'\n"
)
if insert.strip() not in new_main:
    new_main = new_main.replace(import_line, import_line + insert)

MAIN.write_text(new_main, encoding="utf-8")
print(
    "EditarRevisionManual lines:",
    new_main.count("\n") + 1,
    "cliente card:",
    cliente_lines,
    "prestamo card:",
    prestamo_lines,
)
