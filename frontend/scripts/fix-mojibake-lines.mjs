/**
 * Trunca lineas de useExcelUploadPagos.ts u otros TS donde el sufijo es mojibake UTF-8 roto.
 * Conserva el prefijo ASCII hasta el primer caracter de corrupcion tipica (Ã, replacement char).
 */
import fs from 'node:fs';
import path from 'node:path';

const file = path.resolve('src/hooks/useExcelUploadPagos.ts');
let text = fs.readFileSync(file, 'utf8');
const lines = text.split(/\r?\n/);
const out = [];
for (let i = 0; i < lines.length; i++) {
  let line = lines[i];
  if (line.length <= 2000) {
    out.push(line);
    continue;
  }
  const m = /Ã|\uFFFD/.exec(line);
  if (!m) {
    out.push(line);
    continue;
  }
  const idx = m.index;
  let prefix = line.slice(0, idx);
  // Completar comentarios / codigo segun prefijo
  if (prefix.includes('return partes.length > 0 ? partes.join')) {
    prefix = prefix.replace(/\s+$/, '');
    if (!prefix.endsWith("'")) {
      prefix = `${prefix.trimEnd()} 'Revisar (error de validacion)'`;
    } else {
      prefix = `${prefix}Revisar (error de validacion)`;
    }
    line = `${prefix}');`;
    out.push(line);
    continue;
  }
  if (prefix.trimStart().startsWith('* Columnas:')) {
    line = ' * Columnas: cedula, fecha, monto, documento, prestamo, conciliacion';
    out.push(line);
    continue;
  }
  if (prefix.trimStart().startsWith('* Solo Pr')) {
    line = ' * Solo Prestamo / Credito / ID (segun plantilla Excel)';
    out.push(line);
    continue;
  }
  if (prefix.trimStart().startsWith('* v3')) {
    line = ' * v3: validacion de columnas y montos';
    out.push(line);
    continue;
  }
  if (prefix.trimStart().startsWith('// L')) {
    line = '// Layout de columnas segun primera fila';
    out.push(line);
    continue;
  }
  if (prefix.startsWith('/** Infiere observaciones')) {
    line =
      '/** Infiere observaciones desde el mensaje de error del backend (422, 400, etc.) */';
    out.push(line);
    continue;
  }
  if (prefix.includes('if (/fecha_pago')) {
    line =
      "  if (/fecha_pago|formato.*yyyy-mm-dd|fecha.*invalida/i.test(msg)) return 'fecha';";
    out.push(line);
    continue;
  }
  if (prefix.includes('if (/monto|amount')) {
    line = "  if (/monto|amount|debe ser|greater|positive/i.test(msg)) return 'monto';";
    out.push(line);
    continue;
  }
  if (prefix.includes('if (/prestamo_id')) {
    line =
      "  if (/prestamo_id|prestamo.*entre|entre 1 y|id fuera/i.test(msg)) return 'prestamo';";
    out.push(line);
    continue;
  }
  if (prefix.includes('else if (/prestamo|credito')) {
    line =
      "  else if (/prestamo|credito|credito\\/id/i.test(msg)) return 'prestamo';";
    out.push(line);
    continue;
  }
  if (prefix.includes('Evita doble peticion')) {
    line = '  /** Evita doble peticion al subir el mismo archivo */';
    out.push(line);
    continue;
  }
  if (prefix.includes('Incluir todas las C')) {
    line = '  // Incluir todas las columnas relevantes del Excel';
    out.push(line);
    continue;
  }
  if (prefix.includes('Normalizar (sin gui')) {
    line = '    // Normalizar (sin guiones ni espacios extra)';
    out.push(line);
    continue;
  }
  if (prefix.trimStart().startsWith('// B')) {
    line = '  // Buscar fila de encabezados';
    out.push(line);
    continue;
  }
  if (prefix.includes('Carga inicial: buscar Pr')) {
    line = '  // Carga inicial: buscar Prestamos / creditos';
    out.push(line);
    continue;
  }
  // Fallback: cortar en primer caracter corrupto y cerrar comentario
  prefix = prefix.replace(/\s+$/, '');
  if (prefix.endsWith('//')) {
    line = `${prefix} ...`;
  } else if (prefix.includes('/*') && !prefix.includes('*/')) {
    line = `${prefix} */`;
  } else if (prefix.trim().startsWith('//')) {
    line = `${prefix.trimEnd()} (texto truncado por encoding)`;
  } else {
    line = `${prefix}'`;
  }
  out.push(line);
}
fs.writeFileSync(file, out.join('\n').replace(/\n/g, '\n'), 'utf8');
console.log('Fixed long lines in', file);
