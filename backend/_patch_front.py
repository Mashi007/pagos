from pathlib import Path
p = Path(r"C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\components\recibos\ConfiguracionRecibos.tsx")
text = p.read_text(encoding="utf-8")
old = """          <CardDescription>
            Un solo correo de muestra: plantilla HTML{' '}
            <strong>ya guardada</strong> (misma que el envío masivo) más PDF de
            estado de cuenta del primer cliente válido en la ventana (Caracas).
            Destino: solo el correo que indique abajo. CCO según Recibos. Guarde
            la plantilla antes si acaba de editarla.
          </CardDescription>"""
new = """          <CardDescription>
            Un solo correo de muestra: plantilla HTML{' '}
            <strong>ya guardada</strong> (misma que el envío masivo) más PDF de
            estado de cuenta del primer cliente válido en la ventana (Caracas).
            El correo de abajo es el destinatario principal (To). La CCO
            configurada arriba (cobranza@ / notificaciones@) también se envía
            en copia oculta. Guarde la plantilla y la CCO antes de probar.
          </CardDescription>"""
if old not in text:
    raise SystemExit("CardDescription not found")
text = text.replace(old, new, 1)
old2 = """        toast.success(
          msg ||
            'Muestra Recibos enviada: mismo HTML que el envío masivo (plantilla guardada) + PDF, primer cliente en ventana.'
        )"""
new2 = """        toast.success(
          msg ||
            'Muestra Recibos enviada (To = correo indicado; CCO = cobranza@ y notificaciones@ si están configurados).'
        )"""
if old2 not in text:
    raise SystemExit("toast not found")
text = text.replace(old2, new2, 1)
p.write_text(text, encoding="utf-8")
print("OK frontend")
