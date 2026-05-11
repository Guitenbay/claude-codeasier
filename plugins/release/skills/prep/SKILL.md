---
description: 准备 PyPI 发布前置动作：版本号、CHANGELOG、PR、tag 与发布检查
argument-hint: <version>
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash, Edit, Write
---

如果没有提供版本号，就只输出：`用法: /release:prep <version>`，不要执行其他操作。

如果提供了版本号 `$1`，请把它作为**本次待发布版本号**，执行完整的发布前置工作流。目标不是直接发布，而是把“可发布”状态准备好，并在关键节点向用户确认。

版本与发布约束：
- 版本号必须符合 PEP 440（例如：`0.1.3`、`0.1.3a0`、`0.1.3b1`、`0.1.3rc1`、`0.1.3.dev1`）
- 最终 tag 必须是 `v$1`
- 结合 `.github/workflows/publish.yml` 与 `.claude/pypi-release-process.md` 执行
- `main` 是受保护分支，**不能直接 push 到 main**
- 本命令的目标是准备 changelog + PR，合入后再决定是否打 tag

按以下阶段执行：

## 阶段 1：准备与校验

1. 校验用户提供的版本号是否符合 PEP 440；如果不符合，停止并明确指出不合法之处。
2. 读取并遵守：
   - `.claude/pypi-release-process.md`
   - `.github/workflows/publish.yml`
   - 当前 `CHANGELOG.md` 的既有风格
3. 确认本地仓库状态：
   - 获取 `origin/main` 最新状态
   - 获取 tags
   - 检查当前工作区是否存在与本次任务冲突的未提交改动
4. 若发现会影响本次流程的异常（例如当前仓库脏、远程不可达、版本条目已存在等），先汇报，再决定是否继续。

## 阶段 2：必须在独立 worktree 中准备 changelog

1. **必须使用独立 git worktree**，并放在仓库 `.worktrees` 目录下完成本次工作。
2. 基于 `origin/main` 创建用于本次版本准备的分支，分支名应清晰表达版本目的，例如与 `release-prep-$1` 同类。
3. 在该 worktree 中分析最近发布范围：
   - 找到最近一个正式发布基线（优先依据当前仓库发布/tag 语义）
   - 收集从该基线到 `origin/main` 最新提交之间、将被纳入本次版本的已合并 PR
   - 优先使用 PR 元数据；必要时再退化到 commit 信息，并说明精度限制
4. 更新 `CHANGELOG.md`：
   - **只追加/插入本次版本对应的新版本条目**，版本标题必须能被 workflow 正确识别，即使用 `## [$1]` 形式
   - 日期使用当天日期
   - 必须保持当前文件整体风格一致：中文总结 + 分类小节
   - 不要复制现有那个 `## [v0.1.2a0..origin/main]` 草稿式区段的命名方式
   - 不需要附 `Full PR list`
   - 应包含一段发布说明式总览，以及精简后的分类条目
   - 避免机械枚举所有 PR；保留最核心的用户可感知变化
5. 除 `CHANGELOG.md` 外，不要顺手修改其他业务文件；如果确实需要额外改动，必须先说明原因。

## 阶段 3：请用户确认 changelog

1. 完成 changelog 修改后，先不要直接提交或开 PR。
2. 向用户展示：
   - 使用了哪个基线 tag / 范围
   - 纳入了哪些核心变化类别
   - `CHANGELOG.md` 新增条目的内容摘要
3. 明确询问用户：**该 changelog 是否符合预期**。
4. 如果用户未确认、要求调整，继续修改直到确认。

## 阶段 4：在用户确认后提交 PR

只有在用户明确确认 changelog 符合预期后，才继续：

1. 提交本次改动（仅包含 `CHANGELOG.md`）
2. push 分支到远程
3. 创建 PR，标题和描述应清晰表达“为 `$1` 准备发布说明 / changelog”
4. 向用户返回：
   - worktree 路径
   - 分支名
   - PR 链接
5. 不要替用户合并 PR；等待用户自行合入。

## 阶段 5：确认 PR 已合入后，再进入 tag 阶段

只有在确认阶段 4 的 PR **已经合入 `main`** 后，才继续：

1. 再次确认 `origin/main` 已包含本次 changelog PR
2. 在创建 tag 前，基于当前 `origin/main` 复用 `.github/workflows/publish.yml` 的规则做一次**本地 release 校验**：
   - `CHANGELOG.md` 中存在 `## [$1]` 对应版本条目
   - 使用与 workflow 一致的匹配逻辑能够命中该条目，并提取出非空 release notes
   - 如校验失败，停止打 tag，先汇报失败原因并修复 workflow 或 changelog
3. 然后询问用户：
   - 是否需要你协助创建并 push tag `v$1`
   - 或者仅向用户提供命令，由用户自行执行
4. 如果只是提供命令，应给出适用于本仓库的最小命令序列，例如：
   - `git checkout main`
   - `git pull origin main`
   - `git tag v$1`
   - `git push origin v$1`
5. 如果用户明确授权你代为打 tag，再执行；否则不要擅自创建或 push tag。

## 阶段 6：可选的发布跟进

如果用户希望继续跟进发布，则：

1. 检查 GitHub Actions 中 `Publish to PyPI` workflow 的运行状态
2. 重点关注：
   - changelog 校验是否通过
   - build-and-publish 是否成功
   - create-release 是否成功
3. 如果 tag 已推送但因 workflow / release notes 提取问题导致失败，先判断是否适合补发：
   - 若失败原因仅是 workflow 或 release notes 提取逻辑，且用户明确授权，可采用**方案 A**：删除远程同名 tag，并把同名 tag 重建到修复后的 `origin/main` 提交
   - 若不适合改写同名 tag，则建议采用**方案 B**：发布新的 PEP 440 版本（如 `.post1` 或下一个正式版本）
   - 在执行方案 A 前，必须明确提示这是改写已推送 tag 的敏感操作，并再次获得用户确认
4. 最终向用户汇报发布结果；如果失败，指出失败步骤与下一步建议。

工作边界：
- 默认只做“发布前置动作”，不要越权直接发版
- 未经用户确认，不要创建 PR、不要 merge、不要打 tag、不要 push tag
- 除非用户明确要求，不要进入长期轮询或定时检查
- 在每个关键关口都要汇报当前状态和下一步等待项
