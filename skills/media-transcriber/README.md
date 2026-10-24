# 音视频转录与长文整理

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

把音视频、播客、字幕或逐字稿整理成保留案例、数字和推理过程的中文长稿，可按需提供摘要、真实时间戳和原始逐字稿。

| 项 | 值 |
| --- | --- |
| packageId | `skl_media-transcriber` |
| 版本 | 1.1.0 |
| 作者 | 亦仁（uid 36389，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | A、B、C、D、F |
| 市场安装数 | 564（评论 0） |
| 标签 | 内容创作与个人 IP / 内容制作 |
| 详情页 | https://scys.com/skillhub/skills/skl_media-transcriber |
| 整包 sha256 | `13be2aab46f1029a8eb697577203100c2d4099dd559403cdae45c0c8bfb18831` |
| 含脚本目录 | 是（`scripts/`，技能内辅助脚本，按 SKILL.md 手动调用，非安装钩子） |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/media-transcriber/versions/1.1.0/` 并校验 sha256。

## 包内文件（10 个）

- `README.md`
- `SKILL.md`
- `agents/openai.yaml`
- `manifest.json`
- `references/feishu-delivery.md`
- `references/media-tools.md`
- `references/writing-standard.md`
- `scripts/check_environment.py`
- `scripts/normalize_transcript.py`
- `scripts/transcribe_local.py`
