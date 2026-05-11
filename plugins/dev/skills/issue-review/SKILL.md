---
description: 分析 issue 建议是否合理并把结论追加到 issue 评论
argument-hint: <issue_num>
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash, WebFetch
---

如果没有提供 issue 编号，就只输出：`用法: /dev:issue-review <issue_num>`，不要执行其他操作。

如果提供了 issue 编号，请分析 issue #$1 提出的问题改进建议是否确实存在、是否合理，并将分析结果添加到该 issue 评论。

要求：
- 先获取完整上下文，再判断建议是否成立。
- 以代码、现有行为、文档或 API 契约为依据给出结论。
- 评论中要明确区分：
  - 问题是否真实存在
  - 建议是否合理
  - 如果不完全合理，正确边界是什么
- **仅分析并评论，不要修改本地源码。**
- 如果需要仓库/issue 上下文，优先读取当前仓库信息与 issue 内容后再下结论。
