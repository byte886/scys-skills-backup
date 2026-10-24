# 长文章排版skill

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

用户已有微信公众号长文，想选排版样式并得到标题、排版正文和可打开的 article.html 网页成品时使用；不用于重写文章。

| 项 | 值 |
| --- | --- |
| packageId | `skl_wechat-longform-formatter` |
| 版本 | 1.0.0 |
| 作者 | ⃰辰风（uid 818409，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | 通用（不锁定客户端） |
| 市场安装数 | 12（评论 0） |
| 标签 | 内容创作与个人 IP / 内容制作 / 公众号 |
| 详情页 | https://scys.com/skillhub/skills/skl_wechat-longform-formatter |
| 整包 sha256 | `f37f0c70147fd83898d3c018045029e83b07317bf0aecdb69234c73f2817cc32` |
| 含脚本目录 | 是（`scripts/`，技能内辅助脚本，按 SKILL.md 手动调用，非安装钩子） |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/wechat-longform-formatter/versions/1.0.0/` 并校验 sha256。

## 包内文件（3 个）

- `SKILL.md`
- `manifest.json`
- `scripts/render_article.py`
