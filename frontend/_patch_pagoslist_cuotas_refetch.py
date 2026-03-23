from pathlib import Path

p = Path(__file__).resolve().parent / "src/components/pagos/PagosList.tsx"
t = p.read_text(encoding="utf-8")
needle = """               await queryClient.invalidateQueries({
                 queryKey: ['cuotas-prestamo'],
                 exact: false,
               })
               await queryClient.invalidateQueries({
                 queryKey: ['prestamos'],"""
repl = """               await queryClient.invalidateQueries({
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
if c == 0:
    raise SystemExit("needle not found")
t2 = t.replace(needle, repl)
p.write_text(t2, encoding="utf-8")
print("replaced", c, "blocks")
