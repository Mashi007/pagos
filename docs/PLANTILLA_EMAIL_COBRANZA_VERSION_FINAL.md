# Plantilla email cobranza – Versión final

## 1. Uso

- **Pegar en el editor** (EditorPlantillaHTML o PlantillasNotificaciones): el frontend reemplaza automáticamente imágenes base64 **largas** (>400 caracteres) por `{{LOGO_URL}}`. El icono WhatsApp (SVG corto) se mantiene.
- **Guardar**: se persiste el HTML ya con `{{LOGO_URL}}` en lugar del base64 del logo.
- **Envío (prueba o real)**: el backend sustituye `{{LOGO_URL}}` por la URL real del logo antes de enviar.

---

## 2. Plantilla HTML final (lista para pegar)

Sustituir el `src` del logo por `{{LOGO_URL}}`. El icono WhatsApp puede quedarse en base64 (SVG) o en una URL si se prefiere.

```html
<!-- ENCABEZADO GMAIL-COMPATIBLE: Rapi-Credit C.A. -->
<table width="600" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff; font-family:Arial, sans-serif;">

  <!-- Logo -->
  <tr>
    <td align="center" style="background-color:#ffffff; padding:24px 40px 16px 40px; border-bottom:2px solid #f0f2f5;">
      <img src="{{LOGO_URL}}" alt="RapiCredit" height="90" style="display:block; margin:0 auto 10px auto;" />
      <p style="margin:0; color:#1a2744; font-size:11px; letter-spacing:2px; text-transform:uppercase; font-weight:bold;">Soluciones Financieras de Confianza</p>
    </td>
  </tr>

  <!-- Franja alerta -->
  <tr>
    <td align="center" style="background-color:#e87722; padding:10px 40px;">
      <p style="margin:0; color:#ffffff; font-size:13px; font-weight:bold; letter-spacing:1px; text-transform:uppercase;">&#9888; Aviso Importante</p>
    </td>
  </tr>

  <!-- Título + fecha + número -->
  <tr>
    <td style="padding:28px 40px 20px 40px; border-bottom:1px solid #e8ecf0; background-color:#ffffff;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="border-left:4px solid #e87722; padding-left:14px;">
            <p style="margin:0; color:#1a2744; font-size:21px; font-weight:bold; line-height:1.4;">Notificaci&#243;n de Vencimiento de Cuotas</p>
            <p style="margin:8px 0 0 0; color:#888888; font-size:12px;">Caracas, {{FECHA_CARTA}}</p>
            <p style="margin:6px 0 0 0;">
              <span style="display:inline-block; background-color:#f0f4ff; border:1px solid #c0cce8; color:#1a2744; font-size:11px; font-weight:bold; letter-spacing:1px; padding:4px 10px;">
                N&#176; RAP-COB-{{PRESTAMOS.ID}}-{{NUMEROCORRELATIVO}}
              </span>
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- CUERPO -->
  <tr>
    <td style="padding:28px 40px; background-color:#ffffff; color:#333333; font-size:14px; line-height:1.8;">

      <p style="margin:0 0 18px 0; font-size:14px; color:#333333;">Estimado Sr./Sra.<br><strong style="color:#1a2744;">{{CLIENTES.NOMBRE_COMPLETO}}</strong><br><span style="color:#888888; font-size:12px;">C.I.: {{CLIENTES.CEDULA}}</span></p>

      <p style="margin:0 0 16px 0; font-size:14px; color:#333333;">Por medio de la presente, nos dirigimos a usted respetuosamente en nombre de <strong>Rapi-Credit, C.A.</strong>, a fin de notificarle que, a la fecha de esta comunicaci&#243;n, registra cuotas vencidas correspondientes a su cr&#233;dito vigente con nuestra instituci&#243;n.</p>

      <p style="margin:0 0 10px 0; font-size:14px; color:#333333;">Le informamos que las cuotas pendientes de pago son las siguientes:</p>

      {{TABLA_CUOTAS_PENDIENTES}}

      <p style="margin:0 0 16px 0; font-size:14px; color:#333333;">Le recordamos que el cumplimiento oportuno de sus obligaciones crediticias es fundamental para mantener un historial financiero favorable y evitar las consecuencias contractuales derivadas del incumplimiento.</p>

      <p style="margin:0 0 16px 0; font-size:14px; color:#333333;"><strong>Le requerimos formalizar el pago de las cuotas adeudadas en un plazo no mayor a 48 horas.</strong> Le informamos que el pago mediante Zelle no se encuentra disponible. En caso de requerir asistencia o desear establecer un acuerdo de pago, le instamos a comunicarse con nosotros a la brevedad posible.</p>

      <p style="margin:0 0 12px 0; font-size:14px; color:#333333;">Anexo al presente correo encontrar&#225; nuestros canales de pago habilitados para realizar su cancelaci&#243;n.</p>

      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px 0;">
        <tr>
          <td width="4" style="background-color:#2e7d32;">&nbsp;</td>
          <td style="background-color:#eaf4ea; padding:12px 16px;">
            <p style="margin:0; color:#2e7d32; font-size:13px; font-weight:bold;">Si usted ya ha efectuado el pago correspondiente, le agradecemos ignorar esta comunicaci&#243;n y disculpe las molestias ocasionadas.</p>
          </td>
        </tr>
      </table>

      <p style="margin:0 0 16px 0; font-size:14px; color:#333333;">Quedamos a su disposici&#243;n para atender cualquier consulta al respecto. Agradecemos de antemano su pronta gesti&#243;n.</p>

      <p style="margin:0 0 6px 0; font-size:14px; color:#333333;">Para cualquier duda o consulta, puede comunicarse con nosotros a trav&#233;s de los siguientes canales:</p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px 0;">
        <tr>
          <td style="padding:10px 16px; background-color:#f7f9fc; border-left:4px solid #e87722;">
            <p style="margin:0 0 6px 0; font-size:13px; color:#333333;">&#128231; <a href="mailto:cobranza@rapicreditca.com" style="color:#1a2744; font-weight:bold; text-decoration:none;">cobranza@rapicreditca.com</a></p>
            <p style="margin:0; font-size:13px; color:#333333;">
              <a href="https://wa.me/584244579934" style="color:#1a2744; font-weight:bold; text-decoration:none; display:inline-block; vertical-align:middle;">
                <img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgd2lkdGg9IjE4IiBoZWlnaHQ9IjE4Ij48cGF0aCBmaWxsPSIjMjVEMzY2IiBkPSJNMTcuNDcyIDE0LjM4MmMtLjI5Ny0uMTQ5LTEuNzU4LS44NjctMi4wMy0uOTY3LS4yNzMtLjA5OS0uNDcxLS4xNDgtLjY3LjE1LS4xOTcuMjk3LS43NjcuOTY2LS45NCAxLjE2NC0uMTczLjE5OS0uMzQ3LjIyMy0uNjQ0LjA3NS0uMjk3LS4xNS0xLjI1NS0uNDYzLTIuMzktMS40NzUtLjg4My0uNzg4LTEuNDgtMS43NjEtMS42NTMtMi4wNTktLjE3My0uMjk3LS4wMTgtLjQ1OC4xMy0uNjA2LjEzNC0uMTMzLjI5OC0uMzQ3LjQ0Ni0uNTIuMTQ5LS4xNzQuMTk4LS4yOTguMjk4LS40OTcuMDk5LS4xOTguMDUtLjM3MS0uMDI1LS41Mi0uMDc1LS4xNDktLjY2OS0xLjYxMi0uOTE2LTIuMjA3LS4yNDItLjU3OS0uNDg3LS41LS42NjktLjUxLS4xNzMtLjAwOC0uMzcxLS4wMS0uNTctLjAxLS4xOTggMC0uNTIuMDc0LS43OTIuMzcyLS4yNzIuMjk3LTEuMDQgMS4wMTYtMS4wNCAyLjQ3OSAwIDEuNDYyIDEuMDY1IDIuODc1IDEuMjEzIDMuMDc0LjE0OS4xOTggMi4wOTYgMy4yIDUuMDc3IDQuNDg3LjcwOS4zMDYgMS4yNjIuNDg5IDEuNjk0LjYyNS43MTIuMjI3IDEuMzYuMTk1IDEuODcxLjExOC41NzEtLjA4NSAxLjc1OC0uNzE5IDIuMDA2LTEuNDEzLjI0OC0uNjk0LjI0OC0xLjI4OS4xNzMtMS40MTMtLjA3NC0uMTI0LS4yNzItLjE5OC0uNTctLjM0N20tNS40MjEgNy40MDNoLS4wMDRhOS44NyA5Ljg3IDAgMDEtNS4wMzEtMS4zNzhsLS4zNjEtLjIxNC0zLjc0MS45ODIuOTk4LTMuNjQ4LS4yMzUtLjM3NGE5Ljg2IDkuODYgMCAwMS0xLjUxLTUuMjZjLjAwMS01LjQ1IDQuNDM2LTkuODg0IDkuODg4LTkuODg0IDIuNjQgMCA1LjEyMiAxLjAzIDYuOTg4IDIuODk4YTkuODI1IDkuODI1IDAgMDEyLjg5MyA2Ljk5NGMtLjAwMyA1LjQ1LTQuNDM3IDkuODg0LTkuODg1IDkuODg0bTguNDEzLTE4LjI5N0ExMS44MTUgMTEuODE1IDAgMDAxMi4wNSAwQzUuNDk1IDAgLjE2IDUuMzM1LjE1NyAxMS44OTJjMCAyLjA5Ni41NDcgNC4xNDIgMS41ODggNS45NDVMLjA1NyAyNGw2LjMwNS0xLjY1NGExMS44ODIgMTEuODgyIDAgMDA1LjY4MyAxLjQ0OGguMDA1YzYuNTU0IDAgMTEuODktNS4zMzUgMTEuODkzLTExLjg5M2ExMS44MjEgMTEuODIxIDAgMDAtMy40OC04LjQxM3oiLz48L3N2Zz4=" alt="WhatsApp" width="18" height="18" style="vertical-align:middle; margin-right:6px;" />
                <span style="vertical-align:middle;">424-4579934</span>
              </a>
            </p>
          </td>
        </tr>
      </table>

    </td>
  </tr>

</table>
```

