"""
Layer 2: 3 层检索管道
search → timeline → get
参考 claude-mem 的 3 层设计，但向量计算在 Python 侧
"""
import sqlite3
import json
import numpy as np
from datetime import datetime
from typing import Optional

from .embedder import get_embedder, LocalEmbedder

DB_PATH = r"D:\CLAUDE.MD\mem\.db\memory.db"


class MemoryRetriever:
    """
    3 层检索管道：
    1. search    — 语义 + FTS5 混合检索，返回 compact index（~50-100 tokens/result）
    2. timeline  — 补充这些记忆附近的上下文（时间维度）
    3. get       — 获取完整内容（仅对筛选后的 ID）
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.embedder = get_embedder()

    def close(self):
        self.db.close()

    # ---- Layer 1: 搜索 ----

    def search(
        self,
        query: str,
        limit: int = 5,
        type_filter: Optional[str] = None,
        tag_filter: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Layer 1: 语义 + FTS5 混合检索，返回 compact index。
        返回的每条结果只含元数据，不含正文（节省 token）。
        """
        query_vec = self.embedder.encode(query)

        # FTS5 关键词召回
        fts_results = self._fts_search(query, limit * 2)

        # 向量相似度召回
        vector_results = self._vector_search(query_vec, limit * 2)

        # 混合评分：FTS 命中 + 向量相似
        scored = self._hybrid_score(fts_results, vector_results, query_vec)

        # 类型过滤
        if type_filter:
            scored = [r for r in scored if r["type"] == type_filter]

        # 标签过滤
        if tag_filter:
            scored = [
                r for r in scored
                if any(tag in r["tags"] for tag in tag_filter)
            ]

        # 返回 top N，每条只含 compact index 信息
        return scored[:limit]

    def _fts_search(self, query: str, limit: int) -> list[dict]:
        """FTS5 全文搜索"""
        try:
            cur = self.db.execute("""
                SELECT m.id, m.name, m.description, m.type, m.trust_level,
                       m.tags, fts.rank
                FROM memories_fts fts
                JOIN memories m ON m.id = fts.rowid
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, [query, limit])
            return [dict(row) for row in cur.fetchall()]
        except Exception:
            return []

    def _vector_search(self, query_vec: list[float], limit: int) -> list[dict]:
        """向量相似度搜索（Python 侧计算）"""
        cur = self.db.execute("""
            SELECT memory_id, vector
            FROM memory_embeddings
        """)
        rows = cur.fetchall()

        if not rows:
            return []

        scored = []
        q = np.array(query_vec)
        for row in rows:
            mem_vec = LocalEmbedder.deserialize(row["vector"])
            sim = LocalEmbedder.cosine_similarity(q, mem_vec)
            # 查出对应的 memories 表信息
            mem_row = self.db.execute(
                "SELECT id, name, description, type, trust_level, tags FROM memories WHERE id = ?",
                [row["memory_id"]]
            ).fetchone()
            if mem_row:
                entry = dict(mem_row)
                entry["vector_sim"] = sim
                scored.append(entry)

        scored.sort(key=lambda x: x["vector_sim"], reverse=True)
        return scored[:limit]

    def _hybrid_score(
        self,
        fts_results: list[dict],
        vector_results: list[dict],
        query_vec: list[float]
    ) -> list[dict]:
        """混合评分：FTS 排名 + 向量相似度"""
        # 合并结果
        all_results = {}
        for r in fts_results:
            all_results[r["id"]] = {**r, "fts_rank": r.pop("rank", 0)}
        for r in vector_results:
            if r["id"] in all_results:
                all_results[r["id"]]["vector_sim"] = r["vector_sim"]
            else:
                all_results[r["id"]] = {**r, "fts_rank": 999}

        # 归一化评分
        max_fts = max((r["fts_rank"] for r in all_results.values() if r["fts_rank"] < 999), default=1)
        max_vec = max((r.get("vector_sim", 0) for r in all_results.values()), default=1)

        for r in all_results.values():
            fts_score = 1 - (r["fts_rank"] / max_fts) if r["fts_rank"] < 999 else 0
            vec_score = r.get("vector_sim", 0) / max_vec
            # 权重：向量 0.6，FTS 0.4
            r["hybrid_score"] = 0.6 * vec_score + 0.4 * fts_score

        return sorted(
            all_results.values(),
            key=lambda x: x["hybrid_score"],
            reverse=True
        )

    # ---- Layer 2: 时间线 ----

    def timeline(self, memory_ids: list[int], window: int = 2) -> list[dict]:
        """
        Layer 2: 返回这些记忆附近的其他记忆（时间维度增强）。
        对每个 ID，找到它前后各 window 条记忆，补充上下文。
        """
        if not memory_ids:
            return []

        # 获取所有记忆（按时间排序）
        all_memories = self.db.execute("""
            SELECT id, name, description, type, trust_level, tags, created_at
            FROM memories
            ORDER BY created_at DESC
        """).fetchall()

        if not all_memories:
            return []

        # 建立 ID → index 映射
        id_to_idx = {row["id"]: idx for idx, row in enumerate(all_memories)}

        timeline_results = []
        for mid in memory_ids:
            if mid not in id_to_idx:
                continue
            idx = id_to_idx[mid]
            start = max(0, idx - window)
            end = min(len(all_memories), idx + window + 1)
            for i in range(start, end):
                row = dict(all_memories[i])
                row["is_self"] = (row["id"] == mid)
                row["distance"] = abs(i - idx)
                timeline_results.append(row)

        # 去重，按时间排序
        seen = set()
        unique = []
        for r in timeline_results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)

        return sorted(unique, key=lambda x: x["created_at"], reverse=True)

    # ---- Layer 3: 完整内容 ----

    def get(self, memory_ids: list[int]) -> list[dict]:
        """
        Layer 3: 获取完整记忆内容（仅对筛选后的 ID）。
        这是最后一层，只取真正需要详细查看的记忆。
        """
        if not memory_ids:
            return []

        placeholders = ",".join("?" * len(memory_ids))
        cur = self.db.execute(f"""
            SELECT id, name, description, type, content, tags,
                   trust_level, version_chain, topic_ref,
                   created_at, updated_at
            FROM memories
            WHERE id IN ({placeholders})
        """, memory_ids)

        results = []
        for row in cur.fetchall():
            r = dict(row)
            r["tags"] = json.loads(r["tags"])
            r["version_chain"] = json.loads(r["version_chain"])
            results.append(r)

        # 按原始 ID 顺序返回
        id_order = {mid: i for i, mid in enumerate(memory_ids)}
        return sorted(results, key=lambda x: id_order.get(x["id"], 999))

    # ---- 便捷方法：完整检索流程 ----

    def retrieve(self, query: str, limit: int = 5) -> dict:
        """
        完整 3 层检索流程。
        返回 {
            "index": [...],      # Layer 1 结果
            "timeline": [...],   # Layer 2 结果
            "details": [...]     # Layer 3 结果（全部详情）
        }
        """
        # Layer 1: 搜索索引
        index = self.search(query, limit=limit)

        # 从 index 提取 ID
        ids = [r["id"] for r in index]

        # Layer 2: 时间线增强
        tl = self.timeline(ids, window=2)

        # Layer 3: 完整内容
        details = self.get(ids)

        return {
            "index": index,
            "timeline": tl,
            "details": details,
            "query": query,
            "retrieved_at": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # 测试（需要数据库有数据）
    r = MemoryRetriever()
    result = r.retrieve("测试查询")
    print(f"检索完成: {len(result['index'])} 条索引, {len(result['timeline'])} 条时间线")
    r.close()
