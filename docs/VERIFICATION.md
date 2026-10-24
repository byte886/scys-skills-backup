# 备份完整性与离线核验报告

核验时间：2026-10-24 21:50（+0800）｜ 核验人：AI 助手（byte886）｜ 方式：从 GitHub **干净 clone 到临时目录**后只读核验，未安装到任何真实客户端。

## 一、核验结论（先看）

| 层级 | 结果 |
| --- | --- |
| 技能数量 | 19/19，与市场公开精选一致 |
| 整包 zip sha256 | **19/19** 与官方 `artifactSha256` 完全一致 |
| 文件级 sha256 | **127/127**（12 个含文件级清单的包，逐项全部一致） |
| SKILL.md 入口 | **19/19** 存在、可打开、非空 |
| 解压文件总数 | 170 个 |
| 远程仓库可克隆 | 是，`git clone https://github.com/byte886/scys-skills-backup` |
| 离线可用性 | 通过：不依赖网络签名链接，仅凭仓内 zip / extracted 即可查阅 |

## 二、两层校验的口径

1. **整包级（19 个全覆盖）**：每个 `<code>-<version>.zip` 下载后用 `sha256` 比对官方能力卡 `artifactSha256`，不符即中止。19 个全部通过。这是覆盖所有包的强校验。
2. **文件级（12 个包）**：12 个包的 `manifest.json` 含 `files[]`（每项带 path + sha256），对其中 127 个文件逐项算 sha256，**全部一致，且磁盘文件与 manifest 清单无出入**。
3. **简版 manifest（7 个包）**：以下 7 个包的 `manifest.json` 未提供文件级 `files[]` 清单，故只有整包级校验、无文件级校验可做（属原作者打包形态，非缺失）：
   - `field-manual-customizer`
   - `base-bili-script-writing`、`base-bili-product-intake`、`base-bili-publish-review`、`base-bili-visual-planning`、`base-bili-script-review`、`base-bili-product-ranking`（Lynn 的 6 个 B 站带货技能，均为 SKILL.md + manifest.json 两文件）

## 三、关于 `scriptsPresent=false` 的口径说明（重要，勿误读）

19 个技能的能力卡 `capabilityCard.scriptsPresent` 全部为 `false`，但实际解压后 **9 个包内带有 `scripts/` 目录**：

- `helin-analyze-livestream-commerce`、`helin-livestream-planning-master`
- `field-manual-customizer`
- `assess-ai-enterprise-fde-fit`
- `media-transcriber`
- `tietu-food-specialty`、`tietu-marriage-family`
- `wechat-longform-formatter`
- `claude-reinstall-keep-data`

这两个事实不矛盾，口径如下：

- `scriptsPresent=false` + `allowShell=false` 表示**安装阶段不自动执行任何脚本/Shell**；
- 包内的 `scripts/` 是**技能自带的辅助脚本**（如报告渲染、PDF 导出、转录、长文排版、重装流程），由使用者在按 `SKILL.md` 操作时**手动调用**，不是安装钩子。
- 本备份不修改服务端字段，只如实记录上述差异；安装前应阅读对应 SKILL.md 了解脚本用途。

## 四、可复现的核验命令

```bash
git clone https://github.com/byte886/scys-skills-backup /tmp/scys-verify
cd /tmp/scys-verify
# 整包级：python3 scripts/build_catalog.py（catalog.json 的 sha256Verified 实时由文件系统算出）
# 文件级：遍历 skills/*/extracted/manifest.json 的 files[] 逐项算 sha256
```

`scripts/build_catalog.py` 为幂等脚本：以 `docs/source-*.json` 为元数据事实源、以 `skills/` 实际文件实时计算校验状态，重跑即可重建 `catalog/skills-catalog.json/.md`。

## 五、未做的事（边界）

- 本次只做**只读、隔离**核验，未把任何技能安装到 `~/.scys-market/skills/` 或 Claude/Codex 等客户端目录。
- 未执行包内任何 `scripts/` 脚本。
- OSS 签名下载链接约 1 小时过期，未入库、不可长期保存；仓内留存的是已校验的 zip 原件，离线以它为准。
