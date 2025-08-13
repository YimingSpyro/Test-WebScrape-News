# src/cache_db.py  (overwrite existing)
import sqlite3
import json
import time
from typing import Optional, Any

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

    def get(self, url: str, max_age_seconds: int = 86400) -> Optional[dict]:
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute("SELECT title, summary, meta, ts FROM summaries WHERE url = ?", (url,))
        r = c.fetchone()
        conn.close()
        if not r:
            return None
        title, summary_json, meta_json, ts = r
        if int(time.time()) - ts > max_age_seconds:
            return None
        # safe loads — tolerate plain strings
        try:
            summary_obj = json.loads(summary_json)
        except Exception:
            summary_obj = summary_json
        try:
            meta_obj = json.loads(meta_json)
        except Exception:
            meta_obj = meta_json
        return {"title": title, "summary": summary_obj, "meta": meta_obj}

    def save(self, url: str, title: str, summary: Any, meta: Any):
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute("""
        INSERT OR REPLACE INTO summaries (url, title, summary, meta, ts)
        VALUES (?, ?, ?, ?, ?)
        """, (url, title,
              json.dumps(summary, ensure_ascii=False),
              json.dumps(meta, ensure_ascii=False),
              int(time.time())))
        conn.commit()
        conn.close()
