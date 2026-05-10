#!/usr/bin/env python3
"""
SessionStart hook for 融合记忆系统.
每次新对话开始时运行，输出上下文摘要供 Claude 注入。
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MEM_DB = r"D:\CLAUDE.MD\mem\.db\memory.db"


def get_db():
    import sqlite3
    conn = sqlite3.connect(MEM_DB)
    conn.row_factory = sqlite3.Row
    return conn


def build_context() -> str:
    """构建上下文摘要，print 到 stdout"""
    try:
        conn = get_db()

        lines = []

        # 1. Identity 记忆（L2+ 才自动注入）
        rows = conn.execute("""
            SELECT name, description, trust_level
            FROM memories
            WHERE type = 'identity' AND trust_level >= 2
            ORDER BY trust_level DESC, updated_at DESC
            LIMIT 3
        """).fetchall()

        if rows:
            lines.append("【关于你】")
            for r in rows:
                lines.append(f"• {r['description']}")
            lines.append("")

        # 2. 最近对话
        last = conn.execute("""
            SELECT date, summary FROM conversations
            ORDER BY created_at DESC LIMIT 1
        """).fetchone()

        if last and last["summary"]:
            lines.append(f"【上次对话摘要】{last['summary'][:150]}")
            lines.append("")

        # 3. 待审核记忆数量
        pending = conn.execute(
            "SELECT COUNT(*) FROM pending_memories WHERE status = 'pending'"
        ).fetchone()[0]

        if pending > 0:
            lines.append(f"【记忆待审核】{pending} 条记忆待审核，运行 `python -m mem pending` 查看，或回复「检查记忆」")
            lines.append("")

        # 4. 最近的 topic
        topics = conn.execute("""
            SELECT name, description FROM memories
            WHERE type = 'topic'
            ORDER BY updated_at DESC LIMIT 2
        """).fetchall()

        if topics:
            lines.append("【最近话题】")
            for t in topics:
                lines.append(f"• {t['name']}: {t['description'][:50]}")
            lines.append("")

        conn.close()
        return "\n".join(lines)

    except Exception as e:
        return f"[记忆系统错误: {e}]"


def main():
    # SessionStart 可能没有 stdin 数据（只传递 session_id 等环境变量）
    # 尝试读取，不影响主流程
    try:
        context = build_context()
        if context.strip():
            print(context)
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
