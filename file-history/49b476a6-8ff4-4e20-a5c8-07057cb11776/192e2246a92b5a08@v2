# 记忆框架

Claude Code 的持久记忆系统，包含 4 种类型。

> **2026-05-08 更新**：已升级为融合记忆框架系统（5层架构，SQLite+FTS5+向量检索）
> 新系统位置：`D:\CLAUDE.MD\mem\`
> 旧 md 文件系统作为备份保留，新记忆已迁移至新系统。

## 类型说明

| 类型 | 用途 | 保存时机 |
|------|------|----------|
| user | 用户角色、目标、职责、知识 | 了解用户角色、偏好时 |
| feedback | 用户的指导反馈（规则、偏好） | 用户纠正或确认时 |
| project | 项目中的非代码信息（目标、截止、决策） | 了解项目背景时 |
| reference | 外部系统信息指针 | 了解外部资源时 |

## 写入步骤

1. 每个记忆一个文件，使用 frontmatter 格式
2. 在 MEMORY.md 中添加一行索引（标题 + 一行描述 + 链接）

## 存储位置

- 记忆文件：`D:\CLAUDE.MD\projects\D--Apps-ClaudeCode\memory\`
- 索引文件：`D:\CLAUDE.MD\projects\D--Apps-ClaudeCode\memory\MEMORY.md`

## 新融合记忆系统（推荐）

新系统 CLI：`$env:PYTHONPATH = "D:\CLAUDE.MD"; python -m mem <command>`

| 命令 | 说明 |
|------|------|
| `mem status` | 查看统计 |
| `mem search "查询"` | 向量+语义检索 |
| `mem add --name X --body Y --type identity` | 添加记忆 |
| `mem pending` | 查看待审核 |
| `mem evolve` | 触发主动反思 |
| `mem doctor` | 诊断问题 |
| `mem health` | 健康报告 |

具体实现见：`D:\CLAUDE.MD\mem\`