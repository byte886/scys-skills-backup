#!/usr/bin/env python3
"""把资源完全内嵌的离线手册网页打印为 PDF（仅使用 Python 标准库）。

用法：python3 scripts/export_pdf.py 手册.html --out-dir 手册输出目录
可选：--output 文件名.pdf、--overwrite、--timeout 60、--browser 浏览器可执行文件。

退出码：0 成功；2 输入不安全或无效；3 找不到 Chrome/Edge/Chromium；
4 浏览器导出失败；5 浏览器超时。失败时保留网页，使用网页里的「分享」按钮手动导出，
并在交付说明注明「PDF 未自动生成」。

导出只接受资源完全内嵌的单文件 HTML。脚本只读取这一个输入文件，浏览器
实际打开它在隔离临时目录中的副本。外链只保留为 PDF 中可点击的链接，
不会在导出时作为子资源加载。浏览器禁用脚本、代理和后台联网，且将所有
主机名解析为不存在；此限制用于离线导出，不替代操作系统的网络隔离。
"""

import argparse
import base64
import binascii
import hashlib
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser
from html import escape
from pathlib import Path
from urllib.parse import unquote_to_bytes, urlsplit


MAX_HTML_BYTES = 50 * 1024 * 1024
PDF_MARKER_RE = re.compile(
    r'(<button id="print-button" type="button" data-pdf-name=")([^"]*)(">分享</button>)'.encode("utf-8"))
DATA_IMAGE_RE = re.compile(
    r"\A(?:data:image/(?:png|jpeg|webp);base64,|data:image/svg\+xml(?:;base64)?,)", re.I)
HTML_TAGS = frozenset({
    "html", "head", "meta", "title", "style", "script", "body", "header", "nav",
    "main", "section", "details", "summary", "div", "span", "h1", "h2", "h3",
    "h4", "h5", "h6", "p", "ol", "ul", "li", "table", "thead", "tbody",
    "tfoot", "tr", "th", "td", "strong", "em", "b", "i", "code", "pre",
    "blockquote", "hr", "br", "a", "img", "figure", "figcaption", "label", "input", "textarea", "button", "small",
    "sup", "sub", "mark", "cite", "time",
})
GLOBAL_ATTRIBUTES = frozenset({
    "id", "class", "lang", "title", "role", "hidden", "aria-label", "aria-live",
    "aria-controls", "aria-expanded", "aria-modal", "aria-labelledby", "aria-describedby",
    "data-manual-id", "data-check-id",
})
TAG_ATTRIBUTES = {
    "meta": frozenset({"charset", "name", "content", "http-equiv"}),
    "a": frozenset({"href", "target", "rel"}),
    "img": frozenset({"src", "alt", "width", "height"}),
    "label": frozenset({"for"}),
    "input": frozenset({"type", "placeholder", "autocomplete", "disabled", "checked", "readonly"}),
    "textarea": frozenset({"readonly", "rows"}),
    "button": frozenset({"type", "disabled", "data-pdf-name"}),
    "details": frozenset({"open"}),
    "th": frozenset({"scope", "colspan", "rowspan"}),
    "td": frozenset({"colspan", "rowspan"}),
    "time": frozenset({"datetime"}),
}
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SVG_ATTRIBUTES = {
    "svg": frozenset({"xmlns", "width", "height", "viewbox"}),
    "circle": frozenset({"cx", "cy", "r", "fill"}),
    "rect": frozenset({"x", "y", "width", "height", "rx", "ry", "fill"}),
    "text": frozenset({"x", "y", "text-anchor", "font-family", "font-size", "fill"}),
}
SVG_NUMBER_RE = re.compile(r"\A\d+(?:\.\d+)?\Z")
SVG_COLOR_RE = re.compile(r"\A(?:#[0-9a-fA-F]{3,8}|[a-zA-Z]+)\Z")
# 0.6.1 与 0.7.0 模板的完整 CSS 指纹，兼容旧手册；两版均无资源加载语法。
PREVIOUS_TEMPLATE_STYLE_SHA256 = frozenset({
    "6d590ed50943451ab62cb062fbdd728b2bd4f33c6afb7a0aa51c2f53eb86e92c",
    "e21c2317833f45cad2e20eb6234f86b00376ce1a771b55df5feb1c04706100f2",
    "e839d26b408351c35012b03c1c5c0a569346900cf02a098b2d60e385907f0cd4",  # 0.7.3
    "5472acfc62f93dd37ae5ddb8264452148df5d2a14e2b14e14412d6f67445b1ed",  # 0.8.0
    "7bd57dbb656fa0e7542e659e295b211147cb3465c5f135762b48da69533755e8",  # 0.8.1
    "d7cace39656e50072cc23c228048280b35cb3ab43d9abfc5203c0154320ecae6",  # 0.8.2
    "204ea6c3a820eb020867ac2d335d808db078da1687ae08efe143799e2cb46214",  # 0.8.3
})

