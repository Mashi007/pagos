# Add pagination to list_unread_with_attachments so ALL unread are fetched
path = "app/services/pagos_gmail/gmail_service.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    def _fetch() -> List[dict]:
        result = service.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=500).execute()
        messages = result.get("messages", [])
        out = []
        for msg in messages:"""

new = """    def _fetch() -> List[dict]:
        # Paginacion: obtener TODOS los no leidos (unico criterio = UNREAD)
        all_msg_refs: List[dict] = []
        page_token: Optional[str] = None
        while True:
            params: dict = {"userId": "me", "labelIds": ["UNREAD"], "maxResults": 500}
            if page_token:
                params["pageToken"] = page_token
            result = service.users().messages().list(**params).execute()
            batch = result.get("messages", [])
            all_msg_refs.extend(batch)
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        out = []
        for msg in all_msg_refs:"""

if old not in content:
    print("Old block not found")
    exit(1)
content = content.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("OK: pagination added to list_unread_with_attachments")
