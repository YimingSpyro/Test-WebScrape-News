import sqlite3
import json
import time

class CacheDB:
    def __init__(self, path="data/cache.db"):
        self.path = path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            url TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            meta TEXT,
            ts INTEGER
        );
        """)
        conn.commit()
        conn.close()

    def get(self, url, max_age_seconds=86400):
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute("SELECT title, summary, meta, ts FROM summaries WHERE url = ?", (url,))
        r = c.fetchone()
        conn.close()
        if not r:
            return None
        title, summary, meta_json, ts = r
        if int(time.time()) - ts > max_age_seconds:
            return None
        return {"title": title, "summary": summary, "meta": json.loads(meta_json)}

    def save(self, url, title, summary, meta):
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute("""
        INSERT OR REPLACE INTO summaries (url, title, summary, meta, ts)
        VALUES (?, ?, ?, ?, ?)
        """, (url, title, summary, json.dumps(meta), int(time.time())))
        conn.commit()
        conn.close()
