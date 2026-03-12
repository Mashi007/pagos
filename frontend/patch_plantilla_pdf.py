# -*- coding: utf-8 -*-
path = r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\components\notificaciones\PlantillaAnexoPdf.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Block 1: Cuerpo principal
old1 = """        <div>
          <label htmlFor="pdf-cuerpo" className="text-sm font-medium text-gray-700">Cuerpo principal (HTML)</label>
          <Textarea
            id="pdf-cuerpo"
            value={cuerpoPrincipal}
            onChange={(e) => setCuerpoPrincipal(e.target.value)}
            rows={6}
            placeholder={DEFAULT_CUERPO}
            className="mt-1 font-mono text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">Variables: {'{monto_total_usd}'}, {'{num_cuotas}'}, {'{fechas_str}'}</p>
        </div>"""

new1 = """        <div>
          <label htmlFor="pdf-cuerpo" className="text-sm font-medium text-gray-700">Cuerpo principal (HTML)</label>
          <p className="text-xs text-gray-500 mt-0 mb-2">Edite a la izquierda; a la derecha se muestra la vista previa en formato enriquecido.</p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 border rounded-lg overflow-hidden bg-white mt-1">
            <div className="flex flex-col min-h-[200px]">
              <span className="text-xs font-medium text-slate-600 bg-slate-50 px-2 py-1 border-b">Código / HTML</span>
              <Textarea
                id="pdf-cuerpo"
                value={cuerpoPrincipal}
                onChange={(e) => setCuerpoPrincipal(e.target.value)}
                rows={8}
                placeholder={DEFAULT_CUERPO}
                className="flex-1 font-mono text-sm resize-none rounded-none border-0 focus-visible:ring-1"
              />
            </div>
            <div className="flex flex-col min-h-[200px] border-l border-slate-200 bg-slate-50">
              <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 border-b">Vista previa (formato enriquecido)</span>
              <div
                className="flex-1 overflow-auto p-4 prose prose-sm max-w-none text-left"
                style={{ minHeight: 160 }}
                dangerouslySetInnerHTML={{
                  __html: cuerpoPrincipal?.trim()
                    ? (cuerpoPrincipal.startsWith('<') ? cuerpoPrincipal : '<div style="white-space: pre-wrap;">' + cuerpoPrincipal.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>')
                    : '<p class="text-slate-400 text-center text-sm">La vista previa aparecerá aquí.</p>',
                }}
              />
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-1">Variables: {'{monto_total_usd}'}, {'{num_cuotas}'}, {'{fechas_str}'}</p>
        </div>"""

# Block 2: Cláusula - match the mojibake label
old2a = """        <div>
          <label className="text-sm font-medium text-gray-700">ClAusula SAcptima (HTML)</label>
          <Textarea
            value={clausulaSeptima}
            onChange={(e) => setClausulaSeptima(e.target.value)}
            rows={8}
            placeholder={DEFAULT_CLAUSULA}
            className="mt-1 font-mono text-sm"
          />
        </div>"""

new2 = """        <div>
          <label className="text-sm font-medium text-gray-700">Cláusula Séptima (HTML)</label>
          <p className="text-xs text-gray-500 mt-0 mb-2">Edite a la izquierda; a la derecha se muestra la vista previa en formato enriquecido.</p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 border rounded-lg overflow-hidden bg-white mt-1">
            <div className="flex flex-col min-h-[220px]">
              <span className="text-xs font-medium text-slate-600 bg-slate-50 px-2 py-1 border-b">Código / HTML</span>
              <Textarea
                value={clausulaSeptima}
                onChange={(e) => setClausulaSeptima(e.target.value)}
                rows={10}
                placeholder={DEFAULT_CLAUSULA}
                className="flex-1 font-mono text-sm resize-none rounded-none border-0 focus-visible:ring-1"
              />
            </div>
            <div className="flex flex-col min-h-[220px] border-l border-slate-200 bg-slate-50">
              <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 border-b">Vista previa (formato enriquecido)</span>
              <div
                className="flex-1 overflow-auto p-4 prose prose-sm max-w-none text-left"
                style={{ minHeight: 180 }}
                dangerouslySetInnerHTML={{
                  __html: clausulaSeptima?.trim()
                    ? (clausulaSeptima.startsWith('<') ? clausulaSeptima : '<div style="white-space: pre-wrap;">' + clausulaSeptima.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>')
                    : '<p class="text-slate-400 text-center text-sm">La vista previa aparecerá aquí.</p>',
                }}
              />
            </div>
          </div>
        </div>"""

if old1 in content:
    content = content.replace(old1, new1)
    print("Replaced Cuerpo principal")
else:
    print("Old1 not found")

# Try different encodings for the clause label
for old2 in [old2a, old2a.replace("ClAusula SAcptima", "Cláusula Séptima"), """        <div>
          <label className="text-sm font-medium text-gray-700">Cláusula Séptima (HTML)</label>
          <Textarea
            value={clausulaSeptima}
            onChange={(e) => setClausulaSeptima(e.target.value)}
            rows={8}
            placeholder={DEFAULT_CLAUSULA}
            className="mt-1 font-mono text-sm"
          />
        </div>"""]:
    if old2 in content:
        content = content.replace(old2, new2)
        print("Replaced Cláusula")
        break
else:
    # Find by unique part
    if "rows={8}" in content and "placeholder={DEFAULT_CLAUSULA}" in content:
        import re
        content = re.sub(
            r'<div>\s*<label className="text-sm font-medium text-gray-700">[^<]+\(HTML\)</label>\s*<Textarea\s+value=\{clausulaSeptima\}\s+onChange=\{\(e\) => setClausulaSeptima\(e\.target\.value\)\}\s+rows=\{8\}\s+placeholder=\{DEFAULT_CLAUSULA\}\s+className="mt-1 font-mono text-sm"\s*/>\s*</div>',
            new2,
            content,
            count=1,
            flags=re.DOTALL
        )
        print("Replaced Cláusula via regex")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