PRINT_TOC_EMPTY = '<ol class="print-toc-list" id="print-toc-list"></ol>'
UNSUPPORTED_OUTLINE_RE = re.compile(
    r"(?:(?:unknown|unrecognized|unsupported|invalid)[^\r\n]*--generate-pdf-document-outline|"
    r"--generate-pdf-document-outline[^\r\n]*(?:unknown|unrecognized|unsupported|invalid))", re.I)


def valid_pdf_name(name):
    """仅接受同目录文件名；空串只用于尚未自动导出的模板。"""
    return (isinstance(name, str) and (not name or
            (Path(name).name == name and name not in {".", ".."} and
             name.lower().endswith(".pdf") and "/" not in name and "\\" not in name and
             not re.match(r"^[A-Za-z]:", name) and
             not any(ord(char) < 32 or ord(char) == 127 for char in name))))


class InlineSVGInspector(HTMLParser):
    """只解析示例虚构头像的基本图形；任何未知元素、属性、嵌套均拒绝。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.seen_svg = False

    def check_tag(self, tag, attributes):
        if tag not in SVG_ATTRIBUTES or (tag == "svg") != (not self.stack):
            raise ValueError("内嵌 SVG 含可能读取其他资源的元素")
        attrs = dict(attributes)
        if len(attrs) != len(attributes) or any(name not in SVG_ATTRIBUTES[tag] for name in attrs):
            raise ValueError("内嵌 SVG 含可能读取其他资源的属性")
        if tag == "svg":
            if self.seen_svg or attrs.get("xmlns") != SVG_NAMESPACE:
                raise ValueError("内嵌 SVG 图片格式无效")
            self.seen_svg = True
        for name, value in attrs.items():
            if value is None:
                raise ValueError("内嵌 SVG 含可能读取其他资源的属性")
            if name == "xmlns":
                valid = value == SVG_NAMESPACE
            elif name == "fill":
                valid = SVG_COLOR_RE.fullmatch(value)
            elif name == "viewbox":
                valid = len(value.split()) == 4 and all(SVG_NUMBER_RE.fullmatch(x) for x in value.split())
            elif name == "text-anchor":
                valid = value in {"start", "middle", "end"}
            elif name == "font-family":
                valid = value == "sans-serif"
            else:
                valid = SVG_NUMBER_RE.fullmatch(value)
            if not valid:
                raise ValueError("内嵌 SVG 含可能读取其他资源的属性")

    def handle_starttag(self, tag, attributes):
        self.check_tag(tag, attributes)
        self.stack.append(tag)

    def handle_startendtag(self, tag, attributes):
        self.check_tag(tag, attributes)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise ValueError("内嵌 SVG 图片格式无效")

    def handle_data(self, data):
        if data.strip() and (not self.stack or self.stack[-1] != "text"):
            raise ValueError("内嵌 SVG 图片格式无效")

    def handle_decl(self, _declaration):
        raise ValueError("内嵌 SVG 不允许文档声明")

    def handle_pi(self, _instruction):
        raise ValueError("内嵌 SVG 不允许处理指令")

    def handle_comment(self, _data):
        raise ValueError("内嵌 SVG 不允许注释")

    def unknown_decl(self, _data):
        raise ValueError("内嵌 SVG 不允许未知声明")


def validate_svg(svg):
    """虚构头像只使用基本图形和纯值属性，拒绝一切 SVG 子资源入口。"""
    if "<!" in svg or "<?" in svg:
        raise ValueError("内嵌 SVG 不允许文档声明")
    inspector = InlineSVGInspector()
    inspector.feed(svg)
    inspector.close()
    if not inspector.seen_svg or inspector.stack:
        raise ValueError("内嵌 SVG 图片格式无效")


def validate_data_image(source):
    if not DATA_IMAGE_RE.match(source):
        raise ValueError("网页图片必须内嵌为 data URI，不能读取其他文件或网络资源")
    if not source.lower().startswith("data:image/svg+xml"):
        try:
            base64.b64decode(source.split(",", 1)[1], validate=True)
        except binascii.Error:
            raise ValueError("内嵌图片格式无效") from None
        return
    header, payload = source.split(",", 1)
    try:
        raw = (base64.b64decode(payload, validate=True) if header.lower().endswith(";base64")
               else unquote_to_bytes(payload))
        if len(raw) > 200 * 1024:
            raise ValueError("内嵌 SVG 头像过大")
        svg = raw.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError("内嵌 SVG 图片格式无效") from None
    if "<!" in svg or "<?" in svg:
        raise ValueError("内嵌 SVG 不允许文档声明")
    validate_svg(svg)


def template_style():
    """用 Skill 自带模板的固定 CSS，不解释任意生成的 CSS 表达式。"""
    template = Path(__file__).resolve().parents[1] / "templates" / "manual.html"
    html = template.read_text(encoding="utf-8")
    styles = re.findall(r"<style>(.*?)</style>", html, flags=re.S | re.I)
    if len(styles) != 1:
        raise ValueError("Skill 网页模板样式不完整")
    return styles[0]


class OfflineHTMLInspector(HTMLParser):
    """按标签、属性和固定模板 CSS 许可，阻断所有子资源入口。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_style = False
        self.style_parts = []
        self.style_count = 0
        self.expected_style = template_style()

    def handle_starttag(self, tag, attributes):
        if tag not in HTML_TAGS:
            raise ValueError(f"网页含不能离线打印的 <{tag}> 元素")
        if len(attributes) != len({name for name, _ in attributes}):
            raise ValueError("网页含重复属性")
        attrs = dict(attributes)
        allowed = GLOBAL_ATTRIBUTES | TAG_ATTRIBUTES.get(tag, frozenset())
        if any(name not in allowed for name in attrs):
            raise ValueError("网页含可能读取其他资源的属性")
        if "data-pdf-name" in attrs:
            if (tag != "button" or attrs.get("id") != "print-button" or
                    not valid_pdf_name(attrs["data-pdf-name"])):
                raise ValueError("PDF 标记只能是分享按钮上的同目录文件名")
        if tag == "meta":
            if "http-equiv" in attrs and (attrs["http-equiv"] or "").lower() != "content-security-policy":
                raise ValueError("网页含不允许的元信息")
            if "name" in attrs and (attrs["name"] or "").lower() != "viewport":
                raise ValueError("网页含不允许的元信息")
            if "charset" in attrs and (attrs["charset"] or "").lower() != "utf-8":
                raise ValueError("网页含不允许的元信息")
        if tag == "img":
            source = attrs.get("src") or ""
            validate_data_image(source)
        if tag == "a" and "href" in attrs:
            href = attrs["href"] or ""
            parsed = urlsplit(href)
            if (any(ord(char) < 32 or ord(char) == 127 for char in href) or
                    not (href.startswith("#") or parsed.scheme.lower() in {"http", "https"}) or
                    href.startswith("//")):
                raise ValueError("网页链接只允许 http(s) 原文或页内锚点")
        if tag == "style":
            if self.in_style or self.style_count:
                raise ValueError("网页只能使用模板中的单个固定样式块")
            self.in_style = True
            self.style_count += 1

    def handle_endtag(self, tag):
        if tag == "style":
            style = "".join(self.style_parts)
            if (style != self.expected_style and
                    hashlib.sha256(style.encode("utf-8")).hexdigest() not in PREVIOUS_TEMPLATE_STYLE_SHA256):
                raise ValueError("网页样式必须与 Skill 模板一致")
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.style_parts.append(data)

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)

    def handle_decl(self, declaration):
        if declaration.lower() != "doctype html":
            raise ValueError("网页含不允许的文档声明")

    def handle_pi(self, _instruction):
        raise ValueError("网页含不允许的处理指令")

    def handle_comment(self, _data):
        if self.in_style:
            raise ValueError("网页样式必须与 Skill 模板一致")

    def unknown_decl(self, _data):
        raise ValueError("网页含不允许的文档声明")

    def finish(self):
        self.close()
        if self.in_style or self.style_count != 1:
            raise ValueError("网页必须使用模板中的单个固定样式块")


