#!/usr/bin/env python3
"""
EDLM Memory Manager v2.0 - 融合记忆框架
EDLM 内容组织 + Ruflo AgentDB 搜索索引

纯文件操作，零外部依赖（搜索交给 Ruflo MCP）
"""

import os
import json
import math
import re
import uuid
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ========== 路径配置 ==========

BASE_DIR = Path("D:/CLAUDE.MD")
MEMORY_DIR = BASE_DIR / "memory"
EXPERIENCES_DIR = MEMORY_DIR / "experiences"
PATTERNS_DIR = MEMORY_DIR / "patterns"
BRIEFING_DIR = MEMORY_DIR / "briefing"
BRIEFING_HISTORY_DIR = BRIEFING_DIR / "history"
ARCHIVE_DIR = MEMORY_DIR / "archive"
EDLM_DIR = MEMORY_DIR / ".edlm"
SKILLS_DIR = EDLM_DIR / "skills"
CONFIG_PATH = EDLM_DIR / "config.json"

# 默认配置（会被 config.json 覆盖）
DEFAULT_CONFIG = {
    "decay": {"lambda": 0.1, "hot_days": 7, "warm_days": 30, "hot_min_score": 0.5, "warm_min_score": 0.1},
    "type_weights": {"process": 1.5, "decision": 1.2, "memory": 1.0}
}

SUMMARY_MAX_CHARS = 500

# ========== 配置加载 ==========

