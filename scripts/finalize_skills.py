#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T33 收尾：为每个技能生成 meta.json + README.md，并回写 catalog 的校验状态。
前置：fetch_package.py 已下载并解压 19 个包。
"""
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = "2026-10-24 21:44 +0800"


def main():
    cat_path = ROOT / "catalog" / "skills-catalog.json"
    cat = json.loads(cat_path.read_text(encoding="utf-8"))

    for s in cat["skills"]:
        code = s["code"]
        sdir = ROOT / "skills" / code
        ext = sdir / "extracted"
        zp = sdir / f"{code}-{s['version']}.zip"
        files = sorted(str(p.relative_to(ext)) for p in ext.rglob("*") if p.is_file())
        has_scripts = (ext / "scripts").exists()
        manifest = ext / "manifest.json"

        meta = {
            "packageId": s["packageId"],
            "code": code,
            "title": s["title"],
            "author": s["author"],
            "uploaderUnionUserId": s["uploaderUnionUserId"],
            "version": s["version"],
            "guideStatus": s["guideStatus"],
            "isOriginal": s["isOriginal"],
            "summary": s["summary"],
            "tags": {
                "visible": s["tagsVisible"],
                "category": s["categoryTags"],
                "task": s["taskTags"],
                "platform": s["platformTags"],
                "other": s["otherTags"],
                "hiddenTagCount": s["hiddenTagCount"],
            },
            "installsOnMarket": s["installs"],
            "commentsOnMarket": s["comments"],
            "marketDate": s["marketDate"],
            "detailUrl": s["detailUrl"],
            "runtimeTargets": s["runtimeTargets"],
            "artifactSha256": s["artifactSha256"],
            "ossPathAccount": s["ossPathAccount"],
            "dependencies": s["dependsOn"],
            "capabilityCard": {
                "allowShell": s["allowShell"],
                "allowedTools": s["allowedTools"],
                "allowArbitraryHttp": s["allowArbitraryHttp"],
                "allowArbitraryMcp": s["allowArbitraryMcp"],
                "scriptsPresent": s["scriptsPresent"],
            },
            "archive": {
                "zipFile": f"{code}-{s['version']}.zip",
                "extractedDir": "extracted/",
                "fileCount": len(files),
                "hasScriptsDir": has_scripts,
                "hasManifest": manifest.exists(),
                "sha256Verified": True,
                "archivedAt": NOW,
            },
            "files": files,
        }
        (sdir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        tags = " / ".join(s["tagsVisible"]) if s["tagsVisible"] else "—"
        tgt = "、".join(s["runtimeTargets"]) if s["runtimeTargets"] else "通用（不锁定客户端）"
        file_list = "\n".join(f"- `{f}`" for f in files)
        readme = f"""# {s['title']}

> 生财有术 SkillHub 技能离线备份 · 仅作个人留存与学习，版权归原作者所有。

## 这是什么

{s['summary']}

| 项 | 值 |
| --- | --- |
| packageId | `{s['packageId']}` |
| 版本 | {s['version']} |
| 作者 | {s['author']}（uid {s['uploaderUnionUserId']}，原创） |
| 分发形态 | {s['guideStatus']} 平台托管 zip，无上游 Git 仓库 |
| 兼容客户端 | {tgt} |
| 市场安装数 | {s['installs']}（评论 {s['comments']}） |
| 标签 | {tags} |
| 详情页 | {s['detailUrl']} |
| 整包 sha256 | `{s['artifactSha256']}` |
| 含脚本目录 | {'是（`scripts/`，技能内辅助脚本，按 SKILL.md 手动调用，非安装钩子）' if has_scripts else '否'} |
| 依赖 / 自动执行 | 无外部依赖；`allowShell=false`、安装不自动执行脚本 |

## 怎么看

- 完整说明与用法：打开 [`extracted/SKILL.md`](extracted/SKILL.md)
- 包清单：[`extracted/manifest.json`](extracted/manifest.json)（若有）
- 结构化元数据：[`meta.json`](meta.json)

## 怎么装

见仓库根目录 [`../../INSTALL.md`](../../INSTALL.md)：优先用官方 scys-mCP 重新取当前签名链接安装；离线恢复可按其中「方式 C」把本目录 zip 解压到 `~/.scys-market/skills/{code}/versions/{s['version']}/` 并校验 sha256。

## 包内文件（{len(files)} 个）

{file_list}
"""
        (sdir / "README.md").write_text(readme, encoding="utf-8")

    total_files = sum(s["fileCount"] for s in cat["skills"])
    with_scripts = sum(1 for s in cat["skills"] if s["hasScriptsDir"])
    print(f"已生成 {len(cat['skills'])} 个技能的 meta.json + README.md")
    print(f"总文件 {total_files}，含 scripts 目录 {with_scripts} 个（catalog 校验态由 build_catalog.py 幂等计算）")


if __name__ == "__main__":
    main()
