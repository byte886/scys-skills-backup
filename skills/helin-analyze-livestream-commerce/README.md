# 河林直播拆解

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

把直播回放转写稿拆成五模块报告：货盘与出场台账、排品动线与憋卡踢促循环、主推品话术、带合规提示的可复用话术框架、操盘点评；适配视频号、抖音、小红书。

| 项 | 值 |
| --- | --- |
| packageId | `skl_helin-analyze-livestream-commerce` |
| 版本 | 2.1.0 |
| 作者 | 河林（uid 215990，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | 通用（不锁定客户端） |
| 市场安装数 | 8（评论 0） |
| 标签 | 电商经营与获客 / 数据分析与复盘 / 小红书 |
| 详情页 | https://scys.com/skillhub/skills/skl_helin-analyze-livestream-commerce |
| 整包 sha256 | `8aadbb3d48d0788c34d620d1aefeccb510954af52616fbbbd4126fdfa6211eff` |
| 含脚本目录 | 是（`scripts/`，技能内辅助脚本，按 SKILL.md 手动调用，非安装钩子） |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/helin-analyze-livestream-commerce/versions/2.1.0/` 并校验 sha256。

## 包内文件（8 个）

- `SKILL.md`
- `agents/openai.yaml`
- `manifest.json`
- `references/analysis-rules.md`
- `references/example-report.md`
- `references/helin-method.md`
- `references/report-template.md`
- `scripts/transcript_ledger.py`
