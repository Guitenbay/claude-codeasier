---
description: 在独立 worktree 中修复指定 issue
argument-hint: <issue-num>
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash, Edit, Write
---

如果 `$ARGUMENTS` 为空，就只输出：`用法: /dev:issue-resolve <issue-num>`，不要执行其他操作。

如果提供了 issue 编号，请按空白解析 `$ARGUMENTS`：第一个词为 issue 编号。如果存在额外参数，停止并输出：`用法: /dev:issue-resolve <issue-num>`。然后修复该 issue。

要求：
- **必须使用独立的 git worktree**，并放在仓库 `.worktrees` 目录下。
- 先理解 issue 目标和当前实现，再做最小必要修改。
- 改完后运行相关验证，并汇报改动与结果。
