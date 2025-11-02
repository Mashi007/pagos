# 🔀 Explicación: Sub-rutas vs Modales

## 📍 SUB-RUTAS (URLs diferentes)

**¿Qué son?**
- Cada vista detallada tiene su propia URL única
- Al hacer clic en un botón, cambias completamente de página
- La barra de direcciones muestra la nueva ruta

**Ejemplo:**
```
Usuario está en: /dashboard/financiamiento
Click en "Ver Financiamientos Activos"
Navega a: /dashboard/financiamiento/activos
```

**Ventajas:**
✅ Puedes compartir el enlace directo a una vista específica
✅ Puedes usar "Atrás" del navegador para volver
✅ Puedes marcar como favorito una vista específica
✅ Más fácil de implementar (cada página es independiente)
✅ Mejor para SEO y navegación avanzada

**Desventajas:**
❌ Pierdes el contexto de la página anterior
❌ Tienes que cargar todo de nuevo

**Código ejemplo:**
```tsx
// En DashboardFinanciamiento.tsx
<Button onClick={() => navigate('/dashboard/financiamiento/activos')}>
  Ver Financiamientos Activos
</Button>

// Nueva página: DashboardFinanciamientoActivos.tsx
export function DashboardFinanciamientoActivos() {
  // Contenido detallado aquí
}
```

---

## 🪟 MODALES (Ventanas flotantes)

**¿Qué son?**
- Al hacer clic, se abre una ventana flotante (modal) SOBRE la página actual
- La página original sigue visible en el fondo (a veces con overlay oscuro)
- No cambia la URL

**Ejemplo:**
```
Usuario está en: /dashboard/financiamiento
Click en "Ver Financiamientos Activos"
Se abre un modal encima de la página
URL sigue siendo: /dashboard/financiamiento
```

**Ventajas:**
✅ No pierdes el contexto de la página principal
✅ Puedes ver la información detallada mientras mantienes la vista general
✅ Transición más rápida (solo cargas el contenido del modal)
✅ Sensación de "no salir" de la página

**Desventajas:**
❌ No puedes compartir un enlace directo a esa vista
❌ Si cierras el modal, pierdes lo que estabas viendo
❌ Puede ser más complejo de implementar
❌ No funciona bien con el botón "Atrás" del navegador

**Código ejemplo:**
```tsx
// En DashboardFinanciamiento.tsx
const [isModalOpen, setIsModalOpen] = useState(false)

<Button onClick={() => setIsModalOpen(true)}>
  Ver Financiamientos Activos
</Button>

{isModalOpen && (
  <Modal>
    {/* Contenido detallado aquí */}
    <Button onClick={() => setIsModalOpen(false)}>Cerrar</Button>
  </Modal>
)}
```

---

## 🤔 ¿CUÁL ELEGIR?

**Para este proyecto, RECOMIENDO: SUB-RUTAS**
- Es más profesional y escalable
- Más fácil de implementar
- Permite mejor organización del código
- Los usuarios pueden compartir links específicos
- Es más común en aplicaciones empresariales

**Los modales son mejores para:**
- Información muy breve (confirmaciones, detalles pequeños)
- Cuando necesitas mantener el contexto visual constantemente
- Aplicaciones más simples

---

## 📊 VISUALIZACIÓN

**SUB-RUTAS:**
```
Página 1: /dashboard/financiamiento
    ↓ (click)
Página 2: /dashboard/financiamiento/activos
    ↓ (botón atrás)
Página 1: /dashboard/financiamiento
```

**MODALES:**
```
Página: /dashboard/financiamiento
    ↓ (click)
[Modal se abre encima]
    ↓ (cerrar)
Página: /dashboard/financiamiento (siempre la misma)
```

