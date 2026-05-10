"""
Layer 6: 生命周期钩子 — SessionEnd
每次对话结束时调用
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.extractor import (
    generate_conv_id,
    save_conversation,
    extract_memories_from_conversation,
    write_pending_memories,
    get_pending_memories,
)
from tools.curator import update_curator_state
from tools.db_init import DB_PATH
import sqlite3


def session_end_hook(messages: list[dict], summary: str = "") -> dict:
    """
    对话结束时的处理：
    1. 保存原始对话 JSONL
    2. 提取新记忆 → 写入待审核区
    3. 更新 curator 状态
    4. 检查是否需要提醒用户触发反思

    messages: [{"role": "user"|"assistant", "content": "..."}]
    返回处理结果
    """
    result = {
        "conv_id": None,
        "saved": False,
        "extracted_count": 0,
        "pending_total": 0,
        "should_remind_reflection": False,
        "error": None,
    }

    try:
        # 1. 生成 ID 并保存对话
        conv_id = generate_conv_id()
        raw_path = save_conversation(conv_id, messages, summary)
        result["conv_id"] = conv_id
        result["saved"] = True

        # 2. 提取记忆
        extracted = extract_memories_from_conversation(conv_id, messages)
        count = write_pending_memories(conv_id, extracted)
        result["extracted_count"] = count

        # 3. 更新 curator 状态
        curator_state = update_curator_state()
        result["pending_total"] = curator_state.get("pending", 0)

        # 4. 判断是否应该提醒反思（积累 20 条或每周）
        should_remind = _should_remind_reflection(curator_state)
        result["should_remind_reflection"] = should_remind

    except Exception as e:
        result["error"] = str(e)

    return result


def _should_remind_reflection(curator_state: dict) -> bool:
    """
    判断是否应该提醒用户触发主动反思。
    规则：
    - pending 数量 >= 20
    """
    pending = curator_state.get("pending", 0)
    return pending >= 20


def get_reflection_reminder(pending_count: int) -> str:
    """生成反思提醒文本"""
    if pending_count >= 20:
        return (
            f"\n\n【记忆系统】你积累了 {pending_count} 条待审核记忆。"
            f"建议运行 `python -m mem evolve` 触发主动反思，"
            f"合并重复记忆、处理矛盾。\n"
        )
    return ""


if __name__ == "__main__":
    # 测试：读取当前数据库状态
    result = session_end_hook([], summary="测试对话")
    print("=== SessionEnd Hook ===")
    print(f"conv_id: {result['conv_id']}")
    print(f"saved: {result['saved']}")
    print(f"extracted: {result['extracted_count']} 条")
    print(f"pending total: {result['pending_total']}")
    print(f"should remind: {result['should_remind_reflection']}")
    if result.get("error"):
        print(f"error: {result['error']}")
