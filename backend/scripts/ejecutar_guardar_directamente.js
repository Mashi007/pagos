// ============================================
// EJECUTAR GUARDAR DIRECTAMENTE
// Este código intenta ejecutar la función de guardar
// incluso si el botón está deshabilitado
// ============================================

(() => {
  console.log('🔍 Buscando componente React...');
  
  // Método 1: Buscar el botón y forzar su ejecución
  const buttons = Array.from(document.querySelectorAll('button'));
  const guardarButton = buttons.find(b => b.textContent.includes('Guardar'));
  
  if (guardarButton) {
    console.log('✅ Botón encontrado');
    
    // Remover completamente la restricción disabled
    guardarButton.removeAttribute('disabled');
    guardarButton.disabled = false;
    guardarButton.style.opacity = '1';
    guardarButton.style.cursor = 'pointer';
    guardarButton.style.pointerEvents = 'auto';
    
    // Intentar encontrar el componente React
    const reactKey = Object.keys(guardarButton).find(key => 
      key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')
    );
    
    if (reactKey) {
      console.log('✅ Componente React encontrado');
      const reactInstance = guardarButton[reactKey];
      
      // Intentar encontrar el handler
      if (reactInstance && reactInstance.memoizedProps) {
        const onClick = reactInstance.memoizedProps.onClick;
        if (onClick) {
          console.log('✅ Handler onClick encontrado, ejecutando...');
          try {
            onClick({ preventDefault: () => {}, stopPropagation: () => {} });
            console.log('✅ Handler ejecutado');
            return;
          } catch (e) {
            console.error('❌ Error ejecutando handler:', e);
          }
        }
      }
    }
    
    // Método 2: Forzar click múltiples veces
    console.log('🖱️ Intentando click forzado...');
    guardarButton.click();
    
    // Método 3: Disparar evento de click completo
    const clickEvent = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      view: window,
      detail: 1
    });
    guardarButton.dispatchEvent(clickEvent);
    
    // Método 4: Disparar eventos mousedown y mouseup también
    const mouseDownEvent = new MouseEvent('mousedown', { bubbles: true, cancelable: true });
    const mouseUpEvent = new MouseEvent('mouseup', { bubbles: true, cancelable: true });
    guardarButton.dispatchEvent(mouseDownEvent);
    guardarButton.dispatchEvent(mouseUpEvent);
    guardarButton.dispatchEvent(clickEvent);
    
    console.log('✅ Eventos disparados');
    
  } else {
    console.log('❌ No se encontró el botón');
  }
})();

