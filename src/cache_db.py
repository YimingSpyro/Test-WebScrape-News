# src/cache_db.py
import os
import sqlite3
import json
import time
import tempfile
import warnings
from typing import Optional, Any

class CacheDB:
    def __init__(self, path: Optional[str] = None):
        default = "data/cache.db"
        self.path = path or os.environ.get("CACHE_DB_PATH", default)
        self.path = os.path.abspath(self.path)

        # Try to create parent dir (may fail on some hosts)
        dirpath = os.path.dirname(self.path)
        try:
            os.makedirs(dirpath, exist_ok=True)
        except Exception as e:
            warnings.warn(f"Could not create directory {dirpath}: {e}. Falling back to temp dir.")
            tmp = tempfile.gettempdir()
            self.path = os.path.join(tmp, os.path.basename(self.path))

        # Try to init DB; fallback to in-memory if still failing
        try:
            self._init_db()
        except sqlite3.OperationalError as e:
            warnings.warn(f"Failed to initialize DB at {self.path}: {e}. Using in-memory DB instead.")
            self.path = ":memory:"
            self._init_db()

    def _init_db(self):
        # check_same_thread=False for multi-threaded environments like Streamlit's worker threads
        conn = sqlite3.connect(self.path, check_same_thread=False)
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
        conn = sqlite3.connect(self.path, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT title, summary, meta, ts FROM summaries WHERE url = ?", (url,))
        r = c.fetchone()
        conn.close()
        if not r:
            return None
        title, summary_json, meta_json, ts = r
        if int(time.time()) - ts > max_age_seconds:
            return None
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
        conn = sqlite3.connect(self.path, check_same_thread=False)
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
