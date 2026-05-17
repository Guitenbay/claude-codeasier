---
description: 按本仓库 SOP 处理 PR review 后续动作
argument-hint: <pr-number> [focus]
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash, WebFetch
---

如果 `$ARGUMENTS` 为空，就只输出：`用法: /dev:pr-followup <pr-number> [focus]`，不要执行其他操作。

如果提供了 PR 编号，请按空白解析 `$ARGUMENTS`：第一个词为 PR 编号，其余内容为可选 focus。然后按以下流程处理该 PR 的 review 后续动作。

# PR Post-Review 处理流程

适用于本仓库的 post-review 通用工作流。

## 目标

在收到 review 意见后，快速判断：
- 评论是否合理
- 是否必须修复
- 应该修到什么范围
- 是否需要 rebase、补测、回复 review、push 更新

重点不是“把 reviewer 说的都做掉”，而是：
- 保持问题导向
- 保持改动范围稳定
- 用代码、测试、文档和 API 契约来验证判断
- **不要漏掉分支同步：在 commit / push / 回复 review 前，必须确认是否需要 rebase 到 `origin/main`，并处理好冲突后再继续**

## 一、SOP：按这个顺序执行

1. 看 PR metadata / review / line comments。
2. 确认对应 worktree、当前分支状态、相对 `origin/main` 的领先/落后状态。
3. 如果落后 main，先执行：
   - `git fetch origin main`
   - `git rebase origin/main`
4. 如果有冲突，先解决冲突，并重新检查代码 / 测试 / 文档一致性。
5. 对照关联 issue，判断当前 PR 的真实目标。
6. 查代码 + API 文档 / 官方文档 / `gh` 语义。
7. 把意见分成：必须修 / 应该修 / 不该在这个 PR 修。
8. 按“最小正确修复”收口代码范围。
9. 同步更新测试与必要文档。
10. 跑相关测试和 lint。
11. 如果 rebase 发生在修改之后，再次验证 rebase 后结果。
12. commit。
13. push：
   - 未 rebase：正常 push
   - 已 rebase：`git push --force-with-lease`
14. 用 `gh` 回复 review，说明保留和调整的边界。
15. 再检查 PR mergeability / checks。

执行时按以上流程推进，不要为了“对齐 gh”而无依据扩大修复范围。
