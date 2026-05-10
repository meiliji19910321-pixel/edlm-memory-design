#!/usr/bin/env python3
"""
将今天的记忆系统设计会话写入永久记忆区
"""
import sys
import os
sys.path.insert(0, r"D:\CLAUDE.MD")
sys.path.insert(0, r"D:\CLAUDE.MD\mem")

from tools.memory_file import create_memory_file, list_memories_by_type
from tools.db_init import DB_PATH
import sqlite3

MEMORIES = [
    {
        "name": "融合记忆系统设计过程",
        "body": """三框架深度分析：claude-mem（生命周期钩子+渐进式注入）、MemPalace（结构化palace+96.6%召回率）、palaia（多智能体+MCP+sqlite-vec）。

设计决策：
- 5层架构：Storage→Access→Organization→Evolution→Curator
- 存储：SQLite+FTS5+BLOB向量，无外部API依赖
- 向量：all-MiniLM-L6-v2（384维，90MB），可切换bge-m3
- 信任等级：L1新建→L2验证→L3稳定，被动进化
- Curator层：规则驱动（矛盾检测/合并提醒/健康报告）
- 对话原文60天后清除，只保留摘要
- Python sqlite3不支持sqlite-vec扩展加载，向量计算用Python实现

实现时间：2026-05-08""",
        "type": "artifact",
        "description": "今天设计的第二记忆层系统的完整记录",
        "tags": ["记忆系统", "AI工具", "架构", "今日创作"],
    },
    {
        "name": "融合记忆系统的局限性",
        "body": """1. 记忆回音壁风险：系统强化已有观点，可能过滤掉有价值的旧观点。解法：Curator层强制保留"未解决争议"。

2. 信任等级进化慢：每次需用户批准。解法：3次验证自动升级。

3. sqlite-vec扩展无法加载：Python sqlite3编译时禁用了扩展加载。解法：向量用Python计算，对10k记忆足够快。

4. bge-m3模型过大（550MB）：首次下载卡住。解法：先用all-MiniLM-L6-v2（90MB）替代。

5. "超级大脑"是营销语言：真实定位是"第二记忆层"，不能替你做判断。""",
        "type": "memory",
        "description": "融合记忆系统的已知局限和应对策略",
        "tags": ["记忆系统", "局限性", "风险"],
    },
    {
        "name": "记忆系统未来升级方向",
        "body": """1. 切换到bge-m3嵌入模型（更高精度），需解决首次下载卡住问题

2. Claude Code插件级集成：当前hooks机制可用，但需验证SessionStart/End是否真的触发

3. 升级向量引擎：研究sqlite-vec扩展替代方案（如FAISS、pgvector）

4. 增加MCP协议支持：让其他MCP Client（Claude Desktop、Cursor）也能用记忆系统

5. 可视化记忆浏览器：WebUI查看记忆图谱

6. 多语言支持：当前CLI和记忆都是中文，接口可扩展""",
        "type": "memory",
        "description": "记忆系统后续迭代计划",
        "tags": ["记忆系统", "升级", "未来计划"],
    },
]


def main():
    print("=== 写入今日会话记忆 ===\n")

    # 检查是否已有重复
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    existing = conn.execute(
        "SELECT name FROM memories WHERE type IN ('artifact','memory')"
    ).fetchall()
    existing_names = {r["name"] for r in existing}
    conn.close()

    for mem in MEMORIES:
        if mem["name"] in existing_names:
            print(f"[SKIP] 已存在: {mem['name']}")
            continue

        try:
            path, mid = create_memory_file(
                name=mem["name"],
                body=mem["body"],
                mem_type=mem["type"],
                description=mem["description"],
                tags=mem["tags"],
            )
            print(f"[OK] #{mid} {mem['name']}")
        except Exception as e:
            print(f"[ERROR] {mem['name']}: {e}")

    print("\n=== 当前记忆列表 ===")
    for t in ["identity", "artifact", "topic", "memory"]:
        rows = list_memories_by_type(t)
        print(f"  {t}: {len(rows)} 条")
        for r in rows:
            print(f"    - {r['name']} (L{r['trust_level']})")


if __name__ == "__main__":
    main()
