# Scripts SQL y verificaciones

## Verificacion cascada (pagos a cuotas en orden)

Archivos en disco pueden conservar el prefijo `verificar_fifo_*` (historico). La semantica es **cascada** (orden por numero de cuota).

- **verificar_fifo_cuotas.sql** — Consultas de verificacion: resumen, detalle y resultado global. Solo lectura (SELECT).
- **verificar_fifo_resumen_por_prestamo.sql** — Resumen por prestamo: cuota sin completar y lista de cuotas posteriores con pago.
- **run_verificar_cascada.py** — Wrapper Python: pide escribir `fin` antes de ejecutar (usa `verificar_cascada` en el backend).
- **run_verificar_fifo.py** — Compat: redirige al wrapper anterior.
- **run_verificar_fifo.ps1** — Wrapper PowerShell: pide escribir `fin` antes de ejecutar la verificacion (usa `psql`).

Ejecucion con confirmacion: no se ejecuta la verificacion hasta que escribas la palabra **fin**.

