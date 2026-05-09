# 融合架构方案：Markdown 记忆层 + SQLite-vec 向量检索

## Context

用户需要：
1. 永久记忆（已有 D:\CLAUDE.MD\memory\）
2. 向量语义检索（claude-mem 的 Chroma 未运行）
3. 节省存储空间（排斥全量 verbatim + 外部向量库）

现有系统问题：
- claude-mem：Chroma 外部服务占空间（~936MB/10K向量），且服务未运行
- 全量 verbatim：token 浪费严重
- 我内置记忆：无向量检索，纯 grep

## 四者优势融合

| 优势 | 来源 |
|------|------|
| 三层衰减（HOT/WARM/COLD）+ 自动归档 | **palaia** |
| 类型加权（process/memory/task × 1.5/1.0/1.2）| **palaia** |
| BM25 + 向量混合检索（sqlite-vec）| **palaia** + mempalace-node |
| LRU 向量缓存（~7.5MB/5K向量）| mempalace-node |
| 流式 top-K，内存峰值恒定 | mempalace-node |
| Session Briefing（上次摘要+开放任务）| **palaia** |
| 自动捕获（LLM 提取对话知识点）| **palaia** |
| 200行硬上限强制合并 | agent-recall-mcp |
| Obsidian 兼容 Markdown 格式 | agent-recall-mcp |
| 隐私块 `<private>` 不参与捕获 | **palaia** |
| 新鲜度 boost（24h内 1.3x）| **palaia** |
| 手动写入 boost（1.3x > 自动捕获）| **palaia** |

## 推荐架构

### 存储布局

```
D:\CLAUDE.MD\
├── memory\
│   ├── me.md              # L0: 身份 ~100 tokens，始终加载
│   ├── core.md            # L1: 全局索引，始终加载
│   ├── session\
│   │   ├── current.md     # 当前会话 Briefing（上次摘要 + 开放任务）
│   │   └── YYYY-MM-DD.md  # 每日日志（自动捕获的知识点）
│   ├── projects\
│   │   └── {project}\     # L2: 项目记忆（按需加载）
│   │       ├── identity.md
│   │       ├── decisions\  # type=decision, weight=1.0
│   │       ├── processes\ # type=process, weight=1.5 (SOP/工作流)
│   │       └── learnings\  # type=memory, weight=1.0
│   └── archive\           # COLD: 30天+未访问，过期记忆
└── corpora\
    ├── memory.db          # SQLite + sqlite-vec（~37MB/10K向量）
    └── .palaia\           # palaia 配置（可选，用其 CLI）
```

### 三层衰减（palaia 模式）

| 层 | 定义 | 搜索 | 衰减规则 |
|----|------|------|----------|
| **HOT** | < 7天 / 访问≥10次 | 始终 | `access_count++`，`decay_score` 不变 |
| **WARM** | 7-30天 / 访问≥3次 | 默认 | `decay_score -= 0.1/天` |
| **COLD** | > 30天未访问 | 仅 `--all` | 移入 archive/ |

**权重**：`process=1.5x`，`task=1.2x`，`memory=1.0x`
**Boost**：`freshness（24h内）= 1.3x`，`manual（手动写入）= 1.3x`

### frontmatter 元数据

```markdown
---
id: abc-123-uuid
tier: hot           # hot | warm | cold
type: decision      # memory | process | task
weight: 1.0         # 1.0=memory, 1.2=task, 1.5=process
scope: private      # private | team | public
tags: [架构,python]
last_access: 2026-05-07
access_count: 12
decay_score: 0.92   # WARM层每日-0.1，<0.3时移入COLD
---

<!-- <private>敏感内容不参与自动捕获</private> -->

# 决策：采用 SQLite-vec 向量方案
```

### 向量检索（vs Chroma）

| 方案 | 10K向量占用 | 服务依赖 |
|------|------------|----------|
| Chroma | ~936MB | 独立进程 |
| **SQLite-vec** | **~37MB** | 无，嵌入进程 |

