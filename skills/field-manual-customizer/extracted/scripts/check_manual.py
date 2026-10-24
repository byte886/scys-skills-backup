#!/usr/bin/env python3
"""检查文件并读取内容核对记录，不把脚本成功当作手册可用。

python3 scripts/check_manual.py 手册.md [--review review.json] [--json]
退出 1：文件错误、核对记录失效或已登记的内容失败。
退出 0：没有上述错误；可能仍未内容核对、未真实试用，必须查看分项结果。
"""
import argparse
import base64
import binascii
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True  # 在导入同目录模块前禁止写入已安装 Skill 的 __pycache__。
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from fetch_images import MAX_IMAGE_BYTES, divider_level, image_size, supported_image

VERSION = "0.10.1"
STEP_HEADING = re.compile(r"^#{2,3}\s+步骤\s*\d+\s+\S")
LEGACY_STEP_HEADING = re.compile(r"^#{2,3}\s+S\d+\s+\S")
MANUAL_TYPE = re.compile(r"^>\s*手册类型：(通用版|定制版)\s*$")
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
SUSPECT = ["刷单", "刷评", "小号评论", "刷回复率", "去水印", "买粉", "刷量",
           "互关", "互赞", "红包加热", "洗稿", "过查重", "搬运", "伪装所在地"]
RESIDUE = re.compile(r"\b(?:TODO|TBD)\b|\{\{|IMG:")
CHECK_IDS = ("route", "rules", "numbers", "images", "schedule", "scope")
DATA_IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
DATA_IMAGE_HEADER = re.compile(r"data:(image/(?:png|jpeg|webp));base64\Z", re.I)
SOURCE_ID = re.compile(r"source-([os]\d+)\Z", re.I)
PLAIN_MARKER = re.compile(r"\[[OS]\d+(?:\s*[,、]\s*[OS]\d+)*\]", re.I)
ADJACENT_MARKERS = re.compile(r"\[[OS]\d+\]\s*\[[OS]\d+\]", re.I)
# 模板已自动生成网页侧栏与 PDF 打印目录；源稿再手写一节会在 PDF 里重复出现。
TOC_HEADING = re.compile(r"(?:本手册)?(?:可点击的?)?(?:目\s*录|table\s+of\s+contents|contents|toc)"
                         r"(?:\s*[（(][^）)]*[）)])?\s*[:：]?", re.I)
FENCE = re.compile(r"(`{3,}|~{3,})")
HEADING = re.compile(r"(#{1,6})\s+(.*?)\s*#*\s*$")
INLINE_ANCHOR = re.compile(r"<a\s+id=\"[^\"]*\"\s*>\s*</a>|\{#[^}]*\}", re.I)
SOURCE_HEADING = re.compile(r"(?:附录\s*[A-Za-z0-9]*\s*[｜|:：、]?\s*)?(?:参考|资料|引用)?来源")
LOCAL_LINK = re.compile(r"\]\(#[^)\s]+\)|href=\"#[^\"]+\"")
LATER_NOTE = re.compile(r"先不做|暂不做|以后再看|之后再看")
# 取资料的过程只进来源节和资料记录；单独的“存档”“快照日期”是读者需要的日期说明，不在此列。
PROCESS_TRACE = re.compile(
    r"web\.archive\.org|internet\s+archive|wayback\s+machine"
    r"|(?:返回|报错?|状态码|HTTP|Cloudflare)\s*[:：]?\s*403(?!\s*[\d.元份条个人次位粉篇张天件])"
    r"|(?<!\d)403\s*(?:Forbidden|错误)"
    r"|(?:拒绝|挡(?:了|住)?)了?\s*程序(?:直接)?访问"
    r"|(?:改读|改用|转读|读的是)(?:网页|页面的?|官方页面的?)?存档", re.I)


