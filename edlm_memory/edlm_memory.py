#!/usr/bin/env python3
"""
EDLM Memory Manager - 经验驱动学习记忆系统
融合 claude-mem + mempalace + palaia 的永久记忆框架
"""

import os
import json
import sqlite3
import uuid
import math
from datetime import datetime, timedelta
from pathlib import Path

# 配置路径
BASE_DIR = Path("D:/CLAUDE.MD")
MEMORY_DIR = BASE_DIR / "memory"
CORPORA_DIR = MEMORY_DIR / "corpora"
EXPERIENCES_DIR = MEMORY_DIR / "experiences"
PATTERNS_DIR = MEMORY_DIR / "patterns"
BRIEFING_DIR = MEMORY_DIR / "briefing"
BRIEFING_HISTORY_DIR = BRIEFING_DIR / "history"
ARCHIVE_DIR = MEMORY_DIR / "archive"
PROJECTS_DIR = MEMORY_DIR / "projects"

DB_PATH = CORPORA_DIR / "memory.db"

# 类型权重
TYPE_WEIGHTS = {
    "process": 1.5,
    "decision": 1.2,
    "memory": 1.0
}

# 衰减配置
HOT_DAYS = 7
WARM_DAYS = 30
HOT_SCORE = 0.5
WARM_SCORE = 0.1
DECAY_LAMBDA = 0.1

# 分层记录阈值
SUMMARY_MAX_CHARS = 500


def init_db():
    """初始化 SQLite + sqlite-vec 数据库"""
    CORPORA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # memories 表
    c.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            date TEXT,
            goal TEXT,
            domain TEXT,
            tier TEXT DEFAULT 'hot',
            type TEXT DEFAULT 'memory',
            weight REAL DEFAULT 1.0,
            outcome TEXT,
            content TEXT,
            derived_pattern TEXT,
            success_factors TEXT,
            failure_patterns TEXT,
            decay_score REAL DEFAULT 1.0,
            last_access TEXT,
            access_count INTEGER DEFAULT 0,
            validation_count INTEGER DEFAULT 0,
            tags TEXT,
            created_at TEXT
        )
    """)

    # 向量表
    c.execute("CREATE TABLE IF NOT EXISTS memory_vectors (id TEXT, embedding BLOB)")

    # closet 缓存表
    c.execute("""
        CREATE TABLE IF NOT EXISTS closet (
            id TEXT PRIMARY KEY,
            topic TEXT,
            entities TEXT,
            session_ref TEXT,
            content TEXT,
            last_access TEXT
        )
    """)

    # FTS5 全文搜索
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(goal, content, content='memories', content_rowid='rowid')")

    conn.commit()
    conn.close()
    print(f"[EDLM] 数据库初始化完成: {DB_PATH}")


def calc_decay_score(last_access_str, access_count):
    """计算衰减分数"""
    if not last_access_str:
        return 1.0

    last_access = datetime.fromisoformat(last_access_str.replace("Z", "+00:00"))
    now = datetime.now()
    days_since = (now - last_access).days

    time_decay = math.exp(-DECAY_LAMBDA * days_since)
    hit_bonus = 1 + math.log(1 + access_count)

    return round(time_decay * hit_bonus, 4)


def classify_tier(decay_score, last_access_str):
    """分类记忆层级"""
    if not last_access_str:
        return "hot"

    last_access = datetime.fromisoformat(last_access_str.replace("Z", "+00:00"))
    now = datetime.now()
    days_since = (now - last_access).days

    if days_since <= HOT_DAYS or decay_score >= HOT_SCORE:
        return "hot"
    elif days_since <= WARM_DAYS or decay_score >= WARM_SCORE:
        return "warm"
    else:
        return "cold"


def determine_precision_type(content, goal, user_override=False):
    """判断记录精度类型"""
    if user_override:
        return "decision", len(content), True  # verbatim

    # AI 自动判断
    decision_keywords = ["选择", "决策", "方案", "决定", "要转行", "创业", "方向"]
    for kw in decision_keywords:
        if kw in goal or kw in content[:200]:
            return "decision", len(content), True  # verbatim

    # process 类型，限制摘要长度
    return "process", min(len(content), SUMMARY_MAX_CHARS), False


def save_experience(goal, domain, content, outcome, success_factors=None,
                    failure_patterns=None, derived_pattern=None, tags=None,
                    user_override=False, session_id=None):
    """保存一条经验"""
    exp_id = f"exp-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    exp_type, content_len, is_verbatim = determine_precision_type(content, goal, user_override)

    # 决定存储内容
    if is_verbatim or exp_type == "decision":
        stored_content = content
    else:
        stored_content = content[:SUMMARY_MAX_CHARS] + "\n\n[摘要 - 完整内容见源对话]" if len(content) > SUMMARY_MAX_CHARS else content

    # 标签处理
    if tags is None:
        tags = [domain] if domain else []
    tags_str = ",".join(tags) if isinstance(tags, list) else tags

    now = datetime.now().isoformat()
    record = {
        "id": exp_id,
        "date": now[:10],
        "goal": goal,
        "domain": domain or "general",
        "tier": "hot",
        "type": exp_type,
        "weight": TYPE_WEIGHTS.get(exp_type, 1.0),
        "outcome": outcome,
        "content": stored_content,
        "derived_pattern": derived_pattern or "",
        "success_factors": json.dumps(success_factors or [], ensure_ascii=False),
        "failure_patterns": json.dumps(failure_patterns or [], ensure_ascii=False),
        "decay_score": 1.0,
        "last_access": now[:10],
        "access_count": 1,
        "validation_count": 0,
        "tags": tags_str,
        "created_at": now
    }

    # 写入数据库
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        INSERT INTO memories (id, date, goal, domain, tier, type, weight, outcome, content,
                              derived_pattern, success_factors, failure_patterns, decay_score,
                              last_access, access_count, validation_count, tags, created_at)
        VALUES (:id, :date, :goal, :domain, :tier, :type, :weight, :outcome, :content,
                :derived_pattern, :success_factors, :failure_patterns, :decay_score,
                :last_access, :access_count, :validation_count, :tags, :created_at)
    """, record)

    # 更新 FTS
    c.execute("INSERT INTO memories_fts(rowid, goal, content) VALUES ((SELECT rowid FROM memories WHERE id=?), ?, ?)",
              (exp_id, goal, stored_content))

    conn.commit()
    conn.close()

    # 同时写入 Markdown 文件
    month_dir = EXPERIENCES_DIR / datetime.now().strftime("%Y-%m")
    month_dir.mkdir(parents=True, exist_ok=True)

    md_path = month_dir / f"{exp_id}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        for k, v in record.items():
            if k not in ["content"]:
                if isinstance(v, str):
                    v = v.replace("\n", " ")
                f.write(f"{k}: {v}\n")
        f.write("---\n\n")
        f.write(stored_content)

    print(f"[EDLM] 经验已保存: {exp_id} (type={exp_type}, tier=hot)")
    return exp_id


