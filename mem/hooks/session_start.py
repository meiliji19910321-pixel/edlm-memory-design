"""
Layer 6: 生命周期钩子 — SessionStart
每次新对话开始时调用
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.retriever import MemoryRetriever
from tools.memory_file import list_memories_by_type
from tools.extractor import get_pending_memories
from tools.db_init import DB_PATH
import sqlite3


def session_start_hook() -> dict:
    """
    返回启动上下文，供 Claude 注入。
    包括：identity 记忆、最近对话摘要、待审核记忆提醒
    """
    result = {
        "identity": [],
        "recent_topics": [],
        "recent_artifacts": [],
        "pending_review": [],
        "last_conversation": None,
    }

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # 1. 读取 identity 记忆
        identities = conn.execute("""
            SELECT name, description, content, trust_level
            FROM memories WHERE type = 'identity'
            ORDER BY trust_level DESC, updated_at DESC
            LIMIT 5
        """).fetchall()
        result["identity"] = [dict(r) for r in identities]

        # 2. 最近话题
        topics = conn.execute("""
            SELECT name, description, updated_at
            FROM memories WHERE type = 'topic'
            ORDER BY updated_at DESC LIMIT 5
        """).fetchall()
        result["recent_topics"] = [dict(r) for r in topics]

        # 3. 最近创作物
        artifacts = conn.execute("""
            SELECT name, description, updated_at
            FROM memories WHERE type = 'artifact'
            ORDER BY updated_at DESC LIMIT 3
        """).fetchall()
        result["recent_artifacts"] = [dict(r) for r in artifacts]

        # 4. 待审核记忆
        pending = conn.execute("""
            SELECT COUNT(*) as cnt FROM pending_memories WHERE status = 'pending'
        """).fetchone()["cnt"]
        result["pending_review"] = pending

        # 5. 最近一次对话
        last_conv = conn.execute("""
            SELECT id, date, summary FROM conversations
            ORDER BY created_at DESC LIMIT 1
        """).fetchone()
        if last_conv:
            result["last_conversation"] = dict(last_conv)

        conn.close()

    except Exception as e:
        result["error"] = str(e)

    return result


def build_context_summary(hook_result: dict) -> str:
    """
    将 hook 结果格式化为人类可读的上下文摘要，
    用于注入到 Claude 的 system prompt 或开场提示。
    """
    lines = []

    if hook_result.get("error"):
        return ""

    identities = hook_result.get("identity", [])
    if identities:
        lines.append("【关于你】")
        for i in identities[:3]:
            if i.get("trust_level", 1) >= 2:
                lines.append(f"- {i['description']}")
        lines.append("")

    pending = hook_result.get("pending_review", 0)
    if pending > 0:
        lines.append(f"【待审核】你有 {pending} 条新记忆待审核，可以回复「检查记忆」查看】")
        lines.append("")

    last = hook_result.get("last_conversation")
    if last and last.get("summary"):
        lines.append(f"【上次对话摘要】{last['summary'][:200]}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    result = session_start_hook()
    summary = build_context_summary(result)
    print("=== SessionStart Hook ===")
    print(summary)
    print(f"待审核记忆: {result.get('pending_review', 0)} 条")