def validate_html(html_file, output_dir):
    """先解析真实路径，再做有界读取和单文件资源检查。"""
    try:
        output_dir = Path(output_dir).resolve(strict=True)
        html_file = Path(html_file).resolve(strict=True)
    except OSError:
        raise ValueError("手册输出目录或网页文件不存在") from None
    if not output_dir.is_dir():
        raise ValueError("--out-dir 不是目录")
    if not html_file.is_file() or html_file.suffix.lower() != ".html":
        raise ValueError("输入必须是存在的 HTML 文件")
    if not html_file.is_relative_to(output_dir):
        raise ValueError("网页路径越出手册输出目录")
    if html_file.stat().st_size > MAX_HTML_BYTES:
        raise ValueError("网页文件过大")
    with html_file.open("rb") as source:
        raw = source.read(MAX_HTML_BYTES + 1)
    if len(raw) > MAX_HTML_BYTES:
        raise ValueError("网页文件过大")
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("网页必须是 UTF-8 编码") from None
    inspector = OfflineHTMLInspector()
    inspector.feed(html)
    inspector.finish()
    return html_file, raw


class PrintDirectoryInspector(HTMLParser):
    """从正文顶层块抽取与网页侧边目录相同的标题和锚点。"""

    VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
                           "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.current = None
        self.capture_depth = None
        self.parts = []
        self.entries = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        parent = self.stack[-1] if self.stack else None
        if (tag == "details" and "manual-section" in (attrs.get("class") or "").split()
                and parent and parent[0] == "div" and parent[1].get("id") == "sections"):
            self.current = ("chapter", attrs.get("id"), len(self.stack))
        elif tag == "section" and attrs.get("id") in {"overview", "sources"}:
            self.current = ("other", attrs["id"], len(self.stack))
        self.stack.append((tag, attrs))
        if self.current and self.capture_depth is None:
            kind = self.current[0]
            if ((kind == "chapter" and tag == "span" and
                 "section-title" in (attrs.get("class") or "").split() and
                 any(parent_tag == "summary" for parent_tag, _ in self.stack[self.current[2]:-1])) or
                (kind == "other" and tag == "h2" and len(self.stack) == self.current[2] + 2)):
                self.capture_depth = len(self.stack)
                self.parts = []
        if tag in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.capture_depth is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if not self.stack:
            return
        if self.capture_depth == len(self.stack):
            title = "".join(self.parts).strip()
            if title and self.current and not any(item[0] == self.current[1] for item in self.entries):
                self.entries.append((self.current[1], title, self.current[0]))
            self.capture_depth = None
        if self.current and self.current[2] == len(self.stack) - 1:
            self.current = None
        self.stack.pop()

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)
        if tag not in self.VOID_TAGS:
            self.handle_endtag(tag)


