"""
Layer 4: 信任等级机制
记忆被验证次数越多，信任等级越高，注入上下文的程度越轻
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional

DB_PATH = r"D:\CLAUDE.MD\mem\.db\memory.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class TrustManager:
    """
    信任等级：
    L1（新建，未验证）→ 显示原文，不自动注入
    L2（再次验证）→ 摘要注入上下文
    L3（验证 3 次以上）→ 仅提示存在，用户主动问才展示
    """

    def bump_trust(self, memory_id: int) -> int:
        """记忆被再次验证，信任等级 +1，最高 3"""
        conn = get_db()
        row = conn.execute(
            "SELECT trust_level FROM memories WHERE id = ?", [memory_id]
        ).fetchone()

        if not row:
            conn.close()
            return 0

        old_level = row["trust_level"] or 1
        new_level = min(old_level + 1, 3)

        conn.execute(
            "UPDATE memories SET trust_level = ?, updated_at = ? WHERE id = ?",
            [new_level, datetime.now().isoformat(), memory_id]
        )
        conn.commit()
        conn.close()
        return new_level

    def get_injection_strategy(self, memory_id: int) -> str:
        """根据信任等级决定注入策略"""
        conn = get_db()
        row = conn.execute(
            "SELECT trust_level FROM memories WHERE id = ?", [memory_id]
        ).fetchone()
        conn.close()

        if not row:
            return "full"

        trust = row["trust_level"] or 1
        return {1: "full", 2: "summary", 3: "hint"}[trust]

    def get_trust_level(self, memory_id: int) -> int:
        """获取当前信任等级"""
        conn = get_db()
        row = conn.execute(
            "SELECT trust_level FROM memories WHERE id = ?", [memory_id]
        ).fetchone()
        conn.close()
        return row["trust_level"] if row else 0

    def get_memories_by_trust(self, min_level: int = 1) -> list[dict]:
        """获取指定信任等级以上的所有记忆"""
        conn = get_db()
        rows = conn.execute(
            "SELECT id, name, description, type, trust_level, created_at FROM memories WHERE trust_level >= ? ORDER BY trust_level DESC, created_at DESC",
            [min_level]
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# 全局单例
_trust_manager: Optional[TrustManager] = None


def get_trust_manager() -> TrustManager:
    global _trust_manager
    if _trust_manager is None:
        _trust_manager = TrustManager()
    return _trust_manager


def apply_trust_bump(conversation_id: str, memory_ids: list[int]) -> dict:
    """
    对话结束后，对本次提取的记忆进行信任等级更新。
    对话中涉及的记忆 → 信任等级 +1
    """
    from .extractor import get_db as ext_get_db

    manager = get_trust_manager()
    results = {}

    for mid in memory_ids:
        old = manager.get_trust_level(mid)
        new = manager.bump_trust(mid)
        results[mid] = {"old": old, "new": new}

    # 更新 curator_state 中的对话计数
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM pending_memories WHERE conversation_id = ? AND status = 'approved'",
        [conversation_id]
    ).fetchone()["cnt"]
    conn.execute(
        "INSERT OR REPLACE INTO curator_state (key, value, updated_at) VALUES (?, ?, ?)",
        ["total_approved_memories", str(count), datetime.now().isoformat()]
    )
    conn.commit()
    conn.close()

    return results
