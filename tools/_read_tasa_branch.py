from pathlib import Path
t = Path(r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/hooks/useExcelUploadPagos.ts").read_text(encoding="utf-8")
i = t.find("field === 'tasa_cambio_manual'")
print(t[i : i + 500] if i >= 0 else "not found")