def prepare_print_html(html_bytes):
    """仅改已通过离线校验的浏览器临时副本；目录链接只取原文现有锚点。"""
    html = html_bytes.decode("utf-8")
    # --disable-javascript 在部分 Chrome 上被忽略；额外的 CSP 仅作用于打印副本。
    html = re.sub(r"<head(?:\s[^>]*)?>", lambda match: match.group(0) +
                  "\n<meta http-equiv=\"Content-Security-Policy\" content=\"script-src 'none'\">",
                  html, count=1, flags=re.I)
    if html.count(PRINT_TOC_EMPTY) != 1:
        # 旧版手册仍允许导出，其原有页面未声明打印目录。
        return html.encode("utf-8")
    inspector = PrintDirectoryInspector()
    inspector.feed(html)
    inspector.close()
    links = "".join(f'<li><a href="#{escape(identifier, quote=True)}">{escape(title)}</a></li>'
                    for identifier, title, _ in inspector.entries)
    html = html.replace(PRINT_TOC_EMPTY,
                        f'<ol class="print-toc-list" id="print-toc-list">{links}</ol>', 1)
    # Chrome 的大纲只认语义标题：将章节 summary 的标题升级为 h2，避免正文 h3 入大纲。
    html = re.sub(r'(<summary>\s*)<span class="section-title">(.*?)</span>(\s*</summary>)',
                  r'\1<h2 class="section-title">\2</h2>\3', html, flags=re.S)
    # 保留视觉层级，但只把书级标题、导言、每章、来源写进 PDF 书签。
    def flatten_minor_headings(match, keep_first_h2=False):
        heading_seen = False
        def replace_heading(heading):
            nonlocal heading_seen
            level, attrs, content = heading.groups()
            if level == "2" and 'class="section-title"' in attrs:
                return heading.group(0)
            if level == "2" and keep_first_h2 and not heading_seen:
                heading_seen = True
                return heading.group(0)
            return f'<div data-pdf-heading="{level}"{attrs}>{content}</div>'
        body = re.sub(r'<h([2-6])\b([^>]*)>(.*?)</h\1>', replace_heading,
                      match.group(2), flags=re.S | re.I)
        return match.group(1) + body + match.group(3)

    for section, keep_first in (("INTRO", True), ("SECTIONS", False), ("SOURCES", True)):
        pattern = rf'(<!-- {section}_HTML_START.*?-->)(.*?)(<!-- {section}_HTML_END -->)'
        html = re.sub(pattern, lambda match: flatten_minor_headings(match, keep_first),
                      html, count=1, flags=re.S)
    return html.encode("utf-8")


