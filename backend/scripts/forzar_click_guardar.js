// ============================================
// FORZAR CLICK EN BOTÓN GUARDAR
// Ejecutar en la consola del navegador
// ============================================

(() => {
  // Buscar el botón
  const buttons = Array.from(document.querySelectorAll('button'));
  const guardarButton = buttons.find(b => 
    b.textContent.includes('Guardar') || 
    b.textContent.includes('guardar')
  );
  
  if (guardarButton) {
    console.log('✅ Botón encontrado');
    
    // Habilitar el botón
    guardarButton.disabled = false;
    guardarButton.style.opacity = '1';
    guardarButton.style.cursor = 'pointer';
    guardarButton.style.pointerEvents = 'auto';
    
    // Forzar el click directamente
    console.log('🖱️ Forzando click en el botón...');
    
    // Crear un evento de click y dispararlo
    const clickEvent = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      view: window
    });
    
    guardarButton.dispatchEvent(clickEvent);
    
    console.log('✅ Click disparado');
    
    // También intentar hacer click programáticamente
    setTimeout(() => {
      guardarButton.click();
      console.log('✅ Click ejecutado también con .click()');
    }, 100);
    
  } else {
    console.log('❌ No se encontró el botón');
  }
})();

