# 记忆系统实现计划

> **2026-05-08 实施状态**
> ✅ 已完成：Layer 1、Layer 2（embedder+retriever）、Layer 3（memory_file）、Layer 4（trust+extractor）、Layer 5（curator）、钩子、CLI
> ⏳ 未完成：bge-m3 模型（当前用 all-MiniLM-L6-v2 替代）、Claude Code 插件级集成

## 阶段一：存储层（Layer 1）— 数据库基础设施

---

### Task: 创建目录结构和数据库 Schema

**File(s)**
- `D:\CLAUDE.MD\mem\.db\memory.db`
- `D:\CLAUDE.MD\mem\memories\identity\`
- `D:\CLAUDE.MD\mem\memories\artifact\`
- `D:\CLAUDE.MD\mem\memories\topic\`
- `D:\CLAUDE.MD\mem\memories\memory\`
- `D:\CLAUDE.MD\mem\conversations\`
- `D:\CLAUDE.MD\mem\hooks\`

**What to do**
创建 SQLite 数据库，包含以下表：
- `memories`（id, type, content, vector_id, trust_level, created_at, updated_at, version_chain）
- `topics`（id, name, current_version_id, created_at）
- `topic_versions`（id, topic_id, version_num, content, created_at）
- `conversations`（id, date, summary_id, raw_path, status, created_at）
- `pending_memories`（id, conversation_id, extracted_content, trust_level, status, created_at）
- `memory_embeddings`（memory_id, vector, embedding_model）
- FTS5 虚拟表用于全文搜索

WAL 模式：`PRAGMA journal_mode=WAL;`

**Verification**
```sql
SELECT * FROM memories LIMIT 1;  -- 应返回空，无报错
PRAGMA journal_mode;             -- 应返回 WAL
```

---

### Task: 实现 sqlite-vec 向量扩展初始化

**File(s)**
- `D:\CLAUDE.MD\mem\tools\db_init.py`

**What to do**
用 Python 实现：
1. `pip install sqlite-vec` 初始化
2. 创建向量表：`CREATE TABLE memory_embeddings (...)`
3. 注册 vec0 扩展（SQLite 扩展）
4. 验证向量存储功能正常

**Verification**
```python
import sqlite_vec
# 向量存储和相似度查询正常返回
```

---

## 阶段二：记忆组织（Layer 3）— 文件格式与结构

---

### Task: 定义记忆文件 frontmatter 格式

**File(s)**
- `D:\CLAUDE.MD\mem\schema\memory_frontmatter.md`

**What to do**
标准记忆文件格式：
```markdown
---
name: memory-name
description: 一句话描述（用于索引）
type: identity | artifact | topic | memory
tags: [标签1, 标签2]
trust_level: 1 | 2 | 3
version: v1 | v2 | v3
created_at: 2026-05-08
updated_at: 2026-05-08
topic_ref: ai-memory  # 关联话题
---

# 记忆正文内容
```

**Verification**
创建一条示例记忆，验证格式正确

---

### Task: 实现记忆文件读写工具

**File(s)**
- `D:\CLAUDE.MD\mem\tools\memory_file.py`

**What to do**
Python 函数：
- `read_memory(path)` — 解析 frontmatter + 正文
- `write_memory(path, frontmatter, content)` — 写入记忆文件
- `list_memories_by_type(type)` — 按类型列出所有记忆
- `update_memory(path, updates)` — 更新记忆（保留版本链）

**Verification**
运行测试：写入 → 读取 → 对比内容一致

---

## 阶段三：Access 层（Layer 2）— 检索管道

---

### Task: 实现向量嵌入（bge-m3 本地模式）

**File(s)**
- `D:\CLAUDE.MD\mem\tools\embedder.py`

**What to do**
```python
from sentence_transformers import SentenceTransformer

