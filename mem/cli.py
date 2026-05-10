"""
记忆系统 CLI 入口
用法：
    python -m mem init          # 初始化
    python -m mem status        # 查看状态
    python -m mem search "查询"  # 检索记忆
    python -m mem add "内容"     # 手动添加记忆
    python -m mem pending       # 查看待审核
    python -m mem evolve        # 触发反思
    python -m mem doctor        # 诊断问题
    python -m mem health        # 健康报告
"""
import sys
import os
import json

# 确保 tools 可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_init():
    """初始化记忆系统"""
    print("[INFO] 初始化记忆系统...")
    from tools.db_init import init_db, verify_db
    init_db()
    verify_db()
    print("[OK] 初始化完成！")
    print("")
    print("下一步：")
    print("  python -m mem add --type identity --name '我的身份' --body '我是...'  # 添加你的第一条记忆")
    print("  python -m mem status  # 查看状态")


def cmd_status():
    """查看记忆统计"""
    from tools.db_init import DB_PATH
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM pending_memories WHERE status = 'pending'"
    ).fetchone()[0]
    by_type = {}
    for row in conn.execute(
        "SELECT type, COUNT(*) as cnt FROM memories GROUP BY type"
    ).fetchall():
        by_type[row["type"]] = row["cnt"]
    trust_dist = {}
    for row in conn.execute(
        "SELECT trust_level, COUNT(*) as cnt FROM memories GROUP BY trust_level"
    ).fetchall():
        trust_dist[str(row["trust_level"])] = row["cnt"]

    last_conv = conn.execute(
        "SELECT date, summary FROM conversations ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    conn.close()

    print(f"永久记忆总数：{total}")
    print(f"待审核记忆：{pending}")
    print(f"类型分布：{by_type}")
    print(f"信任等级：L1={trust_dist.get('1',0)}, L2={trust_dist.get('2',0)}, L3={trust_dist.get('3',0)}")
    print(f"")
    print(f"最近对话：{last_conv['date'] if last_conv else '无'}")
    if last_conv and last_conv["summary"]:
        print(f"摘要：{last_conv['summary'][:100]}")


def cmd_search(query: str, limit: int = 5):
    """检索记忆"""
    from tools.retriever import MemoryRetriever

    r = MemoryRetriever()
    result = r.retrieve(query, limit=limit)
    r.close()

    print(f"=== 检索结果（query: {query}）===")
    print(f"找到 {len(result['index'])} 条相关记忆")
    print("")

    for item in result["index"]:
        print(f"  [{item['type']}] #{item['id']} {item['name']}")
        print(f"    描述：{item['description'][:80]}")
        print(f"    信任：L{item['trust_level']} | 混合评分：{item.get('hybrid_score', 0):.3f}")
        print("")


def cmd_add(
    name: str,
    body: str,
    mem_type: str = "memory",
    description: str = "",
    tags: list[str] = None
):
    """手动添加记忆"""
    from tools.memory_file import create_memory_file

    if mem_type not in ("identity", "artifact", "topic", "memory"):
        print(f"[ERROR] 未知的类型: {mem_type}")
        print(f"可用类型：identity, artifact, topic, memory")
        return

    path, mid = create_memory_file(
        name=name,
        body=body,
        mem_type=mem_type,
        description=description or body[:100],
        tags=tags or [],
    )
    print(f"[OK] 记忆已创建: {path}")
    print(f"     memory_id: {mid}")


def cmd_pending():
    """查看待审核记忆"""
    from tools.extractor import get_pending_memories

    pending = get_pending_memories("pending")
    print(f"待审核记忆：{len(pending)} 条")
    print("")

    for p in pending:
        print(f"  [{p['suggested_type']}] {p['extracted_content'][:80]}")
        print(f"    置信度：{p['confidence']:.2f} | 日期：{p['created_at'][:10]}")
        print(f"    [批准: python -m mem approve {p['id']}]")
        print(f"    [拒绝: python -m mem reject {p['id']}]")
        print("")


def cmd_approve(pending_id: int):
    """批准待审核记忆"""
    from tools.extractor import approve_memory
    mid = approve_memory(pending_id)
    if mid:
        print(f"[OK] 记忆已批准并写入永久区 (id={mid})")
    else:
        print(f"[ERROR] 未找到待审核记忆 id={pending_id}")


def cmd_reject(pending_id: int):
    """拒绝待审核记忆"""
    from tools.extractor import reject_memory
    reject_memory(pending_id)
    print(f"[OK] 记忆已标记为拒绝")


def cmd_evolve():
    """触发主动反思"""
    from tools.curator import generate_health_report, update_curator_state

    print("[INFO] 运行主动反思...")
    print("")

    # 更新状态
    state = update_curator_state()
    print(f"当前状态：{state['pending']} 条待审核，{state['approved']} 条永久记忆")
    print("")

    # 生成健康报告
    report = generate_health_report()
    print(report)
    print("")
    print("[INFO] 如需批准/拒绝待审核记忆，使用:")
    print("  python -m mem pending   # 查看列表")
    print("  python -m mem approve <id>  # 批准")
    print("  python -m mem reject <id>   # 拒绝")


def cmd_doctor():
    """诊断问题"""
    print("[INFO] 运行诊断...")
    print("")

    # 检查数据库
    from tools.db_init import DB_PATH, verify_db
    import sqlite3

    issues = []

    if not os.path.exists(DB_PATH):
        issues.append("数据库文件不存在，需要运行 `python -m mem init`")
    else:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check")
            ok = cur.fetchone()[0]
            if ok != "ok":
                issues.append(f"数据库完整性问题: {ok}")
            cur.execute("PRAGMA journal_mode")
            mode = cur.fetchone()[0]
            if mode != "wal":
                issues.append(f"journal_mode 应为 WAL，当前: {mode}")
            conn.close()
        except Exception as e:
            issues.append(f"数据库连接错误: {e}")

    # 检查向量模型
    try:
        from tools.embedder import get_embedder
        emb = get_embedder()
        dim = emb.dimension
        print(f"  [OK] 嵌入模型正常，维度: {dim}")
    except Exception as e:
        issues.append(f"嵌入模型加载失败: {e}")

    # 检查目录
    for subdir in ["memories/identity", "memories/artifact", "memories/topic", "memories/memory", "conversations", ".db"]:
        path = os.path.join(os.path.dirname(DB_PATH), "..", subdir)
        if not os.path.exists(path):
            issues.append(f"目录不存在: {subdir}")

    if issues:
        print("[ISSUE] 发现以下问题：")
        for iss in issues:
            print(f"  - {iss}")
    else:
        print("[OK] 所有检查通过，记忆系统运行正常！")


def cmd_health():
    """生成健康报告"""
    from tools.curator import generate_health_report
    print(generate_health_report())


def main():
    args = sys.argv[1:]  # 跳过 Python 自身路径

    if not args or args[0] == "help":
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "init":
        cmd_init()
    elif cmd == "status":
        cmd_status()
    elif cmd == "search":
        query = " ".join(args[1:]) if len(args) > 1 else ""
        if not query:
            print("[ERROR] 请提供查询内容：python -m mem search \"查询内容\"")
        else:
            cmd_search(query)
    elif cmd == "add":
        # python -m mem add --name xxx --body xxx --type xxx
        kwargs = {}
        remaining = args[1:]
        i = 0
        while i < len(remaining):
            if remaining[i].startswith("--"):
                key = remaining[i][2:]
                val = remaining[i+1] if i+1 < len(remaining) and not remaining[i+1].startswith("--") else ""
                kwargs[key] = val
                i += 2
            else:
                i += 1
        if "body" not in kwargs and "name" in kwargs:
            print("[ERROR] 请提供 --body 参数")
        else:
            name = kwargs.get("name", "未命名记忆")
            cmd_add(name, kwargs.get("body", ""),
                   mem_type=kwargs.get("type", "memory"),
                   description=kwargs.get("description", ""),
                   tags=kwargs.get("tags", "").split(",") if kwargs.get("tags") else None)
    elif cmd == "pending":
        cmd_pending()
    elif cmd == "approve":
        try:
            cmd_approve(int(args[1]))
        except (IndexError, ValueError):
            print("[ERROR] 请提供待审核记忆 ID：python -m mem approve <id>")
    elif cmd == "reject":
        try:
            cmd_reject(int(args[1]))
        except (IndexError, ValueError):
            print("[ERROR] 请提供待审核记忆 ID：python -m mem reject <id>")
    elif cmd == "evolve":
        cmd_evolve()
    elif cmd == "doctor":
        cmd_doctor()
    elif cmd == "health":
        cmd_health()
    else:
        print(f"[ERROR] 未知命令: {cmd}")
        print("运行 `python -m mem help` 查看帮助")


if __name__ == "__main__":
    main()
