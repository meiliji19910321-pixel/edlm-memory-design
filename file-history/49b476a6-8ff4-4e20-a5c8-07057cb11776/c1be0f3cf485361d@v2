"""
Layer 1: 数据库初始化
SQLite + FTS5 + sqlite-vec
"""
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = r"D:\CLAUDE.MD\mem\.db\memory.db"


def get_version() -> str:
    """返回当前记忆系统版本"""
    return "1.0.0"


def init_db():
    """初始化数据库 schema"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # ---- memories 主表 ----
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            description     TEXT NOT NULL DEFAULT '',
            type            TEXT NOT NULL CHECK(type IN (
                                'identity','artifact','topic','memory','conversation'
                            )),
            content         TEXT NOT NULL DEFAULT '',
            tags            TEXT NOT NULL DEFAULT '[]',
            trust_level     INTEGER NOT NULL DEFAULT 1 CHECK(trust_level BETWEEN 1 AND 3),
            version_chain   TEXT NOT NULL DEFAULT '[]',
            topic_ref       TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)

    # ---- FTS5 全文搜索 ----
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            name, description, content, tags,
            content=memories,
            content_rowid=id
        )
    """)

    # ---- 触发器：memories_fts 同步 ----
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_fts_insert
        AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, name, description, content, tags)
            VALUES (new.id, new.name, new.description, new.content, new.tags);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_fts_delete
        AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, name, description, content, tags)
            VALUES ('delete', old.id, old.name, old.description, old.content, old.tags);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_fts_update
        AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, name, description, content, tags)
            VALUES ('delete', old.id, old.name, old.description, old.content, old.tags);
            INSERT INTO memories_fts(rowid, name, description, content, tags)
            VALUES (new.id, new.name, new.description, new.content, new.tags);
        END
    """)

    # ---- topic_versions 表（话题版本链）----
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topic_versions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id        INTEGER NOT NULL,
            version_num     INTEGER NOT NULL,
            content         TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (topic_id) REFERENCES memories(id)
        )
    """)

    # ---- conversations 表（对话存档）----
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id              TEXT PRIMARY KEY,
            date            TEXT NOT NULL,
            summary         TEXT NOT NULL DEFAULT '',
            raw_path        TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','summarized','cleared')),
            created_at      TEXT NOT NULL
        )
    """)

    # ---- pending_memories 表（待审核记忆）----
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_memories (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id     TEXT NOT NULL,
            extracted_content   TEXT NOT NULL,
            suggested_type      TEXT NOT NULL,
            suggested_tags      TEXT NOT NULL DEFAULT '[]',
            confidence          REAL NOT NULL DEFAULT 0.5,
            status              TEXT NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending','approved','rejected','merged')),
            reviewed_at         TEXT,
            created_at          TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)

    # ---- curator_state 表（Curator 层状态）----
    conn.execute("""
        CREATE TABLE IF NOT EXISTS curator_state (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)

    # ---- 元数据 ----
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO meta (key, value, updated_at) VALUES
        ('version', ?, ?)
    """, [get_version(), datetime.now().isoformat()])

    conn.commit()

    # ---- memory_embeddings 向量存储（Python 序列化，无须扩展）----
    # 向量在 Python 侧用 sentence-transformers 生成，存储为 BLOB
    # 相似度计算也在 Python 侧做（对 ~10k 记忆足够快）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_embeddings (
            memory_id    INTEGER PRIMARY KEY,
            vector       BLOB NOT NULL,
            model        TEXT NOT NULL DEFAULT 'bge-m3',
            FOREIGN KEY (memory_id) REFERENCES memories(id)
        )
    """)
    print("[OK] memory_embeddings 表已创建（BLOB 存储，Python 计算相似度）")

    conn.close()
    print(f"[OK] 数据库初始化完成: {DB_PATH}")
    print("[INFO] 向量搜索使用 Python 实现（sentence-transformers + numpy）")


def verify_db():
    """验证数据库状态"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # WAL 模式检查
    cur.execute("PRAGMA journal_mode")
    mode = cur.fetchone()[0]
    print(f"[CHECK] journal_mode = {mode}")

    # 表列表
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"[CHECK] 表: {tables}")

    # 空数据库行数
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"[CHECK] {t}: {cur.fetchone()[0]} 行")

    # FTS5 检查
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")
    fts = [r[0] for r in cur.fetchall()]
    print(f"[CHECK] FTS5 表: {fts}")

    conn.close()
    print("[OK] 数据库验证通过")


if __name__ == "__main__":
    import sys
    if "--verify" in sys.argv:
        verify_db()
    else:
        init_db()
        verify_db()