def mark_exported_pdf(html_file, original_html, pdf_name):
    """只替换模板分享按钮的固定标记；旧网页无标记时仍可导出。"""
    matches = list(PDF_MARKER_RE.finditer(original_html))
    if not matches:
        return False
    if len(matches) != 1 or not valid_pdf_name(pdf_name):
        raise RuntimeError("PDF 已生成，但网页分享标记无效")
    if html_file.read_bytes() != original_html:
        raise RuntimeError("PDF 已生成，但网页在导出期间发生变化，未回写分享标记")
    match = matches[0]
    encoded = escape(pdf_name, quote=True).encode("utf-8")
    updated = original_html[:match.start(2)] + encoded + original_html[match.end(2):]
    if updated == original_html:
        return True
    descriptor, temporary = tempfile.mkstemp(prefix=".manual-html-", dir=html_file.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(updated)
        os.chmod(temporary, stat.S_IMODE(html_file.stat().st_mode))
        os.replace(temporary, html_file)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def browser_candidates():
    """先看常见安装位置，再查 PATH；调用方也可用 --browser 明确指定。"""
    if sys.platform == "darwin":
        app_names = (
            "Google Chrome.app/Contents/MacOS/Google Chrome",
            "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "Chromium.app/Contents/MacOS/Chromium",
        )
        for base in (Path("/Applications"), Path.home() / "Applications"):
            for name in app_names:
                yield base / name
    elif os.name == "nt":
        bases = [Path(os.environ[key]) for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")
                 if os.environ.get(key)]
        for base in bases:
            for name in ("Google/Chrome/Application/chrome.exe",
                         "Microsoft/Edge/Application/msedge.exe",
                         "Chromium/Application/chrome.exe"):
                yield base / name
    else:
        for name in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
                     "/usr/bin/microsoft-edge", "/opt/google/chrome/chrome",
                     "/opt/microsoft/msedge/msedge"):
            yield Path(name)
    for name in ("google-chrome", "google-chrome-stable", "chrome", "msedge",
                 "microsoft-edge", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            yield Path(found)


def find_browser(explicit=None):
    for candidate in ([Path(explicit)] if explicit else browser_candidates()):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def browser_arguments(browser, html_file, pdf_file, profile, document_outline=True):
    arguments = [
        str(browser),
        "--headless",
        "--disable-gpu",
        "--disable-javascript",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-extensions",
        "--disable-sync",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-proxy-server",
        "--host-resolver-rules=MAP * ~NOTFOUND",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        *(["--generate-pdf-document-outline"] if document_outline else []),
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf_file}",
        html_file.as_uri(),
    ]
    return arguments


