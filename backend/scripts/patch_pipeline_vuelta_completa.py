# -*- coding: utf-8 -*-
"""
Parche: pipeline Gmail debe volver al inicio de la bandeja hasta cumplir vuelta completa.
- Con filtro "unread": un solo bucle que lista desde inicio -> procesa hasta el final -> vuelve a listar;
  termina cuando una pasada no devuelve correos (vuelta completa).
- Sin límite para "unread" (igual que "all").
"""
import re

PATH = "app/services/pagos_gmail/pipeline.py"

def main():
    with open(PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1) Sin límite para "unread" además de "all"
    old1 = """        max_emails = getattr(settings, "PAGOS_GMAIL_MAX_EMAILS_PER_RUN", 0)
        total = len(messages)
        if scan_filter == "all":
            max_emails = 0"""
    new1 = """        max_emails = getattr(settings, "PAGOS_GMAIL_MAX_EMAILS_PER_RUN", 0)
        total = len(messages)
        # Con "unread" o "all" procesamos todos (sin límite); "unread" además hace vueltas hasta completar.
        if scan_filter in ("all", "unread"):
            max_emails = 0"""
    if old1 in content:
        content = content.replace(old1, new1, 1)
        print("OK: max_emails para unread/all")
    else:
        print("SKIP (no match): max_emails block")

    # 2) Reemplazar: process_message_batch(messages, "inicial") + ciclo revisión unread
    #    por: bucle único para unread (listar desde inicio -> procesar -> repetir hasta vuelta completa)
    pattern = r'(\s+)process_message_batch\(messages, "inicial"\)\s+\n\s+# Ciclo de revisi[^\n]+\s+\n\s+if scan_filter == "unread":\s+\n\s+max_revision_passes = 10\s+\n\s+for pass_num in range\(1, max_revision_passes \+ 1\):\s+\n\s+raw_again = list_messages_by_filter\(gmail_svc, "unread"\)\s+\n\s+again_dedup = \[\]\s+\n\s+seen_again = set\(\)\s+\n\s+for m in raw_again:\s+\n\s+if m\["id"\] in seen_again:\s+\n\s+continue\s+\n\s+seen_again\.add\(m\["id"\]\)\s+\n\s+again_dedup\.append\(m\)\s+\n\s+if not again_dedup:\s+\n\s+if pass_num > 1:\s+\n\s+logger\.warning\("[PAGOS_GMAIL\] Ciclo revisi[^"]+"\)\s+\n\s+break\s+\n\s+if max_emails and max_emails > 0 and len\(again_dedup\) > max_emails:\s+\n\s+again_dedup = again_dedup\[:max_emails\]\s+\n\s+logger\.warning\("[PAGOS_GMAIL\] Ciclo revisi[^"]+%d\): %d correo\(s\)[^"]+", pass_num, len\(again_dedup\)\)\s+\n\s+process_message_batch\(again_dedup, "revisi[^"]+%d" % pass_num\)'
    # Simpler: replace the block between two known lines
    old2 = '''        process_message_batch(messages, "inicial")

        # Ciclo de revisión solo para "unread": volver a listar no leídos y procesar hasta que no quede ninguno (máx 10 pasadas)
        if scan_filter == "unread":
            max_revision_passes = 10
            for pass_num in range(1, max_revision_passes + 1):
                raw_again = list_messages_by_filter(gmail_svc, "unread")
                again_dedup = []
                seen_again = set()
                for m in raw_again:
                    if m["id"] in seen_again:
                        continue
                    seen_again.add(m["id"])
                    again_dedup.append(m)
                if not again_dedup:
                    if pass_num > 1:
                        logger.warning("[PAGOS_GMAIL] Ciclo revisión: no quedan no leídos - fin")
                    break
                if max_emails and max_emails > 0 and len(again_dedup) > max_emails:
                    again_dedup = again_dedup[:max_emails]
                logger.warning("[PAGOS_GMAIL] Ciclo revisión (pasada %d): %d correo(s) sin leer - procesando", pass_num, len(again_dedup))
                process_message_batch(again_dedup, "revisi\u00f3n pasada %d" % pass_num)

        # Fin del loop'''

    new2 = '''        # Con "unread": bucle que llega al final de la bandeja y vuelve al inicio hasta vuelta completa (0 sin leer).
        if scan_filter == "unread":
            vuelta_num = 0
            max_vueltas = 20
            while True:
                vuelta_num += 1
                logger.warning("[PAGOS_GMAIL] Listando no leídos desde inicio de bandeja (vuelta %d)...", vuelta_num)
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
                    logger.warning("[PAGOS_GMAIL] Máximo de vueltas (%d) alcanzado.", max_vueltas)
                    break
        else:
            process_message_batch(messages, "inicial")

        # Fin del loop'''

    if "process_message_batch(messages, \"inicial\")" in content and "Ciclo de revisión solo para" in content:
        # Find and replace the block (allow slight encoding differences)
        idx = content.find('        process_message_batch(messages, "inicial")')
        if idx == -1:
            idx = content.find('process_message_batch(messages, "inicial")')
        end_marker = "        # Fin del loop"
        end_idx = content.find(end_marker, idx)
        if end_idx != -1:
            end_idx += len(end_marker)
            before = content[:idx]
            after = content[end_idx:]
            content = before + new2 + "\n\n" + after
            print("OK: bucle vuelta completa")
        else:
            print("SKIP: no encontrado # Fin del loop")
    else:
        print("SKIP: block inicial/revision no encontrado tal cual")

    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("Escrito:", PATH)


if __name__ == "__main__":
    main()