class LocalEmbedder:
    def __init__(self, model_name="BAAI/bge-m3"):
        self.model = SentenceTransformer(model_name)  # 340MB
        self.dimension = 1024  # bge-m3 输出维度

    def encode(self, text: str) -> list[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return embeddings.tolist()
```

**Verification**
```python
emb = LocalEmbedder()
v = emb.encode("今天天气很好")
assert len(v) == 1024  # bge-m3 dimension
assert isinstance(v[0], float)
```

---

### Task: 实现 3 层检索管道

**File(s)**
- `D:\CLAUDE.MD\mem\tools\retriever.py`

**What to do**
```python
class MemoryRetriever:
    def __init__(self, db_path, embedder):
        self.db = sqlite3.connect(db_path)
        self.embedder = embedder

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Layer 1: 语义检索，返回 compact index (~50-100 tokens/result)"""
        query_vec = self.embedder.encode(query)
        # sqlite-vec 相似度查询
        results = self.db.execute("""
            SELECT m.id, m.type, m.description, m.trust_level,
                   vec_distance_L2(e.vector, ?) as distance
            FROM memories m
            JOIN memory_embeddings e ON m.id = e.memory_id
            ORDER BY distance
            LIMIT ?
        """, [query_vec, limit])
        return [dict(row) for row in results]

    def timeline(self, memory_ids: list[int]) -> list[dict]:
        """Layer 2: 补充这些记忆附近的上下文（时间维度）"""
        # 查找这些记忆前后各 N 条，按时间排序
        pass

    def get(self, memory_ids: list[int]) -> list[dict]:
        """Layer 3: 获取完整内容（仅对筛选后的 ID）"""
        pass

    def hybrid_search(self, query: str, limit: int = 5) -> list[dict]:
        """FTS5 关键词 + 向量混合评分"""
        pass
```

**Verification**
```python
r = MemoryRetriever(...)
ids = r.search("记忆框架设计")  # 返回 ID 列表
timeline = r.timeline(ids[:2])  # 返回上下文
full = r.get(ids[:2])          # 返回完整内容
```

---

## 阶段四：Evolution 层（Layer 4）— 自进化机制

---

### Task: 实现对话摘要提取

**File(s)**
- `D:\CLAUDE.MD\mem\tools\extractor.py`

**What to do**
```python
def extract_memories_from_conversation(conversation_jsonl: str) -> list[dict]:
    """
    输入：对话 JSONL 文件路径
    输出：提取的记忆列表
    [
        {
            "content": "用户目标是做AI自媒体一人公司创业",
            "type": "identity",
            "tags": ["目标", "创业"],
            "confidence": 0.9
        },
        ...
    ]
    """
    # 读取 JSONL
    # 用 LLM（本地或 API）提取新增事实
    # 与已有记忆对比，去重
    # 返回待审核记忆列表
```

**Verification**
用真实对话 JSONL 测试，验证提取结果合理

---

### Task: 实现信任等级机制

**File(s)**
- `D:\CLAUDE.MD\mem\tools\trust.py`

**What to do**
```python
class TrustManager:
    def __init__(self, db):
        self.db = db

    def bump_trust(self, memory_id: int) -> int:
        """记忆被再次验证，信任等级 +1，最高 3"""
        row = self.db.execute(
            "SELECT trust_level FROM memories WHERE id = ?", [memory_id]
        ).fetchone()
        new_level = min((row[0] or 1) + 1, 3)
        self.db.execute(
            "UPDATE memories SET trust_level = ? WHERE id = ?",
            [new_level, memory_id]
        )
        return new_level

    def get_injection_strategy(self, memory_id: int) -> str:
        """L1: 原文注入  L2: 摘要注入  L3: 仅提示"""
        trust = self.db.execute(
            "SELECT trust_level FROM memories WHERE id = ?", [memory_id]
        ).fetchone()[0]
        return {1: "full", 2: "summary", 3: "hint"}[trust]
```

**Verification**
测试信任等级递增逻辑，边界情况（已达 L3 不再增）

---

## 阶段五：Curator 层（Layer 5）— 主动管理

---

### Task: 实现矛盾检测

**File(s)**
- `D:\CLAUDE.MD\mem\tools\curator.py`

**What to do**
```python
def detect_conflicts(memory_id: int, db) -> list[dict]:
    """
    检查新记忆是否与已有记忆矛盾
    简单策略：字符串 overlap + 否定词检测
    '应该用A' vs '不应该用A' → 矛盾
    返回：[{"conflict_with": id, "reason": "...", "severity": "high|medium|low"}]
    """
    pass

def suggest_merge(topic_id: int) -> list[dict]:
    """检测某话题下是否有过多未合并记忆 → 建议合并"""
    pass

def generate_health_report(db) -> str:
    """生成季度健康报告（中文）"""
    pass
```

**Verification**
输入两条明显矛盾的记忆，检测出矛盾；输入相似记忆，检测出可合并

---

## 阶段六：生命周期钩子

---

### Task: 实现 SessionStart 钩子

**File(s)**
- `D:\CLAUDE.MD\mem\hooks\session_start.py`

**What to do**
```python
def session_start_hook():
    """
    1. 读取 identity 记忆 → 注入上下文
    2. 检索最近一次对话的 topic + artifact
    3. 检查 pending 记忆是否有未审核项 → 提醒用户
    4. 输出：给用户看的"上次回顾"摘要
    """
```

**Verification**
启动新对话时，系统自动输出"上次回顾"（如果有记忆）

---

### Task: 实现对话结束钩子

**File(s)**
- `D:\CLAUDE.MD\mem\hooks\session_end.py`

**What to do**
```python
def session_end_hook(conversation_jsonl_path: str):
    """
    1. 提取本次对话中的新记忆 → 写入 pending_memories
    2. 保存原始对话 JSONL 到 conversations/
    3. 检查 curator 条件（积累量）→ 决定是否提醒反思
    4. 更新最后对话时间索引
    """
```

**Verification**
对话结束后，检查 pending_memories 表有新记录

---

## 阶段七：CLI 工具

---

### Task: 实现 mem init 初始化命令

**File(s)**
- `D:\CLAUDE.MD\mem\cli.py`

**What to do**
```bash
python -m mem init  # 初始化记忆系统
```
- 创建目录结构
- 初始化 SQLite 数据库（含 FTS5 + sqlite-vec）
- 下载 bge-m3 模型（340MB）
- 创建 MEMORY.md 索引文件
- 验证一切正常

**Verification**
运行 `python -m mem init` 后，`D:\CLAUDE.MD\mem` 目录完整，数据库可查询

---

### Task: 实现核心 CLI 命令

**File(s)**
- `D:\CLAUDE.MD\mem\cli.py`

**What to do**
```bash
python -m mem search "记忆框架"           # 检索记忆
python -m mem add --type memory "内容"     # 手动添加记忆
python -m mem status                        # 查看记忆统计
python -m mem pending                        # 查看待审核记忆
python -m mem evolve                        # 触发反思（用户批准后）
python -m mem doctor                         # 诊断问题
python -m mem health                        # 记忆健康报告
```

**Verification**
每个命令返回预期输出，无报错

---

## 验收总览

| 阶段 | 任务数 | 验收标准 |
|------|--------|---------|
| Layer 1 存储层 | 2 | 数据库建好，WAL 模式，sqlite-vec 可用 |
| Layer 3 组织层 | 2 | 记忆文件格式正确，读写正常 |
| Layer 2 Access | 2 | 向量检索返回结果，混合搜索正常 |
| Layer 4 Evolution | 2 | 提取记忆，信任等级递增 |
| Layer 5 Curator | 1 | 矛盾检测有输出 |
| 钩子 | 2 | 启动有回顾，结束有沉淀 |
| CLI | 2 | init 成功，search/add/status 正常 |
