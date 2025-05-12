import sqlite3
from datetime import datetime
import threading
class LocalDB:
    def __init__(self, db_path="attendance.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self.create_tables()


    def create_tables(self):
        with self.lock:
            c = self.conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    idempresa INTEGER,
                    idoficina INTEGER,
                    idagente INTEGER PRIMARY KEY,
                    name TEXT,
                    enrolled_at TEXT
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idagente INTEGER,
                    finger_id INTEGER,
                    FOREIGN KEY (idagente) REFERENCES users(idagente)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    timestamp TEXT,
                    type TEXT,
                    synced INTEGER DEFAULT 0
                )
            ''')
            self.conn.commit()

    def add_user(self, idempresa, idoficina, idagente, name=""):
        with self.lock:
            c = self.conn.cursor()
            c.execute(
                'INSERT OR REPLACE INTO users (idempresa, idoficina, idagente, name, enrolled_at) VALUES (?, ?, ?, ?, ?)',
                (idempresa, idoficina, idagente, name, datetime.now().isoformat())
            )
            self.conn.commit()

    def get_finger_ids_by_user(self, idagente):
        c = self.conn.cursor()
        rows = c.execute("SELECT finger_id FROM fingerprints WHERE idagente = ?", (idagente,)).fetchall()
        return [r[0] for r in rows]

    def count_fingerprints_by_user(self, idagente):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM fingerprints WHERE idagente = ?", (idagente,))
        result = c.fetchone()
        return result[0] if result else 0
    
    def count_all_fingerprints(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM fingerprints")
        return c.fetchone()[0]

    def remove_fingerprints_by_user(self, idagente):
        try:
            self.lock.acquire()
            c = self.conn.cursor()
            c.execute("DELETE FROM fingerprints WHERE idagente = ?", (idagente,))
            self.conn.commit()
        except Exception as e:
            print(f"Error removing fingerprints for user {idagente}: {e}")
        finally:
            self.lock.release()

    def get_finger_ids_by_user(self, idagente):
        return [row[0] for row in self.conn.execute(
            "SELECT finger_id FROM fingerprints WHERE idagente = ?", (idagente,)
        )]

    def get_next_available_finger_id(self, max_id=127):
        c = self.conn.cursor()
        used_ids = c.execute('SELECT finger_id FROM fingerprints').fetchall()
        used_ids = set(row[0] for row in used_ids)

        for i in range(max_id + 1):
            if i not in used_ids:
                return i

        raise Exception("No available fingerprint slots")

    def add_fingerprint(self, idagente, finger_id):
        with self.lock:
            c = self.conn.cursor()
            c.execute('INSERT INTO fingerprints (idagente, finger_id) VALUES (?, ?)', (idagente, finger_id))
            self.conn.commit()
    
    def get_agent_by_finger_id(self, finger_id):
        c = self.conn.cursor()
        c.execute('SELECT idagente FROM fingerprints WHERE finger_id = ?', (finger_id,))
        result = c.fetchone()
        return result[0] if result else None
    
    def add_event(self, user_id, type='checkin', timestamp=None):
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        with self.lock:
            c = self.conn.cursor()
            c.execute('INSERT INTO events (user_id, timestamp, type) VALUES (?, ?, ?)',
                    (user_id, timestamp, type))
            self.conn.commit()

    def get_user(self, user_id):
        c = self.conn.cursor()
        c.execute('SELECT * FROM users WHERE idagente = ?', (user_id,))
        return c.fetchone()

    def get_unsynced_events(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM events WHERE synced = 0')
        return c.fetchall()

    def mark_event_synced(self, event_id):
        with self.lock:
            c = self.conn.cursor()
            c.execute('UPDATE events SET synced = 1 WHERE id = ?', (event_id,))
            self.conn.commit()

    def get_unsynced_attlogs(self):
        c = self.conn.cursor()
        c.execute('''
            SELECT events.id, user_id, timestamp
            FROM events
            WHERE synced = 0
        ''')
        return c.fetchall()