def load_config():
    """加载 .edlm/config.json，不存在则用默认值"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG

# ========== Frontmatter 解析 ==========

def parse_frontmatter(text):
    """解析 markdown frontmatter，返回 (metadata_dict, body_text)"""
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    header = text[3:end].strip()
    body = text[end + 3:].strip()

    meta = {}
    for line in header.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()

        # 类型转换
        if val.lower() == "true":
            val = True
        elif val.lower() == "false":
            val = False
        elif re.match(r"^-?\d+$", val):
            val = int(val)
        elif re.match(r"^-?\d+\.\d+$", val):
            val = float(val)

        meta[key] = val

    return meta, body


def write_frontmatter(meta, body):
    """将 metadata + body 写成 markdown 格式"""
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            v = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, bool):
            v = str(v).lower()
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)

# ========== 衰减计算 ==========

def calc_decay_score(last_access_str, access_count, config=None):
    """计算衰减分数：exp(-λ * days) * (1 + log(1 + access_count))"""
    if not last_access_str:
        return 1.0

    cfg = config or load_config()
    lam = cfg.get("decay", {}).get("lambda", 0.1)

    try:
        last_access = datetime.fromisoformat(last_access_str.replace("Z", "+00:00"))
    except ValueError:
        return 1.0

    days_since = (datetime.now() - last_access).days
    time_decay = math.exp(-lam * days_since)
    hit_bonus = 1 + math.log(1 + access_count)

    return round(time_decay * hit_bonus, 4)


def classify_tier(decay_score, last_access_str, config=None):
    """分类记忆层级：hot / warm / cold"""
    if not last_access_str:
        return "hot"

    cfg = config or load_config()
    decay_cfg = cfg.get("decay", DEFAULT_CONFIG["decay"])

    try:
        last_access = datetime.fromisoformat(last_access_str.replace("Z", "+00:00"))
    except ValueError:
        return "hot"

    days_since = (datetime.now() - last_access).days

    if days_since <= decay_cfg.get("hot_days", 7) or decay_score >= decay_cfg.get("hot_min_score", 0.5):
        return "hot"
    elif days_since <= decay_cfg.get("warm_days", 30) or decay_score >= decay_cfg.get("warm_min_score", 0.1):
        return "warm"
    else:
        return "cold"

# ========== 类型判断 ==========

def determine_type(content, goal, user_override=False):
    """判断记录类型：decision（verbatim）或 process（摘要）"""
    if user_override:
        return "decision"

    decision_keywords = ["选择", "决策", "方案", "决定", "要转行", "创业", "方向", "对比", "选型"]
    for kw in decision_keywords:
        if kw in goal or kw in content[:200]:
            return "decision"

    return "process"

# ========== 保存经验 ==========

def save_experience(goal, domain, content, outcome, success_factors=None,
                    failure_patterns=None, derived_pattern=None, tags=None,
                    user_override=False):
    """保存一条经验到文件系统"""
    config = load_config()
    weights = config.get("type_weights", DEFAULT_CONFIG["type_weights"])

    exp_id = f"exp-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    exp_type = determine_type(content, goal, user_override)

    # 决定存储内容
    if exp_type == "decision" or user_override:
        stored_content = content
    else:
        stored_content = content[:SUMMARY_MAX_CHARS]
        if len(content) > SUMMARY_MAX_CHARS:
            stored_content += "\n\n[摘要截断 - 完整内容见源对话]"

    # 标签处理
    if tags is None:
        tags = [domain] if domain else []
    tags_str = ",".join(tags) if isinstance(tags, list) else tags

    today = datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat()

    meta = {
        "id": exp_id,
        "date": today,
        "goal": goal,
        "domain": domain or "general",
        "tier": "hot",
        "type": exp_type,
        "weight": weights.get(exp_type, 1.0),
        "outcome": outcome,
        "derived_pattern": derived_pattern or "",
        "success_factors": json.dumps(success_factors or [], ensure_ascii=False),
        "failure_patterns": json.dumps(failure_patterns or [], ensure_ascii=False),
        "decay_score": 1.0,
        "last_access": today,
        "access_count": 1,
        "validation_count": 0,
        "tags": tags_str,
        "created_at": now_iso
    }

    # 写入 Markdown 文件
    month_dir = EXPERIENCES_DIR / datetime.now().strftime("%Y-%m")
    month_dir.mkdir(parents=True, exist_ok=True)

    md_path = month_dir / f"{exp_id}.md"
    md_content = write_frontmatter(meta, stored_content)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[EDLM] 经验已保存: {exp_id} (type={exp_type}, tier=hot)")
    return exp_id

# ========== 加载经验 ==========

def load_all_experiences():
    """扫描所有 experience 文件，返回 (metadata, body, filepath) 列表"""
    experiences = []
    if not EXPERIENCES_DIR.exists():
        return experiences

    for md_file in sorted(EXPERIENCES_DIR.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if meta.get("id"):
            experiences.append((meta, body, md_file))

    return experiences

# ========== 更新衰减 ==========

def update_decay(filepath):
    """更新单个 experience 文件的衰减分数和层级"""
    text = filepath.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    if not meta.get("id"):
        return

    config = load_config()
    last_access = meta.get("last_access", meta.get("date", ""))
    access_count = meta.get("access_count", 0)

    new_score = calc_decay_score(last_access, access_count, config)
    new_tier = classify_tier(new_score, last_access, config)

    meta["decay_score"] = new_score
    meta["tier"] = new_tier

    md_content = write_frontmatter(meta, body)
    filepath.write_text(md_content, encoding="utf-8")

    return new_tier, new_score

# ========== 搜索记忆（文件扫描） ==========

def search_memories(query, tier_filter=None, limit=5):
    """搜索记忆（纯文件扫描，作为 Ruflo 的 fallback）"""
    config = load_config()
    weights = config.get("type_weights", DEFAULT_CONFIG["type_weights"])
    query_lower = query.lower()

    results = []
    for meta, body, filepath in load_all_experiences():
        # tier 过滤
        if tier_filter and meta.get("tier") not in tier_filter:
            continue

        # 文本匹配：搜索 goal + content + tags + derived_pattern
        searchable = " ".join([
            str(meta.get("goal", "")),
            str(meta.get("tags", "")),
            str(meta.get("derived_pattern", "")),
            body
        ]).lower()

        # 简单关键词匹配得分
        query_words = query_lower.split()
        match_count = sum(1 for w in query_words if w in searchable)
        if match_count == 0:
            continue

        text_score = match_count / len(query_words)

        # 综合评分
        decay = meta.get("decay_score", 1.0)
        access = meta.get("access_count", 0)
        weight = weights.get(meta.get("type", "memory"), 1.0)
        combined = 0.6 * text_score + 0.4 * decay * (1 + math.log(1 + access)) * weight

        results.append((combined, meta, body, filepath))

    results.sort(reverse=True, key=lambda x: x[0])
    return results[:limit]

# ========== Session Briefing ==========

def save_briefing(session_id, what_done, open_tasks, key_decisions, derived_patterns):
    """保存 Session Briefing"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")

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
    BRIEFING_DIR.mkdir(parents=True, exist_ok=True)
    BRIEFING_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    current_path = BRIEFING_DIR / "current.md"
    with open(current_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 追加到历史
    history_path = BRIEFING_HISTORY_DIR / f"{date_str}.md"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n<!-- {session_id} -->\n")
        f.write(content)

    print(f"[EDLM] Briefing 已保存: {session_id}")
    return str(current_path)


def load_briefing():
    """加载当前 briefing"""
    current_path = BRIEFING_DIR / "current.md"
    if current_path.exists():
        return current_path.read_text(encoding="utf-8")
    return ""

# ========== Pattern 提取 ==========

def extract_pattern(experience_ids):
    """从多个经验中提取 pattern"""
    if not experience_ids or len(experience_ids) < 2:
        return None

    patterns = []
    for meta, body, _ in load_all_experiences():
        if meta.get("id") in experience_ids and meta.get("derived_pattern"):
            patterns.append(meta)

    if len(patterns) < 2:
        return None

    domains = [p.get("domain", "") for p in patterns]
    main_domain = max(set(domains), key=domains.count)

    all_factors = []
    for p in patterns:
        factors = p.get("success_factors", "[]")
        if isinstance(factors, str):
            try:
                factors = json.loads(factors)
            except json.JSONDecodeError:
                factors = []
        all_factors.extend(factors)

    unique_factors = list(dict.fromkeys(all_factors))[:5]

    pat_id = f"pat-{main_domain}-{datetime.now().strftime('%Y%m%d')}"
    pat_content = f"""---
id: {pat_id}
tier: hot
type: process
weight: 1.5
domain: {main_domain}
decay_score: 1.0
last_access: {datetime.now().strftime('%Y-%m-%d')}
access_count: 1
validation_count: {len(patterns)}
derived_from: {json.dumps(experience_ids, ensure_ascii=False)}
---

# Pattern: {main_domain}

## 成功因素
{chr(10).join(f"- {f}" for f in unique_factors)}

## 适用场景
- {patterns[0].get('derived_pattern', '待提取')}

## 验证状态
validation_count >= 5 时可写入 skills/
"""

    # 保存到 patterns 目录
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    pat_path = PATTERNS_DIR / f"{pat_id}.md"
    pat_path.write_text(pat_content, encoding="utf-8")

    print(f"[EDLM] Pattern 已提取: {pat_id}")
    return pat_id

# ========== 旋转归档 ==========

def check_and_rotate():
    """检查并旋转记忆层级（cold -> archive）"""
    if not EXPERIENCES_DIR.exists():
        return

    rotated = 0
    for md_file in EXPERIENCES_DIR.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)

        if not meta.get("id"):
            continue

        config = load_config()
        last_access = meta.get("last_access", meta.get("date", ""))
        access_count = meta.get("access_count", 0)

        new_score = calc_decay_score(last_access, access_count, config)
        new_tier = classify_tier(new_score, last_access, config)
        old_tier = meta.get("tier", "hot")

        if new_tier != old_tier:
            meta["decay_score"] = new_score
            meta["tier"] = new_tier

            if new_tier == "cold":
                # 移入 archive
                month_dir = ARCHIVE_DIR / datetime.now().strftime("%Y-%m")
                month_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(md_file), str(month_dir / md_file.name))
                print(f"[EDLM] 归档: {meta['id']} -> archive/{month_dir.name}/")
            else:
                md_content = write_frontmatter(meta, body)
                md_file.write_text(md_content, encoding="utf-8")

            rotated += 1

    print(f"[EDLM] 旋转完成: {rotated} 条记忆已更新")