def pdf_complete(path):
    """只在 PDF 已封尾时判断完成；配合大小稳定时间避免读到写入中间态。"""
    try:
        with path.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                return False
            stream.seek(max(0, path.stat().st_size - 2048))
            return b"%%EOF" in stream.read()
    except OSError:
        return False


class WindowsBrowserJob:
    """Windows Job Object 保存整棵浏览器进程树，包括已退出的启动进程的子进程。"""

    def __init__(self):
        import ctypes

        self.ctypes = ctypes
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p)
        self.kernel.CreateJobObjectW.restype = ctypes.c_void_p
        self.kernel.AssignProcessToJobObject.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        self.kernel.AssignProcessToJobObject.restype = ctypes.c_int
        self.kernel.TerminateJobObject.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        self.kernel.TerminateJobObject.restype = ctypes.c_int
        self.kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
        self.kernel.CloseHandle.restype = ctypes.c_int
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process):
        if not self.kernel.AssignProcessToJobObject(self.handle, process._handle):
            raise self.ctypes.WinError(self.ctypes.get_last_error())

    def terminate(self):
        if not self.kernel.TerminateJobObject(self.handle, 1):
            raise self.ctypes.WinError(self.ctypes.get_last_error())

    def close(self):
        self.kernel.CloseHandle(self.handle)


def stop_browser(process):
    """即使主进程已退出，也有界清理本次独立进程组的后代。"""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                os.killpg(process.pid, 0)
            except (ProcessLookupError, PermissionError):
                break
            time.sleep(0.05)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        process.wait(timeout=3)


def run_browser(arguments, timeout, pdf_file, stderr=None):
    options = {"stdout": subprocess.DEVNULL, "stderr": stderr or subprocess.DEVNULL,
               "start_new_session": os.name != "nt"}
    job = None
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        # 包装进程等待加入 Job 后才启动浏览器，消除主进程过快退出的登记竞态。
        wrapper = ("import subprocess,sys; sys.stdin.buffer.read(1); "
                   "sys.exit(subprocess.run(sys.argv[1:], stdin=subprocess.DEVNULL).returncode)")
        options["stdin"] = subprocess.PIPE
        process = subprocess.Popen([sys.executable, "-c", wrapper, *arguments], **options)
        try:
            job = WindowsBrowserJob()
            job.assign(process)
            process.stdin.write(b"1")
            process.stdin.close()
        except BaseException:
            try:
                if job is not None:
                    job.terminate()
            finally:
                try:
                    stop_browser(process)
                finally:
                    if job is not None:
                        job.close()
            raise
    else:
        process = subprocess.Popen(arguments, **options)
    deadline = time.monotonic() + timeout
    last_size = -1
    stable_since = None
    try:
        while True:
            result = process.poll()
            if result is not None:
                return result
            now = time.monotonic()
            try:
                size = pdf_file.stat().st_size
            except FileNotFoundError:
                size = -1
            if size != last_size:
                last_size = size
                stable_since = now
            elif size > 0 and stable_since is not None and now - stable_since >= 1.0:
                if pdf_complete(pdf_file):
                    return 0
            if now >= deadline:
                raise subprocess.TimeoutExpired(arguments, timeout)
            time.sleep(min(0.2, deadline - now))
    finally:
        try:
            if job is not None:
                job.terminate()
        finally:
            try:
                stop_browser(process)
            finally:
                if job is not None:
                    job.close()