class RenderedManualScanner(HTMLParser):
    """扫描网页可见围栏、正文配图及来源锚点；作者头像不计入正文图片。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.literal_depth = 0
        self.lines = []
        self.elements = []
        self.body_image_count = 0
        self.image_warnings = []
        self.ids = set()
        self.duplicate_ids = []
        self.local_links = []
        self.source_refs = []
        self.source_backrefs = []
        self.source_entries = set()
        self.plain_markers = []

    def nearest_figure(self):
        return next((item for item in reversed(self.elements) if item["tag"] == "figure"), None)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.append(element_id)
            self.ids.add(element_id)
        classes_here = set((values.get("class") or "").split())
        active_classes = set().union(*(item["classes"] for item in self.elements)) if self.elements else set()
        if "sources" in active_classes and element_id and SOURCE_ID.fullmatch(element_id):
            self.source_entries.add(element_id)
        if tag == "a":
            href = values.get("href") or ""
            if href.startswith("#"):
                self.local_links.append((href[1:], self.getpos()[0]))
            if "source-ref" in classes_here:
                self.source_refs.append([element_id, href, self.getpos()[0],
                                         "source-markers" in active_classes, "",
                                         bool({"intro", "section-body"} & active_classes)])
            if "source-backref" in classes_here:
                entry = next((item["id"] for item in reversed(self.elements)
                              if item["id"] and SOURCE_ID.fullmatch(item["id"])), None)
                self.source_backrefs.append((href, self.getpos()[0],
                                             "sources" in active_classes, entry))
        if tag in ("pre", "code", "script", "style"):
            self.literal_depth += 1
        if tag == "img":
            classes = (item["classes"] for item in self.elements)
            active_classes = set().union(*classes) if self.elements else set()
            if "section-body" in active_classes and "source-credit" not in active_classes:
                self.body_image_count += 1
                figure = self.nearest_figure()
                if figure is None:
                    self.image_warnings.append(self.getpos()[0])
                else:
                    figure["images"].append(self.getpos()[0])
            return
        if tag in {"meta", "input", "br", "hr", "link", "source", "wbr"}:
            return
        self.elements.append({"tag": tag, "id": element_id, "classes": classes_here, "images": [],
                              "source_ref_index": len(self.source_refs) - 1 if tag == "a" and
                              "source-ref" in classes_here else None,
                              "caption_text": False})

    def handle_endtag(self, tag):
        if tag in ("pre", "code", "script", "style") and self.literal_depth:
            self.literal_depth -= 1
        for index in range(len(self.elements) - 1, -1, -1):
            if self.elements[index]["tag"] == tag:
                for item in reversed(self.elements[index:]):
                    if item["tag"] == "a" and item["source_ref_index"] is not None:
                        self.source_refs[item["source_ref_index"]][4] = item.get("text", "")
                    if item["tag"] == "figure" and item["images"] and not item["caption_text"]:
                        self.image_warnings.extend(item["images"])
                del self.elements[index:]
                break

    def handle_data(self, data):
        for item in reversed(self.elements):
            if item["tag"] == "a":
                item["text"] = item.get("text", "") + data
                break
        if not self.literal_depth and any("section-body" in item["classes"] or "intro" in item["classes"]
               for item in self.elements) and not any(
                   "source-markers" in item["classes"] for item in self.elements):
            if PLAIN_MARKER.search(data):
                self.plain_markers.append(self.getpos()[0])
        if data.strip() and any(item["tag"] == "figcaption" for item in self.elements):
            figure = self.nearest_figure()
            if figure is not None:
                figure["caption_text"] = True
        if self.literal_depth:
            return
        first_line = self.getpos()[0]
        for offset, line in enumerate(data.splitlines()):
            if line.lstrip().startswith("```"):
                self.lines.append(first_line + offset)


def scan_rendered_html(manual):
    html = manual.with_suffix(".html")
    if not html.exists() and not html.is_symlink():
        return None, []
    target = html.resolve(strict=False)
    if not target.is_relative_to(manual.parent) or not target.is_file():
        return None, [{"code": "html_path_outside", "message": "网页文件路径越界或不是文件"}]
    scanner = RenderedManualScanner()
    with target.open(encoding="utf-8") as stream:
        while chunk := stream.read(64 * 1024):
            scanner.feed(chunk)
    scanner.close()
    for item in scanner.elements:
        if item["tag"] == "figure" and item["images"] and not item["caption_text"]:
            scanner.image_warnings.extend(item["images"])
    failures = [{"code": "unrendered_code_fence", "line": line,
                      "message": "网页仍有 Markdown 代码围栏；请改用 <pre><code>"}
                     for line in scanner.lines]
    failures.extend({"code": "duplicate_anchor", "message": f"重复锚点：{anchor}"}
                    for anchor in scanner.duplicate_ids)
    failures.extend({"code": "dangling_anchor", "line": line, "message": "页内链接没有目标"}
                    for target, line in scanner.local_links if not target or unquote(target) not in scanner.ids)
    failures.extend({"code": "plain_source_marker", "line": line,
                     "message": "正文来源标记须是可点击的锚点链接"}
                    for line in scanner.plain_markers)
    for cite_id, href, line, grouped, label, in_body in scanner.source_refs:
        target = href[1:] if href.startswith("#") else ""
        if (not cite_id or not grouped or not in_body or target not in scanner.source_entries
                or target.lower() != f"source-{label.strip().lower()}"):
            failures.append({"code": "invalid_source_reference", "line": line,
                             "message": "来源标记须位于标记组内并指向文末对应来源"})
    for entry in scanner.source_entries:
        refs = [cite_id for cite_id, ref_href, _, _, _, _ in scanner.source_refs
                if ref_href == f"#{entry}"]
        if not refs:
            failures.append({"code": "unreferenced_source", "message": f"来源条目没有正文标记：{entry}"})
        elif not any(back_href == f"#{cite_id}" and in_sources and back_entry == entry
                     for back_href, _, in_sources, back_entry in scanner.source_backrefs
                     for cite_id in refs):
            failures.append({"code": "missing_source_backlink",
                             "message": f"来源条目缺少回到正文的链接：{entry}"})
    return scanner, failures


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def embedded_image_size(src):
    header, separator, payload = src.partition(",")
    match = DATA_IMAGE_HEADER.fullmatch(header)
    if not separator or not match:
        raise ValueError("内嵌图片只支持 PNG、JPEG、WebP 的 base64 数据")
    mime = match.group(1).lower()
    # 先按编码长度拒绝巨量输入，避免解码时再分配超限字节。
    if len(payload) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
        raise ValueError("内嵌图片超过 20 MiB 上限")
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("内嵌图片 base64 无效") from None
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("内嵌图片超过 20 MiB 上限")
    extension, size = supported_image(data)
    if extension != DATA_IMAGE_TYPES[mime]:
        raise ValueError("内嵌图片 MIME 与实际格式不一致")
    return size


def lines_outside_fences(lines):
    """逐行给出代码围栏外的内容；围栏内是模板或示例，不算手册结构。"""
    fence = None
    for number, line in enumerate(lines, 1):
        stripped = line.lstrip()
        marker = FENCE.match(stripped)
        if fence:
            if (marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence)
                    and not stripped[len(marker.group(1)):].strip()):
                fence = None
            continue
        if marker:
            fence = marker.group(1)
            continue
        yield number, line


def heading_outline(lines):
    """返回围栏外的 (行号, 级别, 去掉锚点后的标题文字)。"""
    outline = []
    for number, line in lines_outside_fences(lines):
        match = HEADING.fullmatch(line)
        if match:
            text = INLINE_ANCHOR.sub("", match.group(2)).strip()
            outline.append((number, len(match.group(1)), text))
    return outline


def section_lines(lines, outline, start_line):
    """取某个二级标题到下一个一、二级标题之间、围栏外的正文行。"""
    end_line = next((number for number, level, _ in outline if number > start_line and level <= 2),
                    len(lines) + 1)
    return [(number, line) for number, line in lines_outside_fences(lines)
            if start_line < number < end_line]


def opening_structure_issues(lines):
    """开头固定为：阅读说明 → 路线图 → 其余内容；源稿不手写目录。"""
    failures, warnings = [], []
    outline = heading_outline(lines)
    for number, level, text in outline:
        if level <= 2 and TOC_HEADING.fullmatch(text):
            failures.append({"code": "handwritten_toc", "line": number,
                             "message": "源稿不要手写「目录」一节；网页与 PDF 目录由模板自动生成，手写会在 PDF 里重复出现"})
    order = [(number, text) for number, level, text in outline
             if level == 2 and not TOC_HEADING.fullmatch(text)]
    reading = next((index for index, (_, text) in enumerate(order) if "阅读说明" in text), None)
    roadmap = next((index for index, (_, text) in enumerate(order) if "路线图" in text), None)
    if reading is not None and roadmap is None:
        warnings.append({"code": "missing_roadmap", "line": order[reading][0],
                         "message": "完整手册应在阅读说明之后紧接按周或阶段的路线图；局部更新可忽略"})
    if reading is None or roadmap is None:
        return failures, warnings
    if roadmap < reading:
        failures.append({"code": "reading_note_after_roadmap", "line": order[reading][0],
                         "message": "「阅读说明」须排在「路线图」之前"})
    elif reading != 0 or roadmap != 1:
        opening = "、".join(text for _, text in order[:roadmap + 1])
        failures.append({"code": "opening_order", "line": order[roadmap][0],
                         "message": f"源稿正文须以「阅读说明」开头、紧接「路线图」；当前开头是：{opening}"})
    body = section_lines(lines, outline, order[roadmap][0])
    if not any(LOCAL_LINK.search(line) for _, line in body):
        warnings.append({"code": "roadmap_without_links", "line": order[roadmap][0],
                         "message": "路线图的每一步应能点到对应章节，目前没有页内链接"})
    if not any(LATER_NOTE.search(line) for _, line in body):
        warnings.append({"code": "roadmap_without_later_note", "line": order[roadmap][0],
                         "message": "路线图下面应写一句这一阶段先不做什么、以后再看什么，并链到附录"})
    return failures, warnings


def process_trace_warnings(lines):
    """来源节之外的读者正文不写取数过程；来源节与资料记录里可以写。"""
    warnings = []
    in_sources = False
    for number, line in lines_outside_fences(lines):
        match = HEADING.fullmatch(line)
        if match and len(match.group(1)) <= 2:
            in_sources = bool(SOURCE_HEADING.match(INLINE_ANCHOR.sub("", match.group(2)).strip()))
        if in_sources:
            continue
        words = sorted({item.group(0) for item in PROCESS_TRACE.finditer(line)})
        if words:
            warnings.append({"code": "process_trace_in_body", "line": number, "words": words,
                             "message": "取资料的过程（如 403、网页存档）写进来源节和资料记录；读者正文只留规则本身和日期"})
    return warnings


def split_sections(lines):
    sections, cur = [], []
    for line in lines:
        if line.startswith("### "):
            if cur:
                sections.append("\n".join(cur))
            cur = [line]
        elif re.match(r"^#{1,2} ", line):
            if cur:
                sections.append("\n".join(cur))
            cur = []
        elif cur:
            cur.append(line)
    if cur:
        sections.append("\n".join(cur))
    return sections


def is_step(section):
    return "从哪进" in section or "点击路径" in section or any(
        line.count("→") >= 2 for line in section.splitlines()
        if not line.lstrip().startswith(">")
    )


def step_shape_warnings(lines):
    """只对完整手册中显式编号的步骤提醒；局部修订不强制重排。"""
    warnings = []
    sections = []
    current = None
    for number, line in enumerate(lines, 1):
        if STEP_HEADING.match(line):
            if current:
                sections.append(current)
            current = (number, [])
        elif current and re.match(r"^#{1,3}\s", line):
            sections.append(current)
            current = None
        elif current:
            current[1].append(line)
    if current:
        sections.append(current)
    for number, body in sections:
        text = "\n".join(body)
        actions = sum(bool(re.match(r"^\s*\d+\.\s+", line)) for line in body)
        if not ("**目标**" in text and "**做完的标准**" in text and 3 <= actions <= 5):
            warnings.append({"code": "step_shape", "line": number,
                             "message": "编号步骤建议用一句话目标、3–5 条动作清单和做完的标准"})
    return warnings


def manual_type_issues(lines):
    """整本手册在书名后声明视角；局部更新不强制补齐整本格式。"""
    failures = []
    outline = heading_outline(lines)
    title_line = next((number for number, level, _ in outline if level == 1), None)
    marker_line = title_line + 2 if title_line is not None else None
    marker = MANUAL_TYPE.fullmatch(lines[marker_line - 1]) if marker_line and marker_line <= len(lines) else None
    if marker is None and any(level == 2 and "阅读说明" in title for _, level, title in outline):
        failures.append({"code": "manual_type_missing", "line": marker_line,
                         "message": "整本手册须在一级书名后空一行写 > 手册类型：通用版 或 > 手册类型：定制版"})
    return marker.group(1) if marker else None, failures


def text_value(value):
    return isinstance(value, str) and bool(value.strip())


def evidence_errors(items, root, label):
    errors = []
    if not isinstance(items, list) or not items:
        return [f"{label}：缺少原文证据"]
    for i, item in enumerate(items):
        prefix = f"{label} 证据 {i + 1}"
        if not isinstance(item, dict):
            errors.append(f"{prefix}：应为对象")
            continue
        if not all(text_value(item.get(k)) for k in ("path", "locator", "sha256")):
            errors.append(f"{prefix}：需要 path、locator、sha256")
            continue
        p = (root / item["path"]).resolve()
        if not p.is_relative_to(root.resolve()):
            errors.append(f"{prefix}：证据须位于本工作目录内")
        elif not p.is_file():
            errors.append(f"{prefix}：找不到文件 {item['path']}")
        elif sha256(p) != item["sha256"]:
            errors.append(f"{prefix}：证据文件已变更，需重核")
    return errors


def review_record(path, manual, text):
    content = {"status": "not_reviewed", "errors": [], "gaps": [], "pending": []}
    usability = {"status": "not_tested", "scope": "", "errors": []}
    if not path.exists():
        return content, usability
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        content.update(status="invalid", errors=[f"无法读取核对记录：{exc}"])
        return content, usability
    if not isinstance(record, dict):
        content.update(status="invalid", errors=["核对记录应为 JSON 对象"])
        return content, usability
    errors = content["errors"]
    if record.get("schema_version") != 1:
        errors.append("不支持的 schema_version")
    if record.get("skill_version") != VERSION:
        errors.append(f"记录的技能版本不是 {VERSION}，需按当前版本重核")
    if record.get("manual_sha256") != sha256(manual):
        errors.append("正文与核对记录的 SHA-256 不同，旧核对已失效")
    for field in ("reviewer", "reviewed_at", "goal"):
        if not text_value(record.get(field)):
            errors.append(f"缺少 {field}")
    try:
        datetime.fromisoformat(str(record.get("reviewed_at", "")).replace("Z", "+00:00"))
    except ValueError:
        errors.append("reviewed_at 不是 ISO 日期或时间")
    content["reviewer"] = record.get("reviewer")
    content["reviewed_at"] = record.get("reviewed_at")
    headings = {re.sub(r"^#{1,6}\s+", "", line).strip()
                for line in text.splitlines() if re.match(r"^#{1,6}\s+", line)}
    steps = record.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("需要从用户目标倒推的 steps，不能仅检查已写出的章节")
        steps = []
    seen = set()
    critical_count = 0
    for step in steps:
        if not isinstance(step, dict):
            errors.append("steps 中每项应为对象")
            continue
        sid = step.get("id")
        if not text_value(sid) or sid in seen:
            errors.append("步骤 ID 缺失或重复")
        if text_value(sid):
            seen.add(sid)
        if not text_value(step.get("title")) or not isinstance(step.get("critical"), bool):
            errors.append(f"{sid}：缺少 title 或布尔值 critical")
        critical_count += step.get("critical") is True
        if not text_value(step.get("note")):
            errors.append(f"{sid}：缺少具体核对结果或缺口说明 note")
        status = step.get("status")
        if status == "supported":
            if not text_value(step.get("section")) or step["section"] not in headings:
                errors.append(f"{sid}：正文找不到对应标题，可能漏写该步骤")
            errors.extend(evidence_errors(step.get("evidence"), manual.parent, str(sid)))
        elif status == "gap":
            content["gaps"].append({"id": sid, "critical": step.get("critical"),
                                    "note": step.get("note")})
        elif status != "not_applicable":
            errors.append(f"{sid}：status 应为 supported、gap 或 not_applicable")
    if steps and not critical_count:
        errors.append("steps 至少应列出一个本次目标必需的 critical 动作")
    checks = record.get("checks")
    checks = checks if isinstance(checks, list) else []
    check_map = {}
    failed = []
    for check in checks:
        if not isinstance(check, dict) or check.get("id") not in CHECK_IDS:
            errors.append("checks 含无效检查项")
            continue
        cid = check["id"]
        if cid in check_map:
            errors.append(f"重复检查项：{cid}")
        check_map[cid] = check
        if check.get("status") not in ("pass", "fail", "not_reviewed"):
            errors.append(f"{cid}：无效 status")
        elif check["status"] == "not_reviewed":
            content["pending"].append(cid)
        elif not text_value(check.get("evidence")):
            errors.append(f"{cid}：核对结果缺少具体 evidence")
        if check.get("status") == "fail":
            failed.append(cid)
    for cid in CHECK_IDS:
        if cid not in check_map:
            content["pending"].append(cid)
    content["failed_checks"] = failed
    if errors:
        content["status"] = "invalid"
    elif failed or any(g["critical"] for g in content["gaps"]):
        content["status"] = "failed"
    elif content["pending"] or content["gaps"]:
        content["status"] = "partial"
    else:
        content["status"] = "recorded"
    trial = record.get("usability", {})
    if not isinstance(trial, dict) or trial.get("status") not in ("not_tested", "passed", "failed"):
        usability.update(status="invalid", errors=["usability 缺失或状态无效"])
    elif trial["status"] != "not_tested":
        usability.update(status=trial["status"], scope=trial.get("scope", ""))
        if not text_value(trial.get("scope")):
            usability["errors"].append("实际试用必须注明范围")
        usability["errors"].extend(evidence_errors(trial.get("evidence"), manual.parent, "实际试用"))
        if usability["errors"]:
            usability["status"] = "invalid"
    # 正文或证据失效时，不能继续显示旧版试用已通过。
    if errors and usability["status"] == "passed":
        usability.update(status="stale", errors=usability["errors"] + ["内容记录失效，试用结论不适用于当前稿"])
    return content, usability


def audit_manual(path, review_path=None):
    path = Path(path).resolve()
    text = path.read_text(encoding="utf-8")
    failures, warnings = [], []
    lines = text.splitlines()
    if ADJACENT_MARKERS.search(text):
        failures.append({"code": "adjacent_source_markers",
                         "message": "同一处的多个来源标记应合为一个标记组"})
    warnings.extend(step_shape_warnings(lines))
    in_source_section = False
    for number, line in lines_outside_fences(lines):
        heading = HEADING.fullmatch(line)
        if heading and len(heading.group(1)) <= 2 and not LEGACY_STEP_HEADING.match(line):
            in_source_section = bool(SOURCE_HEADING.match(INLINE_ANCHOR.sub("", heading.group(2)).strip()))
        if LEGACY_STEP_HEADING.match(line) and not in_source_section:
            failures.append({"code": "legacy_step_heading", "line": number,
                             "message": "旧步骤编号 S 会与站内来源 S 混淆；请将步骤标题改为「步骤 1 …」，并同步 plan.md 与 review.json 的步骤 ID"})
    structure_failures, structure_warnings = opening_structure_issues(lines)
    failures.extend(structure_failures)
    warnings.extend(structure_warnings)
    warnings.extend(process_trace_warnings(lines))
    manual_type, type_failures = manual_type_issues(lines)
    failures.extend(type_failures)
    if manual_type == "通用版":
        for line_no, line in enumerate(lines, 1):
            if any(term in line for term in ("你的条件", "未经你确认")):
                failures.append({"code": "general_manual_personal_address", "line": line_no,
                                 "message": "通用版不得把读者条件写成某个人的条件"})
    if not text.strip():
        failures.append({"code": "empty_manual", "message": "正文为空"})
    rendered, rendered_failures = scan_rendered_html(path)
    failures.extend(rendered_failures)
    images = []
    manual_dir = path.parent.resolve()
    for line_no, line in enumerate(lines, 1):
        for src in IMG_RE.findall(line):
            images.append(src)
            if src.startswith(("http://", "https://")):
                warnings.append({"code": "remote_image", "line": line_no,
                                 "message": "远程图片可能过期；需核交付后可用性"})
                continue
            if src.lower().startswith("data:"):
                try:
                    size = embedded_image_size(src)
                except ValueError as exc:
                    failures.append({"code": "invalid_data_uri", "line": line_no, "message": str(exc)})
                    continue
                if divider_level(size):
                    warnings.append({"code": "inspect_flat_image", "line": line_no,
                                     "message": "图片较扁，须看实际内容；形状不决定删除或通过"})
                continue
            decoded_src = unquote(src.strip("<>"))
            if urlsplit(decoded_src).scheme:
                failures.append({"code": "unsupported_image_scheme", "line": line_no,
                                 "message": "图片协议不受支持"})
                continue
            local_name = Path(decoded_src)
            p = (manual_dir / local_name).resolve(strict=False)
            if local_name.is_absolute() or not p.is_relative_to(manual_dir):
                failures.append({"code": "image_path_outside", "line": line_no,
                                 "message": "图片路径越界"})
                continue
            if not p.is_file():
                failures.append({"code": "missing_image", "line": line_no, "path": src})
                continue
            if p.stat().st_size > MAX_IMAGE_BYTES:
                failures.append({"code": "image_too_large", "line": line_no, "path": src,
                                 "message": "图片超过 20 MiB 上限"})
                continue
            with p.open("rb") as image_file:
                data = image_file.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                failures.append({"code": "image_too_large", "line": line_no, "path": src,
                                 "message": "图片超过 20 MiB 上限"})
                continue
            size = image_size(data)
            if not size or not all(size):
                failures.append({"code": "unrecognized_image", "line": line_no, "path": src})
            elif divider_level(size):
                warnings.append({"code": "inspect_flat_image", "line": line_no, "path": src,
                                 "message": "图片较扁，须看实际内容；形状不决定删除或通过"})
        if RESIDUE.search(line):
            failures.append({"code": "unfinished_placeholder", "line": line_no})
    body_image_count = rendered.body_image_count if rendered is not None else len(images)
    if body_image_count == 0:
        warnings.append({"code": "zero_body_images",
                         "message": "手册正文没有配图；请人工复核目标读者能否仅凭文字读懂关键动作"})
    if rendered is not None:
        for line_no in rendered.image_warnings:
            warnings.append({"code": "image_without_figure_caption", "line": line_no,
                             "message": "正文图片未与非空图注放在同一个 figure；请复核打印同页效果"})
    # 这些是待核线索，不能由否定词或标题决定合规/不合规。
    suspect_lines = [{"line": n, "words": [w for w in SUSPECT if w in line]}
                     for n, line in enumerate(lines, 1) if any(w in line for w in SUSPECT)]
    steps = [s for s in split_sections(lines) if is_step(s)]
    content, usability = review_record(
        Path(review_path).resolve() if review_path else path.parent / "review.json", path, text
    )
    blocking = bool(failures) or content["status"] in ("invalid", "failed") or usability["status"] in ("invalid", "failed", "stale")
    return {
        "schema_version": 1, "checker_version": VERSION, "manual": str(path),
        "manual_sha256": sha256(path),
        "files": {"status": "failed" if failures else "passed", "failures": failures,
                  "warnings": warnings, "image_references": len(images), "unique_images": len(set(images))},
        "content_review": content, "usability": usability,
        "review_hints": {"suspect_lines": suspect_lines, "recognized_operation_sections": len(steps),
                         "limits": "关键词和章节识别仅供定位，不能证明行为性质或全部必要动作已覆盖"},
        "blocking_errors": blocking,
        "limits": "文件检查不证明内容正确；核对记录只验证结构、版本、文件与哈希，不替代语义核对或真实试用"
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manual", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = audit_manual(args.manual, args.review)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"检查失败：{exc}\n")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("文件检查：" + result["files"]["status"])
        for issue in result["files"]["failures"] + result["files"]["warnings"]:
            print("  " + json.dumps(issue, ensure_ascii=False))
        print("内容核对记录：" + result["content_review"]["status"])
        for key in ("errors", "gaps", "pending", "failed_checks"):
            for issue in result["content_review"].get(key, []):
                print("  " + str(issue))
        print("真实试用记录：" + result["usability"]["status"])
        print("可疑措辞待逐处核对：" + str(len(result["review_hints"]["suspect_lines"])) + " 行")
        print(result["limits"])
    return 1 if result["blocking_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
