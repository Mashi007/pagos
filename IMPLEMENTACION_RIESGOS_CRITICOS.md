# 🔧 IMPLEMENTACIÓN RECOMENDADA: PRIMERAS MEJORAS CRÍTICAS

**Fecha:** 20 de Marzo, 2026  
**Enfoque:** Soluciones técnicas específicas para los riesgos críticos identificados

---

## 1️⃣ VALIDACIÓN EXPLÍCITA DE TASA DE CAMBIO

### Problema
Cuando se intenta registrar un pago en Bolívares pero no hay tasa ingresada, el sistema falla sin mensaje claro.

### Solución Recomendada

#### Step 1: Crear endpoint de verificación

```python
# backend/app/api/v1/endpoints/admin_tasas_cambio.py

@router.get("/validar-para-pago")
def validar_tasa_para_pago(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Verifica si el sistema puede procesar pagos en Bolívares hoy.
    Usado antes de procesar pagos.
    """
    tasa = obtener_tasa_hoy(db)
    
    return {
        "puede_procesar_bs": tasa is not None,
        "tasa_actual": float(tasa.tasa_oficial) if tasa else None,
        "fecha_tasa": tasa.fecha.isoformat() if tasa else None,
        "mensaje": (
            "Listo para procesar pagos en Bolívares" 
            if tasa 
            else "⚠️ ALERTA: Tasa de cambio no ingresada. "
                 "Pagos en Bolívares serán rechazados. "
                 "Contacte a administración."
        ),
        "accion": (
            "PROCEDER" 
            if tasa 
            else "CONTACTAR_ADMIN"
        )
    }
```

#### Step 2: Usar en pagos_service.py

```python
# backend/app/services/cobros/pagos_service.py

def procesar_pago_bs(
    db: Session,
    cliente_id: int,
    monto_bs: float,
    prestamo_id: int
) -> dict:
    """
    Procesa pago en Bolívares con conversión a USD.
    """
    # 1. Verificar tasa ANTES de procesar
    from app.services.tasa_cambio_service import obtener_tasa_hoy
    from fastapi import HTTPException
    
    tasa = obtener_tasa_hoy(db)
    if not tasa:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "TASA_NO_INGRESADA",
                "mensaje": "No se puede procesar pago en Bolívares. "
                          "Tasa de cambio oficial no ingresada hoy. "
                          "Use USD o contacte administración.",
                "acciones": [
                    "Cambiar a USD",
                    "Contactar administrador",
                    "Reintentar más tarde"
                ]
            }
        )
    
    # 2. Convertir
    try:
        monto_usd = convertir_bs_a_usd(monto_bs, tasa.tasa_oficial)
    except ValueError as e:
        logger.error(f"Error en conversión: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # 3. Procesar normalmente
    # ... resto del código
    
    return {
        "exito": True,
        "monto_bs": monto_bs,
        "monto_usd": monto_usd,
        "tasa_usada": float(tasa.tasa_oficial),
        "fecha_tasa": tasa.fecha.isoformat()
    }
```

#### Step 3: Frontend - Mostrar alerta antes de pagar

```typescript
// frontend/src/components/pagos/FormPagoBs.tsx

import { useMutation, useQuery } from '@tanstack/react-query'
import { tasaCambioService } from '../../services/tasaCambioService'
import { Alert, AlertDescription, AlertTitle } from '../ui/alert'
import { AlertTriangle, CheckCircle } from 'lucide-react'

export function FormPagoBs() {
    const { data: validacion, isLoading } = useQuery({
        queryKey: ['validar-tasa-pago'],
        queryFn: () => tasaCambioService.validarParaPago(),
        refetchInterval: 60000, // Cada minuto
    })
    
    if (isLoading) return <div>Verificando...</div>
    
    if (!validacion?.puede_procesar_bs) {
        return (
            <Alert variant="destructive" className="mb-4">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>No se puede procesar pagos en Bolívares</AlertTitle>
                <AlertDescription className="mt-2">
                    <p>{validacion?.mensaje}</p>
                    <p className="mt-2 text-sm">
                        Se recomienda usar USD o contactar a administración.
                    </p>
                </AlertDescription>
            </Alert>
        )
    }
    
    return (
        <div>
            <Alert className="mb-4">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertTitle>Tasa de cambio lista</AlertTitle>
                <AlertDescription>
                    Tasa actual: <strong>{validacion?.tasa_actual} Bs/USD</strong>
                </AlertDescription>
            </Alert>
            
            {/* Formulario de pago */}
            <FormaPago />
        </div>
    )
}
```

---

## 2️⃣ VALIDACIÓN DE EMAILS

### Problema
Se envían notificaciones a direcciones de email inválidas.

### Solución

#### Step 1: Función de validación