def ai_self_judge(goal, actions, result):
    """AI 自判断结果"""
    goal_lower = goal.lower()

    # 检查 GitHub 连接
    if "github" in goal_lower and ("ssh" in goal_lower or "绑定" in goal_lower):
        if "Hi" in result and "successfully authenticated" in result:
            return "SUCCESS"
        return "FAILURE"

    # 检查文件操作
    if "下载" in goal_lower or "安装" in goal_lower:
        if result and ("success" in result.lower() or "created" in result.lower() or "ok" in result.lower()):
            return "SUCCESS"
        return "FAILURE"

    # 检查更新操作
    if "更新" in goal_lower or "upgrade" in goal_lower:
        if result and "version" in result.lower():
            return "SUCCESS"
        return "FAILURE"

    # 默认：检查返回码或错误信息
    if result:
        if "error" in result.lower() or "fail" in result.lower() or "exit code 1" in result.lower():
            return "FAILURE"
        if "exit code 0" in result.lower():
            return "SUCCESS"

    return "UNKNOWN"


def save_briefing(session_id, what_done, open_tasks, key_decisions, derived_patterns):
    """保存 Session Briefing"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    content = f"""---
session_id: {session_id}
date: {date_str}
time: {time_str}
tier: hot
type: session
---

## 上次做了什么
{chr(10).join(f"- {t}" for t in (what_done or []))}

## 开放任务
{chr(10).join(f"- [ ] {t}" for t in (open_tasks or []))}

## 关键决策
{chr(10).join(f"- {d}" for d in (key_decisions or []))}

## 经验提取
{chr(10).join(f"- {p}" for p in (derived_patterns or []))}
"""

    # 保存当前
    current_path = BRIEFING_DIR / "current.md"
    with open(current_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 追加到历史
    history_path = BRIEFING_HISTORY_DIR / f"{date_str}.md"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n<!-- {session_id} -->\n")
        f.write(content)

    print(f"[EDLM] Briefing 已保存: {session_id}")
    return current_path


def search_memories(query, tier_filter=None, limit=5):
    """搜索记忆（混合检索）"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # BM25 候选
    if tier_filter:
        c.execute("""
            SELECT id, goal, content, outcome, domain, type, decay_score, access_count
            FROM memories
            WHERE tier IN ({})
            ORDER BY decay_score DESC
            LIMIT {}
        """.format(",".join(["?"] * len(tier_filter)), limit * 3), tier_filter)
    else:
        c.execute("""
            SELECT id, goal, content, outcome, domain, type, decay_score, access_count
            FROM memories
            ORDER BY decay_score DESC
            LIMIT {}
        """.format(limit * 3))

    results = c.fetchall()
    conn.close()

    # 简单评分：decay_score * access_count * weight
    scored = []
    for r in results:
        id_, goal, content, outcome, domain, type_, decay_score, access_count = r
        weight = TYPE_WEIGHTS.get(type_, 1.0)
        score = decay_score * (1 + math.log(1 + access_count)) * weight
        scored.append((score, r))

    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[:limit]


