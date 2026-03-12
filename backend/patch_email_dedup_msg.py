# Refactor: compute msg_bytes once, use in both sendmail branches
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old_block = """        port = int(cfg.get("smtp_port") or 587)
        all_recipients = to_emails + cc_list + bcc_list
        use_tls = (cfg.get("smtp_use_tls") or "true").lower() == "true"
        if port == 465:
            with smtplib.SMTP_SSL(cfg["smtp_host"], port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.login(cfg["smtp_user"], cfg["smtp_password"])
                msg_str = msg.as_string(policy=__import__("email").policy.SMTP); msg_bytes = msg_str.replace("\\r\\n", "\\n").replace("\\n", "\\r\\n").encode("utf-8"); server.sendmail(msg["From"], all_recipients, msg_bytes)
        else:
            with smtplib.SMTP(cfg["smtp_host"], port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                if use_tls:
                    server.starttls()
                server.login(cfg["smtp_user"], cfg["smtp_password"])
                msg_str = msg.as_string(policy=__import__("email").policy.SMTP); msg_bytes = msg_str.replace("\\r\\n", "\\n").replace("\\n", "\\r\\n").encode("utf-8"); server.sendmail(msg["From"], all_recipients, msg_bytes)"""

new_block = """        port = int(cfg.get("smtp_port") or 587)
        all_recipients = to_emails + cc_list + bcc_list
        use_tls = (cfg.get("smtp_use_tls") or "true").lower() == "true"
        msg_str = msg.as_string(policy=__import__("email").policy.SMTP)
        msg_bytes = msg_str.replace("\\r\\n", "\\n").replace("\\n", "\\r\\n").encode("utf-8")
        if port == 465:
            with smtplib.SMTP_SSL(cfg["smtp_host"], port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.login(cfg["smtp_user"], cfg["smtp_password"])
                server.sendmail(msg["From"], all_recipients, msg_bytes)
        else:
            with smtplib.SMTP(cfg["smtp_host"], port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                if use_tls:
                    server.starttls()
                server.login(cfg["smtp_user"], cfg["smtp_password"])
                server.sendmail(msg["From"], all_recipients, msg_bytes)"""

if new_block in c and "msg_str = msg.as_string" in c and c.count("msg_str = msg.as_string") == 1:
    print("Already deduplicated")
else:
    c = c.replace(old_block, new_block)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Deduplicated msg_str/msg_bytes")
