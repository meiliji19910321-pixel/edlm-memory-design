#!/usr/bin/env python3
"""
Briefing 生成器 - 从会话数据自动生成 Session Briefing
供 Stop 钩子调用
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from edlm_memory import save_briefing, load_all_experiences


def generate_briefing_from_session(session_data):
    """从会话数据生成 briefing"""
    session_id = session_data.get("session_id", datetime.now().strftime("%Y%m%d-%H%M"))
    return save_briefing(
        session_id=session_id,
        what_done=session_data.get("what_done", []),
        open_tasks=session_data.get("open_tasks", []),
        key_decisions=session_data.get("key_decisions", []),
        derived_patterns=session_data.get("derived_patterns", [])
    )


def auto_generate_briefing(session_id=None):
    """自动生成 briefing（从最近的 experience 推断）"""
    session_id = session_id or datetime.now().strftime("%Y%m%d-%H%M")
    today = datetime.now().strftime("%Y-%m-%d")

    experiences = load_all_experiences()
    today_exps = [exp for exp in experiences if exp[0].get("date") == today]

    what_done = []
    key_decisions = []
    derived_patterns = []

    for meta, body, _ in today_exps:
        goal = meta.get("goal", "")
        outcome = meta.get("outcome", "")
        if outcome == "SUCCESS":
            what_done.append(f"完成: {goal}")
        else:
            what_done.append(f"尝试: {goal} ({outcome})")
        if meta.get("type") == "decision":
            key_decisions.append(goal)
        if meta.get("derived_pattern"):
            derived_patterns.append(meta["derived_pattern"])

    if not what_done:
        what_done = ["暂无记录的经验"]

    return save_briefing(session_id, what_done, [], key_decisions, derived_patterns)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            data = json.loads(sys.argv[1])
            result = generate_briefing_from_session(data)
        except json.JSONDecodeError:
            result = auto_generate_briefing(sys.argv[1])
    else:
        result = auto_generate_briefing()
    print(f"Briefing 已生成: {result}")
