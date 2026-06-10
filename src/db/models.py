import json
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    importance TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    content_vi TEXT NOT NULL,
    content_en TEXT NOT NULL,
    coin_tags TEXT NOT NULL,
    format TEXT NOT NULL,
    status TEXT NOT NULL,
    scheduled_time TEXT,
    posted_at TEXT,
    error_msg TEXT,
    batch TEXT NOT NULL,
    image_url TEXT
);

CREATE TABLE IF NOT EXISTS dedup (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title_normalized TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dedup_title ON dedup(title_normalized);
CREATE INDEX IF NOT EXISTS idx_posts_batch ON posts(batch);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)
            # Idempotent column migration for existing DBs
            cols = {r[1] for r in c.execute("PRAGMA table_info(posts)").fetchall()}
            if "image_url" not in cols:
                c.execute("ALTER TABLE posts ADD COLUMN image_url TEXT")

    def insert_article(self, *, source: str, url: str, title: str, content: str,
                       scraped_at: str, importance: str) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO articles(source,url,title,content,scraped_at,importance) "
                "VALUES (?,?,?,?,?,?)",
                (source, url, title, content, scraped_at, importance),
            )
            return cur.lastrowid

    def list_articles_unposted(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT a.* FROM articles a "
                "LEFT JOIN posts p ON p.article_id = a.id "
                "WHERE p.id IS NULL ORDER BY a.scraped_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_post(self, *, article_id: int, content_vi: str, content_en: str,
                    coin_tags: list[str], format: str, batch: str,
                    scheduled_time: str | None = None,
                    image_url: str | None = None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO posts(article_id,content_vi,content_en,coin_tags,format,"
                "status,scheduled_time,batch,image_url) VALUES (?,?,?,?,?,?,?,?,?)",
                (article_id, content_vi, content_en, json.dumps(coin_tags),
                 format, "pending", scheduled_time, batch, image_url),
            )
            return cur.lastrowid

    def update_post_status(self, post_id: int, *, status: str,
                           posted_at: str | None = None,
                           error_msg: str | None = None) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE posts SET status=?, posted_at=COALESCE(?,posted_at), "
                "error_msg=COALESCE(?,error_msg) WHERE id=?",
                (status, posted_at, error_msg, post_id),
            )

    def list_posts_by_batch(self, batch: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM posts WHERE batch=? ORDER BY scheduled_time", (batch,)
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_dedup(self, *, url: str, title_normalized: str, created_at: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO dedup(url,title_normalized,created_at) VALUES (?,?,?)",
                (url, title_normalized, created_at),
            )

    def dedup_url_exists(self, url: str) -> bool:
        with self._conn() as c:
            row = c.execute("SELECT 1 FROM dedup WHERE url=?", (url,)).fetchone()
            return row is not None

    def list_dedup_titles(self) -> list[str]:
        with self._conn() as c:
            rows = c.execute("SELECT title_normalized FROM dedup").fetchall()
            return [r["title_normalized"] for r in rows]

    def list_posts_for_summary(self, since_iso: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM posts WHERE posted_at >= ? OR scheduled_time >= ?",
                (since_iso, since_iso),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_failed_posts_by_batch(self, batch: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM posts WHERE batch=? AND status='failed'", (batch,)
            ).fetchall()
            return [dict(r) for r in rows]
