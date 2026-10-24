# OPC 一人公司流量诊断

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

帮一人公司把“没流量、有曝光没成交、用户不留存”等问题拆成一个主瓶颈，并设计 7–14 天只改一件事的增长验证实验。

| 项 | 值 |
| --- | --- |
| packageId | `skl_opc-growth` |
| 版本 | 1.0.0 |
| 作者 | 松月（uid 456738，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | 通用（不锁定客户端） |
| 市场安装数 | 7（评论 0） |
| 标签 | 私域运营与成交 / 数据分析与复盘 / 判断与决策 |
| 详情页 | https://scys.com/skillhub/skills/skl_opc-growth |
| 整包 sha256 | `15b0c7d94a84953b6dd3896c26722fb2a0e9b866bda319006d026f6308d93ebd` |
| 含脚本目录 | 否 |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/opc-growth/versions/1.0.0/` 并校验 sha256。

## 包内文件（6 个）

- `SKILL.md`
- `agents/openai.yaml`
- `manifest.json`
- `references/diagnostic-matrix.md`
- `references/experiment-template.md`
- `references/source-map.md`
