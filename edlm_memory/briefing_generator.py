#!/usr/bin/env python3
"""
Session Briefing 生成器
在 Claude Code 会话结束时自动调用
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from edlm_memory import save_briefing, save_experience

def generate_briefing():
    """从会话历史生成 briefing"""
    session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    return {
        "session_id": session_id,
        "what_done": [],
        "open_tasks": [],
        "key_decisions": [],
        "derived_patterns": []
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 从 Claude Code 接收数据
        data = json.loads(sys.argv[1])
        save_briefing(
            session_id=data.get("session_id", datetime.now().strftime("%Y%m%d-%H%M%S")),
            what_done=data.get("what_done", []),
            open_tasks=data.get("open_tasks", []),
            key_decisions=data.get("key_decisions", []),
            derived_patterns=data.get("derived_patterns", [])
        )
    else:
        # 测试模式
        print(generate_briefing())