import sqlite3
import json
import os
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), 'cyberspace.db')
db_lock = threading.Lock()

def init_db():
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS store (key TEXT PRIMARY KEY, data TEXT)''')
        conn.commit()
        conn.close()

def save_data(key, data):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO store (key, data) VALUES (?, ?)''', (key, json.dumps(data)))
        conn.commit()
        conn.close()

def load_data(key, default):
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''SELECT data FROM store WHERE key = ?''', (key,))
            row = c.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
    except:
        pass
    return default
