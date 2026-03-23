# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "services" / "notificaciones_prueba_paquete.py"
lines = p.read_text(encoding="utf-8").splitlines(True)
out = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'cuerpo = (' in line and i + 1 < len(lines) and 'Estimado/a {nombre}' in lines[i + 1]:
        # Replace first block (retrasadas)
        out.append(line)
        i += 1
        block = [
            '            "Estimado/a {nombre} (cedula {cedula}),\\n\\n"\n',
            '            "Le recordamos que tiene una cuota en mora.\\n"\n',
            '            "Fecha de vencimiento: {fecha_vencimiento}\\n"\n',
            '            "Numero de cuota: {numero_cuota}\\n"\n',
            '            "Monto: {monto}\\n\\n"\n',
            '            "Por favor regularice su pago lo antes posible.\\n\\n"\n',
            '            "Saludos,\\nRapicredit"\n',
            '        )\n',
        ]
        # Skip until closing paren of cuerpo
        while i < len(lines) and not (lines[i].strip() == ')' and '        )' in lines[i]):
            i += 1
        if i < len(lines):
            i += 1  # skip old )
        out.extend(block)
        continue
    if 'cuerpo = (' in line and i + 1 < len(lines) and 'Aviso prejudicial' in ''.join(lines[i : i + 5]):
        out.append(line)
        i += 1
        block = [
            '            "Estimado/a {nombre} (cedula {cedula}),\\n\\n"\n',
            '            "Le informamos que su cuenta presenta varias cuotas en mora.\\n"\n',
            '            "Fecha de vencimiento de referencia: {fecha_vencimiento}\\n"\n',
            '            "Cuota de referencia: {numero_cuota}\\n"\n',
            '            "Monto de referencia: {monto}\\n\\n"\n',
            '            "Por favor contacte a la entidad para regularizar su situacion.\\n\\n"\n',
            '            "Saludos,\\nRapicredit"\n',
            '        )\n',
        ]
        while i < len(lines) and not (lines[i].strip() == ')' and lines[i].startswith('        )')):
            i += 1
        if i < len(lines):
            i += 1
        out.extend(block)
        continue
    out.append(line)
    i += 1

p.write_text(''.join(out), encoding='utf-8')
print('ok')
