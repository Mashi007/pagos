# coding: utf-8
path = "app/services/pagos_gmail/pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

start = c.find('process_message_batch(messages, "inicial")')
if start == -1:
    print("start not found")
    exit(1)
line_start = c.rfind("\n", 0, start) + 1
end = c.find("# Fin del loop", start)
if end == -1:
    print("end not found")
    exit(1)
end = c.find("\n", end) + 1

new_block = r'''        # Con "unread": bucle que llega al final de la bandeja y vuelve al inicio hasta vuelta completa (0 sin leer).
        if scan_filter == "unread":
            vuelta_num = 0
            max_vueltas = 20
            while True:
                vuelta_num += 1
                logger.warning("[PAGOS_GMAIL] Listando no leidos desde inicio de bandeja (vuelta %d)...", vuelta_num)
                raw_messages = list_messages_by_filter(gmail_svc, "unread")
                seen_ids = set()
                messages = []
                for m in raw_messages:
                    mid = m["id"]
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)
                    messages.append(m)
                if not messages:
                    logger.warning("[PAGOS_GMAIL] Vuelta completa: no quedan correos sin leer.")
                    break
                logger.warning("[PAGOS_GMAIL] Correos en esta vuelta: %d (procesando hasta el final de bandeja)", len(messages))
                process_message_batch(messages, "vuelta %d" % vuelta_num)
                if vuelta_num >= max_vueltas:
                    logger.warning("[PAGOS_GMAIL] Maximo de vueltas (%d) alcanzado.", max_vueltas)
                    break
        else:
            process_message_batch(messages, "inicial")

        # Fin del loop'''

out = c[:line_start] + new_block + "\n\n" + c[end:]
with open(path, "w", encoding="utf-8") as f:
    f.write(out)
print("OK: bucle vuelta completa aplicado")
