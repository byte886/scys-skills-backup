# 实战手册定制

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

告诉它你想做的项目和手头条件，它结合生财站内经验和平台规则，给你定制一份能照着做的实战手册。

| 项 | 值 |
| --- | --- |
| packageId | `skl_field-manual-customizer` |
| 版本 | 0.10.1 |
| 作者 | 亦仁（uid 36389，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | claude_code、codex |
| 市场安装数 | 56（评论 0） |
| 标签 | 研究与选题 / 判断与决策 |
| 详情页 | https://scys.com/skillhub/skills/skl_field-manual-customizer |
| 整包 sha256 | `899342d07c3c83db09e1af71e20076c5fcf91677bbb11521e68078f7267ed614` |
| 含脚本目录 | 是（`scripts/`，技能内辅助脚本，按 SKILL.md 手动调用，非安装钩子） |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/field-manual-customizer/versions/0.10.1/` 并校验 sha256。

## 包内文件（19 个）

- `README.md`
- `SKILL.md`
- `agents/openai.yaml`
- `examples/fictional-zine-exchange.html`
- `examples/fictional-zine-exchange.md`
- `manifest.json`
- `references/forbidden-practices.md`
- `references/manual-outline.md`
- `references/manual-review.md`
- `references/records-and-review.md`
- `references/scys-mcp-tools.md`
- `references/web-delivery.md`
- `references/writing-rules.md`
- `scripts/check_manual.py`
- `scripts/embed_avatar.py`
- `scripts/export_pdf.py`
- `scripts/fetch_images.py`
- `scripts/render_diagram.py`
- `templates/manual.html`
