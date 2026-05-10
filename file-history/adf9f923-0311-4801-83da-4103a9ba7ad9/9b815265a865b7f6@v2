# EDLM + PERMANENT MEMORY 融合框架

最后更新：2026-05-10

## 框架概述

**全称**：Experience-Driven Learning Memory + PERMANENT MEMORY
**融合来源**：claude-mem (5钩子自动化) + mempalace (verbatim存储) + palaia (三层衰减+类型权重)
**核心目标**：AI自主学习能力 + 永久记忆存储

---

## 核心工作流

```
用户提出目标
     ↓
AI 执行 → 结果 → 自判断 SUCCESS/FAILURE
     ↓
存入 experience（含 tier/decay_score/type/weight）
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
│   │   └── {YYYY-MM}\            # 按月组织
│   │       └── exp-{id}.md      # 每条经验
│   ├── patterns\                 # 成功模式（palaia 衰减）
│   │   └── {domain}.md          # 按领域组织 hot/warm/cold
│   ├── briefing\                 # Session 摘要
│   │   ├── current.md            # 本次会话摘要
│   │   └── history\YYYY-MM-DD.md # 历史会话摘要
│   └── archive\                  # COLD 层（30天+归档，不删）
└── corpora\
    └── memory.db                 # SQLite + sqlite-vec（~37MB/10K向量）
```

---

## Experience 格式

```markdown
---
id: exp-2026-0510-001
date: 2026-05-10
goal: "下载 Git 到 D 盘并绑定 GitHub"
domain: 系统运维
tier: hot                    # hot | warm | cold（palaia 衰减）
type: process               # memory | decision | process（权重不同）
weight: 1.5                  # process=1.5, decision=1.2, memory=1.0
decay_score: 1.0
outcome: SUCCESS
success_factors:
  - 正确使用 D:\Apps\Git\usr\bin\ssh.exe
  - 先添加 known_hosts 再连接
failure_patterns: []
derived_pattern: "SSH 配置失败时，先检查 known_hosts 是否包含目标主机"
last_access: 2026-05-10
access_count: 1
validation_count: 0
---

## 执行过程
[500字以内摘要]（type=process时）
[完整verbatim记录]（type=decision 或 override时）
```

---

## Pattern 格式

```markdown
---
id: pat-git-ssh
tier: hot
type: process
weight: 1.5
domain: 系统运维
decay_score: 0.88
last_access: 2026-05-10
access_count: 3
validation_count: 3
derived_from: [exp-2026-0510-001]
---

# Git + SSH 故障排查模式

## 触发条件
- Git SSH 连接失败（Permission denied）
- 私钥已添加 GitHub 但连接不上

## 首选解决方案
1. `ssh -T git@github.com` 检查连接
2. 确认 `~\.ssh\known_hosts` 包含 github.com
3. 确认私钥在 `~\.ssh\` 下（默认读取路径）
4. 用 `ssh -v` 调试模式排查

## 验证方式
返回 "Hi {username}!" 即成功

## 自主升级条件
validation_count >= 5 → 写入 `D:\CLAUDE.MD\skills\{domain}\SKILL.md`
```

---

## palaia 三层衰减机制

### 层级定义

| 层级 | 定义 | decay_score | 默认搜索 |
|------|------|-------------|----------|
| **HOT** | < 7 天 或 score >= 0.5 | 0.5 ~ 1.0 | ✅ 始终 |
| **WARM** | 7-30 天 或 score >= 0.1 | 0.1 ~ 0.5 | ✅ 默认 |
| **COLD** | > 30 天 且 score < 0.1 | 0.0 ~ 0.1 | ❌ 仅 --all |

### 衰减公式

```python
decay_score = exp(-0.1 * days_since_access) * (1 + log(1 + access_count))
```

### 自动旋转

- 每次访问时更新 `last_access` 和 `access_count`
- 低于阈值时自动移入 `archive/`
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
| **override** | 你说"这个重要/详细记住/记住这个方案/这是关键决策" | verbatim | ~20KB |

### AI 判断示例

