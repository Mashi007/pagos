#!/usr/bin/env python3
import re

filePath = './DialogConciliacion.tsx'

with open(filePath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove all resumen-related state declarations
content = re.sub(
    r'  const \[resumen, setResumen\] = useState<ResumenConciliacion \| null>\(null\)\n',
    '',
    content
)

content = re.sub(
    r'  const \[cargandoResumen, setCargandoResumen\] = useState\(false\)\n',
    '',
    content
)

content = re.sub(
    r"  const \[tab, setTab\] = useState<'carga' \| 'resumen'>\('carga'\)",
    "  const [descargaDisponible, setDescargaDisponible] = useState(false)",
    content
)

# Remove ResumenConciliacion import
content = re.sub(
    r', ResumenConciliacion',
    '',
    content
)

# Remove the Resumen & Descarga button block
content = re.sub(
    r'            <button\n              onClick=\{\(\) => setTab\(\'resumen\'\)\}[\s\S]*?Resumen & Descarga[\s\S]*?</button>\n',
    '',
    content
)

# Remove handleCargarResumen function
content = re.sub(
    r'  const handleCargarResumen = async \(\) => \{[\s\S]*?\n  \}\n',
    '',
    content
)

# Hide Tab Resumen
content = re.sub(
    r"\{tab === 'resumen' && \(",
    "{false && (",
    content
)

# Unwrap Tab Carga
content = re.sub(
    r"\{/\* Tab Carga \*/\}\n          \{tab === 'carga' && \(\n            <>",
    "<>",
    content
)

content = re.sub(
    r"\n            </>\n          \)}\n",
    "\n          </>\n",
    content
)

# Remove all remaining setTab calls
content = re.sub(
    r"        setTab\('[^']*'\)\n",
    "",
    content
)

# Update save success message
content = re.sub(
    r"        toast\.success\('Datos guardados correctamente\. Puede descargar el reporte\.'\)\n        onGuardar\?\(\)\n",
    "        setDescargaDisponible(true)\n        toast.success('Datos guardados. Ya puede descargar el reporte.')\n        onGuardar?.()\n",
    content
)

with open(filePath, 'w', encoding='utf-8') as f:
    f.write(content)

print("DialogConciliacion cleaned")
