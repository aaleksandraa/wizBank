import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from wizvod.core.db import Database
from wizvod.core.email_fetcher import EmailFetcher
from wizvod.core.pdf_parser import PDFParser
from wizvod.core.logger import get_logger
from wizvod.core.license_manager import LicenseManager
from wizvod.core.config_manager import AppConfig
from wizvod.core.sync_sessions import SyncSession

log = get_logger("worker")


def run_worker():
    """Glavna funkcija workera — automatsko preuzimanje izvoda sa podrškom za sesije."""
    log.info("Pokrećem worker proces...")

    from wizvod.core.db import DB_PATH

    log.info(f"🧭 Trenutni radni direktorij: {os.getcwd()}")
    log.info(f"👤 Korisnički HOME: {Path.home()}")
    log.info(f"📦 Baza: {DB_PATH}")

    # === Inicijalizacija modula ===
    db = Database()
    cfg = AppConfig(db)
    lic = LicenseManager(db)

    # Provjera licence
    try:
        lic.ensure_valid_or_exit()
    except SystemExit:
        log.error("❌ Licenca nije validna. Worker ne može raditi.")
        return
    log.info("✅ Licenca je validna.")

    # === Kreiraj sesiju sinhronizacije ===
    session = SyncSession(db)
    session.start()

    try:
        settings = cfg.get_settings()
        lookback_days = int(settings.get("lookback_days", 7))
        unread_only = settings.get("read_mode", "unread") == "unread"
        mark_as_read = settings.get("mark_as_read", "1") == "1"

        since = datetime.now() - timedelta(days=lookback_days)
        accounts = db.list_mail_accounts()
        clients = db.list_clients()

        total_downloaded = 0
        total_skipped = 0
        total_errors = 0

        if not accounts:
            log.warning("⚠️ Nema konfiguriranih email naloga.")
            session.end("error")
            return

        if not clients:
            log.warning("⚠️ Nema konfiguriranih klijenata.")
            session.end("error")
            return

        fetcher = EmailFetcher()
        parser = PDFParser()

        for acc in accounts:
            email = acc.get("email")
            log.info(f"🔍 Provjeravam nalog {email} — broj klijenata: {len(clients)}")

            try:
                fetcher.connect_imap(acc)
                log.info(f"✅ Povezan na {email}")
            except Exception as e:
                log.error(f"❌ Neuspjelo povezivanje za {email}: {e}")
                total_errors += 1
                continue

            for client in clients:
                try:
                    sender_list = [s.strip() for s in client["sender_email"].split(",") if s.strip()]
                    if not sender_list:
                        log.warning(f"⚠️ Klijent '{client['name']}' nema definisan sender_email.")
                        continue

                    for sender in sender_list:
                        log.info(f"   📧 Tražim poruke od: {sender}")
                        msgs = fetcher.search_messages(since, sender, unread_only)
                        log.info(f"   📨 Pronađeno {len(msgs)} poruka od {sender} u zadnjih {lookback_days} dana")

                        if not msgs:
                            continue

                        for msg in msgs:
                            subj = fetcher.get_subject(msg)
                            sender_addr = msg.get("From", "")
                            attachments = fetcher.extract_attachments(msg)
                            if not attachments:
                                continue

                            for fname, content in attachments:
                                try:
                                    # 1️⃣ pročitaj PDF tekst
                                    text = parser.read_text_from_pdf_bytes(content)

                                    # 2️⃣ izvuci broj računa i broj izvoda
                                    acct_no, stmt_no = parser.extract_all(sender_addr, subj, fname, text)
                                    stmt_no = stmt_no or "unknown"

                                    # 3️⃣ provjera duplikata
                                    cur = db.conn.execute(
                                        "SELECT 1 FROM logs WHERE client_id=? AND statement_number=? LIMIT 1",
                                        (client["id"], stmt_no),
                                    ).fetchone()
                                    if cur:
                                        total_skipped += 1
                                        db.add_log(
                                            client["id"],
                                            subj,
                                            sender_addr,
                                            stmt_no,
                                            fname,
                                            "skipped",
                                            "Izvod već preuzet.",
                                            session_id=session.session_id,
                                        )
                                        continue

                                    # 4️⃣ spremanje PDF-a
                                    client_dir = Path(client["folder_path"])
                                    client_dir.mkdir(parents=True, exist_ok=True)

                                    base_name = stmt_no if stmt_no and stmt_no != "unknown" else Path(fname).stem
                                    save_name = f"{base_name}.pdf"
                                    pdf_path = client_dir / save_name

                                    counter = 2
                                    while pdf_path.exists():
                                        save_name = f"{base_name}_{counter}.pdf"
                                        pdf_path = client_dir / save_name
                                        counter += 1

                                    pdf_path.write_bytes(content)

                                    db.add_log(
                                        client["id"],
                                        subj,
                                        sender_addr,
                                        stmt_no,
                                        str(pdf_path),
                                        "ok",
                                        f"Izvod {stmt_no} preuzet i sačuvan kao {save_name}.",
                                        session_id=session.session_id,
                                    )
                                    total_downloaded += 1

                                    if mark_as_read:
                                        fetcher.mark_as_read(msg)

                                except Exception as e:
                                    total_errors += 1
                                    err_text = traceback.format_exc()
                                    log.error(f"❌ Greška u obradi {fname}: {e}\n{err_text}")
                                    db.add_log(
                                        client["id"],
                                        subj,
                                        sender_addr,
                                        "?",
                                        fname,
                                        "error",
                                        str(e),
                                        session_id=session.session_id,
                                    )

                except Exception as e:
                    total_errors += 1
                    log.error(f"❌ Greška kod klijenta {client['name']}: {e}")
                    continue

            fetcher.close()

        session.end("completed")
        log.info(f"✅ Worker završio. Preuzeto: {total_downloaded}, Preskočeno: {total_skipped}, Greške: {total_errors}")

    except Exception as e:
        log.exception("❌ Kritična greška u workeru:")
        session.end("error")


if __name__ == "__main__":
    try:
        run_worker()
    except Exception as e:
        log.error(f"❌ Neočekivana greška pri pokretanju workera: {e}\n{traceback.format_exc()}")
