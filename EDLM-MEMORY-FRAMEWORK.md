# EDLM + Ruflo 融合记忆框架 v2.0

最后更新：2026-05-13

## 框架概述

**全称**：Experience-Driven Learning Memory + Ruflo AgentDB
**融合来源**：EDLM（内容组织）+ Ruflo AgentDB（向量搜索索引）
**核心目标**：AI自主学习能力 + 永久记忆存储 + 语义检索

### v2.0 变更（相比 v1.0）

- 移除 SQLite/sqlite-vec 依赖 → 纯文件操作 + Ruflo 向量索引
- 移除 FTS5 全文搜索 → Ruflo HNSW 语义搜索
- 修复 rotation 逻辑 bug（列索引错误）
- 修复 search 命令（v1.0 忽略查询词）
- 新增 Ruflo memory_store 同步接口
- 新增会话上下文加载函数

---

## 核心工作流

```
用户提出目标
     ↓
AI 执行 → 结果 → 自判断 SUCCESS/FAILURE
     ↓
存入 experience（含 tier/decay_score/type/weight）→ 写入 Markdown 文件
     ↓
同时索引到 Ruflo AgentDB（edlm-memory namespace）
     ↓
定期提取 pattern → 更新 patterns/
     ↓
validation_count >= 5 → 写入 skills/（自主升级）
```

---

## 存储结构

```
D:\CLAUDE.MD\
├── memory\
│   ├── me.md                     # L0: 身份（始终加载）
│   ├── core.md                   # L1: 全局索引（始终加载）
│   ├── experiences\              # 经验库（核心）
│   │   └── {YYYY-MM}\
│   │       └── exp-{id}.md       # 每条经验（frontmatter + body）
│   ├── patterns\                 # 成功模式
│   │   └── pat-{domain}-{date}.md
│   ├── briefing\                 # Session 摘要
│   │   ├── current.md            # 本次会话摘要
│   │   └── history\YYYY-MM-DD.md # 历史会话摘要
│   ├── archive\                  # COLD 层（30天+归档，不删）
│   └── .edlm\                    # 融合框架元数据
│       ├── config.json           # 衰减参数/类型权重/搜索配置
│       └── skills\               # 自主升级技能存储
```

---

## Experience 格式

```markdown
---
id: exp-20260510-xxxxxxxx
date: 2026-05-10
goal: "下载 Git 到 D 盘并绑定 GitHub"
domain: 系统运维
tier: hot
type: process
weight: 1.5
outcome: SUCCESS
derived_pattern: SSH 配置时，私钥必须在默认路径下
success_factors: ["正确使用 ssh.exe 路径", "先生成密钥再添加"]
failure_patterns: []
decay_score: 1.0
last_access: 2026-05-10
access_count: 1
validation_count: 0
tags: Git,GitHub,SSH
created_at: 2026-05-10T01:40:05
---

[执行过程内容]
```

---

## Pattern 格式

```markdown
---
id: pat-系统运维-20260510
tier: hot
type: process
weight: 1.5
domain: 系统运维
decay_score: 1.0
last_access: 2026-05-10
access_count: 1
validation_count: 3
derived_from: ["exp-xxx", "exp-yyy"]
---

# Pattern: 系统运维

## 成功因素
- 因素1
- 因素2

## 适用场景
- 场景描述

## 验证状态
validation_count >= 5 时可写入 skills/
```

---

## 衰减机制

### 衰减公式

```python
decay_score = exp(-λ * days_since_access) * (1 + log(1 + access_count))
```

- λ = 0.1（可在 config.json 中调整）
- 每次访问时更新 `last_access` 和 `access_count`

### 层级定义

| 层级 | 定义 | decay_score | 默认搜索 |
|------|------|-------------|----------|
| **HOT** | < 7 天 或 score >= 0.5 | 0.5 ~ 1.0 | 始终 |
| **WARM** | 7-30 天 或 score >= 0.1 | 0.1 ~ 0.5 | 默认 |
| **COLD** | > 30 天 且 score < 0.1 | 0.0 ~ 0.1 | 仅 --all |

### 自动旋转

- `rotate` 命令重新计算所有非 COLD 记忆的 decay_score
- 降级为 COLD 的记忆自动移入 `archive/`
- **COLD 层不删除，只归档**

---

## 类型权重系统