# ========== 状态统计 ==========

def show_status():
    """显示记忆库状态"""
    experiences = load_all_experiences()
    config = load_config()

    tier_count = {"hot": 0, "warm": 0, "cold": 0}
    type_count = {"process": 0, "decision": 0, "memory": 0}

    for meta, _, _ in experiences:
        tier = meta.get("tier", "hot")
        mem_type = meta.get("type", "memory")
        tier_count[tier] = tier_count.get(tier, 0) + 1
        type_count[mem_type] = type_count.get(mem_type, 0) + 1

    # Pattern 统计
    pattern_count = len(list(PATTERNS_DIR.glob("*.md"))) if PATTERNS_DIR.exists() else 0

    # Briefing 统计
    briefing_count = len(list(BRIEFING_HISTORY_DIR.glob("*.md"))) if BRIEFING_HISTORY_DIR.exists() else 0

    print("=" * 50)
    print("  EDLM 融合记忆系统 v2.0")
    print("=" * 50)
    print(f"\n  经验总数: {len(experiences)}")
    print(f"    HOT: {tier_count['hot']}  |  WARM: {tier_count['warm']}  |  COLD: {tier_count['cold']}")
    print(f"    process: {type_count['process']}  |  decision: {type_count['decision']}  |  memory: {type_count['memory']}")
    print(f"\n  Patterns: {pattern_count}")
    print(f"  Briefings: {briefing_count}")
    print(f"\n  衰减 λ: {config.get('decay', {}).get('lambda', 0.1)}")
    print(f"  搜索后端: {config.get('search', {}).get('primary', 'file-scan')}")
    print("=" * 50)

