# 融合记忆框架设计（FUSED-MEMORY）

最后更新：2026-05-09

## Context

用户需求：
- A：会话启动时自动加载上下文（最高优先级）
- B1：语义检索能力（自然语言查询）
- C：SQLite-vec 本地嵌入（~37MB/10K向量，无需独立服务）
- 自动化：零手动操作

三插件核心优势：
| 来源 | 核心优势 |
|------|----------|
| claude-mem | 5 钩子生命周期自动捕获 + 3层渐进式披露 |
| mempalace | verbatim 逐字存储 + Closet 隐式缓存 + BM25 混合检索 |
| palaia | HOT/WARM/COLD 三层衰减 + 类型权重 + SQLite WAL |

---

## 核心设计原则

1. **记忆内容不压缩**：逐字保留，靠衰减和权重管理，不是摘要
2. **衰减驱动而非预算驱动**：HOT/WARM/COLD 自动旋转，不是 token 预算
3. **SQLite-vec 嵌入式**：~37MB vs ChromaDB ~936MB，无独立进程
4. **5 钩子自动化**：SessionStart/End + prompt 构建时自动捕获
5. **Session Briefing 注入**：会话开始时自动加载上次摘要 + 开放任务

---

## 架构总览

```
D:\CLAUDE.MD\memory\
├── me.md                    # L0: 身份（始终加载）
├── core.md                  # L1: 全局索引（始终加载）
├── briefing\
│   ├── current.md          # 本次会话摘要（自动生成）
│   └── history\
│       └── YYYY-MM-DD.md    # 历史会话摘要
├── verbatim\
│   └── YYYY-MM-DD\         # 按日期存储原始对话
│       └── {session_id}.md
├── projects\
│   └── {project}\          # L2: 项目记忆（按需加载）
├── closet\                  # L2缓存: 主题指针（LRU）
└── archive\                 # COLD: 30天+归档
```

```
D:\CLAUDE.MD\corpora\
├── memory.db               # SQLite + sqlite-vec
│   ├── memories            # 向量 + 元数据
│   ├── closet_index        # 主题指针缓存
│   └── sessions            # 会话元数据
└── palaia_config.json      # palaia 配置
```

---

## 三层衰减机制（融合 palaia）

| 层级 | 定义 | decay_score 范围 | 搜索范围 |
|------|------|-----------------|----------|
| **HOT** | < 7 天 或 score >= 0.5 | 0.5 ~ 1.0 | 始终 |
| **WARM** | 7-30 天 或 score >= 0.1 | 0.1 ~ 0.5 | 默认 |
| **COLD** | > 30 天 且 score < 0.1 | 0.0 ~ 0.1 | 仅 --all |

**衰减公式**（来自 palaia）：
```python
decay_score = exp(-λ * days_since_access) * (1 + log(1 + access_count))
```

**自动旋转**：
- 每次访问时更新 `last_access` 和 `access_count`
- 低于阈值时自动归档到 `archive/`

---

## 类型权重系统（融合 palaia）

| 类型 | 权重 | 说明 |
|------|------|------|
| **process** | 1.5x | 工作流程、SOP、执行步骤 |
| **decision** | 1.2x | 决策、选择、结论 |
| **memory** | 1.0x | 一般记忆、知识点 |

**GC 时保留优先级**：process > decision > memory

---

## 5 钩子自动化（融合 claude-mem）

| 钩子 | 时机 | 动作 |
|------|------|------|
| **SessionStart** | 会话开始 | 加载 me.md + core.md + briefing/current.md |
| **UserPromptSubmit** | 用户输入时 | 捕获用户意图更新 closet 索引 |
| **PostToolUse** | 工具执行后 | 捕获执行结果作为观察 |
| **Stop** | 停止时 | 生成会话摘要写入 briefing/history/ |
| **SessionEnd** | 会话结束 | 触发向量存储 + 衰减检查 |

---

