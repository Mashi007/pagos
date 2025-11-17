// ============================================
// BUSCAR DIRECTAMENTE EL INPUT DE "Email del Remitente"
// ============================================

(() => {
  console.log('🔍 BUSCANDO "Email del Remitente"\n');

  // Buscar todos los elementos que contengan "Remitente"
  const todosLosElementos = Array.from(document.querySelectorAll('*'));
  let inputRemitente = null;

  todosLosElementos.forEach(elem => {
    const texto = elem.textContent || '';
    if (texto.includes('Email del Remitente') ||
        (texto.includes('Remitente') && texto.includes('Email'))) {

      console.log('✅ Encontrado texto "Remitente"');
      console.log(`   Elemento: ${elem.tagName}, Texto: "${texto.substring(0, 100)}"`);

      // Buscar el input más cercano
      // 1. Buscar en el mismo contenedor
      const contenedor = elem.closest('div');
      if (contenedor) {
        const input = contenedor.querySelector('input[type="email"]');
        if (input) {
          inputRemitente = input;
          console.log('   → Input encontrado en el mismo contenedor');
        }
      }

      // 2. Buscar en el siguiente hermano
      if (!inputRemitente) {
        let siguiente = elem.nextElementSibling;
        let intentos = 0;
        while (siguiente && intentos < 5) {
          const input = siguiente.querySelector('input[type="email"]');
          if (input) {
            inputRemitente = input;
            console.log('   → Input encontrado en siguiente hermano');
            break;
          }
          siguiente = siguiente.nextElementSibling;
          intentos++;
        }
      }

      // 3. Buscar en el padre
      if (!inputRemitente) {
        let padre = elem.parentElement;
        let intentos = 0;
        while (padre && intentos < 3) {
          const input = padre.querySelector('input[type="email"]');
          if (input) {
            inputRemitente = input;
            console.log('   → Input encontrado en padre');
            break;
          }
          padre = padre.parentElement;
          intentos++;
        }
      }
    }
  });

  if (inputRemitente) {
    const valor = inputRemitente.value || '';
    console.log(`\n✅ Input de Remitente encontrado:`);
    console.log(`   Valor actual: "${valor}"`);

    if (!valor || valor.trim() === '') {
      console.log(`\n❌ ESTÁ VACÍO - Llenando automáticamente...`);

      // Llenar el campo
      inputRemitente.value = 'pafo.kampei@gmail.com';

      // Disparar TODOS los eventos posibles para React
      const eventos = ['input', 'change', 'blur', 'keyup'];
      eventos.forEach(tipo => {
        const evento = new Event(tipo, { bubbles: true, cancelable: true });
        inputRemitente.dispatchEvent(evento);
      });

      // También intentar con InputEvent
      try {
        const inputEvent = new InputEvent('input', {
          bubbles: true,
          cancelable: true,
          inputType: 'insertText',
          data: 'pafo.kampei@gmail.com'
        });
        inputRemitente.dispatchEvent(inputEvent);
      } catch (e) {
        // InputEvent puede no estar disponible en todos los navegadores
      }

      // Hacer foco y scroll
      inputRemitente.focus();
      inputRemitente.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Seleccionar el texto para que el usuario vea que se llenó
      inputRemitente.select();

      console.log(`✅ Campo llenado con: pafo.kampei@gmail.com`);
      console.log(`✅ Eventos disparados`);
      console.log(`\n💡 Verifica si el botón "Guardar" se habilitó.`);
      console.log(`   Si no, intenta hacer clic en el campo y presionar Tab.`);
    } else {
      console.log(`\n✅ Ya tiene valor: "${valor}"`);
      console.log(`\n⚠️ Si el botón sigue deshabilitado, puede haber otro problema.`);
    }
  } else {
    console.log(`\n❌ No se encontró el input de "Email del Remitente"`);
    console.log(`\n💡 Intenta buscar manualmente el campo en la página.`);
    console.log(`   Debería estar después del campo "Email (Usuario Gmail / Google Workspace)"`);
  }

  return { inputRemitente, valor: inputRemitente?.value || '' };
})();

