// ============================================
// MOSTRAR TODOS LOS INPUTS CON SU INFORMACIÓN COMPLETA
// Para identificar qué campos faltan
// ============================================

(() => {
  console.log('🔍 MOSTRANDO TODOS LOS INPUTS\n');
  console.log('='.repeat(60));

  const inputs = Array.from(document.querySelectorAll('input, textarea'));
  const inputsVisibles = inputs.filter(inp => inp.offsetParent !== null);

  console.log(`\n📊 Total de inputs visibles: ${inputsVisibles.length}\n`);

  inputsVisibles.forEach((input, index) => {
    const tipo = input.type || input.tagName.toLowerCase();
    const valor = input.value || '';
    const placeholder = input.placeholder || '';
    const name = input.name || '';
    const id = input.id || '';

    // Buscar label
    let labelTexto = '';
    if (input.id) {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (label) labelTexto = label.textContent.trim();
    }

    if (!labelTexto) {
      const contenedor = input.closest('div');
      const label = contenedor?.querySelector('label');
      if (label) labelTexto = label.textContent.trim();
    }

    if (!labelTexto) {
      let elem = input.previousElementSibling;
      for (let i = 0; i < 3 && elem; i++) {
        if (elem.tagName === 'LABEL' || (elem.classList.contains('text-sm') && elem.classList.contains('font-medium'))) {
          labelTexto = elem.textContent.trim();
          break;
        }
        elem = elem.previousElementSibling;
      }
    }

    // Buscar texto alrededor del input
    const contenedor = input.closest('div');
    const textoContenedor = contenedor?.textContent || '';

    console.log(`\n📝 INPUT #${index + 1}:`);
    console.log(`   Tipo: ${tipo}`);
    console.log(`   Valor: ${tipo === 'password' ? '***' : (valor || '(vacío)')}`);
    console.log(`   Placeholder: "${placeholder}"`);
    console.log(`   Name: "${name}"`);
    console.log(`   ID: "${id}"`);
    console.log(`   Label: "${labelTexto}"`);
    console.log(`   Texto alrededor: "${textoContenedor.substring(0, 100)}..."`);

    // Intentar identificar
    const labelLower = labelTexto.toLowerCase();
    const placeholderLower = placeholder.toLowerCase();
    const textoLower = textoContenedor.toLowerCase();

    if (labelLower.includes('servidor') || placeholderLower.includes('smtp.gmail.com') || valor.includes('smtp.gmail.com')) {
      console.log(`   🎯 IDENTIFICADO COMO: smtp_host`);
    } else if (labelLower.includes('puerto') || placeholderLower.includes('587') || valor === '587') {
      console.log(`   🎯 IDENTIFICADO COMO: smtp_port`);
    } else if (labelLower.includes('usuario') || labelLower.includes('gmail') && tipo === 'email') {
      console.log(`   🎯 IDENTIFICADO COMO: smtp_user`);
    } else if (labelLower.includes('remitente') && tipo === 'email') {
      console.log(`   🎯 IDENTIFICADO COMO: from_email`);
    } else if (labelLower.includes('nombre') && !labelLower.includes('usuario')) {
      console.log(`   🎯 IDENTIFICADO COMO: from_name`);
    } else if (tipo === 'password') {
      console.log(`   🎯 IDENTIFICADO COMO: smtp_password`);
    }
  });

  // Buscar checkboxes
  console.log(`\n\n📋 CHECKBOXES:\n`);
  const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
  checkboxes.forEach((cb, index) => {
    const label = cb.nextElementSibling;
    const texto = label?.textContent || '';
    console.log(`   Checkbox #${index + 1}: ${cb.checked ? '✅ Marcado' : '❌ Desmarcado'}`);
    console.log(`   Label: "${texto}"`);
    if (texto.includes('TLS')) {
      console.log(`   🎯 IDENTIFICADO COMO: smtp_use_tls`);
    }
  });

  console.log('\n' + '='.repeat(60));

  return { inputs: inputsVisibles.length, checkboxes: checkboxes.length };
})();

