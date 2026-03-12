# Patch PlantillasNotificaciones: allow HTML in encabezado/cuerpo/firma and render in preview
import re

path = "src/components/notificaciones/PlantillasNotificaciones.tsx"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) Remove the block that escapes HTML when content doesn't start with '<'
old_block = """    if (!html.trim().startsWith('<')) {
      html = `<div style="white-space: pre-wrap; font-family: sans-serif; padding: 16px;">${html.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>`
    }
    const doc = """
new_line = """    // Siempre renderizar como HTML (encabezado, cuerpo y firma pueden contener código HTML)
    const doc = """
if old_block in c:
    c = c.replace(old_block, new_line)
    print("1. Removed HTML-escape block")
else:
    print("1. Block not found")

# 2) Add hint and update labels
old_labels = """            <div className="col-span-2">
              <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">Formato rápido (encabezado/cuerpo/firma):"""
new_labels = """            <div className="col-span-2">
              <p className="text-xs text-gray-500 mb-1">Puede usar código HTML en encabezado, cuerpo y firma. Use el botón «Vista previa (datos de ejemplo)» para ver cómo queda el resultado.</p>
              <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">Formato rápido (encabezado/cuerpo/firma):"""
if new_labels not in c and "Formato rápido" in c:
    c = c.replace(
        """            <div className="col-span-2">
              <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">Formato rápido (encabezado/cuerpo/firma):""",
        new_labels,
        1,
    )
    print("2. Added HTML hint")
else:
    print("2. Hint already present or pattern not found")

c = c.replace('<label className="text-sm text-gray-600">Encabezado</label>', '<label className="text-sm text-gray-600">Encabezado (puede incluir HTML)</label>')
c = c.replace('<label className="text-sm text-gray-600">Firma</label>', '<label className="text-sm text-gray-600">Firma (puede incluir HTML)</label>')
c = c.replace('<label className="text-sm text-gray-600">Cuerpo</label>', '<label className="text-sm text-gray-600">Cuerpo (puede incluir HTML)</label>')
print("3. Updated labels")

c = c.replace('placeholder="Encabezado"', 'placeholder="Encabezado (ej. <p>Texto</p>)"')
c = c.replace('placeholder="Firma"', 'placeholder="Firma (ej. <p>Atentamente,</p>)"')
c = c.replace('placeholder="Contenido principal"', 'placeholder="Contenido principal (ej. <p>Hola <b>{{nombre}}</b></p>)"')
print("4. Updated placeholders")

with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(c)
print("Done.")
