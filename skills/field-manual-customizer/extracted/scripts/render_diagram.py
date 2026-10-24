#!/usr/bin/env python3
"""把已画好的纯 SVG 教学示意图用本机 Chrome/Edge/Chromium 转成同目录 PNG。

用法：python3 scripts/render_diagram.py <手册目录>/images/路线.svg --out-dir <手册目录>
默认以 2 倍像素导出；1200 像素宽的画布得到 2400 像素宽 PNG，在约 8 英寸
打印宽度下约为 300 dpi。只接受基本图形和文字，不读取 SVG 内的其他资源。
退出码：0 成功，2 输入无效，3 无浏览器，4 截图失败，5 超时。
"""

import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path

from export_pdf import find_browser, stop_browser
from fetch_images import MAX_IMAGE_BYTES


SVG_NS = "http://www.w3.org/2000/svg"
TAGS = {"svg", "g", "rect", "line", "circle", "ellipse", "polygon", "polyline", "text"}
ATTRS = {
    "svg": {"width", "height", "viewBox"},
    "g": {"fill", "stroke", "stroke-width"},
    "rect": {"x", "y", "width", "height", "rx", "fill", "stroke", "stroke-width"},
    "line": {"x1", "y1", "x2", "y2", "stroke", "stroke-width", "stroke-linecap"},
    "circle": {"cx", "cy", "r", "fill", "stroke", "stroke-width"},
    "ellipse": {"cx", "cy", "rx", "ry", "fill", "stroke", "stroke-width"},
    "polygon": {"points", "fill", "stroke", "stroke-width"},
    "polyline": {"points", "fill", "stroke", "stroke-width"},
    "text": {"x", "y", "fill", "font-family", "font-size", "font-weight", "text-anchor"},
}
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)")
POINTS = re.compile(r"[\d\s.,+\-]+")
COLOR = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|none")


