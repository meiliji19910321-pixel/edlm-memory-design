"""
Layer 5: Curator 层 — 主动管理
规则驱动，不需要 LLM
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = r"D:\CLAUDE.MD\mem\.db\memory.db"
CONV_DIR = r"D:\CLAUDE.MD\mem\conversations"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---- 矛盾检测 ----

NEGATION_WORDS = [
    "不", "没", "非", "否", "不要", "不能", "不会", "不应该",
    "不要用", "停止", "不再", "否定", "错误"
]


def detect_conflicts(new_content: str, db_path: str = DB_PATH) -> list[dict]:
    """
    检查新记忆是否与已有记忆矛盾。
    策略：否定词 + 重叠关键词检测。
    返回: [{"conflict_with": id, "reason": str, "severity": "high|medium|low"}]
    """
    new_lower = new_content.lower()
    has_negation = any(w in new_content for w in NEGATION_WORDS)

    conn = get_db()
    rows = conn.execute("""
        SELECT id, name, content, type FROM memories
        WHERE type IN ('identity', 'memory')
        LIMIT 50
    """).fetchall()
    conn.close()

    conflicts = []
    for row in rows:
        row_content = row["content"]
        # 提取关键词（简单重叠）
        new_words = set(new_content[:50])
        old_words = set(row_content[:50])
        overlap = len(new_words & old_words)

        if overlap >= 3:
            row_has_negation = any(w in row_content for w in NEGATION_WORDS)
            if has_negation != row_has_negation:
                # 一个肯定一个否定，可能矛盾
                severity = "high" if overlap >= 5 else "medium"
                conflicts.append({
                    "conflict_with": row["id"],
                    "reason": f"新记忆含否定词={has_negation}，已有记忆含否定词={row_has_negation}，重叠词数={overlap}",
                    "severity": severity,
                    "old_content": row_content[:80]
                })

    return conflicts


# ---- 合并建议 ----

def suggest_merge(topic_name: str = None) -> list[dict]:
    """
    检测某话题下是否有过多未合并的记忆。
    返回: [{"topic_id": int, "topic_name": str, "memory_count": int, "suggestion": str}]
    """
    conn = get_db()

    if topic_name:
        rows = conn.execute("""
            SELECT m.id, m.name, COUNT(pm.id) as pending_count
            FROM memories m
            LEFT JOIN pending_memories pm ON pm.suggested_type = 'topic' AND pm.status = 'pending'
            WHERE m.type = 'topic' AND (m.name LIKE ? OR ? IS NULL)
            GROUP BY m.id
            HAVING pending_count > 5
        """, [f"%{topic_name}%", topic_name]).fetchall()
    else:
        rows = conn.execute("""
            SELECT m.id, m.name, COUNT(pm.id) as pending_count
            FROM memories m
            LEFT JOIN pending_memories pm ON pm.suggested_type = 'topic'
            WHERE m.type = 'topic'
            GROUP BY m.id
            HAVING pending_count > 5
        """).fetchall()

    conn.close()

    suggestions = []
    for row in rows:
        suggestions.append({
            "topic_id": row["id"],
            "topic_name": row["name"],
            "memory_count": row["pending_count"],
            "suggestion": f"话题「{row['name']}」积累了 {row['pending_count']} 条未处理记忆，建议合并"
        })

    return suggestions


# ---- 每周检查：Curator 状态更新 ----

def update_curator_state():
    """更新 Curator 层状态（每周调用一次）"""
    conn = get_db()

    # 待审核数量
    pending = conn.execute(
        "SELECT COUNT(*) FROM pending_memories WHERE status = 'pending'"
    ).fetchone()[0]

    # 已批准总数
    approved = conn.execute(
        "SELECT COUNT(*) FROM memories"
    ).fetchone()[0]

    # 信任等级分布
    trust_dist = {}
    rows = conn.execute(
        "SELECT trust_level, COUNT(*) as cnt FROM memories GROUP BY trust_level"
    ).fetchall()
    for row in rows:
        trust_dist[str(row["trust_level"])] = row["cnt"]

    # 上次更新
    now = datetime.now().isoformat()
    for key, val in [
        ("pending_count", str(pending)),
        ("total_memories", str(approved)),
        ("trust_distribution", json.dumps(trust_dist)),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO curator_state (key, value, updated_at) VALUES (?, ?, ?)",
            [key, val, now]
        )

    conn.commit()
    conn.close()

    return {
        "pending": pending,
        "approved": approved,
        "trust_distribution": trust_dist
    }


# ---- 每月检查：Identity 过时检测 ----

def check_identity_stale() -> list[dict]:
    """检测 identity 类型记忆是否可能过时（30天未更新）"""
    conn = get_db()
    rows = conn.execute("""
        SELECT id, name, description, updated_at
        FROM memories
        WHERE type = 'identity' AND updated_at < ?
        ORDER BY updated_at ASC
    """, [(datetime.now() - timedelta(days=30)).isoformat()]).fetchall()
    conn.close()

    return [dict(r) for r in rows]


# ---- 健康报告 ----

def generate_health_report() -> str:
    """生成季度健康报告（中文）"""
    conn = get_db()
    now = datetime.now()

    # 基本统计
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    by_type = {}
    for row in conn.execute(
        "SELECT type, COUNT(*) as cnt FROM memories GROUP BY type"
    ).fetchall():
        by_type[row["type"]] = row["cnt"]

    pending = conn.execute(
        "SELECT COUNT(*) FROM pending_memories WHERE status = 'pending'"
    ).fetchone()[0]

    approved_total = conn.execute(
        "SELECT COUNT(*) FROM pending_memories WHERE status = 'approved'"
    ).fetchone()[0]

    rejected_total = conn.execute(
        "SELECT COUNT(*) FROM pending_memories WHERE status = 'rejected'"
    ).fetchone()[0]

    # 信任等级分布
    trust_rows = conn.execute(
        "SELECT trust_level, COUNT(*) as cnt FROM memories GROUP BY trust_level"
    ).fetchall()
    trust_dist = {str(r["trust_level"]): r["cnt"] for r in trust_rows}

    # 话题数
    topics = conn.execute(
        "SELECT COUNT(*) FROM memories WHERE type = 'topic'"
    ).fetchone()[0]

    # 最早和最新的记忆
    oldest = conn.execute(
        "SELECT name, created_at FROM memories ORDER BY created_at ASC LIMIT 1"
    ).fetchone()
    newest = conn.execute(
        "SELECT name, created_at FROM memories ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    conn.close()

    report_lines = [
        f"# 记忆健康报告",
        f"",
        f"生成时间：{now.strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 概览",
        f"- 永久记忆总数：{total}",
        f"- 话题数：{topics}",
        f"- 待审核记忆：{pending} 条",
        f"- 历史已批准：{approved_total} 条",
        f"- 历史已拒绝：{rejected_total} 条",
        f"",
        f"## 类型分布",
    ]

    for t, cnt in by_type.items():
        report_lines.append(f"- {t}：{cnt} 条")

    report_lines.extend([
        f"",
        f"## 信任等级分布",
        f"- L1（新建）：{trust_dist.get('1', 0)} 条",
        f"- L2（验证中）：{trust_dist.get('2', 0)} 条",
        f"- L3（稳定）：{trust_dist.get('3', 0)} 条",
        f"",
        f"## 时间跨度",
    ])

    if oldest:
        report_lines.append(f"- 最早记忆：{oldest['name']}（{oldest['created_at'][:10]}）")
    if newest:
        report_lines.append(f"- 最新记忆：{newest['name']}（{newest['created_at'][:10]}）")

    report_lines.extend([
        f"",
        f"## Curator 状态",
    ])

    # 待合并话题
    merges = suggest_merge()
    if merges:
        report_lines.append(f"- 建议合并的话题：{len(merges)} 个")
        for m in merges[:3]:
            report_lines.append(f"  - {m['suggestion']}")
    else:
        report_lines.append(f"- 暂无建议合并的话题")

    # Identity 过时检测
    stale = check_identity_stale()
    if stale:
        report_lines.append(f"- 可能过时的身份记忆：{len(stale)} 条")
        for s in stale[:3]:
            report_lines.append(f"  - {s['name']}（{s['updated_at'][:10]}）")

    return "\n".join(report_lines)


# ---- 清理对话（60天后清除原文）----

def cleanup_old_conversations(days: int = 60) -> int:
    """清除超过 N 天的原始对话文件（保留摘要）"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    conn = get_db()

    # 找到需要清理的对话
    old_convs = conn.execute("""
        SELECT id, raw_path, status FROM conversations
        WHERE created_at < ? AND status = 'active'
    """, [cutoff]).fetchall()

    removed = 0
    for conv in old_convs:
        raw_path = conv["raw_path"]
        # 删除原始文件
        if os.path.exists(raw_path):
            try:
                os.remove(raw_path)
                removed += 1
            except Exception:
                pass
        # 更新状态
        conn.execute(
            "UPDATE conversations SET status = 'cleared' WHERE id = ?",
            [conv["id"]]
        )

    conn.commit()
    conn.close()
    return removed
