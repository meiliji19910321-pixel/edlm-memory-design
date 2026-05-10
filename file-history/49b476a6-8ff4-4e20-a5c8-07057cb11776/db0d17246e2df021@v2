"""
Layer 3: 记忆文件读写工具
解析 frontmatter + 正文，写入标准格式记忆文件
"""
import os
import re
import json
import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = r"D:\CLAUDE.MD\mem\.db\memory.db"
MEM_DIR = r"D:\CLAUDE.MD\mem\memories"
TYPE_SUBDIRS = {
    "identity": "identity",
    "artifact": "artifact",
    "topic": "topic",
    "memory": "memory",
}


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """解析 frontmatter + 正文，返回 (frontmatter_dict, body)"""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not match:
        return {}, raw
    fm_raw, body = match.groups()
    fm = {}
    for line in fm_raw.split("\n"):
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            # 解析列表: [a, b, c]
            items = [s.strip().rstrip(",") for s in val[1:-1].split(",")]
            fm[key.strip()] = [i for i in items if i]
        elif val.startswith('"') and val.endswith('"'):
            fm[key.strip()] = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            fm[key.strip()] = val[1:-1]
        else:
            try:
                fm[key.strip()] = int(val)
            except ValueError:
                try:
                    fm[key.strip()] = float(val)
                except ValueError:
                    fm[key.strip()] = val
    return fm, body


def write_frontmatter(fm: dict) -> str:
    """将 frontmatter dict 序列化为 YAML 风格的字符串"""
    lines = []
    for key, val in fm.items():
        if isinstance(val, list):
            lines.append(f"{key}: [{', '.join(val)}]")
        elif isinstance(val, str) and ("," in val or ":" in val):
            lines.append(f'{key}: "{val}"')
        else:
            lines.append(f"{key}: {val}")
    return "\n".join(lines)


def read_memory(path: str) -> tuple[dict, str]:
    """读取记忆文件，返回 (frontmatter, body)"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return parse_frontmatter(raw)


def write_memory(
    path: str,
    frontmatter: dict,
    body: str,
    auto_timestamp: bool = True
) -> None:
    """写入记忆文件（frontmatter + 正文）"""
    if auto_timestamp:
        now = datetime.now().strftime("%Y-%m-%d")
        if "created_at" not in frontmatter:
            frontmatter["created_at"] = now
        frontmatter["updated_at"] = now

    content = f"---\n{write_frontmatter(frontmatter)}\n---\n\n{body}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def memory_to_db(
    path: str,
    db_path: str = DB_PATH,
    compute_vector: bool = True
) -> int:
    """
    将记忆文件写入数据库。
    返回新插入的 memory id。
    """
    fm, body = read_memory(path)
    name = fm.get("name", os.path.basename(path).replace(".md", ""))
    desc = fm.get("description", "")
    mem_type = fm.get("type", "memory")
    tags = fm.get("tags", [])
    trust_level = int(fm.get("trust_level", 1))
    topic_ref = fm.get("topic_ref")

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO memories (name, description, type, content, tags,
                             trust_level, topic_ref, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        name, desc, mem_type, body.strip(),
        json.dumps(tags, ensure_ascii=False),
        trust_level, topic_ref,
        fm.get("created_at", datetime.now().isoformat()),
        fm.get("updated_at", datetime.now().isoformat()),
    ])
    memory_id = cur.lastrowid
    conn.commit()
    conn.close()

    # 向量存储
    if compute_vector:
        try:
            from .embedder import get_embedder
            from .db_init import DB_PATH as _db
            emb = get_embedder()
            text_for_embedding = f"{name} {desc} {body[:200]}"
            vec_blob = emb.encode_and_serialize(text_for_embedding)
            conn2 = get_db()
            conn2.execute(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, vector, model) VALUES (?, ?, ?)",
                [memory_id, vec_blob, emb.dimension]
            )
            conn2.commit()
            conn2.close()
        except Exception as e:
            print(f"[WARN] 向量存储失败（不影响主存储）: {e}")

    return memory_id


def db_to_memory(
    memory_id: int,
    db_path: str = DB_PATH
) -> str:
    """从数据库读取记忆，转换为前端显示格式"""
    conn = get_db()
    row = conn.execute(
        "SELECT name, description, type, content, tags, trust_level, version_chain, topic_ref, created_at, updated_at FROM memories WHERE id = ?",
        [memory_id]
    ).fetchone()
    conn.close()

    if not row:
        return None

    fm = {
        "name": row["name"],
        "description": row["description"],
        "type": row["type"],
        "tags": json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"],
        "trust_level": row["trust_level"],
        "version_chain": json.loads(row["version_chain"]) if isinstance(row["version_chain"], str) else row["version_chain"],
        "topic_ref": row["topic_ref"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    return f"---\n{write_frontmatter(fm)}\n---\n\n{row['content']}"


def list_memories_by_type(mem_type: str) -> list[dict]:
    """列出某类型的所有记忆"""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, description, trust_level, created_at FROM memories WHERE type = ? ORDER BY created_at DESC",
        [mem_type]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_memory_trust(memory_id: int, new_level: int) -> None:
    """更新记忆的信任等级"""
    new_level = max(1, min(3, new_level))
    conn = get_db()
    conn.execute(
        "UPDATE memories SET trust_level = ?, updated_at = ? WHERE id = ?",
        [new_level, datetime.now().isoformat(), memory_id]
    )
    conn.commit()
    conn.close()


def slugify(name: str) -> str:
    """将记忆名称转换为合法的文件名"""
    import re
    name = re.sub(r"[^\w\s\-]", "", name)
    name = re.sub(r"[\s]+", "-", name)
    return name.lower()[:80]


def create_memory_file(
    name: str,
    body: str,
    mem_type: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    topic_ref: Optional[str] = None,
) -> tuple[str, int]:
    """
    创建新记忆文件并写入数据库。
    返回 (file_path, memory_id)
    """
    if mem_type not in TYPE_SUBDIRS:
        raise ValueError(f"未知的记忆类型: {mem_type}")

    tags = tags or []
    subdir = TYPE_SUBDIRS[mem_type]
    safe_name = slugify(name)
    now = datetime.now().strftime("%Y-%m-%d")
    filename = f"{now}-{safe_name}.md"
    file_path = os.path.join(MEM_DIR, subdir, filename)

    frontmatter = {
        "name": name,
        "description": description or body[:100],
        "type": mem_type,
        "tags": tags,
        "trust_level": 1,
        "version_chain": [],
        "topic_ref": topic_ref,
    }

    write_memory(file_path, frontmatter, body)
    memory_id = memory_to_db(file_path)

    print(f"[OK] 记忆已创建: {file_path} (id={memory_id})")
    return file_path, memory_id
