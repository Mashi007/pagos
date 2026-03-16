# Patch TablaAmortizacionPrestamo to use backend recibo (same format as cobros)
path = "src/components/prestamos/TablaAmortizacionPrestamo.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove import of generarReciboPagoPDF
old_import = "import { generarReciboPagoPDF } from '../../utils/reciboPagoPDF'\n"
if old_import in content:
    content = content.replace(old_import, "", 1)
    print("Removed reciboPagoPDF import")
else:
    print("Import line not found (may have different format)")

# Replace descargarRecibo body: from "setDescargandoRecibo..." until "setDescargandoRecibo(null)"
# We want: setDescargandoRecibo(cuota.id); try { await prestamoService.getReciboCuotaPdf(prestamo.id, cuota.id); toast.success(...); } catch { toast.error(...); } finally { setDescargandoRecibo(null) }
old_descargar = """  const descargarRecibo = async (cuota: Cuota) => {
    setDescargandoRecibo(cuota.id)
    try {
      await generarReciboPagoPDF(
        {
          id: prestamo.id,
          cedula: prestamo.cedula,
          nombres: prestamo.nombres,
          numero_cuotas: prestamo.numero_cuotas,
          total_financiamiento: prestamo.total_financiamiento,
          modalidad_pago: prestamo.modalidad_pago,
        },
        {
          id: cuota.id,
          numero_cuota: cuota.numero_cuota,
          fecha_vencimiento: cuota.fecha_vencimiento,
          fecha_pago: cuota.fecha_pago,
          monto_cuota: cuota.monto_cuota,
          monto_capital: cuota.monto_capital,
          monto_interes: cuota.monto_interes,
          saldo_capital_final: cuota.saldo_capital_final,
          total_pagado: cuota.total_pagado,
          pago_monto_conciliado: cuota.pago_monto_conciliado,
          pago_id: cuota.pago_id,
          pago_conciliado: cuota.pago_conciliado,
          estado: cuota.estado,
          numero_documento: null,
        }
      )
      toast.success(`Recibo cuota ${cuota.numero_cuota} descargado`)
    } catch (err) {
      console.error('Error generando recibo:', err)
      toast.error('Error al generar el recibo')
    } finally {
      setDescargandoRecibo(null)
    }
  }"""

new_descargar = """  const descargarRecibo = async (cuota: Cuota) => {
    setDescargandoRecibo(cuota.id)
    try {
      await prestamoService.getReciboCuotaPdf(prestamo.id, cuota.id)
      toast.success(`Recibo cuota ${cuota.numero_cuota} descargado`)
    } catch (err) {
      console.error('Error generando recibo:', err)
      toast.error('Error al generar el recibo')
    } finally {
      setDescargandoRecibo(null)
    }
  }"""

if old_descargar in content:
    content = content.replace(old_descargar, new_descargar, 1)
    print("Replaced descargarRecibo")
else:
    print("descargarRecibo block not found exactly, trying minimal replace...")
    # Fallback: just replace the await generarReciboPagoPDF(...) part
    import re
    pattern = r"await generarReciboPagoPDF\(\s*\{[^}]+\},\s*\{[^}]+\}\s*\)"
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(
            pattern,
            "await prestamoService.getReciboCuotaPdf(prestamo.id, cuota.id)",
            content,
            count=1,
            flags=re.DOTALL,
        )
        print("Replaced via regex")
    else:
        print("Could not find pattern")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
