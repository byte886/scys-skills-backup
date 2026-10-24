# 生财深度教程生成器

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

生财深度调研教程工作流。把用户提出的一个问题/方向/人物/航海手册/项目案例，用生财 MCP（scys-mcp）检索站内一手资料，结合世界知识与必要的联网补充，结构化为「概念→逻辑关系→事实与概念知识→实操SOP→实战案例→总结」的图文并茂单文件 HTML 教程，并强制经过 AI 亦仁（商业判断）+ AI 刘小排（AI/产品/增长）双导师详细点评、逐条修订出终版。当用户说「把 XX 做成教程」「调研 XX 产出教程」「把XX生财资料整理成图文教程」「案例拆解教程」「深度调研教程」，或描述了「检索生财 + 结构化 + 双导师点评 + 图文产出」这类组合流程时使用。

| 项 | 值 |
| --- | --- |
| packageId | `skl_scys-deep-tutorial` |
| 版本 | 1.0.0 |
| 作者 | 飞猫（uid 122662，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | claude_code、codex、hermes |
| 市场安装数 | 29（评论 0） |
| 标签 | 内容创作与个人 IP / 研究与选题 / 内容制作 |
| 详情页 | https://scys.com/skillhub/skills/skl_scys-deep-tutorial |
| 整包 sha256 | `284b2d67ee7d11b64332d4f628979b8ea4177a806c38acca5d096cce2dc93064` |
| 含脚本目录 | 否 |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/scys-deep-tutorial/versions/1.0.0/` 并校验 sha256。

## 包内文件（8 个）

- `README.md`
- `SKILL.md`
- `assets/tutorial-skeleton.html`
- `manifest.json`
- `references/acceptance-and-pitfalls.md`
- `references/mentor-review.md`
- `references/research.md`
- `references/tutorial-structure.md`
