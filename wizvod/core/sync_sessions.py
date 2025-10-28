"""
Modul za upravljanje sesijama sinhronizacije i ispisivanje izvoda.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from wizvod.core.db import Database
from wizvod.core.logger import get_logger

log = get_logger("sync_sessions")


class SyncSession:
    """Predstavlja jednu sesiju sinhronizacije."""

    def __init__(self, db: Database):
        self.db = db
        self.session_id = str(uuid.uuid4())[:8]
        self.started_at = datetime.now()
        self.ended_at = None
        self.status = "running"
        self.total_downloaded = 0
        self.total_errors = 0
        self.total_skipped = 0

    def start(self):
        """Započinje novu sesiju sinhronizacije."""
        self.db.conn.execute("""
            INSERT INTO sync_sessions 
            (session_id, started_at, status, total_downloaded, total_errors, total_skipped)
            VALUES (?, ?, ?, 0, 0, 0)
        """, (self.session_id, self.started_at.isoformat(), self.status))
        self.db.conn.commit()
        log.info(f"🔵 Započeta sesija sinhronizacije: {self.session_id}")

    def end(self, status: str = "completed"):
        """Završava sesiju sinhronizacije."""
        self.ended_at = datetime.now()
        self.status = status

        # Prebrojavanje rezultata
        cur = self.db.conn.execute("""
            SELECT 
                COUNT(CASE WHEN status = 'ok' THEN 1 END) as ok_count,
                COUNT(CASE WHEN status = 'error' THEN 1 END) as err_count,
                COUNT(CASE WHEN status = 'skipped' THEN 1 END) as skip_count
            FROM logs
            WHERE session_id = ?
        """, (self.session_id,))
        row = cur.fetchone()

        self.total_downloaded = row[0] if row else 0
        self.total_errors = row[1] if row else 0
        self.total_skipped = row[2] if row else 0

        self.db.conn.execute("""
            UPDATE sync_sessions
            SET ended_at = ?,
                status = ?,
                total_downloaded = ?,
                total_errors = ?,
                total_skipped = ?
            WHERE session_id = ?
        """, (self.ended_at.isoformat(), self.status,
              self.total_downloaded, self.total_errors, self.total_skipped,
              self.session_id))
        self.db.conn.commit()

        duration = (self.ended_at - self.started_at).total_seconds()
        log.info(f"✅ Sesija {self.session_id} završena. "
                 f"Preuzeto: {self.total_downloaded}, "
                 f"Greške: {self.total_errors}, "
                 f"Preskočeno: {self.total_skipped}, "
                 f"Trajanje: {duration:.1f}s")


class SyncSessionManager:
    """Manager za rad sa sesijama sinhronizacije."""

    def __init__(self, db: Database):
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        """Kreira tabele ako ne postoje."""
        self.db.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sync_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                status TEXT NOT NULL,
                total_downloaded INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0,
                total_skipped INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_started 
            ON sync_sessions(started_at DESC);

            CREATE INDEX IF NOT EXISTS idx_sessions_status 
            ON sync_sessions(status);
        """)

        # Dodaj session_id kolonu u logs ako ne postoji
        try:
            self.db.conn.execute("""
                ALTER TABLE logs ADD COLUMN session_id TEXT
            """)
            self.db.conn.commit()
            log.info("✅ Dodana session_id kolona u logs tabelu")
        except Exception:
            pass  # Kolona već postoji

        # Kreiraj index
        try:
            self.db.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_session 
                ON logs(session_id)
            """)
            self.db.conn.commit()
        except Exception:
            pass

    def get_sessions(self, limit: int = 50) -> List[Dict]:
        """Vraća listu svih sesija."""
        cur = self.db.conn.execute("""
            SELECT 
                id,
                session_id,
                started_at,
                ended_at,
                status,
                total_downloaded,
                total_errors,
                total_skipped
            FROM sync_sessions
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))

        sessions = []
        for row in cur.fetchall():
            sessions.append({
                'id': row[0],
                'session_id': row[1],
                'started_at': row[2],
                'ended_at': row[3],
                'status': row[4],
                'total_downloaded': row[5],
                'total_errors': row[6],
                'total_skipped': row[7]
            })

        return sessions

    def get_session_logs(self, session_id: str) -> List[Dict]:
        """Vraća sve logove za određenu sesiju."""
        cur = self.db.conn.execute("""
            SELECT 
                l.id,
                c.name AS client_name,
                l.subject,
                l.sender,
                l.statement_number,
                l.file_path,
                l.status,
                l.message,
                l.created_at
            FROM logs l
            LEFT JOIN clients c ON c.id = l.client_id
            WHERE l.session_id = ?
            ORDER BY l.created_at ASC
        """, (session_id,))

        logs = []
        for row in cur.fetchall():
            logs.append({
                'id': row[0],
                'client_name': row[1] or '—',
                'subject': row[2],
                'sender': row[3],
                'statement_number': row[4],
                'file_path': row[5],
                'status': row[6],
                'message': row[7],
                'created_at': row[8]
            })

        return logs

    def delete_session(self, session_id: str):
        """Briše sesiju i sve vezane logove."""
        self.db.conn.execute("DELETE FROM logs WHERE session_id = ?", (session_id,))
        self.db.conn.execute("DELETE FROM sync_sessions WHERE session_id = ?", (session_id,))
        self.db.conn.commit()
        log.info(f"🗑️ Obrisana sesija: {session_id}")

    def clear_old_sessions(self, keep_last: int = 30):
        """Čisti stare sesije, zadržava samo poslednje N."""
        cur = self.db.conn.execute("""
            SELECT session_id FROM sync_sessions
            ORDER BY started_at DESC
            LIMIT -1 OFFSET ?
        """, (keep_last,))

        old_sessions = [row[0] for row in cur.fetchall()]

        for sid in old_sessions:
            self.delete_session(sid)

        log.info(f"🧹 Obrisano {len(old_sessions)} starih sesija")