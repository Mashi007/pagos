// ============================================
// IDENTIFICAR Y LLENAR from_email CORRECTAMENTE
// ============================================

(() => {
  console.log('🔍 IDENTIFICANDO CAMPOS DE EMAIL\n');
  console.log('='.repeat(60));

  const emailInputs = Array.from(document.querySelectorAll('input[type="email"]'))
    .filter(inp => inp.offsetParent !== null);

  console.log(`📊 Total de inputs email: ${emailInputs.length}\n`);

  const campos = {};

  emailInputs.forEach((inp, i) => {
    const valor = inp.value || '';

    // Buscar el contenedor padre y todo su contexto
    let contenedor = inp.closest('div');
    let nivel = 0;
    let textoCompleto = '';

    // Subir varios niveles para obtener más contexto
    while (contenedor && nivel < 5) {
      textoCompleto = contenedor.textContent + ' ' + textoCompleto;
      contenedor = contenedor.parentElement;
      nivel++;
    }

    // También buscar labels específicos
    const label = inp.closest('div')?.querySelector('label');
    const labelTexto = label?.textContent || '';

    const textoLower = (textoCompleto + ' ' + labelTexto).toLowerCase();

    console.log(`\n📝 Input EMAIL #${i + 1}:`);
    console.log(`   Valor: "${valor}"`);
    console.log(`   Label: "${labelTexto}"`);
    console.log(`   Contexto: "${textoCompleto.substring(0, 200)}..."`);

    // Identificar por el contexto
    if (textoLower.includes('usuario') || textoLower.includes('gmail') && textoLower.includes('workspace')) {
      campos.smtp_user = { input: inp, valor: valor, index: i };
      console.log(`   → IDENTIFICADO: smtp_user`);
    } else if (textoLower.includes('remitente') || textoLower.includes('from email') || textoLower.includes('email del remitente')) {
      campos.from_email = { input: inp, valor: valor, index: i };
      console.log(`   → IDENTIFICADO: from_email`);
    } else if (textoLower.includes('pruebas') || textoLower.includes('prueba')) {
      campos.email_pruebas = { input: inp, valor: valor, index: i };
      console.log(`   → IDENTIFICADO: email_pruebas`);
    } else {
      // Si no se identifica, intentar por posición
      if (i === 0 && !campos.smtp_user) {
        campos.smtp_user = { input: inp, valor: valor, index: i };
        console.log(`   → PROBABLEMENTE: smtp_user (primer input email)`);
      } else if (i === 1 && !campos.from_email) {
        campos.from_email = { input: inp, valor: valor, index: i };
        console.log(`   → PROBABLEMENTE: from_email (segundo input email)`);
      } else {
        campos.email_pruebas = { input: inp, valor: valor, index: i };
        console.log(`   → PROBABLEMENTE: email_pruebas (tercer input email)`);
      }
    }
  });

  console.log('\n' + '='.repeat(60));
  console.log('📋 RESUMEN:\n');

  if (campos.smtp_user) {
    console.log(`✅ smtp_user: "${campos.smtp_user.valor}"`);
  }

  if (campos.from_email) {
    if (campos.from_email.valor && campos.from_email.valor.trim() !== '') {
      console.log(`✅ from_email: "${campos.from_email.valor}"`);
    } else {
      console.log(`❌ from_email: VACÍO`);
      console.log(`\n💡 LLENANDO from_email AUTOMÁTICAMENTE...`);

      // Llenar el campo
      const input = campos.from_email.input;
      input.value = 'pafo.kampei@gmail.com';

      // Disparar evento change para que React lo detecte
      const event = new Event('input', { bubbles: true });
      input.dispatchEvent(event);

      // También disparar change
      const changeEvent = new Event('change', { bubbles: true });
      input.dispatchEvent(changeEvent);

      // Hacer foco
      input.focus();
      input.scrollIntoView({ behavior: 'smooth', block: 'center' });

      console.log(`✅ Campo llenado con: pafo.kampei@gmail.com`);
      console.log(`✅ Eventos disparados para actualizar React`);
      console.log(`\n⚠️ Si el botón no se habilita, intenta hacer clic en el campo y presionar Tab`);
    }
  } else {
    console.log(`⚠️ from_email: NO IDENTIFICADO`);
  }

  if (campos.email_pruebas) {
    console.log(`ℹ️ email_pruebas: "${campos.email_pruebas.valor || '(vacío - opcional)'}"`);
  }

  return campos;
})();