class SVGInspector(HTMLParser):
    """只接受纯图形/文字标签和无资源引用的属性；不依赖系统 expat。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.seen_root = False
        self.width = None
        self.height = None

    def inspect_tag(self, tag, attributes):
        if tag not in TAGS or len(attributes) != len({key for key, _ in attributes}):
            raise ValueError("SVG 含不支持的元素或重复属性")
        attrs = dict(attributes)
        if tag == "svg":
            if self.stack or self.seen_root or attrs.get("xmlns") != SVG_NS:
                raise ValueError("输入必须是单个标准 SVG 图形")
            self.seen_root = True
            try:
                self.width = int(attrs["width"])
                self.height = int(attrs["height"])
            except (KeyError, ValueError):
                raise ValueError("SVG 须写整数 width 与 height") from None
            if not (1000 <= self.width <= 1800 and 500 <= self.height <= 1200):
                raise ValueError("SVG 画布须在 1000–1800 × 500–1200 像素范围内")
            if attrs.get("viewbox") != f"0 0 {self.width} {self.height}":
                raise ValueError("SVG viewBox 须与画布尺寸一致")
            allowed = ATTRS[tag] | {"xmlns", "viewbox"}
        else:
            if not self.stack:
                raise ValueError("SVG 图形元素必须位于画布内")
            allowed = ATTRS[tag]
        if any(name not in allowed for name in attrs):
            raise ValueError("SVG 含可能加载资源的属性")
        for name, value in attrs.items():
            if name in {"width", "height", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy",
                        "r", "rx", "ry", "stroke-width", "font-size"}:
                valid = NUMBER.fullmatch(value)
            elif name == "points":
                valid = POINTS.fullmatch(value) and len(value) <= 4096
            elif name in {"fill", "stroke"}:
                valid = COLOR.fullmatch(value)
            elif name == "viewbox":
                valid = value == f"0 0 {self.width} {self.height}"
            elif name == "xmlns":
                valid = value == SVG_NS
            elif name == "font-family":
                valid = value == "sans-serif"
            elif name == "font-weight":
                valid = value in {"normal", "bold"}
            elif name == "text-anchor":
                valid = value in {"start", "middle", "end"}
            elif name == "stroke-linecap":
                valid = value in {"butt", "round", "square"}
            else:
                valid = False
            if not valid:
                raise ValueError("SVG 属性值无效或可能加载资源")

    def handle_starttag(self, tag, attributes):
        self.inspect_tag(tag, attributes)
        self.stack.append(tag)

    def handle_startendtag(self, tag, attributes):
        self.inspect_tag(tag, attributes)
        if tag == "svg":
            raise ValueError("SVG 画布不能为空")

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise ValueError("SVG 标签结构无效")

    def handle_data(self, data):
        if data.strip() and (not self.stack or self.stack[-1] != "text"):
            raise ValueError("图形元素不能含未标记文本")

    def handle_decl(self, _declaration):
        raise ValueError("SVG 不允许文档声明")

    def handle_pi(self, _instruction):
        raise ValueError("SVG 不允许处理指令")

    def handle_comment(self, _data):
        raise ValueError("SVG 不允许注释")

    def unknown_decl(self, _data):
        raise ValueError("SVG 不允许未知声明")


def validate_svg(data):
    if len(data) > 1024 * 1024 or b"<!" in data or b"<?" in data:
        raise ValueError("示意图须为 1 MiB 以内、不含声明或外部资源的纯 SVG")
    try:
        svg = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("SVG 须为 UTF-8 文本") from None
    inspector = SVGInspector()
    inspector.feed(svg)
    inspector.close()
    if inspector.stack or not inspector.seen_root:
        raise ValueError("SVG 标签结构无效")
    return inspector.width, inspector.height


def png_dimensions(path):
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or not header.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR"):
        raise RuntimeError("浏览器未生成 PNG 图片")
    return struct.unpack(">II", header[16:24])


def png_complete(path):
    try:
        with path.open("rb") as stream:
            stream.seek(-12, os.SEEK_END)
            return stream.read() == b"\x00\x00\x00\x00IEND\xaeB`\x82"
    except (OSError, ValueError):
        return False


def render(source, output_dir, overwrite=False, timeout=40, browser=None):
    try:
        root = Path(output_dir).resolve(strict=True)
        svg_file = Path(source).resolve(strict=True)
    except OSError:
        raise ValueError("手册目录或 SVG 不存在") from None
    images = root / "images"
    if not root.is_dir() or not svg_file.is_file() or svg_file.suffix.lower() != ".svg":
        raise ValueError("输入须为手册 images/ 中的 SVG 文件")
    if not svg_file.is_relative_to(images):
        raise ValueError("SVG 路径须位于手册 images/ 内")
    data = svg_file.read_bytes()
    width, height = validate_svg(data)
    destination = svg_file.with_suffix(".png")
    if (destination.exists() or destination.is_symlink()) and not overwrite:
        raise ValueError("PNG 已存在；仅在明确指定 --overwrite 时覆盖")
    selected_browser = find_browser(browser)
    if selected_browser is None:
        raise FileNotFoundError("找不到可执行的 Chrome、Edge 或 Chromium")
    with tempfile.TemporaryDirectory(prefix="manual-diagram-") as directory:
        private = Path(directory)
        private_svg = private / "diagram.svg"
        private_png = private / "diagram.png"
        private_svg.write_bytes(data)
        arguments = [
            str(selected_browser), "--headless", "--disable-gpu", "--disable-javascript",
            "--disable-background-networking", "--disable-component-update", "--disable-extensions",
            "--disable-sync", "--no-first-run", "--no-default-browser-check", "--no-proxy-server",
            "--host-resolver-rules=MAP * ~NOTFOUND", f"--user-data-dir={private / 'profile'}",
            f"--window-size={width},{height}", "--force-device-scale-factor=2",
            f"--screenshot={private_png}", private_svg.as_uri(),
        ]
        options = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                   "start_new_session": os.name != "nt"}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        process = subprocess.Popen(arguments, **options)
        try:
            deadline = time.monotonic() + timeout
            while not (private_png.is_file() and png_complete(private_png)):
                result = process.poll()
                if result is not None:
                    raise RuntimeError(f"浏览器未生成截图（退出码 {result}）")
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(arguments, timeout)
                time.sleep(0.1)
            if private_png.stat().st_size > MAX_IMAGE_BYTES:
                raise RuntimeError("PNG 超过单图 20 MiB 上限")
            if png_dimensions(private_png) != (width * 2, height * 2):
                raise RuntimeError("PNG 实际尺寸与 2 倍画布尺寸不一致")
        finally:
            stop_browser(process)
        descriptor, temporary = tempfile.mkstemp(prefix=".manual-diagram-", suffix=".png",
                                                  dir=svg_file.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream, private_png.open("rb") as source_png:
                shutil.copyfileobj(source_png, stream)
            if overwrite:
                os.replace(temporary, destination)
            else:
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    raise ValueError("PNG 已存在；仅在明确指定 --overwrite 时覆盖") from None
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return destination, (width * 2, height * 2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="手册 images/ 内已画好的纯 SVG")
    parser.add_argument("--out-dir", required=True, help="手册输出目录")
    parser.add_argument("--browser", help="明确指定本机浏览器可执行文件")
    parser.add_argument("--timeout", type=int, default=40)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 180:
        print("输入错误：--timeout 须为 1–180 秒", file=sys.stderr)
        return 2
    try:
        output, size = render(args.source, args.out_dir, args.overwrite, args.timeout, args.browser)
    except ValueError as exc:
        print(f"输入错误：{exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"浏览器不可用：{exc}", file=sys.stderr)
        return 3
    except subprocess.TimeoutExpired:
        print("示意图转换超时", file=sys.stderr)
        return 5
    except (RuntimeError, OSError) as exc:
        print(f"示意图转换失败：{exc}", file=sys.stderr)
        return 4
    print(f"PNG 已生成：{output}（{size[0]}×{size[1]}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
