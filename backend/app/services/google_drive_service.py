"""
Subida de imágenes a Google Drive y obtención de link público.
Usa configuración desde informe_pagos_config_holder (google_drive_folder_id, google_credentials_json).
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def upload_image_and_get_link(
    image_bytes: bytes,
    filename: str = "papeleta.jpg",
    mime_type: str = "image/jpeg",
) -> Optional[str]:
    """
    Sube la imagen a la carpeta de Google Drive configurada y devuelve el link para ver/compartir.
    Si no hay config o falla, devuelve None.
    """
    from app.core.informe_pagos_config_holder import (
        get_google_drive_folder_id,
        get_google_credentials_json,
        sync_from_db,
    )
    sync_from_db()
    folder_id = get_google_drive_folder_id()
    creds_json = get_google_credentials_json()
    if not folder_id or not creds_json:
        logger.warning("Google Drive no configurado (folder_id o credentials). Configura en Configuración > Informe pagos.")
        return None
    try:
        import json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/drive.file"]
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
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
