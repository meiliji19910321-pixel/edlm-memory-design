# EDLM + PERMANENT MEMORY 融合框架

**Experience-Driven Learning Memory + 永久记忆系统**

融合 claude-mem + mempalace + palaia 三款记忆插件优点的新一代 AI 记忆框架。

---

## 特性

| 特性 | 说明 |
|------|------|
| **AI 自主学习** | validation_count >= 5 时自动升级到 skills/ |
| **分层存储** | decision=完整记录，process=500字摘要 |
| **三层衰减** | HOT(<7天) / WARM(7-30天) / COLD(>30天) |
| **轻量存储** | SQLite-vec ~37MB（vs ChromaDB ~936MB）|
| **零手动操作** | 5 个钩子实现全自动化 |
| **永久可检索** | 所有记忆存储在文件系统 |

---

## 目录结构

```
edlm-memory-framework/
├── README.md                          # 本文件
├── EDLM-MEMORY-FRAMEWORK.md           # 完整设计文档
├── edlm_memory/                       # 核心模块
│   ├── edlm_memory.py                 # 主程序
│   ├── briefing_generator.py          # 会话摘要生成
│   └── stop_hook.ps1                  # 停止钩子脚本
├── settings.json.example              # 配置示例
└── CLAUDE.md.example                  # Claude Code 指令示例
```

---

## 快速安装

### 1. 克隆仓库

```bash
git clone https://github.com/meiliji19910321-pixel/edlm-memory-design.git
cd edlm-memory-design
```

### 2. 安装依赖

```bash
# Python 3.8+
pip install sqlite-vec

# 或使用 requirements.txt
pip install -r requirements.txt
```

### 3. 初始化数据库

```bash
python edlm_memory/edlm_memory.py init
```

### 4. 配置 Claude Code

将 `settings.json.example` 中的配置复制到你的 `D:\CLAUDE.MD\settings.json`：

```json
{
  "hooks": {
    "SessionStart": [...],
    "SessionEnd": [...],
    "Stop": [...]
  }
}
```

---

## 使用方法

### 保存经验

```python
from edlm_memory import save_experience

exp_id = save_experience(
    goal='设计记忆框架',
    domain='AI系统设计',
    content='讨论了融合方案的选择...',
    outcome='SUCCESS',
    success_factors=['通过提问逐步澄清需求'],
    derived_pattern='设计记忆系统时，应该先问用户的核心目标',
    tags=['记忆系统', 'EDLM']
)
```

### 搜索记忆

```python
from edlm_memory import search_memories

results = search_memories('记忆框架')
for score, r in results:
    print(f'[{r[4]}] {r[1]} (score: {score:.2f})')
```

### 查看当前 Briefing

```python
from edlm_memory import load_briefing

briefing = load_briefing()
print(briefing)
```

### 执行层级旋转

```bash
python edlm_memory/edlm_memory.py rotate
```

---

## 存储结构

```
D:\CLAUDE.MD\
├── memory\
│   ├── me.md                     # L0: 身份
│   ├── core.md                   # L1: 全局索引
│   ├── experiences\{YYYY-MM}\    # 经验库
│   ├── patterns\                 # 成功模式
│   ├── briefing\                 # 会话摘要
│   └── archive\                  # COLD 层归档
└── corpora\
    └── memory.db                 # SQLite + sqlite-vec
```

---

## 框架核心逻辑

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

## 与其他框架对比

| 特性 | claude-mem | mempalace | 本框架 |
|------|-----------|-----------|--------|
| 记忆内容 | 压缩摘要 | verbatim | **分层** |
| 向量存储 | ChromaDB(~936MB) | ChromaDB(~936MB) | **SQLite-vec(~37MB)** |
| 衰减机制 | Token预算 | 无 | **HOT/WARM/COLD** |
| 类型权重 | 无 | 无 | **process 1.5x** |
| 自主升级 | 无 | 无 | **validation_count→skills** |

---

## 注意事项

- 所有数据存储在 `D:\CLAUDE.MD\` 目录
- COLD 层不删除，只归档
- 首次使用需要配置 SSH Key 用于 GitHub 同步

---

## License

MIT License