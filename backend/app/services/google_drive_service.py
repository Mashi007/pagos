"""
Subida de imágenes a Google Drive y obtención de link público.
Usa OAuth o cuenta de servicio según informe_pagos_config (folder_id + credentials o refresh_token).
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive.file"]


def upload_image_and_get_link(
    image_bytes: bytes,
    filename: str = "papeleta.jpg",
    mime_type: str = "image/jpeg",
) -> Optional[str]:
    """
    Sube la imagen a la carpeta de Google Drive configurada y devuelve el link para ver/compartir.
    Si no hay config o falla, devuelve None. Usa OAuth (refresh_token) o cuenta de servicio.
    """
    from app.core.informe_pagos_config_holder import get_google_drive_folder_id, sync_from_db
    from app.core.google_credentials import get_google_credentials

    sync_from_db()
    folder_id = get_google_drive_folder_id()
    credentials = get_google_credentials(DRIVE_SCOPE)
    if not folder_id or not credentials:
        logger.warning("Google Drive no configurado (folder_id o credentials/OAuth). Configura en Configuración > Informe pagos.")
        return None
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        drive = build("drive", "v3", credentials=credentials)

        file_metadata = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mime_type, resumable=False)
        file = drive.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
        file_id = file.get("id")
        if not file_id:
            return None
        # Permitir que cualquiera con el link pueda ver
        drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
        link = file.get("webViewLink")
        if link:
            return link
        return f"https://drive.google.com/file/d/{file_id}/view"
    except Exception as e:
        logger.exception("Error subiendo imagen a Google Drive: %s", e)
        return None
