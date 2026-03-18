path = "src/hooks/useExcelUploadPagos.ts"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    "import { pagoConErrorService } from '../services/pagoConErrorService'",
    "import { pagoConErrorService, type PagoConErrorCreate } from '../services/pagoConErrorService'",
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")