```python
# backend/app/utils/validators.py

import re
from typing import Tuple

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def es_email_valido(email: str) -> bool:
    """Valida formato de email"""
    if not email or not isinstance(email, str):
        return False
    
    email = email.strip().lower()
    
    # Validar longitud
    if len(email) < 5 or len(email) > 254:
        return False
    
    # Validar formato
    if not re.match(EMAIL_REGEX, email):
        return False
    
    # Evitar dominios sospechosos
    dominios_bloqueados = ['localhost', '127.0.0.1', 'example.com', 'test.com']
    dominio = email.split('@')[1]
    if dominio in dominios_bloqueados:
        return False
    
    return True

def limpiar_email(email: str) -> Tuple[str, bool]:
    """Limpia y valida email. Retorna (email_limpio, es_valido)"""
    if not email:
        return None, False
    
    email = email.strip().lower()
    if es_email_valido(email):
        return email, True
    
    return email, False
```

#### Step 2: Comando para limpiar base de datos

```python
# backend/scripts/limpiar_emails.py

import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.cliente import Cliente
from app.utils.validators import es_email_valido

def limpiar_emails():
    """Marca emails inválidos en la BD"""
    db: Session = SessionLocal()
    
    try:
        clientes = db.query(Cliente).all()
        inválidos = []
        
        for cliente in clientes:
            if cliente.email and not es_email_valido(cliente.email):
                inválidos.append({
                    'id': cliente.id,
                    'email': cliente.email,
                    'razon': 'Formato inválido'
                })
                
                # Marcar como inválido
                cliente.email_valido = False
                # Opcional: limpiar email
                cliente.email = None
        
        db.commit()
        
        print(f"Total clientes: {len(clientes)}")
        print(f"Emails inválidos encontrados: {len(inválidos)}")
        print("\nDetalles:")
        for item in inválidos[:10]:  # Mostrar primeros 10
            print(f"  - Cliente {item['id']}: {item['email']} ({item['razon']})")
        
        if len(inválidos) > 10:
            print(f"  ... y {len(inválidos) - 10} más")
        
        return len(inválidos)
    
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return -1
    
    finally:
        db.close()

if __name__ == '__main__':
    limpiar_emails()
```

#### Step 3: Ejecutar limpieza

```bash
# Ejecutar desde raíz del proyecto backend
python scripts/limpiar_emails.py

# Output esperado:
# Total clientes: 5234
# Emails inválidos encontrados: 87
# Detalles:
#   - Cliente 123: juan@  (Formato inválido)
#   - Cliente 456: None (Formato inválido)
#   ... y 85 más
```

#### Step 4: Validar en endpoint de notificaciones

```python
# backend/app/api/v1/endpoints/notificaciones_tabs.py

from app.utils.validators import es_email_valido

@router.post("/enviar-todas")
def enviar_todas(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Enviar todas las notificaciones con validación de email"""
    
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403)
    
    clientes = get_clientes_retrasados(db)
    
    estadisticas = {
        "total": len(clientes),
        "enviados": 0,
        "fallidos": 0,
        "saltados_sin_email": 0,
        "errores": []
    }
    
    for cliente in clientes:
        # Validar email ANTES de intentar enviar
        if not cliente.email:
            estadisticas["saltados_sin_email"] += 1
            logger.info(f"Saltando {cliente.id}: sin email")
            continue
        
        if not es_email_valido(cliente.email):
            estadisticas["saltados_sin_email"] += 1
            logger.warning(f"Saltando {cliente.id}: email inválido: {cliente.email}")
            continue
        
        # Intentar enviar
        try:
            resultado = enviar_notificacion(cliente, db)
            if resultado:
                estadisticas["enviados"] += 1
            else:
                estadisticas["fallidos"] += 1
        except Exception as e:
            estadisticas["fallidos"] += 1
            estadisticas["errores"].append({
                "cliente_id": cliente.id,
                "error": str(e)
            })
            logger.error(f"Error enviando a {cliente.id}: {e}")
    
    return estadisticas
```

---

## 3️⃣ TRANSACCIONES EN ENVÍO MASIVO

### Problema
Si falla el envío a mitad del lote, BD queda inconsistente (algunos registrados, otros no).

### Solución

