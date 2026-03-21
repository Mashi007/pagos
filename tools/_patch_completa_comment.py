path = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/reportes/TablaAmortizacionCompleta.tsx"
t = open(path, encoding="utf-8").read()
old = """                                  {cuotasDelPrestamo.map((cuota: Cuota) => {
                                    // Determinar el estado real basado en los datos (igual que en Préstamos)

                                    const estadoReal =
                                      clasificarEstadoCuotaCaracas(cuota)"""
new = """                                  {cuotasDelPrestamo.map((cuota: Cuota) => {
                                    const estadoReal =
                                      clasificarEstadoCuotaCaracas(cuota)"""
if old not in t:
    raise SystemExit("block not found")
open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
print("ok")
