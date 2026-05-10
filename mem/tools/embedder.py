"""
Layer 2: 本地嵌入模型
使用 sentence-transformers + bge-m3
完全本地运行，无 API 依赖
"""
import os
import struct
import numpy as np
from typing import Optional

# 模型缓存目录（放在 D 盘）
MODEL_CACHE_DIR = r"D:\CLAUDE.MD\mem\.models"

# 默认使用轻量模型（90MB），可切换到 bge-m3（550MB，更高精度）
# 切换方式：设置环境变量 MEM_EMBEDDER_MODEL = "BAAI/bge-m3"
MODEL_NAME = os.environ.get("MEM_EMBEDDER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# 各模型的输出维度
MODEL_DIMENSIONS = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "BAAI/bge-m3": 1024,
}


class LocalEmbedder:
    """本地向量嵌入生成器"""

    _instance: Optional["LocalEmbedder"] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is not None:
            return
        os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
        print(f"[INFO] 加载嵌入模型（{MODEL_NAME}）...")
        print(f"[INFO] 模型缓存目录: {MODEL_CACHE_DIR}")

        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(
            MODEL_NAME,
            cache_folder=MODEL_CACHE_DIR,
            device="cpu"  # 强制 CPU，不依赖 CUDA
        )
        self._dimension = self._model.get_embedding_dimension()
        print(f"[OK] 模型加载完成，输出维度: {self._dimension}")

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, text: str) -> list[float]:
        """将单条文本转为归一化向量（list[float]）"""
        embedding = self._model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=False
        )
        # sentence-transformers 返回 numpy.ndarray，转为 Python list
        return embedding.tolist()

    def encode_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """批量编码"""
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=False,
            show_progress_bar=False
        )
        return [e.tolist() for e in embeddings]

    def encode_and_serialize(self, text: str) -> bytes:
        """编码并序列化为 SQLite BLOB（4字节 float32 × 1024）"""
        vec = self.encode(text)
        return struct.pack(f"{len(vec)}f", *vec)

    @staticmethod
    def deserialize(blob: bytes) -> np.ndarray:
        """从 SQLite BLOB 反序列化为 numpy 数组"""
        count = len(blob) // 4
        return np.frombuffer(blob, dtype=np.float32, count=count)

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """计算两个向量的余弦相似度（假设已归一化）"""
        return float(np.dot(a, b))


def get_embedder() -> LocalEmbedder:
    """获取单例嵌入器"""
    return LocalEmbedder()


if __name__ == "__main__":
    # 测试
    emb = get_embedder()
    print(f"向量维度: {emb.dimension}")

    v1 = emb.encode("今天天气很好")
    v2 = emb.encode("今天阳光明媚")
    v3 = emb.encode("Python编程语言很有意思")

    print(f"v1 前5维: {v1[:5]}")
    print(f"v1 全长: {len(v1)}")

    # 测试相似度
    sim_same = LocalEmbedder.cosine_similarity(
        np.array(v1), np.array(v2)
    )
    sim_diff = LocalEmbedder.cosine_similarity(
        np.array(v1), np.array(v3)
    )
    print(f"'今天天气' vs '阳光明媚' 相似度: {sim_same:.4f}")
    print(f"'今天天气' vs 'Python编程' 相似度: {sim_diff:.4f}")

    # 测试序列化
    blob = emb.encode_and_serialize("测试文本")
    restored = LocalEmbedder.deserialize(blob)
    print(f"序列化后 BLOB 大小: {len(blob)} bytes")
    print(f"反序列化后与原文一致: {np.allclose(restored, np.array(v1))}")
