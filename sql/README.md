# Scripts SQL y verificaciones

## Verificación FIFO (pagos a cuotas en orden)

- **verificar_fifo_cuotas.sql** — Consultas de verificación: resumen, detalle y resultado global. Solo lectura (SELECT).
- **verificar_fifo_resumen_por_prestamo.sql** — Resumen por préstamo: cuota sin completar y lista de cuotas posteriores con pago.
- **run_verificar_fifo.ps1** — Wrapper PowerShell: pide escribir `fin` antes de ejecutar la verificación (usa `psql`).
- **run_verificar_fifo.py** — Wrapper Python: pide escribir `fin` antes de ejecutar (usa módulo `verificar_fifo` del backend).

Ejecución con confirmación: no se ejecuta la verificación hasta que escribas la palabra **fin**.