```
用户："我想转行做AI自媒体" → AI自动标记为 decision → verbatim记录
用户："帮我下载 Git" → AI标记为 process → 摘要500字
用户："这个方案很重要，记住" → verbatim（用户override）
```

### override 语法（任一触发）

- "这个重要"
- "详细记住"
- "记住这个方案"
- "这是关键决策"

---

## AI 自主升级机制

### 升级流程

```
experience 积累 → validation_count++
     ↓
validation_count >= 5（同一pattern验证5次成功）
     ↓
写入 `D:\CLAUDE.MD\skills\{domain}\SKILL.md`
     ↓
下次遇到同类问题 → 优先使用 skill 配置
```

### 升级条件

- 同一 derived_pattern 验证 >= 5 次
- 验证标准：执行后 outcome = SUCCESS
- 写入位置：`D:\CLAUDE.MD\skills\{domain}\SKILL.md`

---

## 5 钩子自动化

| 钩子 | 时机 | 动作 |
|------|------|------|
| **SessionStart** | 会话开始 | 加载 me.md + patterns (hot tier) + briefing/current.md |
| **GoalSet** | 用户给出目标 | 创建 experience tracking，设置 goal/domain |
| **PostToolUse** | 工具执行后 | 捕获观察结果，更新 success_factors/failure_patterns |
| **Stop** | 用户结束/你说"结束" | 评估目标达成情况，写入 experience |
| **SessionEnd** | 会话结束 | 提取 pattern，更新 decay_score，检查 rotation |

---

## Session Briefing 格式

```markdown
---
session_id: xxx
date: 2026-05-10
duration: 45min
tier: hot
type: session
---

## 上次做了什么
- [列出主要完成项]

## 开放任务
- [ ] 未完成的任务

## 关键决策
- [列出决策内容]

## 经验提取
- derived_pattern: "..."
```

---

## 向量检索架构

### 混合评分

```python
combined_score = 0.4 * BM25(query, text) + 0.6 * cosine_similarity(embed(query), embed(text))
```

### 检索流程

1. 自然语言 query → embedding（本地 fastembed）
2. BM25 候选（SQLite FTS5）
3. 向量相似度重排（sqlite-vec SIMD）
4. 按 tier/type/weight 过滤
5. 返回 top-K（默认 5 条）

### 存储预估

| 阶段 | 大小 |
|------|------|
| 初期（5K向量） | ~20MB |
| 中期（10K向量） | ~37MB |
| 1年后（50K向量）| ~185MB |

---

## 与各插件对比

| 特性 | claude-mem | mempalace | 本框架 |
|------|-----------|-----------|--------|
| 记忆内容 | 压缩摘要 | verbatim | **分层（decision完整/process摘要）** |
| 向量存储 | ChromaDB（~936MB）| ChromaDB（~936MB）| **SQLite-vec（~37MB）** |
| 衰减机制 | Token预算 | 无 | **HOT/WARM/COLD自动旋转** |
| 类型权重 | 无 | 无 | **process 1.5x / decision 1.2x** |
| 自主升级 | 无 | 无 | **validation_count → skills** |
| Crash安全 | Worker WAL | 文件锁 | **SQLite WAL** |
| 外部依赖 | Bun+ChromaDB | ChromaDB | **仅 Python** |

---

## 成功标准

1. ✅ 新会话开始时自动加载上次摘要（无需手动）
2. ✅ 自然语言能搜到历史经验（语义检索）
3. ✅ 记忆库体积可控（初期~50MB，1年~200MB）
4. ✅ 无需独立进程（SQLite-vec 嵌入 Python）
5. ✅ 零手动操作（启动自动加载，关闭自动保存）
6. ✅ 重启后可查（所有记忆在文件系统）
7. ✅ 重要决策 verbatim，一般事件摘要
8. ✅ AI 能自主升级（validation_count → skills）

---

## GitHub 存档信息

- 存档位置：https://github.com/meiliji19910321-pixel/edlm-memory-design
- 存档内容：本设计文档 + 框架规范
- 用途：跨设备同步、设计备份