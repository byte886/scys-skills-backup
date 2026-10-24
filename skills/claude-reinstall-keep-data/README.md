# Claude 换号重装助手

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

更换 Claude 账号时，清掉 Claude Code 登录状态和本地账号信息并重新安装，保留会话、记忆、Skill、MCP；支持 macOS 和 Windows。

| 项 | 值 |
| --- | --- |
| packageId | `skl_claude-reinstall-keep-data` |
| 版本 | 0.1.5 |
| 作者 | 亦仁（uid 36389，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | claude:global、codex:global |
| 市场安装数 | 16（评论 0） |
| 标签 | AI 自动化与工作流 / 自动化与集成 |
| 详情页 | https://scys.com/skillhub/skills/skl_claude-reinstall-keep-data |
| 整包 sha256 | `0d79139073f9d1b10b1aac70227c089266699025a8fd9e3861c0e89fc1916aaa` |
| 含脚本目录 | 是（`scripts/`，技能内辅助脚本，按 SKILL.md 手动调用，非安装钩子） |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/claude-reinstall-keep-data/versions/0.1.5/` 并校验 sha256。

## 包内文件（5 个）

- `SKILL.md`
- `manifest.json`
- `scripts/claude-reinstall.mjs`
- `scripts/run-mac.command`
- `scripts/run-windows.cmd`