```python
# backend/app/api/v1/endpoints/notificaciones_tabs.py

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

@router.post("/enviar-todas-seguro")
def enviar_todas_con_transaccion(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Envío masivo con transacción ACID"""
    
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403)
    
    estadisticas = {
        "total": 0,
        "enviados": 0,
        "fallidos": 0,
        "estado": "INICIADO",
        "error": None,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Iniciar transacción
        db.begin()
        
        clientes = get_clientes_retrasados(db)
        estadisticas["total"] = len(clientes)
        
        for cliente in clientes:
            # Validaciones
            if not cliente.email or not es_email_valido(cliente.email):
                continue
            
            # Enviar
            try:
                resultado = enviar_notificacion(cliente, db)
                
                # Registrar en BD (dentro de transacción)
                registro = EnvioNotificacion(
                    cliente_id=cliente.id,
                    email=cliente.email,
                    exito=resultado,
                    fecha_envio=datetime.now(),
                    error_mensaje=None if resultado else "Email enviado pero no confirmado"
                )
                db.add(registro)
                
                if resultado:
                    estadisticas["enviados"] += 1
                else:
                    estadisticas["fallidos"] += 1
                    
            except Exception as e:
                # Error en envío individual - registrar y continuar
                logger.error(f"Error con {cliente.id}: {e}")
                
                registro = EnvioNotificacion(
                    cliente_id=cliente.id,
                    email=cliente.email,
                    exito=False,
                    fecha_envio=datetime.now(),
                    error_mensaje=str(e)
                )
                db.add(registro)
                estadisticas["fallidos"] += 1
        
        # COMMIT SOLO si todo fue OK
        db.commit()
        estadisticas["estado"] = "COMPLETADO"
        
        logger.info(f"Lote completado: {estadisticas}")
        return estadisticas
    
    except IntegrityError as e:
        # Error de integridad de datos - ROLLBACK todo
        db.rollback()
        logger.error(f"Error de integridad: {e}")
        
        estadisticas["estado"] = "FALLIDO"
        estadisticas["error"] = f"Error de integridad: {str(e)}"
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "FALLO_TRANSACCION",
                "mensaje": "Falló el envío masivo. Los cambios no fueron guardados.",
                "detalles": str(e)
            }
        )
    
    except Exception as e:
        # Otro error - ROLLBACK todo
        db.rollback()
        logger.error(f"Error inesperado: {e}")
        
        estadisticas["estado"] = "FALLIDO"
        estadisticas["error"] = str(e)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ERROR_DESCONOCIDO",
                "mensaje": str(e)
            }
        )
```

---

## 4️⃣ FIX DE ENCODING UTF-8

### Problema
Caracteres especiales aparecen rotos: "á" → "A3", "é" → "A©"

### Solución

#### Step 1: Auditar archivos

```bash
# Verificar encoding de archivos Python
file -bi backend/app/services/notificacion_service.py
# Esperado: text/x-python; charset=utf-8

# Buscar archivos con encoding incorrecto
find backend -name "*.py" -exec file -bi {} \; | grep -v utf-8
```

#### Step 2: Fijar encoding

```python
# backend/app/services/notificacion_service.py
# ⬆️ AGREGAR AL INICIO DEL ARCHIVO (primeras 2 líneas)

# -*- coding: utf-8 -*-
"""
Servicios de notificación para cobranza.
Maneja envío de emails y SMS con plantillas personalizadas.
"""

from __future__ import unicode_literals
import sys

# Asegurar output UTF-8
if sys.version_info[0] >= 3:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ... resto del código
```

#### Step 3: Fijar en FastAPI

```python
# backend/main.py (o app.py)

from fastapi import FastAPI
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class UTF8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["charset"] = "utf-8"
        if "content-type" in response.headers:
            response.headers["content-type"] = response.headers["content-type"] + "; charset=utf-8"
        return response

app = FastAPI(title="RapiCredit")
app.add_middleware(UTF8Middleware)

# Configurar respuestas JSON con UTF-8
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

@app.get("/test-encoding")
def test_encoding():
    data = {
        "mensaje": "Señal correcta",
        "caracteres": "áéíóú - ÀÈÌÒÙ - ñÑ - ©®™"
    }
    return JSONResponse(
        content=jsonable_encoder(data),
        media_type="application/json; charset=utf-8"
    )
```

#### Step 4: Test

```python
# backend/tests/test_encoding.py

def test_caracteres_especiales():
    from app.services.notificacion_service import format_cuota_item
    
    cliente = {"nombre": "María José García López", "cedula": "12345678"}
    cuota = {"numero": 1, "monto": 1500.00}
    
    resultado = format_cuota_item(cliente, cuota)
    
    assert "María" in resultado["nombre"]
    assert "José" in resultado["nombre"]
    assert "García" in resultado["nombre"]
    assert "López" in resultado["nombre"]
    
    print(f"✓ Caracteres especiales correctos: {resultado['nombre']}")
```

---

## 5️⃣ REINTENTOS EN EMAIL

### Problema
Si SMTP falla, email se pierden sin reintentos.

### Solución

