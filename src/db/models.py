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
    image_url TEXT,
    post_type TEXT,
    article_title TEXT,
    content_type INTEGER,
    binance_id TEXT
);

CREATE TABLE IF NOT EXISTS post_stats (
    binance_id TEXT PRIMARY KEY,
    post_id INTEGER,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    reactions INTEGER,
    bookmarks INTEGER,
    collected_at TEXT
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
            if "post_type" not in cols:
                c.execute("ALTER TABLE posts ADD COLUMN post_type TEXT")
            if "article_title" not in cols:
                c.execute("ALTER TABLE posts ADD COLUMN article_title TEXT")
            if "content_type" not in cols:
                c.execute("ALTER TABLE posts ADD COLUMN content_type INTEGER")
            if "binance_id" not in cols:
                c.execute("ALTER TABLE posts ADD COLUMN binance_id TEXT")

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
                    image_url: str | None = None,
                    post_type: str | None = None,
                    article_title: str | None = None,
                    content_type: int | None = None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO posts(article_id,content_vi,content_en,coin_tags,format,"
                "status,scheduled_time,batch,image_url,post_type,article_title,"
                "content_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (article_id, content_vi, content_en, json.dumps(coin_tags),
                 format, "pending", scheduled_time, batch, image_url,
                 post_type, article_title, content_type),
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

    def set_binance_id(self, post_id: int, binance_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE posts SET binance_id=? WHERE id=?",
                      (binance_id, post_id))

    def find_unmatched_post_by_body(self, body: str) -> dict | None:
        """Best-effort backfill: find a posted row WITHOUT a binance_id whose
        Vietnamese content appears at the start of the given API body text.
        Matches on the first 40 chars of content_vi."""
        if not body:
            return None
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, content_vi, post_type FROM posts "
                "WHERE binance_id IS NULL AND status='posted'"
            ).fetchall()
        body_norm = " ".join(body.split())[:200].lower()
        for r in rows:
            head = " ".join((r["content_vi"] or "").split())[:40].lower()
            if head and head in body_norm:
                return {"post_id": r["id"], "post_type": r["post_type"]}
        return None

    def map_binance_to_post(self) -> dict[str, dict]:
        """Return {binance_id: {post_id, post_type}} for posts that have a
        Binance content id, so stats can be matched back."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, binance_id, post_type FROM posts "
                "WHERE binance_id IS NOT NULL"
            ).fetchall()
            return {r["binance_id"]: {"post_id": r["id"], "post_type": r["post_type"]}
                    for r in rows}

    def upsert_stats(self, *, binance_id: str, post_id: int | None,
                     views: int, likes: int, comments: int, shares: int,
                     reactions: int, bookmarks: int, collected_at: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO post_stats(binance_id,post_id,views,likes,comments,"
                "shares,reactions,bookmarks,collected_at) VALUES (?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(binance_id) DO UPDATE SET post_id=excluded.post_id,"
                "views=excluded.views,likes=excluded.likes,comments=excluded.comments,"
                "shares=excluded.shares,reactions=excluded.reactions,"
                "bookmarks=excluded.bookmarks,collected_at=excluded.collected_at",
                (binance_id, post_id, views, likes, comments, shares,
                 reactions, bookmarks, collected_at),
            )

    def stats_by_post_type(self) -> list[dict]:
        """Aggregate engagement averages per post_type (joined via post_id)."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT p.post_type AS post_type, COUNT(*) AS n, "
                "AVG(s.views) AS avg_views, AVG(s.likes) AS avg_likes, "
                "AVG(s.comments) AS avg_comments, AVG(s.reactions) AS avg_reactions "
                "FROM post_stats s JOIN posts p ON p.id = s.post_id "
                "WHERE p.post_type IS NOT NULL "
                "GROUP BY p.post_type ORDER BY avg_views DESC"
            ).fetchall()
            return [dict(r) for r in rows]

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
