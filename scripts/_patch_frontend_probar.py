"""Patch frontend probar email to pass servicio notificaciones."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]

# --- notificacionService.ts ---
svc_path = root / "frontend" / "src" / "services" / "notificacionService.ts"
t = svc_path.read_text(encoding="utf-8")
old = """  async probarConfiguracionEmail(
    emailDestino?: string,
    subject?: string,
    mensaje?: string,
    emailCC?: string
  ): Promise<any> {
    const params: any = {}

    if (emailDestino) params.email_destino = emailDestino

    if (subject) params.subject = subject

    if (mensaje) params.mensaje = mensaje

    if (emailCC) params.email_cc = emailCC

    return await apiClient.post(`${this.baseUrl}/email/probar`, params)
  }"""

new = """  async probarConfiguracionEmail(
    emailDestino?: string,
    subject?: string,
    mensaje?: string,
    emailCC?: string,
    opts?: { servicio?: string; tipo_tab?: string }
  ): Promise<any> {
    const params: Record<string, string> = {}

    if (emailDestino) params.email_destino = emailDestino

    if (subject) params.subject = subject

    if (mensaje) params.mensaje = mensaje

    if (emailCC) params.email_cc = emailCC

    if (opts?.servicio) params.servicio = opts.servicio

    if (opts?.tipo_tab) params.tipo_tab = opts.tipo_tab

    return await apiClient.post(`${this.baseUrl}/email/probar`, params)
  }"""

if old not in t:
    raise SystemExit("notificacionService block not found")
svc_path.write_text(t.replace(old, new, 1), encoding="utf-8")
print("patched", svc_path)

# --- ConfiguracionNotificaciones.tsx: normalizeConfigFromApi ---
cfg_path = root / "frontend" / "src" / "components" / "notificaciones" / "ConfiguracionNotificaciones.tsx"
t2 = cfg_path.read_text(encoding="utf-8")
old_norm = """  const modoPruebas = data.modo_pruebas === true"""
new_norm = """  const modoPruebas =
    data.modo_pruebas === true ||
    data.modo_pruebas === 'true' ||
    String(data.modo_pruebas || '').toLowerCase() === 'true'"""
if old_norm not in t2:
    raise SystemExit("normalize modoPruebas not found")
t2 = t2.replace(old_norm, new_norm, 1)

old_call = """        const resultado = await emailConfigService.probarConfiguracionEmail(
          destinos[i],

          ASUNTO_PLANTILLA_PREDETERMINADA,

          MENSAJE_PLANTILLA_PREDETERMINADA,

          undefined
        )"""

new_call = """        const resultado = await emailConfigService.probarConfiguracionEmail(
          destinos[i],

          ASUNTO_PLANTILLA_PREDETERMINADA,

          MENSAJE_PLANTILLA_PREDETERMINADA,

          undefined,

          { servicio: 'notificaciones', tipo_tab: 'dias_1_retraso' }
        )"""

if old_call not in t2:
    raise SystemExit("probarConfiguracionEmail call not found")
t2 = t2.replace(old_call, new_call, 1)
cfg_path.write_text(t2, encoding="utf-8")
print("patched", cfg_path)

# --- EditorPlantillaHTML.tsx ---
ed_path = root / "frontend" / "src" / "components" / "notificaciones" / "EditorPlantillaHTML.tsx"
t3 = ed_path.read_text(encoding="utf-8")
insert_after = """import { replaceBase64ImagesWithLogoUrl } from '../../utils/plantillaHtmlLogo'

interface EditorPlantillaHTMLProps {"""

insert_block = """import { replaceBase64ImagesWithLogoUrl } from '../../utils/plantillaHtmlLogo'

/** Mapeo alineado con backend notificaciones_tabs._CONFIG_TIPO_TO_TAB (cuenta SMTP por pesta\\u00f1a). */
const PLANTILLA_TIPO_A_TIPO_TAB: Record<string, string> = {
  PAGO_5_DIAS_ANTES: 'dias_5',
  PAGO_3_DIAS_ANTES: 'dias_3',
  PAGO_1_DIA_ANTES: 'dias_1',
  PAGO_DIA_0: 'hoy',
  PAGO_1_DIA_ATRASADO: 'dias_1_retraso',
  PAGO_3_DIAS_ATRASADO: 'dias_3_retraso',
  PAGO_5_DIAS_ATRASADO: 'dias_5_retraso',
  PREJUDICIAL: 'prejudicial',
  COBRANZA: 'dias_1_retraso',
}

interface EditorPlantillaHTMLProps {"""

if insert_after not in t3:
    raise SystemExit("Editor import block not found")
t3 = t3.replace(insert_after, insert_block, 1)

old_ed = """      await emailConfigService.probarConfiguracionEmail(
        emailPrueba.trim(),

        asunto.trim() || 'Prueba de plantilla',

        replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim(),

        undefined
      )"""

new_ed = """      await emailConfigService.probarConfiguracionEmail(
        emailPrueba.trim(),

        asunto.trim() || 'Prueba de plantilla',

        replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim(),

        undefined,

        {
          servicio: 'notificaciones',
          tipo_tab: PLANTILLA_TIPO_A_TIPO_TAB[tipo] || 'dias_1_retraso',
        }
      )"""

if old_ed not in t3:
    raise SystemExit("Editor probar call not found")
t3 = t3.replace(old_ed, new_ed, 1)
ed_path.write_text(t3, encoding="utf-8")
print("patched", ed_path)
