"""Extract revision tab JSX from PagosList into PagosRevisionTab.tsx."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "components" / "pagos"
MAIN = ROOT / "PagosList.tsx"
OUT = ROOT / "pagosList" / "PagosRevisionTab.tsx"

lines = MAIN.read_text(encoding="utf-8").splitlines(keepends=True)
start = next(i for i, l in enumerate(lines) if 'TabsContent value="revision"' in l)
end = next(
    i
    for i, l in enumerate(lines)
    if i > start and l.strip() == "</TabsContent>"
)
inner = "".join(lines[start + 1 : end])

# variables referenced in inner (heuristic)
used = set(re.findall(r"\b([a-z][a-zA-Z0-9]*)\b", inner))
defined = set(re.findall(r"^  const (\w+)", "".join(lines), re.M))
defined |= {x.split(":")[0].strip() for x in re.findall(r"^  const \{([^}]+)\}", "".join(lines), re.M) for x in re.findall(r"\w+", x)}
props = sorted(used & defined)

component = f'''import {{
  AlertCircle,
  Check,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Download,
  Edit,
  Eye,
  FileSpreadsheet,
  Filter,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  X,
  XCircle,
}} from 'lucide-react'
import {{ Button }} from '../../ui/button'
import {{ Input }} from '../../ui/input'
import {{
  Card,
  CardContent,
  CardHeader,
  CardTitle,
}} from '../../ui/card'
import {{ Badge }} from '../../ui/badge'
import {{
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
}} from '../../ui/select'
import {{
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
}} from '../../ui/table'
import {{ ListPaginationBar }} from '../../ui/ListPaginationBar'
import {{ cn, formatDate }} from '../../../utils'
import {{ textoDocumentoPagoParaListado }} from '../../../utils/pagoExcelValidation'
import {{ OBSERVACION_COL_PAGO_DUPLICADO, observacionesConMarcaDuplicadoCartera, pagoEstaCerradoSoloConsulta }} from './pagosListUtils'
import type {{ PagoConError }} from '../../../services/pagoConErrorService'
import type {{ Pago }} from '../../../services/pagoService'

export type PagosRevisionTabProps = {{
{chr(10).join(f"  {p}: unknown" for p in props)}
}}

export function PagosRevisionTab(props: PagosRevisionTabProps) {{
  const {{
{chr(10).join(f"    {p}," for p in props)}
  }} = props as PagosRevisionTabProps & Record<string, unknown>

  return (
{inner}  )
}}
'''

OUT.write_text(component, encoding="utf-8")

new_lines = (
    lines[: start + 1]
    + ["            <PagosRevisionTab {...pagosRevisionTabProps} />\n"]
    + lines[end:]
)
text = "".join(new_lines)

import_line = "import { useStaffComprobantePreview } from './pagosList/useStaffComprobantePreview'\n"
extra = import_line + "import { PagosRevisionTab, type PagosRevisionTabProps } from './pagosList/PagosRevisionTab'\n"
text = text.replace(import_line, extra)

props_obj = "  const pagosRevisionTabProps: PagosRevisionTabProps = {\n" + "".join(
    f"    {p},\n" for p in props
) + "  }\n\n"

ret = text.find("  return (")
text = text[:ret] + props_obj + text[ret:]

MAIN.write_text(text, encoding="utf-8")
print("revision tab props:", len(props))
