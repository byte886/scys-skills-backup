# 自媒体商业定位教练skill

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

AI 自媒体商业定位教练。通过一对一采访，帮助想做自媒体、个人 IP、知识型 IP 但不确定定位的人，梳理个人优势、判断定位机会、输出完整的自媒体商业定位诊断报告。触发场景一（本人在线采访）：用户说「开始定位采访」「帮我做自媒体定位」「帮我找自媒体方向」「我不知道自己适合做什么账号」「帮我分析我的个人IP定位」「帮我设计一个可以变现的自媒体账号」。触发场景二（材料诊断）：用户不上来一问一答，而是直接给一份材料——可能是自己的自我介绍、简历、账号数据，也可能是教练手上的客户调研表、问卷、微信沟通记录、转介信息，要求「根据这些材料给一个定位和产品方向」，此时不启动采访，改走材料诊断模式。默认只输出一份给用户本人看的报告；内部判断与跟进版仅在明确索取时额外生成。

| 项 | 值 |
| --- | --- |
| packageId | `skl_ai-self-media-coach` |
| 版本 | 3.0.0 |
| 作者 | 竹子。（uid 724673，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | 通用（不锁定客户端） |
| 市场安装数 | 19（评论 0） |
| 标签 | 内容创作与个人 IP / 判断与决策 |
| 详情页 | https://scys.com/skillhub/skills/skl_ai-self-media-coach |
| 整包 sha256 | `24b2c2d809c3cf198e229fcc3eb2ef1c2b844cc982a5ebb2388b67d0ee57c785` |
| 含脚本目录 | 否 |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/ai-self-media-coach/versions/3.0.0/` 并校验 sha256。

## 包内文件（2 个）

- `SKILL.md`
- `manifest.json`
