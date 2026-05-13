# EDLM + Ruflo 融合记忆系统 v2.0

**Experience-Driven Learning Memory + Ruflo AgentDB**

EDLM 提供内容组织逻辑（分层衰减/类型权重/自主升级），Ruflo 提供向量搜索索引。融合成一套零外部依赖的记忆系统。

---

## 架构

```
┌─────────────────────────────────────┐
│  EDLM 层（内容组织）                 │
│  - Experience / Pattern / Skill     │
│  - HOT / WARM / COLD 三层衰减       │
│  - process 1.5x / decision 1.2x    │
│  - validation_count → skills/       │
├─────────────────────────────────────┤
│  Ruflo AgentDB 层（搜索索引）        │
│  - HNSW 向量搜索 + 语义检索         │
│  - 384维 ONNX 嵌入                  │
│  - 零外部依赖（MCP 内置）            │
└─────────────────────────────────────┘
```

---

## 特性

| 特性 | 说明 |
|------|------|
| **分层存储** | decision=完整 verbatim，process=500字摘要 |
| **三层衰减** | HOT(<7天) / WARM(7-30天) / COLD(>30天)，自动归档 |
| **类型权重** | process 1.5x / decision 1.2x / memory 1.0x |
| **AI 自主升级** | 同一 pattern 验证 5 次 → 写入 skills/ |
| **语义搜索** | Ruflo AgentDB HNSW 向量检索 |
| **会话连续** | SessionStart 自动加载 briefing |
| **零依赖** | Python 标准库 + Ruflo MCP（无 SQLite/ChromaDB） |

---

## 目录结构

```
edlm-memory-framework/
├── README.md                          # 本文件
├── EDLM-MEMORY-FRAMEWORK.md           # 完整设计文档
├── edlm_memory/                       # 核心模块
│   ├── edlm_memory.py                 # 主程序（纯文件操作）
│   ├── briefing_generator.py          # 会话摘要生成
│   └── stop_hook.ps1                  # Stop 钩子脚本
├── settings.json.example              # Claude Code 钩子配置示例
└── CLAUDE.md.example                  # Claude Code 指令示例
```

## 存储结构

```
D:\CLAUDE.MD\
├── memory\
│   ├── me.md                     # 身份（始终加载）
│   ├── core.md                   # 全局索引（始终加载）
│   ├── experiences\{YYYY-MM}\    # 经验库（Markdown + frontmatter）
│   ├── patterns\                 # 成功模式
│   ├── briefing\                 # 会话摘要
│   ├── archive\                  # COLD 层归档
│   └── .edlm\
│       ├── config.json           # 融合配置
│       └── skills\               # 自主升级技能
```

---

## 快速使用

### 初始化

```bash
python edlm_memory/edlm_memory.py init
```

### 保存经验

```python
from edlm_memory.edlm_memory import save_experience

exp_id = save_experience(
    goal='设计记忆框架',
    domain='AI系统设计',
    content='讨论了融合方案的选择...',
    outcome='SUCCESS',
    success_factors=['通过提问逐步澄清需求'],
    derived_pattern='设计记忆系统时，先问核心目标',
    tags=['记忆系统', 'EDLM']
)
```

### 搜索记忆（文件扫描 fallback）

```python
from edlm_memory.edlm_memory import search_memories

results = search_memories('记忆框架')
for score, meta, body, _ in results:
    print(f'[{score:.3f}] {meta["goal"]}')
```

### 语义搜索（通过 Ruflo MCP）

在 Claude Code 中直接使用 `memory_search` 工具，namespace 设为 `edlm-memory`。

### 查看状态

```bash
python edlm_memory/edlm_memory.py status
```

输出示例：
```
  EDLM 融合记忆系统 v2.0
  经验总数: 2
    HOT: 2  |  WARM: 0  |  COLD: 0
    process: 1  |  decision: 1  |  memory: 0
  Patterns: 0
  Briefings: 0
  衰减 λ: 0.1
  搜索后端: ruflo-agentdb
```

---

## 钩子配置

将 `settings.json.example` 中的 hooks 配置合并到你的 `D:\.claude\settings.json`：

| 钩子 | 动作 |
|------|------|
| **SessionStart** | 加载 me.md + core.md + briefing/current.md |
| **SessionEnd** | 执行衰减检查和旋转 |
| **Stop** | 自动生成 session briefing |

---

## 框架核心流程

```
用户提出目标
     ↓
AI 执行 → 结果 → 自判断 SUCCESS/FAILURE
     ↓
存入 experience（含 tier/decay_score/type/weight）
     ↓
Ruflo AgentDB 自动索引（语义搜索）
     ↓
定期提取 pattern → 更新 patterns/
     ↓
validation_count >= 5 → 写入 skills/（自主升级）
```

---

## 衰减公式

```python
decay_score = exp(-0.1 * days_since_access) * (1 + log(1 + access_count))
```

| 层级 | 定义 | decay_score |
|------|------|-------------|
| **HOT** | < 7 天 或 score >= 0.5 | 0.5 ~ 1.0 |
| **WARM** | 7-30 天 或 score >= 0.1 | 0.1 ~ 0.5 |
| **COLD** | > 30 天 且 score < 0.1 | 0.0 ~ 0.1 |

COLD 层不删除，只归档到 `archive/`。

---

## License

MIT License