## 向量检索（融合 mempalace + palaia）

**混合评分**：
```python
combined_score = 0.4 * BM25(query, text) + 0.6 * cosine_similarity(embed(query), embed(text))
```

**检索流程**：
1. 自然语言 query → embedding（本地 fastembed）
2. BM25 候选（SQLite FTS5）
3. 向量相似度重排（sqlite-vec SIMD）
4. 按 tier/type/weight 过滤
5. 返回 top-K（默认 5 条）

**Closet 缓存**（来自 mempalace）：
- 主题指针行：`topic|entities|→session_ref`
- 检索时 Closet 命中 +0.15 ~ +0.40 排名加成
- 每个 Closet 最多 1500 chars，LRU 清理

---

## Session Briefing（来自 palaia）

**生成时机**：Stop 钩子触发时

**内容结构**：
```markdown
---
session_id: xxx
date: 2026-05-09
duration: 45min
tier: hot
type: session
---

## 上次做了什么
- 完成了 Git 安装和 GitHub SSH 绑定
- 分析了三款记忆插件架构

## 开放任务
- [ ] 实施融合记忆框架
- [ ] 配置 OpenClaw MiniMax 模型

## 关键决策
- 选择方案 A（palaia CLI）实施记忆系统
- 记忆内容采用 verbatim 不压缩
```

**加载时机**：SessionStart 时，briefing/current.md 注入上下文

---

## 记忆内容格式（verbatim + frontmatter）

```markdown
---
id: {uuid}
tier: hot              # hot | warm | cold
type: decision        # memory | decision | process
weight: 1.0           # 1.0=memory, 1.2=decision, 1.5=process
tags: [记忆框架,GitHub]
last_access: 2026-05-09
access_count: 3
decay_score: 0.85
scope: private
---

<!-- 原始对话内容（逐字，不压缩） -->

User: 帮我下载 Git 工具到 D 盘，并和我的 GitHub 账户绑定

Assistant: Git 已成功安装到 D:\Apps\Git，SSH 密钥已生成并绑定
```

---

## 与 claude-mem 的关键差异

| 特性 | claude-mem | 本框架 |
|------|-----------|--------|
| 记忆内容 | 压缩为摘要 | **verbatim 逐字保留** |
| 向量存储 | ChromaDB 独立进程（~936MB） | **SQLite-vec 嵌入（~37MB）** |
| 衰减机制 | Token 预算渐进式披露 | **HOT/WARM/COLD 自动旋转** |
| 类型权重 | 无 | **process 1.5x / decision 1.2x / memory 1.0x** |
| Session 连续性 | 无 | **Session Briefing 自动注入** |
| 多智能体 | 有限 | **支持（scope: private/team/public）** |
| Crash 安全 | Worker Service WAL | **SQLite WAL + 原子写入** |

---

## 实施步骤

### Phase 1：基础设施
1. 安装依赖：`pip install sqlite-vec fastembed palaia`
2. 初始化 SQLite 数据库（memory.db）
3. 配置 hooks（在 Claude Code settings.json）

### Phase 2：迁移现有记忆
1. 将 me.md / core.md 导入为 HOT 层
2. 按日期组织 verbatim/ 目录
3. 生成历史 briefing/history/

### Phase 3：自动化
1. 配置 5 个 hooks（SessionStart/End 等）
2. 验证 briefing 自动加载
3. 验证 Stop 时自动生成摘要

### Phase 4：验证
1. 新会话：`memory load` 确认上下文加载
2. 对话后：`memory search` 能搜到新记忆
3. 30天后：验证 COLD 自动归档

---

## 成功标准

1. 新会话开始时自动看到上次摘要（无需手动）
2. 用自然语言能搜到历史记忆（语义检索）
3. 记忆库体积 < 50MB（含 10K 向量）
4. 无需独立进程（SQLite-vec 嵌入 Python）
5. 零手动操作（启动自动加载，关闭自动保存）