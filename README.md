# 生财有术 SkillHub 技能备份仓

个人离线备份「生财有术 SkillHub 技能市场」的全部精选 Skill，方便随时查看与恢复，不依赖市场页面或签名链接有效期。

- 备份时间：2026-10-24
- 备份范围：SkillHub 市场「全部来源·综合」公开可见的 **19 个技能**（圈友原创精选 19，外部收录 0）
- 账号：以生财会员账号（只读）经官方 scys-mcp 与市场页采集
- 备份方式：**只整包归档，不做任何二次发布或售卖**；每个技能版权归原作者所有

## 这些技能是怎么分发的（先理解）

市场里的 Skill 不是 Git 仓库，而是生财托管的**版本化 zip 包**：

- 安装时由官方 scys-mcp 的 `skillhubInstallGuide` 返回：版本号、整包 sha256、一个约 1 小时有效的 OSS 签名下载链接、解压计划；
- 本次 19 个技能 **全部为 `hosted`（平台托管原创）、`isOriginal=true`、无任何上游 Git 仓库链接**，因此没有 fork 对象，统一整包 zip 归档；
- 19 个技能均无外部依赖、安装阶段不自动执行脚本、无任意网络/MCP 授权（`dependsOn=[]`、`allowShell=false`、`scriptsPresent=false`）。其中 9 个包内含 `scripts/` **辅助脚本**（报告渲染、转录、排版等），由使用时按 SKILL.md 手动调用，非安装钩子；详见 [`docs/VERIFICATION.md`](docs/VERIFICATION.md)。

## 目录结构

```
scys-skills-backup/
├── README.md                 # 本文件：总览与映射
├── INSTALL.md                # 如何离线查看 / 恢复安装 / 校验（含官方安装规则）
├── catalog/
│   ├── skills-catalog.md     # 19 技能人读总表（标题/作者/版本/安装数/说明/位置）
│   └── skills-catalog.json   # 19 技能结构化目录（含 sha256、标签、兼容客户端等）
├── skills/<code>/            # 每个技能一个目录（19 个，已全部入库）
│   ├── <code>-<version>.zip  #   包原件（与 artifactSha256 一致，19/19 已校验）
│   ├── meta.json             #   该技能 MCP 元数据 + 市场卡片信息 + 归档校验
│   ├── README.md             #   该技能说明（做什么、何时触发、作者、怎么装、文件清单）
│   └── extracted/            #   解包内容（SKILL.md / manifest.json / references…）
├── docs/
│   ├── skillhub-install-guide.md   # 官方安装指南原文（2026-10-24 归档）
│   ├── VERIFICATION.md             # 完整性与离线核验报告（19/19 整包、127/127 文件级）
│   ├── source-market-list.json     # 市场清单原始数据（T27）
│   └── source-metadata.json        # MCP 元数据原始数据（T31）
└── scripts/
    ├── build_catalog.py      # 由 docs/ 源数据 + 实际文件幂等重建 catalog/
    ├── fetch_package.py      # 下载 + sha256 校验 + 解压单包（供复现/更新）
    └── finalize_skills.py    # 为每个技能生成 meta.json + README.md
```

## 19 个技能速览

完整表格见 [`catalog/skills-catalog.md`](catalog/skills-catalog.md)。按作者聚合：

- **Lynn（6）**：B 站带货流水线——商品信息整理 / 讲解排序 / 口播稿生成 / 口播稿检查 / 分镜与封面规划 / 发布检查复盘
- **亦仁（3）**：音视频转录与长文整理、实战手册定制、Claude 换号重装助手
- **⃰辰风（3）**：美食贴图、婚姻家庭贴图、公众号长文章排版
- **河林（2）**：直播拆解、直播策划大师
- **松月（2）**：小红书虚拟产品选品、OPC 一人公司流量诊断
- **竹子。（1）**：自媒体商业定位教练
- **乐阳（1）**：AI 企业服务 FDE 方向选择测评
- **飞猫（1）**：生财深度教程生成器

## 我想查看 / 安装某个技能

- 只想看内容：直接打开 `skills/<code>/extracted/SKILL.md`（技能自带完整说明），或 `skills/<code>/README.md`（一页摘要）。
- 想正式装到 Claude Code / Codex / Hermes 等客户端：按 [`INSTALL.md`](INSTALL.md) 操作；**推荐用官方 MCP 重新获取当前签名链接安装**，本仓 zip 仅用于离线留存与版本比对。

## 完整性与来源

- 每个 zip 入库前都按官方返回的 `artifactSha256` 校验：**19/19 整包一致**；12 个含文件级清单的包共 **127 个文件逐项 sha256 一致**，19/19 SKILL.md 可打开。完整核验过程与从 GitHub 干净 clone 的复现方法见 [`docs/VERIFICATION.md`](docs/VERIFICATION.md)。
- 采集通道：市场清单来自只读浏览（外部 Chrome 登录态），元数据来自官方 scys-mcp 只读调用；全程未执行 install、未写入 `~/.scys-market` 或任何客户端 skills 目录。
- 原始证据与通道验证记录保留在采集工作底稿（不随本仓公开）：官方指南原文已归档于 `docs/skillhub-install-guide.md`。
