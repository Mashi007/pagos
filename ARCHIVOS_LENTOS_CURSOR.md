# Archivos que hacen lento a Cursor

Son los **archivos con más de 1500 líneas**. Cursor los indexa y analiza, y eso puede ralentizar el IDE.

---

## Los 8 más pesados (>1500 líneas)

| Archivo | Líneas |
|---------|--------|
| `frontend/src/components/configuracion/FineTuningTab.tsx` | 2035 |
| `frontend/src/components/configuracion/AIConfig.tsx` | 1723 |
| `frontend/src/components/clientes/ExcelUploader.tsx` | 1768 |
| `frontend/src/components/prestamos/EvaluacionRiesgoForm.tsx` | 1758 |
| `frontend/src/pages/Configuracion.tsx` | 1615 |
| `frontend/src/components/clientes/CrearClienteForm.tsx` | 1612 |
| `frontend/src/pages/DashboardMenu.tsx` | 1520 |
| `frontend/src/pages/Cobranzas.tsx` | 1514 |

---

## Cómo reducir la lentitud

**Opción A – Añadir a `.cursorignore`**  
Pega al final de `.cursorignore` estas líneas (Cursor dejará de indexarlos; el índice irá más rápido, pero en esos archivos tendrás menos ayuda de Cursor):

```
# Archivos muy grandes (>1500 líneas) - reducen lentitud de Cursor
frontend/src/components/configuracion/FineTuningTab.tsx
frontend/src/components/configuracion/AIConfig.tsx
frontend/src/components/clientes/ExcelUploader.tsx
frontend/src/components/prestamos/EvaluacionRiesgoForm.tsx
frontend/src/pages/Configuracion.tsx
frontend/src/components/clientes/CrearClienteForm.tsx
frontend/src/pages/DashboardMenu.tsx
frontend/src/pages/Cobranzas.tsx
```

**Opción B – Refactorizar**  
Dividir cada archivo en componentes más pequeños (~300–500 líneas). Así Cursor sigue indexando todo y además el código será más fácil de mantener.
