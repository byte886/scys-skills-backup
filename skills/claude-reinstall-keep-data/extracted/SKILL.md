---
name: claude-reinstall-keep-data
description: 卸载并重装 Claude Code，同时保留会话记录、记忆、Skill、插件、全局配置和 MCP 配置，只清掉登录账号状态。macOS 和 Windows 通用。用于「Claude 账号被封要换号」「退出旧账号重装 Claude Code」「清理 Claude 登录状态但保留数据」「备份 / 恢复 Claude Code 数据」等场景。
---

# Claude Code 卸载重装（保留数据）

账号被封或要换号时，把 Claude Code 的登录状态清干净、重装，同时把用了很久的会话、记忆、Skill、MCP 服务配置原样带回来（OAuth 类 MCP 需要重新授权）。

所有逻辑都在 `scripts/claude-reinstall.mjs`（Node 脚本，macOS / Windows 通用）。**不要手工逐条删文件**，按下面的方式调用脚本。

## ⚠️ 先判断「你是不是 Claude」

脚本会卸载 Claude Code 本身，所以**由谁来执行完整流程**取决于你是哪个 AI：

- **你是 Claude（Claude Code / Claude Desktop 等）**：只能跑 `--dry-run` 和 `--backup-only`。完整流程和 `--restore` 让用户退出 Claude 后自己运行。在 Claude Code 里，脚本检测到 `CLAUDECODE` 等环境变量会直接拒绝，加 `--yes` 也一样；其他 Claude 环境（如 Claude Desktop）靠下面的进程检测拦截。
- **你是其他 AI 工具（如 Codex）**：可以代为执行完整流程和 `--restore`，但必须分两轮：先跑 `--dry-run` 把结果告诉用户，**等用户看过结果后、在新的一条消息里明确同意**，再加 `--yes` 执行。用户最初那句「帮我重装」不算同意；不要在同一轮里既预览又执行。`--yes` 会跳过脚本内的两次确认。完整流程要跑 3–10 分钟（npm 卸载和重装），请给足命令超时或放到后台运行；万一被中断，按输出里已打印的恢复命令续上（原本没装过 Claude Code 命令行版的用户只需 `--restore` 一步，不会补装），数据都在备份里。需要有权限访问用户主目录、npm 全局目录（macOS 还有钥匙串），沙箱受限时请用户放开权限或改为自己运行。

无论谁执行，完整流程和 `--restore` 开始前都会检查还有没有 Claude Code / Claude Desktop 进程在运行，有就列出进程并停止（此时不做任何改动），请用户全部退出后重试。**检查本身失败时（如 `ps`/`tasklist` 不可用或被占用）不会当成"没有在运行"而放行**：`--yes`（AI 代为执行）一律停止，没有绕过方式；用户自己在交互式终端里运行时，脚本会明确提示检查失败，并要求输入完整短语「确认继续」才会继续（不是简单的 y），由用户自己担保确实已经退出。

| 动作 | Claude | 其他 AI 工具 | 用户自己 |
|-|-|-|-|
| 预览：`--dry-run` | ✅ | ✅ | ✅ |
| 只备份：`--backup-only` | ✅ | ✅ | ✅ |
| 完整卸载重装 | ❌ | ✅ 用户同意后加 `--yes` | 双击 `scripts/run-mac.command` / `scripts/run-windows.cmd`，或 `node scripts/claude-reinstall.mjs` |
| 恢复：`--restore <备份目录>` | ❌ | ✅ 用户同意后加 `--yes` | `node scripts/claude-reinstall.mjs --restore <备份目录>` |

命令都是 `node <skill目录>/scripts/claude-reinstall.mjs <参数>`。

## 推荐步骤

1. 跑 `--dry-run`，把「会备份什么 / 会移走什么 / 预计体积」告诉用户。
2. 请用户退出所有 Claude Code 会话和 Claude Desktop。
3. 执行完整流程：
   - 你是 Claude → 请用户双击对应平台的入口脚本，按提示输入 y；
   - 你是其他 AI 工具 → 用户明确同意后，执行 `node <skill目录>/scripts/claude-reinstall.mjs --yes`，把输出里的警告逐条转告用户。
