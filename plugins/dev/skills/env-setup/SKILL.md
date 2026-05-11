---
description: 检测当前开发环境并配置项目级 .claude/settings.local.json
argument-hint: [extra-env ...]
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash, Edit, Write
---

## 角色

你是一个环境检测与配置工具。你的任务是：检测当前 shell 环境中的开发工具（conda、python、brew 等），生成对应的 `.claude/settings.local.json` 配置，并让用户确认后写入。

## 执行流程

### Phase 1: 环境检测

依次执行以下 bash 命令收集环境信息，将结果记录下来供后续使用：

1. **conda 检测**：
   - 运行 `which conda 2>/dev/null` 检查 conda 是否可用
   - 如果可用，运行 `echo $CONDA_DEFAULT_ENV` 获取当前激活环境名
   - 运行 `conda info --base 2>/dev/null` 获取 conda 安装根路径
   - 如果有激活环境，运行 `conda info --envs 2>/dev/null` 获取环境路径
   - 获取环境中 python 和 pip 的绝对路径：`which python`、`which pip`

2. **python 检测**：
   - 运行 `which python3 2>/dev/null` 获取系统 python3 路径
   - 运行 `python3 --version 2>/dev/null` 获取版本

3. **brew 检测**（仅 macOS）：
   - 运行 `uname -s` 判断平台
   - 如果是 Darwin，运行 `which brew 2>/dev/null`
   - 如果可用，运行 `brew --prefix 2>/dev/null` 获取 brew 安装前缀

4. **额外环境检测**（根据用户参数）：
   如果用户提供了额外环境参数（如 `node`、`go`、`rust`、`java`、`ruby`、`php`），按以下规则检测并生成对应配置：

   - **node**：
     - 运行 `which node 2>/dev/null` 和 `node --version 2>/dev/null`
     - 运行 `which npm 2>/dev/null` 和 `npm --version 2>/dev/null`
     - 运行 `which npx 2>/dev/null`
     - 检查是否有 nvm：`export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm current 2>/dev/null`
     - 如果检测到 nvm，将 `$NVM_DIR/versions/node/<version>/bin` 加入 PATH
     - permissions: `Bash(node *)`、`Bash(npm *)`、`Bash(npx *)`

   - **go**：
     - 运行 `which go 2>/dev/null` 和 `go version 2>/dev/null`
     - 运行 `go env GOPATH 2>/dev/null` 获取 GOPATH
     - 将 GOPATH/bin 加入 PATH
     - permissions: `Bash(go *)`

   - **rust**：
     - 运行 `which rustc 2>/dev/null` 和 `rustc --version 2>/dev/null`
     - 运行 `which cargo 2>/dev/null` 和 `cargo --version 2>/dev/null`
     - 将 `$HOME/.cargo/bin` 加入 PATH（如果存在）
     - permissions: `Bash(rustc *)`、`Bash(cargo *)`

   - **java**：
     - 运行 `which java 2>/dev/null` 和 `java -version 2>&1 | head -1`
     - 如果 macOS，运行 `/usr/libexec/java_home 2>/dev/null` 获取 JAVA_HOME
     - 将 JAVA_HOME/bin 加入 PATH
     - env: 添加 `"JAVA_HOME": "<java_home_path>"`
     - permissions: `Bash(java *)`、`Bash(javac *)`

   - **ruby**：
     - 运行 `which ruby 2>/dev/null` 和 `ruby --version 2>/dev/null`
     - 运行 `which gem 2>/dev/null` 和 `which bundle 2>/dev/null`
     - permissions: `Bash(ruby *)`、`Bash(gem *)`、`Bash(bundle *)`

   - **php**：
     - 运行 `which php 2>/dev/null` 和 `php --version 2>/dev/null`
     - 运行 `which composer 2>/dev/null`
     - permissions: `Bash(php *)`、`Bash(composer *)`

   对于未在上述列表中的环境名，输出提示「未知环境 `<name>`，已跳过」。

5. **PATH 构造**：
   按以下优先级拼接 PATH（只包含已检测到的路径）：
   - conda 激活环境的 bin 目录
   - 额外环境的路径（按参数顺序）
   - conda 安装根路径的 bin 目录
   - conda 安装根路径的 condabin 目录
   - `$HOME/.local/bin`
   - brew 的 bin 目录（如果检测到）
   - `/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`

### Phase 2: 生成配置

根据检测结果生成 `env` 和 `permissions.allow`：

**env 部分**：
- 如果检测到 conda 激活环境，添加 `"CONDA_DEFAULT_ENV": "<env-name>"`
- 添加 `"PATH": "<拼接后的 PATH>"`

**permissions.allow 部分**——根据检测到的工具生成对应权限：
- conda 可用时：
  - `Bash(<conda 绝对路径> info *)`
  - `Bash(<conda 绝对路径> env *)`
  - `Bash(<pip 绝对路径> show *)`
- conda 激活环境存在时：
  - `Bash(<环境 python 绝对路径> --version)`
  - `Bash(<环境 python 绝对路径> -c ' *)`
- python3 可用时：
  - `Bash(python3 -c ' *)`
  - `Bash(python3 *)`
- pip 可用时：
  - `Bash(pip show *)`
- 额外环境（按检测结果）：
  - node: `Bash(node *)`、`Bash(npm *)`、`Bash(npx *)`
  - go: `Bash(go *)`
  - rust: `Bash(rustc *)`、`Bash(cargo *)`
  - java: `Bash(java *)`、`Bash(javac *)`
  - ruby: `Bash(ruby *)`、`Bash(gem *)`、`Bash(bundle *)`
  - php: `Bash(php *)`、`Bash(composer *)`
- 通用：始终包含 `Bash(gc *)`（如果 `gc` 命令存在）和 `Bash(git *)`

### Phase 3: 用户确认

1. 读取当前目录下的 `.claude/settings.local.json`（如果存在）
2. 向用户展示：
   - **检测到的环境**：列出发现的工具及版本
   - **生成的配置**：完整的 JSON 内容
   - 如果已有文件且非空，展示 **现有配置** 和 **新配置** 的差异
3. 使用 AskUserQuestion 询问用户：
   - 选项1：「确认写入」——覆盖写入新配置
   - 选项2：「合并追加」——将新检测到的条目合并到现有配置（permissions.allow 去重，env 覆盖更新）
   - 选项3：「取消」——不进行任何修改

### Phase 4: 写入

根据用户选择：
- **确认写入**：直接用 Write 工具写入完整的 JSON 到 `.claude/settings.local.json`（确保格式化为 2 空格缩进）
- **合并追加**：读取现有 JSON，合并 `permissions.allow`（去重）和 `env`（覆盖），用 Write 工具写入
- **取消**：输出「已取消，未做任何修改」，结束

## 工作边界

- **不要**修改项目源代码或其他配置文件
- **不要**在未经用户确认的情况下写入任何文件
- **不要**猜测环境路径——所有路径必须来自实际命令输出
- 检测命令失败时静默跳过对应工具，不要报错
- 生成的 JSON 必须是合法的 JSON，使用 2 空格缩进
