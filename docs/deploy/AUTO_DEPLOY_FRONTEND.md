# Auto-deploy frontend (Render) sin tocar el Dashboard en cada merge

## Por qué producción no se actualiza sola

Al mergear a `main` con cambios en `frontend/`, GitHub Actions corre
**Render frontend deploy hook** (`.github/workflows/render-frontend-deploy.yml`).

Ese job hace `POST` a un **Deploy Hook** de Render. Si el secret
`RENDER_DEPLOY_HOOK_URL` no está en el repo, **no hay redeploy** y el sitio
sigue en el commit viejo (comprobable en `GET https://rapicredit.onrender.com/health`
→ `renderGitCommit` / `build.builtAt`).

Sin acceso a Render **no se puede inventar** ese hook desde código: la URL
sale del Dashboard. Hace falta **una sola configuración** por quien sí tenga
cuenta.

## Setup de una vez (quien tenga Render)

1. [Render Dashboard](https://dashboard.render.com) → servicio frontend
   (`rapicredit` / `pagos-frontend` / el que sirve `rapicredit.onrender.com`).
2. **Settings → Build & Deploy → Deploy Hook** → Create / Copy URL
   (`https://api.render.com/deploy/srv-…?key=…`).
3. Opcional recomendado: **Auto-Deploy = Yes**, branch `main`
   (doble red de seguridad si el hook falla).
4. GitHub → repo **Mashi007/pagos** → **Settings → Secrets and variables → Actions**
   → **New repository secret**:
   - Name: `RENDER_DEPLOY_HOOK_URL`
   - Value: la URL del paso 2 (no compartir en chat/issues).
5. Probar: **Actions → Render frontend deploy hook → Run workflow**,
   o mergear un cambio mínimo bajo `frontend/`.
6. Esperar el build en Render (varios minutos) y verificar:
   ```bash
   curl -sS https://rapicredit.onrender.com/health
   ```
   `renderGitCommit` debe coincidir con el tip de `main`.

## Mensaje corto para pedir el setup

> Necesito que configures una sola vez el auto-deploy del frontend:
> en Render, copia el Deploy Hook del servicio que sirve rapicredit.onrender.com
> y créalo como secret de GitHub `RENDER_DEPLOY_HOOK_URL` en Mashi007/pagos.
> Detalle: `docs/deploy/AUTO_DEPLOY_FRONTEND.md`. Después de eso, cada merge
> a main con cambios en frontend/ redeploya solo.

## Qué hace / no hace este agent o un contribuidor sin Render

| Puede | No puede |
|-------|----------|
| Mergear a GitHub | Crear el Deploy Hook |
| Correr el workflow de Actions | Pegar el secret sin la URL |
| Ver `health` y el commit viejo | Forzar rebuild en el Dashboard |

Si nadie tiene la cuenta de Render: hay que recuperar acceso a la cuenta
dueña del servicio (email de login / owner del team en Render), no hay
atajo desde este repositorio.
