// ============================================
// FORZAR ACTUALIZACIÓN DEL ESTADO DE REACT
// Para habilitar el botón Guardar
// ============================================

(() => {
  console.log('🔧 FORZANDO ACTUALIZACIÓN DE REACT\n');

  // Buscar todos los inputs y disparar eventos de cambio
  const inputs = Array.from(document.querySelectorAll('input, textarea'))
    .filter(inp => inp.offsetParent !== null);

  console.log(`📊 Disparando eventos en ${inputs.length} inputs...\n`);

  inputs.forEach((inp, i) => {
    const tipo = inp.type || 'text';
    const valor = inp.value || '';

    if (valor && valor.trim() !== '') {
      // Disparar múltiples eventos para asegurar que React los detecte
      const eventos = ['input', 'change', 'blur'];

      eventos.forEach(tipoEvento => {
        const evento = new Event(tipoEvento, {
          bubbles: true,
          cancelable: true
        });
        inp.dispatchEvent(evento);
      });

      // También intentar con InputEvent
      try {
        const inputEvent = new InputEvent('input', {
          bubbles: true,
          cancelable: true,
          inputType: 'insertText',
          data: valor
        });
        inp.dispatchEvent(inputEvent);
      } catch (e) {
        // Ignorar si InputEvent no está disponible
      }

      console.log(`✅ Eventos disparados en input #${i + 1} (${tipo})`);
    }
  });

  // Buscar checkboxes y disparar eventos
  const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
  checkboxes.forEach(cb => {
    const evento = new Event('change', { bubbles: true, cancelable: true });
    cb.dispatchEvent(evento);
    console.log(`✅ Evento disparado en checkbox`);
  });

  // Esperar un momento y verificar el botón
  setTimeout(() => {
    const botonGuardar = Array.from(document.querySelectorAll('button')).find(
      b => b.textContent.includes('Guardar')
    );

    if (botonGuardar) {
      const habilitado = !botonGuardar.disabled;
      console.log(`\n🔘 Estado del botón Guardar: ${habilitado ? '✅ HABILITADO' : '❌ DESHABILITADO'}`);

      if (!habilitado) {
        console.log(`\n⚠️ El botón sigue deshabilitado.`);
        console.log(`\n💡 Intentando forzar habilitación...`);

        // Intentar habilitar manualmente
        botonGuardar.disabled = false;
        botonGuardar.removeAttribute('disabled');
        botonGuardar.style.opacity = '1';
        botonGuardar.style.cursor = 'pointer';
        botonGuardar.style.pointerEvents = 'auto';

        console.log(`✅ Botón habilitado manualmente`);
        console.log(`\n⚠️ Esto es temporal. Intenta hacer clic en el botón ahora.`);
        console.log(`   Si funciona, el problema es de validación en React.`);
        console.log(`   Si no funciona, puede haber un problema con el handler onClick.`);
      } else {
        console.log(`\n✅ ¡El botón se habilitó correctamente!`);
      }
    }
  }, 500);

  console.log(`\n⏳ Esperando 500ms para verificar el botón...`);

  return { inputs: inputs.length, checkboxes: checkboxes.length };
})();

