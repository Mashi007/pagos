/**
 * Revierte cambios del script que rompieron referencias a error, row, index.
 */
const fs = require('fs')
const path = require('path')

const base = path.join(__dirname, 'src')

// ExcelUploader: (_row, _index) solo en el callback que no usa row/index; el resto del archivo usa row e index en otros callbacks.
// Revertir (_row, _index) -> (row, index) para no romper el resto.
// Y } catch { donde se use error -> } catch (err) { y reemplazar error por err en ese bloque.
function fixExcelUploader() {
  const file = path.join(base, 'components', 'clientes', 'ExcelUploader.tsx')
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(/\(_row,\s*_index\)/g, '(row, index)')
  // catch sin variable pero se usa error: buscar bloques catch { ... } que contengan "error" y cambiar a catch (err) y error -> err
  s = s.replace(/} catch \{([^}]*?\berror\b[^}]*)\}/g, (_, block) => '} catch (err) {' + block.replace(/\berror\b/g, 'err') + '}')
  fs.writeFileSync(file, s)
  console.log('Reverted ExcelUploader row/index and catch(err)')
}

// CrearClienteForm: mismo tema con error
function fixCrearClienteForm() {
  const file = path.join(base, 'components', 'clientes', 'CrearClienteForm.tsx')
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(/} catch \{([^}]*?\berror\b[^}]*)\}/g, (_, block) => '} catch (err) {' + block.replace(/\berror\b/g, 'err') + '}')
  fs.writeFileSync(file, s)
  console.log('Reverted CrearClienteForm catch(err)')
}

function fixAIConfig() {
  const file = path.join(base, 'components', 'configuracion', 'AIConfig.tsx')
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(/} catch \{/g, '} catch (error) {')
  s = s.replace(/_PromptEditor/g, 'PromptEditor')
  fs.writeFileSync(file, s)
  console.log('Fixed AIConfig catch(error) and PromptEditor')
}

try {
  fixExcelUploader()
  fixCrearClienteForm()
  fixAIConfig()
} catch (e) {
  console.error(e)
  process.exit(1)
}
