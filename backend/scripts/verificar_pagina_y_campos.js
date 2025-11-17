// ============================================
// VERIFICAR PÁGINA Y BUSCAR CAMPOS DE MANERA MÁS AMPLIA
// ============================================

(() => {
  console.log('🔍 VERIFICACIÓN COMPLETA DE LA PÁGINA\n');
  console.log('='.repeat(60));

  // 1. Verificar URL y título
  console.log('\n📍 INFORMACIÓN DE LA PÁGINA:');
  console.log(`   URL: ${window.location.href}`);
  console.log(`   Título: ${document.title}`);
  console.log(`   Pathname: ${window.location.pathname}`);

  // 2. Buscar texto que indique que estamos en la página de configuración de email
  const textoConfiguracion = document.body.textContent || '';
  const tieneEmail = textoConfiguracion.includes('Configuración de Email') ||
                     textoConfiguracion.includes('SMTP') ||
                     textoConfiguracion.includes('Gmail');

  console.log(`   ¿Contiene texto de email?: ${tieneEmail ? '✅ SÍ' : '❌ NO'}`);

  // 3. Buscar TODOS los inputs sin filtros
  const todosLosInputs = Array.from(document.querySelectorAll('input, textarea'));
  console.log(`\n📊 TOTAL DE INPUTS EN LA PÁGINA: ${todosLosInputs.length}`);

  if (todosLosInputs.length > 0) {
    console.log('\n📝 PRIMEROS 10 INPUTS ENCONTRADOS:');
    todosLosInputs.slice(0, 10).forEach((input, i) => {
      const tipo = input.type || input.tagName.toLowerCase();
      const valor = tipo === 'password' ? '***' : (input.value || '(vacío)');
      const placeholder = input.placeholder || '(sin placeholder)';
      const visible = input.offsetParent !== null;

      console.log(`   ${i + 1}. Tipo: ${tipo}, Valor: ${valor.substring(0, 30)}, Placeholder: ${placeholder.substring(0, 30)}, Visible: ${visible ? '✅' : '❌'}`);
    });
  }

  // 4. Buscar por texto en la página que indique campos específicos
  console.log('\n🔎 BUSCANDO TEXTOS ESPECÍFICOS EN LA PÁGINA:');
  const textosBuscar = [
    'Servidor SMTP',
    'Puerto SMTP',
    'Email (Usuario',
    'Contraseña de Aplicación',
    'Email del Remitente',
    'Nombre del Remitente',
    'Usar TLS',
    'Guardar Configuración'
  ];

  textosBuscar.forEach(texto => {
    const encontrado = textoConfiguracion.includes(texto);
    console.log(`   ${texto}: ${encontrado ? '✅ ENCONTRADO' : '❌ NO ENCONTRADO'}`);
  });

  // 5. Buscar TODOS los botones
  const todosLosBotones = Array.from(document.querySelectorAll('button'));
  console.log(`\n🔘 TOTAL DE BOTONES: ${todosLosBotones.length}`);

  if (todosLosBotones.length > 0) {
    console.log('\n📝 TODOS LOS BOTONES ENCONTRADOS:');
    todosLosBotones.forEach((btn, i) => {
      const texto = btn.textContent.trim();
      const visible = btn.offsetParent !== null;
      const disabled = btn.disabled;
      console.log(`   ${i + 1}. "${texto}" - Visible: ${visible ? '✅' : '❌'}, Disabled: ${disabled ? '❌' : '✅'}`);
    });
  }

  // 6. Buscar elementos que contengan "smtp" o "email" en cualquier atributo
  console.log('\n🔎 BUSCANDO ELEMENTOS CON "smtp" O "email" EN ATRIBUTOS:');
  const elementosConSMTP = Array.from(document.querySelectorAll('[class*="smtp"], [id*="smtp"], [name*="smtp"], [placeholder*="smtp"]'));
  const elementosConEmail = Array.from(document.querySelectorAll('[class*="email"], [id*="email"], [name*="email"], [placeholder*="email"]'));

  console.log(`   Elementos con "smtp": ${elementosConSMTP.length}`);
  console.log(`   Elementos con "email": ${elementosConEmail.length}`);

  // 7. Verificar si hay iframes o shadow DOM
  const iframes = document.querySelectorAll('iframe');
  console.log(`\n🖼️ IFRAMES ENCONTRADOS: ${iframes.length}`);

  // 8. Buscar el componente React directamente por su estructura
  console.log('\n⚛️ BUSCANDO COMPONENTE REACT:');
  const elementosConReact = Array.from(document.querySelectorAll('[data-reactroot], [data-react], [class*="react"]'));
  console.log(`   Elementos con indicadores de React: ${elementosConReact.length}`);

  // 9. Intentar encontrar el formulario o card de configuración
  const cards = Array.from(document.querySelectorAll('[class*="card"], [class*="Card"], [class*="form"], [class*="Form"]'));
  console.log(`\n📦 CARDS/FORMS ENCONTRADOS: ${cards.length}`);

  if (cards.length > 0) {
    console.log('\n📝 PRIMEROS 5 CARDS/FORMS:');
    cards.slice(0, 5).forEach((card, i) => {
      const texto = card.textContent?.substring(0, 100) || '';
      console.log(`   ${i + 1}. Texto: "${texto}..."`);
    });
  }

  console.log('\n' + '='.repeat(60));
  console.log('📋 RESUMEN:');
  console.log(`   Inputs totales: ${todosLosInputs.length}`);
  console.log(`   Botones totales: ${todosLosBotones.length}`);
  console.log(`   ¿Página de email?: ${tieneEmail ? '✅ Probablemente' : '❌ No parece'}`);
  console.log(`   ¿Componente renderizado?: ${todosLosInputs.length > 0 ? '✅ Posiblemente' : '❌ No'}`);

  return {
    inputs: todosLosInputs.length,
    botones: todosLosBotones.length,
    esPaginaEmail: tieneEmail,
    componenteRenderizado: todosLosInputs.length > 0
  };
})();