4. 脚本依次：检查 Claude 进程已退出 → 备份 → 退出登录 → 清理凭据与账号状态文件 → 卸载 → `npm install -g @anthropic-ai/claude-code` 重装（原本只用 Desktop、没装过命令行版的用户会跳过这步；装完会打印实际安装到的版本号，作为安装记录）→ 恢复数据。
5. 完成后让用户重新打开 Claude Code，用新账号登录，并重新授权 OAuth 类 MCP。

## 备份内容（`~/claude-backups/<时间戳>/`）

- 会话：`~/.claude/projects`、`history.jsonl`、`plans`
- 全局记忆：`~/.claude/memory`
- Skill 与扩展：`~/.claude/skills`、`agents`、`commands`、`plugins`（含插件市场与缓存）
- 全局配置：`~/.claude/settings.json`、`settings.local.json`、`keybindings.json`、`CLAUDE.md`
- `~/.claude.json`：完整原件存到「账号状态（不恢复）」目录兜底；恢复时只**合并** `mcpServers` 和 `projects`（项目级 MCP、权限设置），不带回旧账号标识。同名 MCP 服务以当前配置为准；同一项目内的字段以备份为准（重装后生成的多是空壳默认值）
- Claude Desktop 的 `claude_desktop_config.json`（macOS：`~/Library/Application Support/Claude/`；Windows 安装版：`%APPDATA%\Claude\`；Windows Microsoft Store 版：`%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\`，脚本自动识别）
- Claude Desktop 的 Cowork 会话（`local-agent-mode-sessions`）和 Code 标签页会话索引（`claude-code-sessions`），恢复时写回。换账号后 Desktop 的 Code 标签页按账号显示会话，旧账号的会话卡片可能看不到，但对话内容都在 `~/.claude/projects`，可在命令行用 `claude --resume` 继续

备份完成后会逐项比对源和备份的体积：完整流程中不一致就停止（此时还没有卸载或清理任何东西）；`--backup-only` 时 Claude 可能仍在写会话文件，只告警。

清单之外的 `~/.claude` 内容（如 `sessions`、`file-history`、各类缓存）不备份，但也不会被删除（`backups/` 快照目录除外，它含旧账号信息，会被移走，见下）。

备份时软链接会复制成真实内容（避免只备份一个空链接）；失效链接、循环链接、指向备份目录的链接会跳过并提示。备份前会估算体积，磁盘空间不足时直接停止。

恢复时如果目标位置已经是软链接（例如 skill 链接到你自己的仓库），会**保留链接、不覆盖**，避免把备份里的旧内容写进链接指向的源仓库；换新电脑恢复时这些位置不存在，会恢复成普通目录。

## 会被移走的内容（不直接删除）

- 登录状态：先 `claude auth logout`；macOS 再删除钥匙串中所有以 `Claude Code-credentials` 开头的条目兜底（找不到 claude 命令或 logout 失败时也能清掉）；然后移走 `~/.claude.json`、`~/.claude/.credentials.json`、`~/.claude/.claude.json`，以及 Claude Code 自动保存的 `.claude.json` 快照目录 `~/.claude/backups/`（里面同样含旧账号信息）
- Claude Code 程序：npm 全局包、原生安装（`~/.local/bin/claude(.exe)`、`~/.local/share/claude`，以及旧版本地安装 `~/.claude/local`）、macOS 上 Homebrew cask `claude-code` / `claude-code@latest`、Windows 上 WinGet `Anthropic.ClaudeCode`
- Claude Desktop：移走其数据目录（登录会话；macOS `~/Library/Application Support/Claude/`，Windows `%APPDATA%\Claude\`），macOS 还会卸载 / 移走 `Claude.app` 并删除钥匙串条目 `Claude Safe Storage`；Windows 上的 Desktop 程序需用户在「设置 → 应用」里手动卸载。Desktop 的 MCP 配置已备份并会写回，**脚本不会重装 Desktop**，需要的话从 https://claude.ai/download 重新安装后登录新账号

**MCP 的 OAuth 授权需要重新做**：OAuth 类 MCP 服务的令牌和 Claude 登录凭据存在同一处（macOS 钥匙串 / `.credentials.json`），清理登录状态时会一起清掉。MCP 服务配置本身会保留，重装登录后按提示重新授权即可。

移走 `/Applications/Claude.app` 时如果权限不足，脚本**不会**自动用 `sudo` 提权，会跳过这一步、给出警告并继续走完剩余流程（登录凭据、账号状态该清的照常清）——程序本体留在原地，需要的话自己在终端用 `sudo` 移走，或在结尾的警告汇总里核对这一条。

移走的文件去向：macOS 进废纸篓 `~/.Trash/claude-uninstall-<时间戳>/`；Windows 进 `~/claude-uninstalled/<时间戳>/`。确认新账号一切正常后再自行清空。

备份目录 `~/claude-backups/` 每跑一次新增一份（通常几百 MB 到数 GB），不会自动清理；里面含 MCP 密钥和旧账号信息（脚本会尽量收紧为仅当前用户可读，失败时会提示），确认新账号正常后请自行删除旧备份。

## 前置条件与常见问题

- 设置了 `CLAUDE_CONFIG_DIR` 环境变量时，脚本以该目录作为配置目录（`.claude.json` 也在其中），`--dry-run` 会显示实际使用的目录。请在同一个设置了该变量的终端里运行。家目录下遗留的 `~/.claude.json` 也会被移走，并在备份的「账号状态（不恢复）」里留一份副本。旧备份只会在本机、本用户、同一配置目录下被沿用。
- 钥匙串被锁定时无法列出带后缀的凭据条目，脚本会告警，请到「钥匙串访问」里手动检查以 `Claude Code-credentials` 开头的条目。

- 完整流程需要 Node.js 22+ 和 npm（Claude Code 的 npm 包本身要求 Node 22+）；`--dry-run`、`--backup-only`、`--restore` 在 Node 18.15+ 即可运行，可以先备份再升级 Node。
- 重装固定走 npm：原来是原生、Homebrew 或 WinGet 安装的，重装后会变成 npm 版。官方目前推荐原生安装（支持自动更新）；如需改回原生版，恢复完成后按官方文档重新安装即可，数据不受影响。
- 流程中途中断（Ctrl+C、断电、报错）时，脚本在卸载前已打印恢复命令：先 `npm install -g @anthropic-ai/claude-code`（原本没装过命令行版则跳过这步），再 `--restore <本次备份目录>`。
- `--restore` 只接受带 `backup-info.json` 的备份目录，会先确认；覆盖前会把当前的 `settings.json`、`CLAUDE.md`、`history.jsonl`、`.claude.json` 等存到 `~/claude-backups/<时间戳>-pre-restore/`，可随时撤回。它会用备份覆盖 `settings.json`、`CLAUDE.md`、`history.jsonl` 等同名文件（回退备份之后的改动）；项目设置按字段合并、备份优先。单独使用时注意这一点。
- 移走账号状态文件前会先逐个预检；任何一个移不走（如 Windows 上文件被占用），脚本会在卸载程序之前停止，一个都不移。此时已执行过退出登录（macOS 钥匙串凭据已删除），结束 Claude 进程后重跑即可。重跑时若 `~/.claude.json` 已不存在，会沿用上一次备份里的 MCP 与项目设置并提示。
- 重装后如果 PATH 里找不到 `claude`，脚本会提示应加入 PATH 的目录。
- 结尾会分别提示恢复阶段和其他阶段的警告数，有警告时请逐条检查上方输出。
- npm 安装失败时备份不会丢，脚本会打印一条 `--restore` 命令，解决 npm 问题后执行它即可。
- Windows 上如提示文件被占用（EBUSY），说明还有 Claude 进程没退出，在任务管理器里结束后重跑。
- 找不到 `claude` / `npm` 命令时，脚本会跳过对应步骤（登录注销、卸载重装判断）并给出告警；这类情况下服务端登录会话可能没有真正注销，建议之后手动执行 `claude auth logout` 或到 claude.ai 账号设置里撤销会话；命令行版是否需要重装也请自行用 `npm ls -g @anthropic-ai/claude-code` 核实一次。
- macOS 双击 `run-mac.command` 提示「无法打开」或「来自身份不明的开发者」时，执行 `xattr -d com.apple.quarantine <skill目录>/scripts/run-mac.command`；提示没有执行权限时执行 `chmod +x <skill目录>/scripts/run-mac.command`；或直接在终端运行 `node <skill目录>/scripts/claude-reinstall.mjs`。
- 已在 Windows 真机上跑过测试，发现的问题（Store 版 Desktop 识别、进程检测失效放行、CLI 检测漏报等）已在后续版本修复；但覆盖场景有限，仍建议首次使用先跑 `--dry-run` 和 `--backup-only`。
