# Por qué no se envían los mensajes masivos (notificaciones)

## Síntoma en logs

```
[notif_envio_inicio] Inicio envío notificaciones: items=5462 origen=batch modo_pruebas=True
[notif_envio_config] Config envío: modo_pruebas=True email_pruebas_ok=True tipos_habilitados=0
[notif_envio_resumen] Resumen: enviados=0 fallidos=0 sin_email=0 omitidos_config=5462 ...
```

- **tipos_habilitados=0**: ningún tipo de notificación está habilitado en la configuración.
- **omitidos_config=5462**: todos los ítems se omiten porque, para cada uno, el tipo (p. ej. "Faltan 5 días", "Hoy vence", "Retrasadas") tiene **Envío desactivado** en la configuración guardada.

## Causa

La configuración de envíos (tabla `configuracion`, clave `notificaciones_envios`) tiene **todos** los tipos con `habilitado: false`. El backend solo envía correos para ítems cuyo tipo tiene `habilitado: true`.

## Solución

1. Ir a **Configuración > Notificaciones** (o **Configuración > Envíos de notificaciones**, según el menú).
2. En la sección de **envíos por tipo** (por caso: Faltan 5 días, Faltan 3 días, Hoy vence, Retrasadas, Prejudicial, Mora 90+, etc.):
   - Activar **al menos un tipo** (checkbox “Habilitado” / “Envío activo” para ese caso).
   - Opcional: asignar plantilla, CCO, “Incluir PDF anexo”, etc.
3. Guardar la configuración (el frontend suele hacer **PUT** a `/api/v1/configuracion/notificaciones/envios`).
4. Volver a lanzar el envío masivo (**Enviar todas** / **Enviar notificaciones**).

Tras eso, `tipos_habilitados` será &gt; 0 y los ítems de los tipos habilitados dejarán de contarse como `omitidos_config` y se enviarán (respetando además modo pruebas y correo de pruebas si está configurado).

## Modo pruebas

Si en la misma configuración **modo_pruebas** está en `true`:

- Los correos **no** se envían a los clientes; se redirigen al correo de pruebas (`email_pruebas`).
- Para enviar realmente a los clientes, hay que poner **modo_pruebas** en `false` (y asegurar que al menos un tipo siga habilitado).

## Log de advertencia añadido

Si se ejecuta un envío con `tipos_habilitados=0`, el backend escribe un **WARNING** en log indicando que ningún tipo está habilitado y que se debe habilitar al menos uno en Configuración > Notificaciones > Envíos.
