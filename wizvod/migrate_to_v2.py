"""
Migracioni script za Wizvod v2.0

Dodaje nove tabele i kolone potrebne za funkcionalnost istorije i štampanja.

Korištenje:
    python migrate_to_v2.py
"""

import sqlite3
from pathlib import Path
import sys


def migrate_database():
    """Vrši migraciju baze na v2.0 strukturu."""

    # Putanja do baze
    db_path = Path.home() / ".wizvod" / "data" / "wizvod.db"

    if not db_path.exists():
        print("❌ Baza ne postoji. Prvo pokrenite aplikaciju.")
        return False

    print(f"🔍 Pronađena baza: {db_path}")

    # Backup
    backup_path = db_path.parent / f"wizvod_backup_{int(Path.ctime(db_path))}.db"
    print(f"💾 Kreiram backup: {backup_path}")

    import shutil
    shutil.copy2(db_path, backup_path)

    # Konekcija
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("\n🔄 Pokrećem migraciju...\n")

    # ================================================================
    # 1. Kreiraj sync_sessions tabelu
    # ================================================================
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                status TEXT NOT NULL,
                total_downloaded INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0,
                total_skipped INTEGER DEFAULT 0
            )
        """)
        print("✅ Tabela 'sync_sessions' kreirana")
    except Exception as e:
        print(f"⚠️  Tabela 'sync_sessions': {e}")

    # ================================================================
    # 2. Dodaj session_id kolonu u logs
    # ================================================================
    try:
        cur.execute("SELECT session_id FROM logs LIMIT 1")
        print("⚠️  Kolona 'session_id' već postoji u 'logs'")
    except sqlite3.OperationalError:
        try:
            cur.execute("ALTER TABLE logs ADD COLUMN session_id TEXT")
            print("✅ Kolona 'session_id' dodana u 'logs'")
        except Exception as e:
            print(f"❌ Greška pri dodavanju 'session_id': {e}")

    # ================================================================
    # 3. Kreiraj indekse
    # ================================================================
    indexes = [
        ("idx_sessions_started", "CREATE INDEX IF NOT EXISTS idx_sessions_started ON sync_sessions(started_at DESC)"),
        ("idx_sessions_status", "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sync_sessions(status)"),
        ("idx_logs_session", "CREATE INDEX IF NOT EXISTS idx_logs_session ON logs(session_id)"),
    ]

    for idx_name, sql in indexes:
        try:
            cur.execute(sql)
            print(f"✅ Index '{idx_name}' kreiran")
        except Exception as e:
            print(f"⚠️  Index '{idx_name}': {e}")

    # ================================================================
    # 4. Kreiraj početne sesije za postojeće logove (opciono)
    # ================================================================
    try:
        # Grupiši postojeće logove po datumu
        cur.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as cnt
            FROM logs
            WHERE session_id IS NULL
            GROUP BY DATE(created_at)
            ORDER BY created_at DESC
            LIMIT 10
        """)

        dates = cur.fetchall()

        if dates:
            print(f"\n📅 Pronađeno {len(dates)} dana sa logovima bez sesija")
            print("   Kreiram retrospektivne sesije...")

            for date_str, count in dates:
                import uuid
                session_id = f"retro_{str(uuid.uuid4())[:8]}"

                # Kreiraj sesiju
                cur.execute("""
                    INSERT INTO sync_sessions 
                    (session_id, started_at, ended_at, status, total_downloaded, total_errors, total_skipped)
                    SELECT 
                        ?,
                        MIN(created_at),
                        MAX(created_at),
                        'completed',
                        COUNT(CASE WHEN status = 'ok' THEN 1 END),
                        COUNT(CASE WHEN status = 'error' THEN 1 END),
                        COUNT(CASE WHEN status = 'skipped' THEN 1 END)
                    FROM logs
                    WHERE DATE(created_at) = ? AND session_id IS NULL
                """, (session_id, date_str))

                # Ažuriraj logove
                cur.execute("""
                    UPDATE logs
                    SET session_id = ?
                    WHERE DATE(created_at) = ? AND session_id IS NULL
                """, (session_id, date_str))

                print(f"   ✅ Sesija '{session_id}' za {date_str} ({count} logova)")
        else:
            print("\n✅ Nema starih logova za migraciju")

    except Exception as e:
        print(f"⚠️  Retrospektivne sesije: {e}")

    # ================================================================
    # COMMIT
    # ================================================================
    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ Migracija uspješno završena!")
    print("=" * 60)
    print(f"\n📁 Backup sačuvan: {backup_path}")
    print(f"📁 Ažurirana baza: {db_path}")
    print(f"\n🚀 Možete pokrenuti Wizvod v2.0")

    return True


def verify_migration():
    """Provjerava da li je migracija uspješna."""
    db_path = Path.home() / ".wizvod" / "data" / "wizvod.db"

    if not db_path.exists():
        return False

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("\n🔍 Verifikacija migracije:\n")

    # Provjeri tabele
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]

    print("📋 Tabele:")
    for table in tables:
        print(f"   • {table}")

    # Provjeri kolone u logs
    cur.execute("PRAGMA table_info(logs)")
    columns = [row[1] for row in cur.fetchall()]

    print("\n📋 Kolone u 'logs':")
    for col in columns:
        print(f"   • {col}")