import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_DIR = Path(Path.home() / ".wizvod")
DB_PATH = APP_DIR / "data" / "wizvod.db"

APP_DIR.mkdir(parents=True, exist_ok=True)
(DB_PATH.parent).mkdir(parents=True, exist_ok=True)


class Database:
    """Centralna SQLite baza podataka za Wizvod aplikaciju."""

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS mail_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            email TEXT NOT NULL,
            imap_host TEXT NOT NULL,
            imap_port INTEGER NOT NULL DEFAULT 993,
            use_ssl INTEGER NOT NULL DEFAULT 1,
            username TEXT,
            secret_encrypted BLOB
        );

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            account_number TEXT NOT NULL,
            bank_code TEXT,
            sender_email TEXT NOT NULL,
            duplicate_policy TEXT NOT NULL DEFAULT 'skip'
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            subject TEXT,
            sender TEXT,
            statement_number TEXT,
            file_path TEXT,
            status TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS license (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            license_json TEXT,
            public_key_pem TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_logs_client ON logs(client_id);
        CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_logs_status ON logs(status);
        """)
        self.conn.commit()

    # ============================================================
    # SETTINGS
    # ============================================================
    def save_setting(self, key: str, value: str):
        """Čuva ili ažurira setting u bazi."""
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()

    def set_setting(self, key: str, value: str):
        """Alias za save_setting (kompatibilnost sa starijim kodom)."""
        self.save_setting(key, value)

    def get_setting(self, key: str) -> Optional[str]:
        """Vraća jednu vrijednost setting-a po ključu."""
        cur = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None

    def get_settings(self) -> Dict[str, Any]:
        """Vraća sve settings kao dictionary."""
        cur = self.conn.execute("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in cur.fetchall()}

    # ============================================================
    # LOGS
    # ============================================================
    def add_log(self, client_id: int, subject: str, sender: str, stmt_no: str,
                file_path: str, status: str, message: str, session_id: str = None):
        """
        Dodaje novi log u bazu.

        Args:
            client_id: ID klijenta
            subject: Subject emaila
            sender: Email pošiljaoca
            stmt_no: Broj izvoda
            file_path: Putanja do sačuvanog fajla
            status: 'ok', 'skipped', 'error'
            message: Poruka/opis/greška
            session_id: ID sesije sinhronizacije (NOVO)
        """
        self.conn.execute("""
        INSERT INTO logs (client_id, subject, sender, statement_number, file_path, status, message, session_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (client_id, subject, sender, stmt_no, file_path, status, message, session_id))
        self.conn.commit()

    def list_logs(self, limit: int = 300) -> List[Dict[str, Any]]:
        """
        Vraća zadnje logove zajedno s imenom klijenta ako postoji.

        ISPRAVLJENO: Query vraća 'client_name' ali dodaje 'client' kao alias
        za kompatibilnost sa starijim kodom.

        Args:
            limit: Maksimalan broj logova

        Returns:
            Lista dictionary-ja sa log podacima
        """
        cur = self.conn.execute("""
            SELECT 
                l.id, 
                c.name AS client_name,
                l.subject, 
                l.sender, 
                l.statement_number AS statement_no, 
                l.file_path AS saved_path,
                l.status, 
                l.message AS error_message, 
                l.created_at
            FROM logs l
            LEFT JOIN clients c ON c.id = l.client_id
            ORDER BY l.id DESC
            LIMIT ?
        """, (limit,))

        result = []
        for row in cur.fetchall():
            d = dict(row)
            # Dodaj 'client' kao alias za 'client_name' (kompatibilnost)
            d['client'] = d.get('client_name', '—')
            # Dodaj i statement_number kao alias (neki kod koristi ovo ime)
            if 'statement_no' in d:
                d['statement_number'] = d['statement_no']
            result.append(d)

        return result

    def clear_logs(self):
        """Briše sve logove iz baze."""
        self.conn.execute("DELETE FROM logs")
        self.conn.commit()

    def get_logs_count_today(self) -> int:
        """Vraća broj uspješno preuzetih izvoda danas."""
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        cur = self.conn.execute("""
            SELECT COUNT(*) as cnt 
            FROM logs 
            WHERE status = 'ok' 
            AND DATE(created_at) = ?
        """, (today,))
        row = cur.fetchone()
        return row['cnt'] if row else 0

    # ============================================================
    # CLIENTS
    # ============================================================
    def add_client(self, name: str, account_number: str, bank_code: str,
                   sender_email: str, folder_path: str, duplicate_policy: str = "skip") -> int:
        """
        Dodaje novog klijenta i vraća ID.

        Args:
            name: Naziv firme/klijenta
            account_number: Broj računa
            bank_code: Kod banke
            sender_email: Email banke (pošiljalac izvoda)
            folder_path: Folder za čuvanje izvoda
            duplicate_policy: 'skip' ili 'suffix'

        Returns:
            ID novog klijenta
        """
        cur = self.conn.execute("""
            INSERT INTO clients (name, account_number, bank_code, sender_email, folder_path, duplicate_policy)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, account_number, bank_code, sender_email, folder_path, duplicate_policy))
        self.conn.commit()
        return cur.lastrowid

    def update_client(self, client_id: int, name: str, account_number: str, bank_code: str,
                      sender_email: str, folder_path: str, duplicate_policy: str):
        """Ažurira postojeće podatke o klijentu."""
        self.conn.execute("""
            UPDATE clients
            SET name = ?, account_number = ?, bank_code = ?, sender_email = ?, folder_path = ?, duplicate_policy = ?
            WHERE id = ?
        """, (name, account_number, bank_code, sender_email, folder_path, duplicate_policy, client_id))
        self.conn.commit()

    def delete_client(self, client_id: int):
        """Briše klijenta po ID-u."""
        self.conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        self.conn.commit()

    def get_client(self, client_id: int) -> Optional[Dict[str, Any]]:
        """Vraća jednog klijenta po ID-u."""
        cur = self.conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_clients(self) -> List[Dict[str, Any]]:
        """Vraća sve klijente (uređene po nazivu)."""
        cur = self.conn.execute("SELECT * FROM clients ORDER BY name ASC")
        return [dict(row) for row in cur.fetchall()]

    # ============================================================
    # MAIL ACCOUNTS
    # ============================================================
    def add_mail_account(self, provider: str, email: str, imap_host: str, imap_port: int,
                         use_ssl: bool, username: str, secret_encrypted: bytes):
        """Dodaje novi IMAP mail nalog u bazu."""
        self.conn.execute("""
            INSERT INTO mail_accounts (provider, email, imap_host, imap_port, use_ssl, username, secret_encrypted)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (provider, email, imap_host, imap_port, int(use_ssl), username, secret_encrypted))
        self.conn.commit()

    def update_mail_account(self, account_id: int, provider: str, email: str, imap_host: str,
                            imap_port: int, use_ssl: bool, username: str, secret_encrypted: bytes):
        """Ažurira postojeći IMAP nalog."""
        self.conn.execute("""
            UPDATE mail_accounts
            SET provider=?, email=?, imap_host=?, imap_port=?, use_ssl=?, username=?, secret_encrypted=?
            WHERE id=?
        """, (provider, email, imap_host, imap_port, int(use_ssl), username, secret_encrypted, account_id))
        self.conn.commit()

    def delete_mail_account(self, account_id: int):
        """Briše IMAP nalog po ID-u."""
        self.conn.execute("DELETE FROM mail_accounts WHERE id=?", (account_id,))
        self.conn.commit()

    def get_mail_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Vraća jedan IMAP nalog po ID-u."""
        cur = self.conn.execute("SELECT * FROM mail_accounts WHERE id=?", (account_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_mail_accounts(self) -> List[Dict[str, Any]]:
        """Vraća sve IMAP naloge."""
        cur = self.conn.execute("SELECT * FROM mail_accounts ORDER BY email ASC")
        return [dict(row) for row in cur.fetchall()]

    # ============================================================
    # LICENSE
    # ============================================================
    def get_license(self) -> tuple:
        """Vraća (license_json, public_key_pem) ili (None, None)."""
        cur = self.conn.execute("SELECT license_json, public_key_pem FROM license WHERE id=1")
        row = cur.fetchone()
        if row:
            return (row['license_json'], row['public_key_pem'])
        return (None, None)

    def save_license(self, license_json: str, public_key_pem: str):
        """Čuva ili ažurira licencu."""
        self.conn.execute("""
            INSERT INTO license(id, license_json, public_key_pem) VALUES(1,?,?) 
            ON CONFLICT(id) DO UPDATE 
            SET license_json=excluded.license_json, public_key_pem=excluded.public_key_pem
        """, (license_json, public_key_pem))
        self.conn.commit()

    # ============================================================
    # UTILITY
    # ============================================================
    def vacuum(self):
        """Optimizuje bazu (smanjuje veličinu)."""
        self.conn.execute("VACUUM")
        self.conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """Vraća osnovnu statistiku baze."""
        stats = {}

        cur = self.conn.execute("SELECT COUNT(*) as cnt FROM clients")
        stats['clients_count'] = cur.fetchone()['cnt']

        cur = self.conn.execute("SELECT COUNT(*) as cnt FROM mail_accounts")
        stats['accounts_count'] = cur.fetchone()['cnt']

        cur = self.conn.execute("SELECT COUNT(*) as cnt FROM logs")
        stats['logs_count'] = cur.fetchone()['cnt']

        cur = self.conn.execute("SELECT COUNT(*) as cnt FROM logs WHERE status='ok'")
        stats['success_count'] = cur.fetchone()['cnt']

        cur = self.conn.execute("SELECT COUNT(*) as cnt FROM logs WHERE status='error'")
        stats['error_count'] = cur.fetchone()['cnt']

        return stats

    def close(self):
        """Zatvara konekciju."""
        try:
            self.conn.close()
        except Exception:
            pass

    def __del__(self):
        """Zatvara konekciju pri uništenju objekta."""
        self.close()