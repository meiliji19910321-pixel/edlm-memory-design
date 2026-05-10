#!/usr/bin/env python3
"""
SessionEnd hook for 融合记忆系统.
对话结束时运行，保存对话、提取记忆、更新待审核区。
"""
import sys
import os
import json

sys.path.insert(0, r"D:\CLAUDE.MD")
sys.path.insert(0, r"D:\CLAUDE.MD\mem")

from tools.extractor import (
    generate_conv_id,
    save_conversation,
    extract_memories_from_conversation,
    write_pending_memories,
)
from tools.curator import update_curator_state


def main():
    try:
        raw_input = sys.stdin.read()
        if raw_input.strip():
            data = json.loads(raw_input)
        else:
            data = {}
    except json.JSONDecodeError:
        data = {}

    # 获取 transcript（对话内容）
    transcript = data.get("transcript", [])

    if not transcript:
        sys.exit(0)

    # 生成摘要（取最后一条 assistant 消息的前100字）
    summary = ""
    for msg in reversed(transcript):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
            summary = content[:100].strip()
            break

    try:
        # 1. 保存对话
        conv_id = generate_conv_id()
        save_conversation(conv_id, transcript, summary)

        # 2. 提取新记忆
        extracted = extract_memories_from_conversation(conv_id, transcript)
        count = write_pending_memories(conv_id, extracted)

        # 3. 更新 curator 状态
        state = update_curator_state()
        pending = state.get("pending", 0)

        # 4. 如果积累够多，提醒
        if count > 0 or pending >= 20:
            reminder = f"[记忆系统] 本次提取 {count} 条记忆，当前 {pending} 条待审核。"
            if pending >= 20:
                reminder += " 建议运行 `python -m mem evolve` 触发主动反思。"
            print(reminder, file=sys.stderr)
            sys.exit(2)  # exit(2) 表示有输出，但不阻止结束

    except Exception as e:
        print(f"[记忆系统错误: {e}]", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