---

## 3. Variables de plantilla

| Variable | Descripción |
|----------|-------------|
| `{{LOGO_URL}}` | URL del logo (sustituida por el backend al enviar) |
| `{{FECHA_CARTA}}` | Fecha de la carta |
| `{{PRESTAMOS.ID}}` | ID del préstamo |
| `{{NUMEROCORRELATIVO}}` | Número correlativo del envío |
| `{{CLIENTES.NOMBRE_COMPLETO}}` | Nombre del cliente |
| `{{CLIENTES.CEDULA}}` | Cédula del cliente |
| `{{TABLA_CUOTAS_PENDIENTES}}` | Tabla HTML de cuotas pendientes (generada por backend) |

---

## 4. Lógica frontend (versión final)

**Archivo:** `frontend/src/utils/plantillaHtmlLogo.ts`

```ts
const MIN_BASE64_LENGTH_TO_REPLACE = 400

export function replaceBase64ImagesWithLogoUrl(html: string): string {
  if (!html || typeof html !== 'string') return html
  return html.replace(/src="(data:image\/[^"]+)"/gi, (_, dataUrl: string) => {
    if (dataUrl.length >= MIN_BASE64_LENGTH_TO_REPLACE) {
      return 'src="{{LOGO_URL}}"'
    }
    return `src="${dataUrl}"`
  })
}
```

- Usar al **cargar**, **onChange** y **guardar** en el editor de plantillas, y en **Enviar prueba**.
- Solo se reemplazan imágenes base64 con más de 400 caracteres (logo); iconos SVG pequeños (WhatsApp) se mantienen.

---

## 5. Backend

- **Envío de correo:** si el HTML contiene `{{LOGO_URL}}`, se sustituye por la URL real del logo antes de `send_email`.
- **email.py:** reemplazo de `data:image/...;base64,...` en body_html por la URL del logo; body_html + body_text multipart para correcto render en Gmail.

---

## 6. Checklist antes de ingresar la plantilla

1. Logo: en el HTML usar `src="{{LOGO_URL}}"` (o pegar con base64 y dejar que el frontend lo reemplace).
2. Icono WhatsApp: puede quedar en base64 (SVG) o cambiarse luego por URL.
3. Variables `{{...}}` escritas tal cual (FECHA_CARTA, PRESTAMOS.ID, NUMEROCORRELATIVO, CLIENTES.*, TABLA_CUOTAS_PENDIENTES).
4. Guardar desde el editor para que se aplique `replaceBase64ImagesWithLogoUrl` y no se persista el base64 del logo.
