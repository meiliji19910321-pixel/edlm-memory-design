"""
Layer 4: 对话摘要提取
从对话 JSONL 中提取新增记忆，写入待审核区
"""
import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional

DB_PATH = r"D:\CLAUDE.MD\mem\.db\memory.db"
CONV_DIR = r"D:\CLAUDE.MD\mem\conversations"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_conv_id() -> str:
    """生成对话 ID（日期 + 随机哈希）"""
    date = datetime.now().strftime("%Y%m%d")
    raw = f"{date}{datetime.now().isoformat()}"
    short = hashlib.sha1(raw.encode()).hexdigest()[:8]
    return f"{date}-{short}"


def save_conversation(
    conv_id: str,
    messages: list[dict],
    summary: str = ""
) -> str:
    """
    保存原始对话到 JSONL 文件。
    返回 raw_path。
    """
    os.makedirs(CONV_DIR, exist_ok=True)
    raw_path = os.path.join(CONV_DIR, f"{conv_id}.jsonl")

    with open(raw_path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    # 写入 conversations 表
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO conversations (id, date, summary, raw_path, status, created_at)
        VALUES (?, ?, ?, ?, 'active', ?)
    """, [conv_id, datetime.now().strftime("%Y-%m-%d"), summary, raw_path, datetime.now().isoformat()])
    conn.commit()
    conn.close()

    return raw_path


def extract_memories_from_conversation(
    conv_id: str,
    messages: list[dict]
) -> list[dict]:
    """
    从对话消息中提取记忆（规则 + LLM 混合）。
    当前为规则提取（关键词 + 结构化分析）。

    返回格式：
    [{
        "content": "提取的记忆内容",
        "suggested_type": "identity | artifact | topic | memory",
        "suggested_tags": ["标签1", "标签2"],
        "confidence": 0.0-1.0,
        "references": ["原始消息摘要"]
    }]
    """
    extracted = []

    # 合并所有用户消息文本
    user_texts = []
    assistant_texts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
        if role == "user":
            user_texts.append(content)
        elif role == "assistant":
            assistant_texts.append(content)

    all_text = "\n".join(user_texts)

    # ---- 规则提取：类型判断 + 置信度 ----

    # Identity 检测：角色、目标、偏好
    identity_keywords = ["我", "我的", "我是", "我的目标", "我想", "我的偏好", "我的约束"]
    if any(kw in all_text for kw in identity_keywords):
        # 尝试提取身份描述
        for text in user_texts:
            if any(kw in text for kw in ["我叫", "我是", "我的职业", "我做"]):
                extracted.append({
                    "content": text.strip(),
                    "suggested_type": "identity",
                    "suggested_tags": ["身份", "角色"],
                    "confidence": 0.7,
                    "references": [text[:100]]
                })

    # Artifact 检测：代码、文档、设计
    artifact_indicators = ["写", "创建", "设计", "代码", "文档", "方案"]
    if any(ind in all_text for ind in artifact_indicators):
        for i, text in enumerate(user_texts):
            if len(text) > 20 and any(ind in text for ind in artifact_indicators):
                extracted.append({
                    "content": text.strip(),
                    "suggested_type": "artifact",
                    "suggested_tags": ["创作", "代码"],
                    "confidence": 0.6,
                    "references": [text[:100]]
                })

    # Topic 检测：话题关键词
    topic_markers = ["#", "话题", "关于", "讨论", "问题", "研究"]
    for text in user_texts:
        if any(m in text for m in topic_markers) and len(text) > 15:
            extracted.append({
                "content": text.strip(),
                "suggested_type": "topic",
                "suggested_tags": ["话题"],
                "confidence": 0.5,
                "references": [text[:100]]
            })

    # Memory：通用观察
    if not extracted:
        for text in user_texts:
            if len(text) > 10:
                extracted.append({
                    "content": text.strip(),
                    "suggested_type": "memory",
                    "suggested_tags": [],
                    "confidence": 0.4,
                    "references": [text[:100]]
                })

    # 去重（基于内容相似）
    seen = set()
    unique = []
    for e in extracted:
        key = e["content"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def write_pending_memories(
    conv_id: str,
    extracted_memories: list[dict]
) -> int:
    """将提取的记忆写入 pending_memories 表"""
    conn = get_db()
    count = 0
    for mem in extracted_memories:
        # 检查是否已存在相似内容
        existing = conn.execute("""
            SELECT id, extracted_content FROM pending_memories
            WHERE conversation_id != ? AND extracted_content LIKE ?
            LIMIT 1
        """, [conv_id, f"%{mem['content'][:30]}%"]).fetchone()

        if existing:
            continue  # 跳过重复

        conn.execute("""
            INSERT INTO pending_memories
            (conversation_id, extracted_content, suggested_type, suggested_tags, confidence, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, [
            conv_id,
            mem["content"],
            mem["suggested_type"],
            json.dumps(mem["suggested_tags"], ensure_ascii=False),
            mem["confidence"],
            datetime.now().isoformat()
        ])
        count += 1

    conn.commit()
    conn.close()
    return count


def get_pending_memories(status: str = "pending") -> list[dict]:
    """获取待审核记忆"""
    conn = get_db()
    rows = conn.execute("""
        SELECT pm.*, c.date
        FROM pending_memories pm
        JOIN conversations c ON c.id = pm.conversation_id
        WHERE pm.status = ?
        ORDER BY pm.created_at DESC
    """, [status]).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def approve_memory(pending_id: int, final_type: str = None) -> int:
    """批准记忆，转移到永久记忆区，返回 memory_id"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM pending_memories WHERE id = ?", [pending_id]
    ).fetchone()
    conn.close()

    if not row:
        return None

    from .memory_file import create_memory_file

    # 用 create_memory_file 创建真实记忆文件
    _, memory_id = create_memory_file(
        name=row["extracted_content"][:50],
        body=row["extracted_content"],
        mem_type=final_type or row["suggested_type"],
        description=row["extracted_content"][:100],
        tags=json.loads(row["suggested_tags"]) if row["suggested_tags"] else [],
    )

    # 更新 pending 状态
    conn2 = get_db()
    conn2.execute(
        "UPDATE pending_memories SET status = 'approved', reviewed_at = ? WHERE id = ?",
        [datetime.now().isoformat(), pending_id]
    )
    conn2.commit()
    conn2.close()

    # 信任等级 +1（首次验证）
    from .trust import get_trust_manager
    get_trust_manager().bump_trust(memory_id)

    return memory_id


def reject_memory(pending_id: int, reason: str = "") -> None:
    """拒绝记忆"""
    conn = get_db()
    conn.execute(
        "UPDATE pending_memories SET status = 'rejected', reviewed_at = ? WHERE id = ?",
        [datetime.now().isoformat(), pending_id]
    )
    conn.commit()
    conn.close()


def get_conversation_summary(conv_id: str) -> str:
    """获取对话摘要"""
    conn = get_db()
    row = conn.execute(
        "SELECT summary FROM conversations WHERE id = ?", [conv_id]
    ).fetchone()
    conn.close()
    return row["summary"] if row else ""
