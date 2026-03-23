from pathlib import Path

ROOT = Path(r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos")
p = ROOT / "frontend/src/components/pagos/PagosList.tsx"
t = p.read_text(encoding="utf-8")
needle = """              await queryClient.invalidateQueries({
                queryKey: ['cuotas-prestamo'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['prestamos'],"""
repl = """              await queryClient.invalidateQueries({
                queryKey: ['cuotas-prestamo'],
                exact: false,
              })
              await queryClient.refetchQueries({
                queryKey: ['cuotas-prestamo'],
                exact: false,
              })
              await queryClient.invalidateQueries({
                queryKey: ['prestamos'],"""
c = t.count(needle)
print("occurrences", c)
if c == 0:
    raise SystemExit("needle not found")
p.write_text(t.replace(needle, repl), encoding="utf-8")
print("OK")
