# 🧪 Prueba de Conexión Real con Gmail

Este directorio contiene scripts para demostrar que el sistema se conecta **REALMENTE** a los servidores de Google.

## 📋 ¿Qué hacen estos scripts?

Estos scripts prueban la conexión SMTP real con Gmail/Google Workspace para verificar que:
1. El sistema **SÍ se conecta** a los servidores de Google
2. Google **SÍ verifica** las credenciales
3. Google **SÍ responde** si acepta o rechaza

## 🚀 Cómo usar

### Opción 1: Script Interactivo (Recomendado)

```bash
cd backend
python test_gmail_connection.py
```

El script te pedirá:
- Email (Usuario Gmail / Google Workspace)
- Contraseña de Aplicación (no se mostrará en pantalla)

### Opción 2: Script con Argumentos

El script también puede recibir argumentos desde la línea de comandos (ver código fuente para más detalles).

## 📊 Qué verás

### Si Google ACEPTA:
```
✅ Conexión TCP establecida
✅ TLS iniciado
✅ Google ACEPTÓ las credenciales
✅ Conexión cerrada

✅ ÉXITO: Google aceptó la conexión
```

### Si Google RECHAZA:
```
✅ Conexión TCP establecida
✅ TLS iniciado
❌ Google RECHAZÓ: [535 5.7.8 Username and Password not accepted]

Esto demuestra que SÍ se conectó a Google
(Google rechazó porque las credenciales son incorrectas)
```

### Si NO hay internet:
```
❌ Error: [Errno 11001] getaddrinfo failed

Esto demuestra que SÍ intentó conectarse a Google
(No hay conexión a internet)
```

## 🔍 ¿Por qué esto demuestra que es real?

1. **Conexión TCP**: `smtplib.SMTP()` abre un socket real a `smtp.gmail.com:587`
2. **TLS**: `server.starttls()` establece cifrado real con Google
3. **Autenticación**: `server.login()` envía credenciales reales a Google
4. **Respuesta de Google**: Los errores `SMTPAuthenticationError` solo ocurren cuando Google responde

## ⚠️ Requisitos

- Python 3.7+
- Conexión a internet
- Credenciales válidas de Gmail/Google Workspace:
  - Email con 2FA activado
  - Contraseña de Aplicación (App Password) de 16 caracteres

## 📝 Notas

- La contraseña de aplicación NO es tu contraseña normal de Gmail
- Para obtener una App Password:
  - Gmail: https://myaccount.google.com/apppasswords
  - Google Workspace: https://myaccount.google.com/apppasswords (si está habilitado)
- El script NO envía emails, solo prueba la conexión y autenticación

