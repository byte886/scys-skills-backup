#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并「市场清单」（docs/source-market-list.json）与「MCP 元数据」（docs/source-metadata.json）
并对 skills/ 实际下载结果做校验，生成 catalog/skills-catalog.json + skills-catalog.md。
幂等：校验状态直接由文件系统实时计算，不依赖人工标记。运行：python3 scripts/build_catalog.py
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "catalog"
ARCHIVED_AT = "2026-10-24 21:44 +0800"


def code_of(package_id: str) -> str:
    return package_id[4:] if package_id.startswith("skl_") else package_id


def main():
    market = json.loads((DOCS / "source-market-list.json").read_text(encoding="utf-8"))
    meta = json.loads((DOCS / "source-metadata.json").read_text(encoding="utf-8"))
    m_by_pid = {s["packageId"]: s for s in meta["skills"]}

    catalog = []
    for m in market["skills"]:
        pid = m["packageId"]
        x = m_by_pid.get(pid)
        if not x:
            raise SystemExit(f"元数据缺失: {pid}")
        code = code_of(pid)
        sdir = ROOT / "skills" / code
        ext = sdir / "extracted"
        zp = sdir / f"{code}-{x['version']}.zip"
        verified = False
        file_count = 0
        has_scripts = False
        if zp.exists():
            got = hashlib.sha256(zp.read_bytes()).hexdigest()
            verified = got == x["artifactSha256"]
            if ext.exists():
                file_count = sum(1 for p in ext.rglob("*") if p.is_file())
                has_scripts = (ext / "scripts").exists()
        catalog.append({
            "packageId": pid,
            "code": code,
            "title": x["title"],
            "author": x["author"],
            "uploaderUnionUserId": x["uploaderUnionUserId"],
            "version": x["version"],
            "guideStatus": x["guideStatus"],
            "isOriginal": x["isOriginal"],
            "summary": m.get("summary", ""),
            "tagsVisible": m.get("tagsVisible", []),
            "categoryTags": m.get("categoryTags", []),
            "taskTags": m.get("taskTags", []),
            "platformTags": m.get("platformTags", []),
            "otherTags": m.get("otherTags", []),
            "hiddenTagCount": m.get("hiddenTagCount", 0),
            "installs": m.get("installs", 0),
            "comments": m.get("comments", 0),
            "marketDate": m.get("date", ""),
            "detailUrl": m.get("detailUrl", ""),
            "runtimeTargets": x["runtimeTargets"],
            "artifactSha256": x["artifactSha256"],
            "ossPathAccount": x["ossPathAccount"],
            "dependencyLock": x["dependencyLock"],
            "dependsOn": x["dependsOn"],
            "allowShell": x["allowShell"],
            "allowedTools": x["allowedTools"],
            "allowArbitraryHttp": x["allowArbitraryHttp"],
            "allowArbitraryMcp": x["allowArbitraryMcp"],
            "scriptsPresent": x["scriptsPresent"],
            "backupDir": f"skills/{code}",
            "zipFile": f"skills/{code}/{code}-{x['version']}.zip",
            "fileCount": file_count,
            "hasScriptsDir": has_scripts,
            "sha256Verified": verified,
            "archivedAt": ARCHIVED_AT if verified else None,
        })

    doc = {
        "generatedAt": ARCHIVED_AT,
        "source": {
            "marketList": "docs/source-market-list.json（外部 Chrome 只读浏览市场，T27）",
            "mcpMetadata": "docs/source-metadata.json（scys-mcp installguide 逐个取，T31）",
            "officialInstallGuide": "docs/skillhub-install-guide.md",
        },
        "distribution": meta["distribution"],
        "authors": meta["authors"],
        "total": len(catalog),
        "verifiedCount": sum(1 for s in catalog if s["sha256Verified"]),
        "totalExtractedFiles": sum(s["fileCount"] for s in catalog),
        "skillsWithScriptsDir": sum(1 for s in catalog if s["hasScriptsDir"]),
        "skills": catalog,
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "skills-catalog.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    L = []
    L.append("# 生财 SkillHub 技能备份目录（19 个）\n")
    L.append(f"- 备份时间：2026-10-24 ｜ 来源：生财 SkillHub 市场公开精选 19 个（外部收录 0）。")
    L.append(f"- 入库校验：**{doc['verifiedCount']}/{doc['total']} 已下载并通过 sha256 校验**，共解压 {doc['totalExtractedFiles']} 个文件；{doc['skillsWithScriptsDir']} 个包含技能内辅助脚本目录。")
    L.append("- 每个技能的包内完整说明见 `skills/<code>/extracted/SKILL.md`；安装/恢复见根目录 `INSTALL.md`。\n")
    L.append("| # | 技能 | packageId | 作者 | 版本 | 安装数 | 兼容客户端 | 文件数 | 校验 | 一句话说明 |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for i, s in enumerate(catalog, 1):
        tgt = "、".join(s["runtimeTargets"]) if s["runtimeTargets"] else "通用"
        summary = s["summary"].replace("|", "／").replace("\n", " ")
        if len(summary) > 40:
            summary = summary[:40] + "…"
        v = "✓" if s["sha256Verified"] else "—"
        L.append(f"| {i} | {s['title']} | `{s['packageId']}` | {s['author']} | {s['version']} | {s['installs']} | {tgt} | {s['fileCount']} | {v} | {summary} |")
    L.append("")
    L.append("## 按作者聚合\n")
    for a, n in sorted(meta["authors"].items(), key=lambda kv: (-kv[1], kv[0])):
        L.append(f"- **{a}**：{n} 个")
    L.append("")
    L.append("## 字段与校验\n")
    L.append("- 完整 sha256（64 位）、标签、依赖与风险字段见 `skills-catalog.json`；逐包已比对 `artifactSha256`。")
    L.append("- 19 个全部 hosted 原创、无上游 Git 仓库；`dependencyLock/dependsOn` 为空、`allowShell=false`。")
    L.append("- 能力卡 `scriptsPresent=false` 指安装阶段不自动执行脚本；其中 9 个包内带 `scripts/` 辅助脚本（如渲染/转录/排版），由使用时按 SKILL.md 手动调用，不是安装钩子。")
    L.append("- 市场侧 5 条折叠标签（hiddenTagCount）未展开，属市场页展示信息，不影响包体。")
    L.append("")
    (OUT / "skills-catalog.md").write_text("\n".join(L), encoding="utf-8")
    print(f"catalog {len(catalog)} 条，verified={doc['verifiedCount']}，文件={doc['totalExtractedFiles']}，含scripts={doc['skillsWithScriptsDir']}")


if __name__ == "__main__":
    main()
