// ============================================
// DIAGNÓSTICO COMPLETO DEL FORMULARIO DE EMAIL
// Busca todos los campos, incluyendo componentes personalizados
// ============================================

(() => {
  console.log('🔍 DIAGNÓSTICO COMPLETO DEL FORMULARIO DE EMAIL\n');
  console.log('='.repeat(60));

  // 1. Buscar todos los inputs posibles
  const todosLosInputs = document.querySelectorAll('input, textarea, select');
  console.log(`\n📊 Total de inputs encontrados: ${todosLosInputs.length}`);

  // 2. Buscar específicamente en el área de configuración de email
  const seccionEmail = document.querySelector('[class*="email"], [id*="email"], [class*="Email"], [id*="Email"]');
  const seccionSMTP = document.querySelector('[class*="smtp"], [id*="smtp"], [class*="SMTP"], [id*="SMTP"]');

  console.log(`\n📍 Sección Email encontrada: ${seccionEmail ? 'Sí' : 'No'}`);
  console.log(`📍 Sección SMTP encontrada: ${seccionSMTP ? 'Sí' : 'No'}`);

  // 3. Buscar campos específicos de email por name o id
  const camposEsperados = [
    'smtp_host', 'smtp_host', 'smtpHost',
    'smtp_port', 'smtp_port', 'smtpPort',
    'smtp_user', 'smtp_user', 'smtpUser',
    'smtp_password', 'smtp_password', 'smtpPassword',
    'from_email', 'from_email', 'fromEmail',
    'from_name', 'from_name', 'fromName',
    'smtp_use_tls', 'smtp_use_tls', 'smtpUseTls', 'use_tls', 'useTls',
    'modo_pruebas', 'modo_pruebas', 'modoPruebas',
    'email_pruebas', 'email_pruebas', 'emailPruebas'
  ];

  console.log('\n🔎 BUSCANDO CAMPOS ESPECÍFICOS:');
  const camposEncontrados = {};

  camposEsperados.forEach(nombre => {
    // Buscar por name
    let campo = document.querySelector(`[name="${nombre}"]`);
    if (!campo) {
      // Buscar por id
      campo = document.querySelector(`[id="${nombre}"]`);
    }
    if (!campo) {
      // Buscar por id que contenga el nombre
      campo = document.querySelector(`[id*="${nombre}"]`);
    }

    if (campo) {
      const valor = campo.type === 'password' ? '***' : campo.value;
      const vacio = !campo.value || campo.value.trim() === '';
      camposEncontrados[nombre] = {
        elemento: campo,
        valor: valor,
        vacio: vacio,
        tipo: campo.type || campo.tagName,
        visible: campo.offsetParent !== null,
        disabled: campo.disabled
      };

      const estado = vacio ? '❌ VACÍO' : '✅ CON VALOR';
      console.log(`  ${estado} - ${nombre}: ${valor.substring(0, 30)}`);
    }
  });

  // 4. Buscar el botón Guardar y su estado
  console.log('\n🔘 ESTADO DEL BOTÓN GUARDAR:');
  const botones = Array.from(document.querySelectorAll('button'));
  const botonGuardar = botones.find(b => {
    const texto = b.textContent.toLowerCase();
    return texto.includes('guardar') || texto.includes('save');
  });

  if (botonGuardar) {
    console.log(`  - Encontrado: ✅`);
    console.log(`  - Texto: "${botonGuardar.textContent.trim()}"`);
    console.log(`  - Deshabilitado: ${botonGuardar.disabled ? '❌ SÍ' : '✅ NO'}`);
    console.log(`  - Visible: ${botonGuardar.offsetParent !== null ? '✅ SÍ' : '❌ NO'}`);
    console.log(`  - Opacity: ${window.getComputedStyle(botonGuardar).opacity}`);
    console.log(`  - Pointer-events: ${window.getComputedStyle(botonGuardar).pointerEvents}`);
    console.log(`  - Cursor: ${window.getComputedStyle(botonGuardar).cursor}`);

    // Intentar encontrar el estado de validación en React
    const reactKey = Object.keys(botonGuardar).find(key =>
      key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')
    );

    if (reactKey) {
      console.log(`  - Componente React: ✅ Encontrado`);
      try {
        const fiber = botonGuardar[reactKey];
        if (fiber && fiber.memoizedProps) {
          console.log(`  - Props onClick: ${fiber.memoizedProps.onClick ? '✅ Presente' : '❌ Ausente'}`);
          console.log(`  - Props disabled: ${fiber.memoizedProps.disabled}`);
        }
      } catch (e) {
        console.log(`  - No se pudo acceder a props de React`);
      }
    }
  } else {
    console.log(`  - ❌ No encontrado`);
  }

  // 5. Buscar mensajes de error o validación
  console.log('\n⚠️ MENSAJES DE VALIDACIÓN:');
  const mensajesError = document.querySelectorAll(
    '[role="alert"], .error, .text-red, [class*="error"], [class*="Error"], [class*="invalid"]'
  );

  if (mensajesError.length > 0) {
    mensajesError.forEach((msg, i) => {
      const texto = msg.textContent.trim();
      if (texto) {
        console.log(`  ${i + 1}. ${texto}`);
      }
    });
  } else {
    console.log('  ✅ No hay mensajes de error visibles');
  }

  // 6. Resumen final
  console.log('\n' + '='.repeat(60));
  console.log('📋 RESUMEN FINAL:');
  console.log(`  - Campos encontrados: ${Object.keys(camposEncontrados).length}`);
  console.log(`  - Campos vacíos: ${Object.values(camposEncontrados).filter(c => c.vacio).length}`);
  console.log(`  - Campos con valor: ${Object.values(camposEncontrados).filter(c => !c.vacio).length}`);
  console.log(`  - Botón Guardar: ${botonGuardar ? (botonGuardar.disabled ? '❌ DESHABILITADO' : '✅ HABILITADO') : '❌ NO ENCONTRADO'}`);

  return {
    campos: camposEncontrados,
    botonHabilitado: botonGuardar ? !botonGuardar.disabled : false,
    totalCampos: Object.keys(camposEncontrados).length
  };
})();

