# Don't show "Error de conexion" when test email was sent successfully
path = "frontend/src/components/configuracion/EmailConfig.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

old = "!vinculacionConfirmada && !requiereAppPassword && estadoConfiguracion && !estadoConfiguracion.configurada && ("
new = "!vinculacionConfirmada && !requiereAppPassword && estadoConfiguracion && !estadoConfiguracion.configurada && !resultadoPrueba?.success && ("

if old not in text:
    raise SystemExit("Old string not found")
text = text.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Frontend patched OK")