# ========== Ruflo 同步（供外部调用） ==========

def list_for_ruflo_sync():
    """列出所有 experience 元数据，供 Ruflo memory_store 索引"""
    sync_list = []
    for meta, body, filepath in load_all_experiences():
        sync_list.append({
            "id": meta.get("id", ""),
            "goal": meta.get("goal", ""),
            "domain": meta.get("domain", ""),
            "tier": meta.get("tier", ""),
            "type": meta.get("type", ""),
            "weight": meta.get("weight", 1.0),
            "decay_score": meta.get("decay_score", 1.0),
            "tags": meta.get("tags", ""),
            "derived_pattern": meta.get("derived_pattern", ""),
            "content_preview": body[:200],
            "file_path": str(filepath)
        })
    return sync_list

# ========== 会话上下文加载 ==========

def load_session_context():
    """加载会话启动时的上下文内容"""
    sections = []

    # me.md
    me_path = MEMORY_DIR / "me.md"
    if me_path.exists():
        sections.append(("me.md", me_path.read_text(encoding="utf-8")))

    # core.md
    core_path = MEMORY_DIR / "core.md"
    if core_path.exists():
        sections.append(("core.md", core_path.read_text(encoding="utf-8")))

    # current briefing
    briefing = load_briefing()
    if briefing:
        sections.append(("briefing/current.md", briefing))

    return sections


# ========== CLI ==========

def main():
    if len(sys.argv) < 2:
        print("EDLM Memory Manager v2.0 (融合版)")
        print()
        print("Commands:")
        print("  init                初始化目录结构")
        print("  save <goal> <content> <outcome>  保存经验")
        print("  search <query>      搜索记忆")
        print("  briefing            查看当前 briefing")
        print("  rotate              检查并旋转层级")
        print("  status              显示记忆库状态")
        print("  context             加载会话上下文")
        print("  sync-list           列出待同步到 Ruflo 的数据")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        for d in [EXPERIENCES_DIR, PATTERNS_DIR, BRIEFING_DIR, BRIEFING_HISTORY_DIR,
                  ARCHIVE_DIR, EDLM_DIR, SKILLS_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        print("[EDLM] 目录结构已初始化")

    elif cmd == "save":
        if len(sys.argv) < 5:
            print("Usage: save <goal> <content> <outcome> [domain]")
            sys.exit(1)
        domain = sys.argv[5] if len(sys.argv) > 5 else None
        save_experience(sys.argv[2], domain, sys.argv[3], sys.argv[4])

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: search <query>")
            sys.argv(1)
        query = " ".join(sys.argv[2:])
        results = search_memories(query)
        if not results:
            print("未找到匹配的记忆")
        for score, meta, body, _ in results:
            print(f"[{score:.3f}] {meta.get('id', '?')} | {meta.get('goal', '?')[:60]}")
            print(f"        tier={meta.get('tier')} type={meta.get('type')} domain={meta.get('domain')}")

    elif cmd == "briefing":
        content = load_briefing()
        if content:
            print(content)
        else:
            print("暂无 briefing")

    elif cmd == "rotate":
        check_and_rotate()

    elif cmd == "status":
        show_status()

    elif cmd == "context":
        sections = load_session_context()
        for name, content in sections:
            print(f"=== {name} ===")
            print(content[:500])
            print()

    elif cmd == "sync-list":
        items = list_for_ruflo_sync()
        print(json.dumps(items, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
