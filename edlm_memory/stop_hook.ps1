# EDLM Stop Hook - 会话结束时自动生成 briefing
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "python"
& $python "$scriptDir\briefing_generator.py" 2>&1