```python
# backend/app/services/email_service.py

import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict

class EmailService:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.max_reintentos = 3
        self.delay_base = 2  # 2 segundos
    
    def enviar_con_reintentos(
        self,
        destinatario: str,
        asunto: str,
        cuerpo: str,
        adjuntos: Optional[list] = None
    ) -> Dict[str, any]:
        """
        Envía email con reintentos automáticos.
        Usa exponential backoff: 2s, 4s, 8s
        """
        
        for intento in range(1, self.max_reintentos + 1):
            try:
                self._enviar_smtp(destinatario, asunto, cuerpo, adjuntos)
                
                return {
                    "exito": True,
                    "intento": intento,
                    "mensaje": f"Enviado en intento {intento}"
                }
            
            except smtplib.SMTPTemporaryError as e:
                # Error temporal (429 rate limit, 450 unavailable, etc)
                if intento < self.max_reintentos:
                    delay = self.delay_base ** intento
                    logger.warning(
                        f"Error temporal SMTP. "
                        f"Intento {intento}/{self.max_reintentos}. "
                        f"Esperando {delay}s. "
                        f"Error: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Falló después de {self.max_reintentos} intentos: {e}")
                    return {
                        "exito": False,
                        "intento": intento,
                        "error": f"Error temporal SMTP después de {self.max_reintentos} intentos: {e}"
                    }
            
            except smtplib.SMTPAuthenticationError as e:
                # Error de autenticación - no reintentar
                logger.error(f"Error de autenticación SMTP: {e}")
                return {
                    "exito": False,
                    "intento": intento,
                    "error": f"Error de autenticación: {e}"
                }
            
            except Exception as e:
                # Error desconocido
                logger.error(f"Error desconocido en email: {e}")
                if intento < self.max_reintentos:
                    delay = self.delay_base ** intento
                    logger.info(f"Reintentando en {delay}s...")
                    time.sleep(delay)
                else:
                    return {
                        "exito": False,
                        "intento": intento,
                        "error": f"Error desconocido: {e}"
                    }
        
        return {
            "exito": False,
            "intento": self.max_reintentos,
            "error": "Falló después de todos los reintentos"
        }
    
    def _enviar_smtp(self, destinatario: str, asunto: str, cuerpo: str, adjuntos=None):
        """Envía email via SMTP"""
        
        mensaje = MIMEMultipart('alternative')
        mensaje['Subject'] = asunto
        mensaje['From'] = self.username
        mensaje['To'] = destinatario
        
        # Cuerpo
        parte = MIMEText(cuerpo, 'html', 'utf-8')
        mensaje.attach(parte)
        
        # Adjuntos
        if adjuntos:
            for archivo in adjuntos:
                # ... agregar adjuntos
                pass
        
        # Enviar
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as servidor:
            servidor.starttls()
            servidor.login(self.username, self.password)
            servidor.send_message(mensaje)

# Uso
email_service = EmailService(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="noreply@rapicredit.com",
    password="CONTRASEÑA"
)

resultado = email_service.enviar_con_reintentos(
    destinatario="cliente@example.com",
    asunto="Notificación de pago",
    cuerpo="<h1>Hola</h1><p>Tu cuota vence el 25/03</p>"
)

if resultado["exito"]:
    logger.info(f"✓ Email enviado en intento {resultado['intento']}")
else:
    logger.error(f"✗ {resultado['error']}")
```

---

## 🎯 CHECKLIST DE IMPLEMENTACIÓN

### Semana 1

- [ ] **Lunes-Martes: Validación de Tasa**
  - [ ] Crear endpoint `/validar-para-pago`
  - [ ] Integrar en `pagos_service.py`
  - [ ] Frontend: mostrar alerta
  - [ ] Test: verificar mensaje claro
  - [ ] Deploy a staging

- [ ] **Miércoles: Validación de Email**
  - [ ] Función `es_email_valido()`
  - [ ] Script `limpiar_emails.py`
  - [ ] Ejecutar limpieza en BD
  - [ ] Integrar validación en `notificaciones_tabs.py`
  - [ ] Test: verificar saltados

- [ ] **Jueves: Transacciones**
  - [ ] Refactorizar `enviar_todas()` con transacción
  - [ ] Test: simular fallo a mitad
  - [ ] Verify: sin datos parciales

- [ ] **Viernes: Encoding + Reintentos**
  - [ ] Fix encoding UTF-8 en archivos
  - [ ] Implementar `EmailService` con reintentos
  - [ ] Test: verificar caracteres especiales
  - [ ] Test: simular fallo SMTP

### Antes de Deploy

- [ ] ✅ Todos los tests pasan
- [ ] ✅ Code review completado
- [ ] ✅ Staging verificado
- [ ] ✅ Rollback plan documentado
- [ ] ✅ Comunicar cambios a stakeholders

---

**Documento de implementación completado:** 20 de Marzo, 2026