Embedding 优先使用本地 fastembed（CPU，~10ms/query），无 API Key 要求。

### 感知压缩（200行硬上限）

```markdown
---
salience: 0.85
last_access: 2026-05-07
access_count: 12
decay_score: 0.92
type: decision
---
# 决策：向量架构选型

<!-- 正文超过200行时强制摘要合并 -->
```

当 `access_count` 超过阈值或 `decay_score` 低于阈值时，自动归档到 L3。

## 实施步骤

### 方案 A（推荐）：直接使用 palaia CLI（最小开发量）

palaia 已完整实现所有功能，可直接使用：

```powershell
# 安装 palaia（Python CLI）
pip install palaia

# 初始化记忆库
palaia init --path D:\CLAUDE.MD\memory --backend sqlite

# 启动 embed-server（后台常驻，~10ms查询）
palaia embed-server &
```

**迁移现有记忆**：
```powershell
# 将 me.md, core.md 导入为 HOT 层记忆
palaia import D:\CLAUDE.MD\memory\me.md --tier hot --type memory
palaia import D:\CLAUDE.MD\memory\core.md --tier hot --type memory
```

### 方案 B（自建）：SQLite-vec + Markdown Hooks

如果不想依赖 palaia Python 包，用自建方案：

**步骤 1**：安装依赖
```powershell
pip install sqlite-vec fastembed-python
```

**步骤 2**：改造记忆文件
- `me.md` → L0 始终加载
- `core.md` → L1，增加 frontmatter（tier/type/decay_score）
- 新建 `projects/`、`archive/`、`session/`
- 每个文件加 frontmatter 元数据

**步骤 3**：编写 MCP 工具 `memory_search(query, tier, maxResults)`
- 读取 Markdown → 生成 embedding → 存入 sqlite-vec
- 查询时：BM25 候选 → 向量重排 → 按 tier/type/weight 过滤

**步骤 4**：配置 Hooks
```json
{
  "hooks": {
    "SessionStart": ["palaia briefing || memory_load"],
    "Stop": ["palaia capture || memory_save"]
  }
}
```

### 验证步骤

1. 新会话：确认 L0（me.md）+ session briefing 加载（< 400 tokens）
2. 对话后：`palaia list` 或 `memory_search` 能搜到新记忆
3. 30天后：验证 COLD 层自动归档，HOT→WARM→COLD 衰减正常
4. `palaia.db` 文件体积 < 50MB（vs Chroma ~936MB）

## 关键文件

| 文件 | 作用 |
|------|------|
| `D:\CLAUDE.MD\memory\me.md` | L0 身份，始终加载 |
| `D:\CLAUDE.MD\memory\core.md` | L1 全局索引，始终加载 |
| `D:\CLAUDE.MD\memory\session\current.md` | 会话 Briefing（上次摘要+开放任务）|
| `D:\CLAUDE.MD\memory\projects\{proj}\*` | L2 项目记忆，按需加载 |
| `D:\CLAUDE.MD\memory\archive\*` | COLD 层，>30天归档 |
| `D:\CLAUDE.MD\memory\corpora\memory.db` | SQLite + sqlite-vec 向量库 |
| `D:\CLAUDE.MD\plugins\thedotmack\` | 卸载 claude-mem |

## 优点（vs claude-mem）

| | claude-mem | 本方案 |
|--|-----------|--------|
| 向量占用 | ~936MB（Chroma）| ~37MB（SQLite-vec）|
| 外部服务 | Chroma + Worker 双进程 | **无需独立服务** |
| 衰减机制 | 无 | HOT/WARM/COLD 自动归档 |
| 类型权重 | 无 | process 1.5x, task 1.2x |
| Session 连续 | 无 | Briefing 自动注入 |
| Markdown 兼容 | SQLite 不可读 | 100% 可直接编辑 |
| 记忆追溯 | 纯向量 | **Markdown 可人类阅读** |
