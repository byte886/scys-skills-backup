# 乐阳AI企业服务FDE方向选择测评报告

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

根据乐阳老师的方法论，判定使用者在AI企服FDE方向的能力定位、测评评分、产品选择与行动方案。

| 项 | 值 |
| --- | --- |
| packageId | `skl_assess-ai-enterprise-fde-fit` |
| 版本 | 2.1.0 |
| 作者 | 乐阳（uid 54111，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | 通用（不锁定客户端） |
| 市场安装数 | 6（评论 0） |
| 标签 | AI 自动化与工作流 / 判断与决策 |
| 详情页 | https://scys.com/skillhub/skills/skl_assess-ai-enterprise-fde-fit |
| 整包 sha256 | `79414bbeebed66d82306d4438b0ff84d347c3747522269235e347a5aec7f4154` |
| 含脚本目录 | 是（`scripts/`，技能内辅助脚本，按 SKILL.md 手动调用，非安装钩子） |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/assess-ai-enterprise-fde-fit/versions/2.1.0/` 并校验 sha256。

## 包内文件（9 个）

- `SKILL.md`
- `agents/openai.yaml`
- `assets/report-template.html`
- `manifest.json`
- `references/guidance-playbook.md`
- `references/question-bank.md`
- `references/report-schema.md`
- `references/scoring-model.md`
- `scripts/render_report.py`
