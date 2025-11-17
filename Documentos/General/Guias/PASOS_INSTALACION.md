# 📋 PASOS DE INSTALACIÓN - Ejecuta Uno por Uno

## ✅ Paso 1: Cambiar al directorio frontend

En tu terminal, ejecuta:

```bash
cd frontend
```

**Resultado esperado**: No debería mostrar error, simplemente cambia el directorio.

---

## ✅ Paso 2: Instalar dependencias

Ejecuta:

```bash
npm install
```

**Resultado esperado**:
- Debería mostrar "added X packages"
- Toma unos minutos (descarga librerías)
- Al final dice "added X packages, and audited X packages in Xs"

---

## ✅ Paso 3: Verificar instalación

Ejecuta:

```bash
npm list jspdf jspdf-autotable
```

**Resultado esperado**:
```
frontend@x.x.x
├── jspdf@2.5.1
└── jspdf-autotable@3.8.3
```

---

## ✅ Paso 4: Reiniciar servidor de desarrollo

Ejecuta:

```bash
npm run dev
```

**Resultado esperado**:
- Inicia el servidor en `http://localhost:5173` (o similar)
- Muestra "Local: http://localhost:5173"

---

## 🎯 Después de esto:

¡Todo listo! Las funciones de exportación Excel y PDF estarán disponibles.

