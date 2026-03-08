"""
Drive: carpeta por fecha (DDMesAAAA), subir archivo, evitar duplicados por nombre+tamaño; crear hoja por día.
"""
import io
import logging
from datetime import datetime
from typing import Any, Optional, Tuple

from app.core.config import settings
from app.services.pagos_gmail.helpers import get_folder_name_from_date, get_sheet_name_for_date

logger = logging.getLogger(__name__)

ROOT_FOLDER_ID = getattr(settings, "DRIVE_ROOT_FOLDER_ID", "1uzFPzUo00urjiWmeql1F30xgwpjdhm2o")


def build_drive_service(credentials: Any):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    return build("drive", "v3", credentials=credentials, cache_discovery=False), MediaIoBaseUpload


def get_or_create_folder(service: Any, folder_name: str) -> Optional[str]:
    """Busca en root una carpeta con name=folder_name; si no existe, la crea. Devuelve folder_id."""
    try:
        q = f"'{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        resp = service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
        files = resp.get("files", [])
        if files:
            return files[0]["id"]
        meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder", "parents": [ROOT_FOLDER_ID]}
        f = service.files().create(body=meta, fields="id").execute()
        return f["id"]
    except Exception as e:
        logger.exception("Drive get_or_create_folder %s: %s", folder_name, e)
        return None


def upload_file(service: Any, MediaIoBaseUpload, folder_id: str, filename: str, content: bytes, mime_type: str) -> Optional[Tuple[str, str]]:
    """
    Sube el archivo a la carpeta. Evita duplicado por nombre+tamaño en la misma carpeta.
    Returns (file_id, drive_link) o None.
    """
    try:
        size = len(content)
        q = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
        resp = service.files().list(q=q, spaces="drive", fields="files(id,size)").execute()
        for f in resp.get("files", []):
            if str(f.get("size")) == str(size):
                link = f"https://drive.google.com/file/d/{f['id']}/view"
                return (f["id"], link)
        meta = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)
        f = service.files().create(body=meta, media_body=media, fields="id").execute()
        fid = f["id"]
        return (fid, f"https://drive.google.com/file/d/{fid}/view")
    except Exception as e:
        logger.exception("Drive upload_file %s: %s", filename, e)
        return None


def get_or_create_sheet_for_date(service_drive: Any, service_sheets: Any, date: datetime) -> Optional[str]:
    """
    Obtiene o crea la hoja "Pagos_Cobros_DDMesAAAA" dentro de ROOT. Crea el archivo en Drive y la hoja con headers A-F.
    Returns spreadsheet_id para usar con Sheets API.
    """
    sheet_name = get_sheet_name_for_date(date)
    try:
        q = f"'{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and name='{sheet_name}' and trashed=false"
        resp = service_drive.files().list(q=q, spaces="drive", fields="files(id)").execute()
        files = resp.get("files", [])
        if files:
            return files[0]["id"]
        body = {"properties": {"title": sheet_name}, "sheets": [{"data": [{"rowData": [{"values": [
            {"userEnteredValue": {"stringValue": "Correo Origen"}},
            {"userEnteredValue": {"stringValue": "Fecha Pago"}},
            {"userEnteredValue": {"stringValue": "Cédula"}},
            {"userEnteredValue": {"stringValue": "Monto"}},
            {"userEnteredValue": {"stringValue": "Referencia"}},
            {"userEnteredValue": {"stringValue": "Link"}},
        ]}]}]}]}
        create = service_sheets.spreadsheets().create(body=body).execute()
        spreadsheet_id = create["spreadsheetId"]
        try:
            f = service_drive.files().get(fileId=spreadsheet_id, fields="parents").execute()
            prev = f.get("parents") or []
            prev_str = ",".join(prev) if prev else ""
            if prev_str:
                service_drive.files().update(
                    fileId=spreadsheet_id,
                    addParents=ROOT_FOLDER_ID,
                    removeParents=prev_str,
                ).execute()
            else:
                service_drive.files().update(
                    fileId=spreadsheet_id,
                    addParents=ROOT_FOLDER_ID,
                ).execute()
        except Exception as move_err:
            logger.warning("Sheet creado pero no se pudo mover a carpeta: %s", move_err)
        return spreadsheet_id
    except Exception as e:
        logger.exception("get_or_create_sheet_for_date %s: %s", sheet_name, e)
        return None
