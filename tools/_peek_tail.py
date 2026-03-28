p = r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\services\estado_cuenta_pdf.py"
t = open(p, encoding="utf-8").read()
needle = '"amortizaciones_por_prestamo": amortizaciones_por_prestamo'
i = t.rfind(needle)
print(t[i : i + 1200])
