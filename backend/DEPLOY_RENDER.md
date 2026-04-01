# 🚀 Deploy en Render - Pasos Rápidos

## El código se actualizó para que cedula sea opcional

El error 500 era porque el código esperaba `cedula` pero tu tabla no la tenía.

**Ya lo corregí**, ahora necesitas hacer deploy en Render.

---

## ✅ Opción 1: Deploy Automático (Recomendado)

Si Render está configurado con GitHub (que creo que sí):

1. El commit ya está en GitHub
2. Ve a: **Render Dashboard → Pagos Service**
3. Espera a que detecte el nuevo commit
4. O presiona **Manual Deploy** si quieres ahora mismo

---

## ✅ Opción 2: Push Manual

Si no está conectado automáticamente:

```bash
cd c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos
git push origin main
```

Luego ve a Render y presiona **Manual Deploy**.

---

## ⏳ Esperar a que compile

El deploy toma ~2-3 minutos:
- Descarga código
- Instala dependencias
- Compila
- Reinicia servicio

---

## ✅ Verificar que funcionó

Una vez termine:

1. Ve a: `https://pagos-f2qf.onrender.com/pagos/login`
2. Ingresa:
   - Email: `itmaster@rapicreditca.com`
   - Password: (la que corresponde al hash)
3. ¡Debe funcionar ahora! 🚀

---

## 📝 Qué se corrigió

- ✅ Modelo `User` ahora tiene `cedula` como opcional
- ✅ `user_to_response()` usa `getattr()` para cedula
- ✅ Schema `UserResponse` tiene cedula como `Optional`

---

## 🆘 Si aún da error 500

Revisa los **logs de Render**:
1. Render Dashboard → Pagos Service
2. Logs tab
3. Busca el error

O avísame y voy a revisar.

---

¿Ya hiciste el deploy?
