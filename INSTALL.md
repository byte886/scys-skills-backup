# 如何查看 / 安装 / 恢复这些技能

本仓是**离线备份**，不会自动安装任何东西。按你的目的选下面一种方式。官方权威规则原文见 [`docs/skillhub-install-guide.md`](docs/skillhub-install-guide.md)，本文件是结合本仓结构的实操版。

---

## 方式 A：只想看技能是干什么的（不安装，最安全）

直接打开对应技能的解包说明：

- 一页摘要：`skills/<code>/README.md`
- 技能自带完整说明（含触发场景、用法、示例提示词）：`skills/<code>/extracted/SKILL.md`
- 市场卡片信息（标题、标签、安装数、一句话简介）：`skills/<code>/meta.json`

`<code>` 对应关系见 [`catalog/skills-catalog.md`](catalog/skills-catalog.md)。例如转录技能是 `skills/media-transcriber/`。

---

## 方式 B：用官方 MCP 安装（最规范，推荐）

适用：要真正装进 Claude Code / Codex / Hermes 等客户端、联网环境。

1. 豆包桌面端「连接器」确认已启用 **scys-mcp**（OAuth 已授权）。
2. 让 AI 调用 `skillhubInstallGuide(packageId=<技能标识>, operation=install)`，`<技能标识>` 是带 `skl_` 前缀的完整 packageId（如 `skl_media-transcriber`），逐字保留大小写和下划线。
3. 阅读返回里的 `capabilityCard`、`runtimeTargets`、`downloadPlan`：
   - 平台托管包（本仓 19 个全是）会返回 `artifactDownloadUrl`、`artifactSha256`、`extractTo`、`afterExtract`；
   - 下载链接是**约 1 小时有效的 OSS 签名地址**，过期了重新调用即可，不要拼地址。
4. **先核对目录、确认写入影响，再执行**：官方规则要求安装前向用户展示影响并取得确认；平台源存储与客户端目录由本机核对，服务端不背书具体路径。
5. 下载后**先核 SHA-256**，与 `artifactSha256` 不符立即停止，不解压、不写入。
6. 安装完成后，由 AI 调 `skillhubReportInstalled(operation=installed, ...)` 上报；上报失败不影响已完成的安装。

---

## 方式 C：从本仓 zip 手工恢复（离线 / 想固定到备份版本）

> 适用：网络受限、或要锁定本仓保存的具体版本。手工恢复不经过 MCP，也不会触发官方上报，仅在本机自己使用。

平台托管包的标准源存储布局（官方 downloadPlan 给出）：

```
~/.scys-market/skills/<code>/
├── versions/<version>/        # 解压后的包内容
└── current -> versions/<version>   # 软链，指向当前版本
```

恢复步骤（以 `media-transcriber` 1.1.0 为例）：

```bash
CODE=media-transcriber
VER=1.1.0
BASE=~/.scys-market/skills/$CODE

# 1) 校验备份 zip 的 sha256（期望值见 catalog/skills-catalog.json 或该技能 meta.json）
shasum -a 256 "skills/$CODE/$CODE-$VER.zip"

# 2) 解压到版本目录
mkdir -p "$BASE/versions/$VER"
unzip -o "skills/$CODE/$CODE-$VER.zip" -d "$BASE/versions/$VER"

# 3) 建立 current 软链
mkdir -p "$BASE"
ln -sfn "versions/$VER" "$BASE/current"

# 4) 检查入口文件
ls "$BASE/current"            # 应能看到 SKILL.md / manifest.json
```

再按客户端规则把技能放进对应目录（**目录以本机客户端实际规则为准**，官方仅提供参考）：

| 客户端 | 全局 skills 目录（参考） |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.cursor/skills/` |
| Windsurf | `~/.codeium/windsurf/skills/` |
| Codex | `~/.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| 其它（Antigravity/QoderWork/WorkBuddy 等） | 见官方指南「安装目标与目录核对」 |

可把 `~/.scys-market/skills/<code>/current` 软链到客户端 skills 目录（或直接复制版本目录），**装前先确认目标目录是否已有同名技能，避免覆盖**。项目级技能则放项目根的 `.claude/skills`、`.codex/skills` 等候选目录（以所用客户端规则为准）。

---

## 校验与卸载

- **完整性校验**：每个 zip 入库前已按官方 sha256 校验；恢复时建议再次 `shasum -a 256` 比对。也可进一步核 `manifest.json` 中 `files[]` 逐项 hash（技能自校验）。
- **卸载**：删除客户端 skills 目录里的该技能条目（或软链）；平台源存储删除 `~/.scys-market/skills/<code>/` 即可。卸载前先确认该技能没有被其它技能依赖（本仓 19 个 `dependsOn` 均为空，互不依赖）。

## 几条红线（来自官方指南）

- 安装前必须展示影响并取得确认；不擅自覆盖、删除同名目录或无关文件。
- 签名地址过期**重新调用 MCP 取新的**，绝不手工拼下载地址。
- 「外部收录包」（`isOriginal=false`）要走原作者官方源，**禁用**平台 downloadPlan；本仓 19 个当前均为 hosted，不涉及。
- 「安装包缺失」时停止，不要重查/拼装，联系作者重新发布。
- 装好后可在网页查看详情：`https://scys.com/skillhub/skills/<packageId>`。
