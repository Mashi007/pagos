@echo off
echo === SEGUNDO ENFOQUE DE VALIDACION Y RESOLUCION ===
echo.

echo 1. VERIFICACION CONECTIVIDAD BASICA:
curl -s -o nul -w "Status: %%{http_code}\n" https://pagos-f2qf.onrender.com/
if %errorlevel% equ 0 (
    echo    ✅ Servidor respondiendo
) else (
    echo    ❌ Servidor con problemas
)

echo.
echo 2. VERIFICACION ENDPOINT DE AUTH:
curl -s -X POST -H "Content-Type: application/json" -d "{\"email\":\"itmaster@rapicreditca.com\",\"password\":\"R@pi_2025**\"}" https://pagos-f2qf.onrender.com/api/v1/auth/login
echo.

echo 3. VERIFICACION OTROS ENDPOINTS:
echo    Clientes:
curl -s -o nul -w "Status: %%{http_code}\n" https://pagos-f2qf.onrender.com/api/v1/clientes/ping

echo    Validadores:
curl -s -o nul -w "Status: %%{http_code}\n" https://pagos-f2qf.onrender.com/api/v1/validadores/ping

echo    Usuarios:
curl -s -o nul -w "Status: %%{http_code}\n" https://pagos-f2qf.onrender.com/api/v1/usuarios/

echo    Conteo clientes:
curl -s -o nul -w "Status: %%{http_code}\n" https://pagos-f2qf.onrender.com/api/v1/clientes/count

echo.
echo 4. VERIFICACION CONFIGURACION:
curl -s -o nul -w "Status: %%{http_code}\n" https://pagos-f2qf.onrender.com/api/v1/clientes/opciones-configuracion

echo.
echo === CONCLUSIONES DEL SEGUNDO ENFOQUE ===
echo ✅ Si el login es exitoso (200), el problema esta resuelto.
echo ❌ Si el login da 503, el problema persiste.
echo ⚠️ Si el login da 401, las credenciales son incorrectas.
echo ✅ Si otros endpoints funcionan, el sistema esta operativo.
