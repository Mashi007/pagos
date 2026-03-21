t = open(
    r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/services/estado_cuenta_pdf.py",
    encoding="utf-8",
).read()
i = t.find("estado_backend = (getattr(c, ")
j = t.find("pago_conc_display = ", i)
print(repr(t[i:j+80]))
