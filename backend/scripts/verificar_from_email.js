// ============================================
// VERIFICAR ESPECÍFICAMENTE EL CAMPO from_email
// ============================================

(() => {
  console.log('🔍 VERIFICANDO CAMPO from_email\n');

  const inputs = Array.from(document.querySelectorAll('input, textarea'))
    .filter(inp => inp.offsetParent !== null);

  console.log('📋 TODOS LOS INPUTS DE TIPO EMAIL:\n');

  const emailInputs = inputs.filter(inp => inp.type === 'email');

  emailInputs.forEach((inp, i) => {
    const valor = inp.value || '';
    const placeholder = inp.placeholder || '';

    // Buscar label o texto alrededor
    const contenedor = inp.closest('div');
    const textoCompleto = contenedor?.textContent || '';

    console.log(`Input EMAIL #${i + 1}:`);
    console.log(`   Valor: "${valor}"`);
    console.log(`   Placeholder: "${placeholder}"`);
    console.log(`   Texto alrededor: "${textoCompleto.substring(0, 150)}..."`);

    // Identificar
    const textoLower = textoCompleto.toLowerCase();
    if (textoLower.includes('usuario') || textoLower.includes('gmail') && textoLower.includes('workspace')) {
      console.log(`   → IDENTIFICADO COMO: smtp_user`);
    } else if (textoLower.includes('remitente') || textoLower.includes('from email')) {
      console.log(`   → IDENTIFICADO COMO: from_email`);
    } else {
      console.log(`   → NO IDENTIFICADO (¿smtp_user o from_email?)`);
    }
    console.log('');
  });

  // Buscar específicamente el input de "Email del Remitente"
  console.log('🔎 BUSCANDO "Email del Remitente":\n');

  const todosLosTextos = document.body.textContent || '';
  const tieneRemitente = todosLosTextos.includes('Email del Remitente') ||
                         todosLosTextos.includes('Remitente');

  console.log(`¿Tiene texto "Remitente"?: ${tieneRemitente ? '✅ SÍ' : '❌ NO'}`);

  // Buscar el input que está después del texto "Email del Remitente"
  const elementos = Array.from(document.querySelectorAll('*'));
  let inputRemitente = null;

  elementos.forEach(elem => {
    const texto = elem.textContent || '';
    if (texto.includes('Email del Remitente') || texto.includes('Remitente') && elem.tagName === 'LABEL') {
      // Buscar el siguiente input después de este label
      let siguiente = elem.nextElementSibling;
      while (siguiente && siguiente.tagName !== 'INPUT') {
        siguiente = siguiente.nextElementSibling;
      }
      if (siguiente && siguiente.type === 'email') {
        inputRemitente = siguiente;
      }

      // También buscar en el contenedor padre
      const contenedor = elem.closest('div');
      const inputEnContenedor = contenedor?.querySelector('input[type="email"]');
      if (inputEnContenedor) {
        inputRemitente = inputEnContenedor;
      }
    }
  });

  if (inputRemitente) {
    console.log(`✅ Input de Remitente encontrado:`);
    console.log(`   Valor: "${inputRemitente.value || '(vacío)'}"`);
    console.log(`   Placeholder: "${inputRemitente.placeholder || '(sin placeholder)'}"`);

    if (!inputRemitente.value || inputRemitente.value.trim() === '') {
      console.log(`\n❌ PROBLEMA: El campo from_email está VACÍO`);
      console.log(`\n💡 SOLUCIÓN:`);
      console.log(`   1. Haz clic en el campo "Email del Remitente"`);
      console.log(`   2. Ingresa el email: pafo.kampei@gmail.com`);
      console.log(`   3. El botón "Guardar" debería habilitarse automáticamente`);
    } else {
      console.log(`\n✅ El campo from_email tiene valor`);
    }
  } else {
    console.log(`❌ No se encontró el input de Remitente`);
    console.log(`\n💡 Intenta buscar manualmente el campo "Email del Remitente" en la página`);
  }

  return { inputRemitente, valor: inputRemitente?.value || '' };
})();

