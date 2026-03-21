path = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/utils/cuotaEstadoCaracas.ts"
t = open(path, encoding="utf-8").read()
t = t.replace(
    "export type CuotaEstadoInput = {\n  monto_cuota: number\n",
    "export type CuotaEstadoInput = {\n  monto_cuota?: number | null\n",
)
open(path, "w", encoding="utf-8", newline="").write(t)
print("ok")
