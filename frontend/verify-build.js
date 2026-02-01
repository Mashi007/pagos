/**
 * Verificación post-build: asegura que dist/assets/ contiene todos los chunks
 * necesarios. Si faltan archivos, el build falla para detectar builds incompletos
 * (p. ej. timeout/OOM en Render).
 */
import { readdirSync, readFileSync, existsSync } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const distPath = path.join(__dirname, 'dist')
const assetsPath = path.join(distPath, 'assets')

const MIN_JS_CHUNKS = 3 // Mínimo de chunks .js (entry + vendor; casi todas las páginas van en main para evitar 404 en Render)

if (!existsSync(distPath)) {
  console.error('❌ verify-build: dist/ no existe')
  process.exit(1)
}

if (!existsSync(assetsPath)) {
  console.error('❌ verify-build: dist/assets/ no existe')
  process.exit(1)
}

const files = readdirSync(assetsPath)
const jsFiles = files.filter((f) => f.endsWith('.js'))
const cssFiles = files.filter((f) => f.endsWith('.css'))

if (jsFiles.length < MIN_JS_CHUNKS) {
  console.error(
    `❌ verify-build: dist/assets/ tiene ${jsFiles.length} archivos .js (mínimo esperado: ${MIN_JS_CHUNKS}). Build posiblemente incompleto.`
  )
  console.error('   Archivos:', jsFiles.slice(0, 20).join(', '), jsFiles.length > 20 ? '...' : '')
  process.exit(1)
}

const indexPath = path.join(distPath, 'index.html')
if (!existsSync(indexPath)) {
  console.error('❌ verify-build: dist/index.html no existe')
  process.exit(1)
}

const html = readFileSync(indexPath, 'utf8')
const scriptMatch = html.match(/src="\/assets\/(index-[^"]+\.js)"/)
if (!scriptMatch) {
  console.error('❌ verify-build: index.html no referencia el entry JS en /assets/')
  process.exit(1)
}

const entryJs = scriptMatch[1]
if (!jsFiles.includes(entryJs)) {
  console.error(`❌ verify-build: index.html referencia ${entryJs} pero no existe en dist/assets/`)
  process.exit(1)
}

console.log(`✅ verify-build: dist/assets/ tiene ${jsFiles.length} .js y ${cssFiles.length} .css`)
console.log(`✅ verify-build: entry ${entryJs} existe`)
process.exit(0)