def export_pdf(html_file, output_dir, output_name=None, overwrite=False,
               timeout=60, browser=None):
    html_file, html_bytes = validate_html(html_file, output_dir)
    if output_name is None:
        output_name = html_file.with_suffix(".pdf").name
    if not output_name or not valid_pdf_name(output_name):
        raise ValueError("--output 必须是同目录中的 PDF 文件名")
    destination = html_file.parent / output_name
    if destination.exists() or destination.is_symlink():
        if not overwrite:
            raise ValueError("PDF 已存在；仅在明确指定 --overwrite 时覆盖")
    selected_browser = find_browser(browser)
    if selected_browser is None:
        raise FileNotFoundError("找不到可执行的 Chrome、Edge 或 Chromium")
    with tempfile.TemporaryDirectory(prefix="manual-pdf-input-") as private_dir, \
         tempfile.TemporaryDirectory(prefix=".manual-pdf-", dir=html_file.parent) as pdf_dir:
        temporary_html = Path(private_dir) / "manual.html"
        temporary_html.write_bytes(prepare_print_html(html_bytes))
        temporary_pdf = Path(pdf_dir) / "manual.pdf"
        profile = Path(private_dir) / "browser-profile"
        arguments = browser_arguments(selected_browser, temporary_html, temporary_pdf, profile)
        errors = Path(private_dir) / "browser.stderr"
        with errors.open("wb") as stderr:
            result = run_browser(arguments, timeout, temporary_pdf, stderr)
        if result != 0 and not temporary_pdf.exists() and UNSUPPORTED_OUTLINE_RE.search(
                errors.read_text(encoding="utf-8", errors="replace")):
            # 某些旧版浏览器拒绝未知开关；仅在明确点名该开关时降级。
            fallback = browser_arguments(selected_browser, temporary_html, temporary_pdf,
                                         Path(private_dir) / "fallback-profile", document_outline=False)
            result = run_browser(fallback, timeout, temporary_pdf)
        if result != 0 or not temporary_pdf.is_file():
            raise RuntimeError(f"浏览器导出失败（退出码 {result}）")
        if not pdf_complete(temporary_pdf):
            raise RuntimeError("浏览器没有生成完整的 PDF")
        if overwrite:
            os.replace(temporary_pdf, destination)
        else:
            try:
                os.link(temporary_pdf, destination)
            except FileExistsError:
                raise ValueError("PDF 已存在；仅在明确指定 --overwrite 时覆盖") from None
    mark_exported_pdf(html_file, html_bytes, destination.name)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", help="待导出的离线单文件手册 HTML")
    parser.add_argument("--out-dir", required=True, help="手册输出目录（用于限制 HTML 真实路径）")
    parser.add_argument("--output", help="同目录的 PDF 文件名，默认与 HTML 同名")
    parser.add_argument("--overwrite", action="store_true", help="明确允许覆盖已有 PDF")
    parser.add_argument("--timeout", type=int, default=60, help="浏览器超时秒数，默认 60")
    parser.add_argument("--browser", help="明确指定 Chrome、Edge 或 Chromium 可执行文件")
    args = parser.parse_args(argv)
    if args.timeout < 1 or args.timeout > 600:
        print("输入错误：--timeout 必须为 1 至 600 秒", file=sys.stderr)
        return 2
    try:
        destination = export_pdf(args.html, args.out_dir, args.output,
                                 args.overwrite, args.timeout, args.browser)
    except FileNotFoundError as exc:
        print(f"浏览器不可用：{exc}。请保留网页，用“分享”按钮手动导出；交付说明写“PDF 未自动生成”。",
              file=sys.stderr)
        return 3
    except ValueError as exc:
        print(f"输入错误：{exc}。请保留网页，用“分享”按钮手动导出；交付说明写“PDF 未自动生成”。",
              file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired:
        print("PDF 导出超时。请保留网页，用“分享”按钮手动导出；交付说明写“PDF 未自动生成”。",
              file=sys.stderr)
        return 5
    except (RuntimeError, OSError) as exc:
        print(f"PDF 导出失败：{exc}。请保留网页，用“分享”按钮手动导出；交付说明写“PDF 未自动生成”。",
              file=sys.stderr)
        return 4
    print(f"PDF 已生成：{destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
