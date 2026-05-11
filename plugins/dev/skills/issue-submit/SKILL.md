---
description: 识别远程仓库 issue 模板并选择合适的模板提交 issue
argument-hint: <owner/repo>
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash, WebFetch
---

当前参数：`$ARGUMENTS`

如果没有提供仓库标识（即 `$ARGUMENTS` 为空），就只输出：`用法: /dev:issue-submit <owner/repo>`，不要执行其他操作。停止。不要继续后续阶段。

你的任务是：从远程仓库 `$ARGUMENTS` 中识别可用的 issue 模板，让用户选择合适的模板，然后引导用户填写内容并提交 issue。

## 阶段 1：获取 issue 模板列表

使用 `gh` CLI 获取目标仓库的 issue 模板：

```bash
gh api repos/$ARGUMENTS/contents/.github/ISSUE_TEMPLATE --jq '.[].name' 2>/dev/null
```

- 如果返回空或 404，再检查是否存在 `.github/ISSUE_TEMPLATE.md` 单文件模板：
  ```bash
  gh api repos/$ARGUMENTS/contents/.github/ISSUE_TEMPLATE.md --jq '.download_url' 2>/dev/null
  ```
- 如果两者都不存在，告知用户该仓库没有 issue 模板，停止执行。
- 同时获取模板配置文件（如有）：
  ```bash
  gh api repos/$ARGUMENTS/contents/.github/ISSUE_TEMPLATE/config.yml --jq '.download_url' 2>/dev/null
  ```
  如果存在 config.yml，下载并解析其中的 `blank_issues_enabled` 和 `contact_links`。

## 阶段 2：展示模板并让用户选择

1. 用 `gh api` 下载每个模板文件的原始内容：
   ```bash
   gh api repos/$ARGUMENTS/contents/.github/ISSUE_TEMPLATE/<filename> --jq '.download_url' | xargs curl -sL
   ```

2. 解析每个模板的 YAML front matter（`---` 之间的部分），提取：
   - `name`：模板显示名称
   - `description`：模板描述
   - `title`：预填标题（如有）
   - `labels`：预设标签（如有）
   - `assignees`：预设指派人（如有）

3. 向用户展示模板列表，格式如下：

   ```
   仓库 $ARGUMENTS 的可用 issue 模板：

   1. <name> — <description>
   2. <name> — <description>
   ...
   N. 空白 issue（不使用模板）
   ```

   其中"空白 issue"选项始终提供。

4. 使用 AskUserQuestion 让用户选择一个模板。

## 阶段 3：引导用户填写 issue 内容

根据用户选择的模板：

1. **解析模板 body 中的结构化字段**：YAML front matter 中的 `body` 数组定义了表单字段，每项包含：
   - `type`：`input`（文本输入）、`textarea`（多行文本）、`dropdown`（下拉选择）、`checkboxes`（复选框）、`markdown`（说明文字）
   - `attributes.label`：字段标题
   - `attributes.description`：字段说明
   - `attributes.placeholder`：占位提示（如有）
   - `attributes.options`：选项列表（dropdown/checkboxes 类型）
   - `validations.required`：是否必填

2. **逐字段向用户提问**：
   - 对于 `markdown` 类型：跳过（仅作说明用途）
   - 对于 `input`/`textarea` 类型：使用 AskUserQuestion 向用户提问，展示 label、description 和 placeholder
   - 对于 `dropdown` 类型：使用 AskUserQuestion 提供选项列表
   - 对于 `checkboxes` 类型：使用 AskUserQuestion（multiSelect: true）让用户勾选
   - 如果某个字段有 `default` 值，将其作为默认选项展示

3. **如果模板没有结构化 body**（旧格式模板，body 只是 Markdown 字符串），则：
   - 将模板内容作为参考展示给用户
   - 一次性询问用户：标题和正文内容

4. **组装 issue 内容**：
   - 标题：优先使用模板的 `title` 字段预填，再询问用户是否修改
   - 正文：根据用户填写的字段，按照模板 body 中定义的 Markdown 格式组装
   - 如果模板是旧格式且 body 只是 Markdown，直接使用用户提供的正文

5. **向用户预览完整的 issue**：展示标题、正文、标签、指派人，等待用户确认。

## 阶段 4：提交 issue

只有在用户明确确认后才提交：

```bash
gh issue create --repo $ARGUMENTS --title "<title>" --body "<body>" [--label "<label1>,<label2>"] [--assignee "<assignee>"]
```

- `--label`：仅在模板指定了 labels 时添加
- `--assignee`：仅在模板指定了 assignees 时添加
- 提交成功后，输出 issue 的 URL

## 工作边界

- **不要**在本地仓库创建任何文件。
- **不要**修改本地代码。
- **不要**在用户确认前提交 issue。
- 对每个交互式提问，给用户提供清晰的选项和说明，不要替用户做决定。
- 如果 `gh` 命令因权限问题失败，告知用户需要对目标仓库有写入权限。