| 类型 | 权重 | GC 保留优先级 | 说明 |
|------|------|--------------|------|
| **process** | 1.5x | 最高 | 工作流程、故障排查 SOP |
| **decision** | 1.2x | 中等 | 决策、选型、结论 |
| **memory** | 1.0x | 标准 | 一般知识点 |

---

## 分层记录规则

| 类型 | 触发条件 | 精度 | 存储大小 |
|------|----------|------|----------|
| **decision** | type=decision 或含"决策/选择/方案" | verbatim | ~20KB |
| **process** | type=process 或一般执行类 | 摘要500字 | ~5KB |
| **override** | 用户说"这个重要/详细记住" | verbatim | ~20KB |

---

## AI 自主升级机制

```
experience 积累 → validation_count++
     ↓
validation_count >= 5（同一 pattern 验证 5 次成功）
     ↓
写入 D:\CLAUDE.MD\memory\.edlm\skills\{domain}.md
     ↓
下次遇到同类问题 → 优先使用 skill
```

---

## 搜索架构

### 双层搜索

| 层 | 后端 | 用途 |
|----|------|------|
| **主搜索** | Ruflo AgentDB (HNSW) | 语义向量检索，理解自然语言 |
| **Fallback** | 文件扫描 + 关键词匹配 | Ruflo 不可用时的降级方案 |

### Ruflo 同步

每次保存 experience 后，同时通过 `memory_store` 写入 Ruflo AgentDB：
- namespace: `edlm-memory`
- key: experience id
- value: 结构化文本（goal + domain + content_preview + derived_pattern）
- tags: type, tier, domain, 关键词

### Fallback 文件扫描

综合评分：`0.6 * text_score + 0.4 * decay * (1 + log(1 + access)) * weight`

---

## 5 钩子自动化

| 钩子 | 时机 | 动作 |
|------|------|------|
| **SessionStart** | 会话开始 | 加载 me.md + core.md + briefing/current.md |
| **PostToolUse** | 工具执行后 | 捕获观察结果，更新 experience |
| **Stop** | 用户结束 | 自动生成 session briefing |
| **SessionEnd** | 会话结束 | 执行衰减检查，rotate 层级 |
| **onExperience** | 保存经验时 | 写入文件 + 索引到 Ruflo |

---

## 配置文件 (.edlm/config.json)

```json
{
  "version": "2.0",
  "decay": {
    "lambda": 0.1,
    "hot_days": 7,
    "warm_days": 30,
    "hot_min_score": 0.5,
    "warm_min_score": 0.1
  },
  "type_weights": {
    "process": 1.5,
    "decision": 1.2,
    "memory": 1.0
  },
  "search": {
    "primary": "ruflo-agentdb",
    "fallback": "file-scan",
    "default_limit": 5
  }
}
```

---

## CLI 命令

```bash
python edlm_memory/edlm_memory.py init      # 初始化目录结构
python edlm_memory/edlm_memory.py status    # 显示记忆库统计
python edlm_memory/edlm_memory.py search <query>  # 搜索记忆
python edlm_memory/edlm_memory.py rotate    # 执行衰减旋转
python edlm_memory/edlm_memory.py briefing  # 查看当前 briefing
python edlm_memory/edlm_memory.py context   # 加载会话上下文
python edlm_memory/edlm_memory.py sync-list # 列出待 Ruflo 同步数据
```

---

## API

```python
from edlm_memory.edlm_memory import (
    save_experience,     # 保存经验
    search_memories,     # 搜索（文件 fallback）
    load_briefing,       # 加载当前 briefing
    save_briefing,       # 保存 session briefing
    check_and_rotate,    # 执行衰减旋转
    load_session_context,# 加载会话启动上下文
    list_for_ruflo_sync, # 列出同步数据
    show_status,         # 显示统计
)
```

---

## 成功标准

1. 新会话开始时自动加载上次摘要
2. 自然语言能搜到历史经验（语义检索 via Ruflo）
3. 记忆库体积可控（纯 Markdown，无数据库膨胀）
4. 零外部依赖（Python 标准库 + Ruflo MCP）
5. AI 能自主升级（validation_count → skills）
6. COLD 层只归档不删除
7. 重要决策 verbatim，一般事件摘要

---

## GitHub

- 仓库：https://github.com/meiliji19910321-pixel/edlm-memory-design
- 内容：设计文档 + 框架代码 + 配置示例
