/**
 * Falla si detecta senales tipicas de corrupcion de encoding o lineas anormalmente largas en TS/JS.
 * Uso:
 *   node scripts/check-source-hygiene.mjs
 *   node scripts/check-source-hygiene.mjs path/to/a.ts path/to/b.tsx   (p.ej. desde lint-staged)
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_ROOT = path.join(__dirname, '..')
const SRC = path.join(FRONTEND_ROOT, 'src')

/** Lineas mas largas que esto suelen ser pegados corruptos o minificacion accidental. */
const MAX_LINE_LENGTH = Number(process.env.HYGIENE_MAX_LINE || 8000)

/** Subcadenas frecuentes en UTF-8 mal decodificado (doble conversion). */
const MOJIBAKE_HEX = [
  'c383c692c386e28099',
  'c383c692c382c2a2c383c2a2',
  'c383c2a2c3a2e2809ac2acc3a2e2809ec2a2',
  'c383c2a2c3a2e2809ac2acc385e2809c',
  'c383c2a2c3a2e2809ac2ac',
  'c383e280a0c3a2e282ace284a2',
  'c383c2a2c3a2e2809ac2acc385c2a1',
  'c383c692c3a2e282acc5a1c383e2809a',
]
const MOJIBAKE_SNIPPETS = MOJIBAKE_HEX.map(h =>
  Buffer.from(h, 'hex').toString('utf8')
)

function walkDir(dir, acc) {
  if (!fs.existsSync(dir)) return acc
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name)
    const st = fs.statSync(full)
    if (st.isDirectory()) walkDir(full, acc)
    else if (/\.(ts|tsx|js|jsx|mjs|cjs)$/i.test(name)) acc.push(full)
  }
  return acc
}

function checkFile(filePath) {
  const rel = path.relative(FRONTEND_ROOT, filePath)
  let content
  try {
    content = fs.readFileSync(filePath, 'utf8')
  } catch (e) {
    return [{ rel, kind: 'read', detail: String(e) }]
  }

  const issues = []
  const lines = content.split(/\r?\n/)
  lines.forEach((line, i) => {
    const n = i + 1
    if (line.length > MAX_LINE_LENGTH) {
      issues.push({
        rel,
        kind: 'long-line',
        line: n,
        len: line.length,
        detail: `linea ${n} tiene ${line.length} caracteres (max ${MAX_LINE_LENGTH})`,
      })
    }
    for (const snip of MOJIBAKE_SNIPPETS) {
      if (line.includes(snip)) {
        issues.push({
          rel,
          kind: 'mojibake',
          line: n,
          detail: `posible texto corrupto (patron "${snip.slice(0, 8)}...")`,
        })
        break
      }
    }
    if (line.includes('\uFFFD')) {
      issues.push({
        rel,
        kind: 'replacement-char',
        line: n,
        detail: 'caracter de reemplazo Unicode (U+FFFD)',
      })
    }
  })
  return issues
}

function main() {
  const args = process.argv.slice(2)
  let files = []
  if (args.length === 0) {
    files = walkDir(SRC, [])
  } else {
    const cwd = process.cwd()
    files = args
      .map(f => path.resolve(cwd, f))
      .filter(f => fs.existsSync(f) && fs.statSync(f).isFile())
  }

  if (files.length === 0) {
    console.error('check-source-hygiene: no hay archivos para revisar.')
    process.exit(1)
  }

  const all = []
  for (const f of files) {
    all.push(...checkFile(f))
  }

  if (all.length === 0) {
    console.log(
      `check-source-hygiene: OK (${files.length} archivo(s), max linea ${MAX_LINE_LENGTH})`
    )
    process.exit(0)
  }

  console.error('check-source-hygiene: problemas encontrados:\n')
  for (const it of all.slice(0, 80)) {
    console.error(
      `  [${it.kind}] ${it.rel}${it.line ? `:${it.line}` : ''} - ${it.detail}`
    )
  }
  if (all.length > 80) {
    console.error(`  ... y ${all.length - 80} mas.`)
  }
  console.error(
    '\nSugerencia: revisar encoding (UTF-8), ejecutar npm run sanitize:chars, y evitar pegar desde Word sin limpiar.'
  )
  process.exit(1)
}

main()
