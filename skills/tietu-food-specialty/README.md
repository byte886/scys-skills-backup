# 美食贴图skill

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

Use when 用户要创作、改写或检查贴图号美食特产内容，素材涉及地方小吃、冷门食材、时令瓜果、制作过程、产销故事、家庭烹饪或日常食安；不用于无来源的医疗、功效或价格承诺。

| 项 | 值 |
| --- | --- |
| packageId | `skl_tietu-food-specialty` |
| 版本 | 1.0.0 |
| 作者 | ⃰辰风（uid 818409，原创） |
| 分发形态 | hosted 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | 通用（不锁定客户端） |
| 市场安装数 | 15（评论 0） |
| 标签 | 内容创作与个人 IP / 内容制作 / 视觉与素材 |
| 详情页 | https://scys.com/skillhub/skills/skl_tietu-food-specialty |
| 整包 sha256 | `8746b489a4d8d22776f20cae96932361412951f106b6b86bd98ec85149f11923` |
| 含脚本目录 | 是（`scripts/`，技能内辅助脚本，按 SKILL.md 手动调用，非安装钩子） |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/tietu-food-specialty/versions/1.0.0/` 并校验 sha256。

## 包内文件（34 个）

- `SKILL.md`
- `agents/openai.yaml`
- `assets/adjustment-schema.json`
- `assets/reference-layouts/README.md`
- `assets/reference-layouts/example.json`
- `assets/track-profile.json`
- `assets/typography-styles.json`
- `examples/acceptance-cases.md`
- `examples/cover-input.json`
- `examples/invalid-cover-input.json`
- `examples/invalid-image-exception.json`
- `examples/invalid-output.json`
- `examples/valid-output.json`
- `manifest.json`
- `references/finished-image-execution.md`
- `references/human-tone-and-anti-ai.md`
- `references/output-contract-and-checklist.md`
- `references/persona-and-audience.md`
- `references/prompt-sealing-and-adjustments.md`
- `references/reference-image-and-typography.md`
- `references/table-source-links.md`
- `references/topic-keywords-and-titles.md`
- `references/visual-prompt-engine.md`
- `references/writing-and-emotion.md`
- `scripts/render_finished_image.mjs`
- `scripts/render_title_cover.mjs`
- `scripts/validate_output.mjs`
- `tests/render-compatibility.test.mjs`
- `tests/render-finished-image.test.mjs`
- `tests/render-title-cover.test.mjs`
- `tests/typography-styles.test.mjs`
- `tests/validate-output.test.mjs`
- `tests/visual-hook-matrix.test.mjs`
- `tests/visual-routing.test.mjs`
