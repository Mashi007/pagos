path = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/api/v1/endpoints/estado_cuenta_publico.py"
t = open(path, encoding="utf-8").read()
needle = (
    "    las mismas tablas de amortización (cuotas) con Pago conc. y Recibo desde la tabla cuotas.\n\n"
    '    """'
)
repl = (
    "    las mismas tablas de amortización (cuotas) con Pago conc. y Recibo desde la tabla cuotas.\n\n"
    "    Estados de cuota en el PDF: mismas reglas Caracas y etiquetas que la app interna\n\n"
    "    (generar_pdf_estado_cuenta usa etiqueta_estado_cuota).\n\n"
    '    """'
)
if repl.split("Estados")[0] in t and "generar_pdf_estado_cuenta usa etiqueta" in t:
    print("already")
elif needle in t:
    t = t.replace(needle, repl, 1)
    open(path, "w", encoding="utf-8", newline="\n").write(t)
    print("ok")
else:
    print("needle missing", needle[:80])
