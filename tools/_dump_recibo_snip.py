path = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/services/cobros/recibo_pdf.py"
t = open(path, encoding="utf-8").read()
idx = t.find('Paragraph("Aplicado a"')
print(t[idx - 120 : idx + 1400])
