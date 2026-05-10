import sqlite3
import sqlite_vec

# 使用 sqlite_vec 提供的 load() 函数
conn = sqlite3.connect(":memory:")
sqlite_vec.load(conn)

version = conn.execute("SELECT vec_version()").fetchone()
print(f"sqlite-vec version: {version}")

# 创建向量表并测试
conn.execute("""
    CREATE VIRTUAL TABLE memory_vectors USING vec0(
        memory_id INTEGER,
        vector FLOAT[1024]
    )
""")

# 序列化测试向量
import struct
import array
vec = array.array('f', [0.1] * 1024)
vec_bytes = vec.tobytes()

conn.execute("INSERT INTO memory_vectors(memory_id, vector) VALUES (?, ?)", [1, vec_bytes])
result = conn.execute("SELECT memory_id FROM memory_vectors").fetchall()
print(f"Vector insert/query test: {result}")
conn.close()
print("[OK] sqlite-vec fully working")
