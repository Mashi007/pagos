# Add explicit log that we process all unread (no subject/sender filter)
path = "app/services/pagos_gmail/pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
old = """        def process_message_batch(batch: list[dict], label: str) -> None:
            nonlocal emails_ok, files_ok, drive_errors
            for msg_info in batch:"""
new = """        def process_message_batch(batch: list[dict], label: str) -> None:
            nonlocal emails_ok, files_ok, drive_errors
            # Criterio unico: no leidos. No se filtra por asunto ni remitente; se procesan todos.
            if batch:
                logger.warning("[PAGOS_GMAIL] Procesando lote %s: %d correos (todos, sin filtro asunto/remitente)", label, len(batch))
            for msg_info in batch:"""
if old not in c:
    print("Block not found")
    exit(1)
c = c.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: log added")