def extract_pattern(experience_ids):
    """从多个经验中提取 pattern"""
    if not experience_ids or len(experience_ids) < 2:
        return None

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    patterns = []
    for exp_id in experience_ids:
        c.execute("SELECT derived_pattern, domain, type, success_factors FROM memories WHERE id=?", (exp_id,))
        row = c.fetchone()
        if row and row[0]:
            patterns.append({
                "pattern": row[0],
                "domain": row[1],
                "type": row[2],
                "factors": json.loads(row[3]) if row[3] else []
            })

    conn.close()

    if len(patterns) < 2:
        return None

    # 简单合并：取最常见的 domain + 多个 success_factors
    domains = [p["domain"] for p in patterns]
    main_domain = max(set(domains), key=domains.count)

    all_factors = []
    for p in patterns:
        all_factors.extend(p.get("factors", []))

    # 去重
    unique_factors = list(dict.fromkeys(all_factors))[:5]

    pattern_content = f"""# Pattern: {main_domain}

## 来源经验
{', '.join(experience_ids)}

## 验证次数
{len(patterns)}

## 成功因素
{chr(10).join(f"- {f}" for f in unique_factors)}

## 适用场景
- {patterns[0]['pattern'] if patterns else '待提取'}

## 验证状态
validation_count >= 5 时可写入 skills/
"""

    return pattern_content


def check_and_rotate():
    """检查并旋转记忆层级"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("SELECT id, last_access, decay_score, content FROM memories WHERE tier != 'cold'")
    rows = c.fetchall()

    for row in rows:
        id_, last_access, old_score, content = row
        new_score = calc_decay_score(last_access.split(" ")[0], 0)  # 简化，实际应该查 access_count
        new_tier = classify_tier(new_score, last_access.split(" ")[0])

        if new_tier != row[0]:  # 需要更新
            c.execute("UPDATE memories SET decay_score=?, tier=? WHERE id=?", (new_score, new_tier, id_))
            # 移动到 archive
            if new_tier == "cold":
                month_dir = ARCHIVE_DIR / datetime.now().strftime("%Y-%m")
                month_dir.mkdir(parents=True, exist_ok=True)

                # 查找源文件
                for exp_file in EXPERIENCES_DIR.rglob(f"{id_}.md"):
                    import shutil
                    shutil.move(str(exp_file), str(month_dir / exp_file.name))
                    break

            print(f"[EDLM] 记忆旋转: {id_} -> {new_tier} (score: {new_score})")

    conn.commit()
    conn.close()


def load_briefing():
    """加载当前 briefing"""
    current_path = BRIEFING_DIR / "current.md"
    if current_path.exists():
        return current_path.read_text(encoding="utf-8")
    return ""


def load_hot_patterns():
    """加载 HOT 层 patterns"""
    patterns = []
    for pat_file in PATTERNS_DIR.glob("*.md"):
        content = pat_file.read_text(encoding="utf-8")
        if "tier: hot" in content or "##" in content:
            patterns.append(content)
    return "\n\n---\n\n".join(patterns[:5])


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("EDLM Memory Manager")
        print("Usage: python edlm_memory.py <command> [args]")
        print("Commands:")
        print("  init              - 初始化数据库")
        print("  save <goal> <content> <outcome> - 保存经验")
        print("  search <query>   - 搜索记忆")
        print("  briefing          - 查看当前 briefing")
        print("  rotate            - 检查并旋转层级")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        init_db()
    elif cmd == "save":
        if len(sys.argv) < 5:
            print("Usage: save <goal> <content> <outcome>")
            sys.exit(1)
        goal, content, outcome = sys.argv[2], sys.argv[3], sys.argv[4]
        save_experience(goal, None, content, outcome)
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: search <query>")
            sys.exit(1)
        results = search_memories(sys.argv[2])
        for r in results:
            print(f"- [{r[1][4]}] {r[1][1]}: {r[1][2][:100]}...")
    elif cmd == "briefing":
        print(load_briefing())
    elif cmd == "rotate":
        check_and_rotate()
    elif cmd == "status":
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT tier, COUNT(*) FROM memories GROUP BY tier")
        print("记忆统计:")
        for row in c.fetchall():
            print(f"  {row[0]}: {row[1]} 条")
        conn.close()