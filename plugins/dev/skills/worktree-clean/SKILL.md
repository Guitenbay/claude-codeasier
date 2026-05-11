---
description: 检查并清理安全可删除的 git worktree
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash
---

检查当前项目的 git worktree 与 `.worktrees` 目录，按以下规则处理：

0. **先同步远端信息**：
   - 在开始分析前执行 `git fetch origin`，确保与 `origin/main` 的比较基于最新远端状态

1. **遍历所有 worktree**，对每个 worktree 执行检查：
   - 是否存在未提交的变更（包括 staged 和 unstaged）
   - 是否存在相对 `origin/main` **尚未合入的实际变更**
   - 是否存在未跟踪的文件（untracked files）

2. **推荐检查方法**：
   - 用 `git status --short` 检查未提交变更与未跟踪文件
   - 不要仅用 `git rev-list origin/main..HEAD` 或 ahead commit 数量判断风险，因为 squash merge 后可能误报
   - 优先用 `git diff --quiet origin/main...HEAD` 判断当前分支相对 merge-base 是否仍有内容差异
   - 若需要进一步确认 patch 是否已通过 squash merge 等方式合入，用 `git cherry origin/main HEAD` 辅助判断
   - 只有在确认不存在未提交变更、未跟踪文件，且不存在相对 `origin/main` 尚未合入的实际变更时，才可视为干净

3. **风险判定**：
   - 若 worktree **完全干净**（无未提交变更、无相对 `origin/main` 尚未合入的实际变更、无未跟踪文件），直接删除
   - 若 worktree **存在任何上述风险**，**暂停并向我汇报**，等待我确认后再决定是否删除

4. **汇报格式**：
   - 干净 worktree：列出路径，标记「已删除」
   - 风险 worktree：列出路径，并说明具体风险（如“有 3 个未提交文件”、“仍有未合入变更”）

执行时注意：
- 优先使用安全、可核实的 git 状态检查。
- 不要仅根据 commit SHA 是否领先来判定风险；若分支可能已通过 squash merge 合入，应基于 patch / diff 判断是否仍有未合入的实际变更。
- 不要删除存在风险的 worktree，必须先等我确认。
