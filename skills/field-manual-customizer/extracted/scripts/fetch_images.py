#!/usr/bin/env python3
"""下载航海手册和站内帖子里的截图，核对数量，生成对应表。只用 Python 标准库。

输入文件按内容自动识别，四种都行：

1. topicDetail 返回的 JSON（整个存下来，至少含 imageList 和正文字段）
     python3 scripts/fetch_images.py post_22258822155441551.json --out images --prefix p2225

2. activityManualDetail(format="markdown") 返回的正文（存成 .md），或整个返回 JSON
     python3 scripts/fetch_images.py manual_9625_9872.md --out images --prefix m9872

3. 自己写的下载清单，两种写法：
   - 纯文本，一行一个链接，链接后面可以空一格写图注
       https://...签名链接...  开店第一步的入口
   - JSON：{"images": ["https://...", {"url": "https://...", "name": "shop_01", "note": "开店第一步"}],
            "expected_count": 12}
     expected_count 可选：把一篇帖子的图全下载时，填正文里数出来的图片占位个数，用来核对。
     只下载其中几张时不要填，否则一定报「对不上」。

4. 客户端把接口返回存成的文件（有的客户端在返回太长时会存盘，并告诉你文件路径）。
   外面包了一层 [{"type": "text", "text": "..."}] 也能认，直接传进来。

接口返回只在对话里、没有存成文件时，只把准备用的那几张图的链接抄进清单（第 3 种），
不要把整章正文或几十个签名链接全抄一遍：链接很长，抄得越多越容易错。

输出：
- 图片：<prefix>_01.<扩展名> ……（清单里给了 name 的用 name）
- 对应表：<out>/<prefix>_map.json，记录序号、占位名（帖子）、图片前面那段文字（手册）、去掉 query 的链接、文件名、尺寸、
  是否成功、是否像装饰分隔线

默认只允许 HTTPS 的 search01.shengcaiyoushu.com。其他来源须先核对原资料，
再用 --allow-host 精确追加主机名；不接受跳转、IP 地址或内网解析结果。
图片和对应表均不会覆盖已有文件；新建输出目录设为 0700，已有目录不改权限。
下载直连已校验的公网 IP，TLS 仍按原域名验证；不使用环境中的 HTTPS 代理。

退出码：全部成功为 0；有下载失败为 1；输入里找不到图片为 2。
"""
import argparse
import http.client
import html
import ipaddress
import json
import os
import re
import socket
import ssl
import stat
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

# 帖子正文里图片的位置是一个单独的文件名，写法很多：7prIiZPJ.webp、image.png、083fb8ce…e5.jpg、
# ScreenShot_2026-04-15_155337_790.png、微信图片_xxx.jpg、001.png。链接里的文件名（前面是 / 或 %2F）不算。
PLACEHOLDER_RE = re.compile(
    r"(?<![A-Za-z0-9/._%-])[A-Za-z0-9]{8}\.webp(?![A-Za-z0-9])"  # 星球帖的 8 位占位，常紧挨着汉字
    r"|(?<![\w/.%-])[\w\-（）()]+?\.(?:png|jpe?g|webp|gif|bmp|heic)(?![A-Za-z0-9_.])",
    re.I)
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\((\S+?)\)")
IMG_TAG_RE = re.compile(r"<img[^>]+?src=[\"']([^\"']+)[\"'][^>]*>", re.I)  # 整个标签都吃掉，图注不带残留的 />
EXPIRES_RE = re.compile(r"[?&](?:amp;)?Expires=(\d+)")
SAFE_STEM_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
HOST_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+\Z")
DEFAULT_HOSTS = frozenset({"search01.shengcaiyoushu.com"})
MAX_IMAGE_BYTES = 20 * 1024 * 1024
# expected_count 是一篇帖子的图片占位数量；千张已远超一篇手册/帖子，拒绝异常输入。
MAX_EXPECTED_COUNT = 1000


@dataclass(frozen=True)
class PinnedTarget:
    host: str
    family: int
    protocol: int
    address: tuple


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("图片地址发生跳转；请核对目标后重新取得直链")


def safe_stem(value, label):
    if not isinstance(value, str) or not SAFE_STEM_RE.fullmatch(value):
        raise ValueError(f"{label} 只能由 ASCII 字母、数字、下划线和连字符组成，最长 80 字符")
    return value


def trusted_host(value):
    if not isinstance(value, str) or not HOST_RE.fullmatch(value) or len(value) > 253:
        raise ValueError("--allow-host 必须是完整域名，不含协议、端口、路径或通配符")
    return value.lower()


def validated_target(url, allowed_hosts, resolver=socket.getaddrinfo):
    if not isinstance(url, str):
        raise ValueError("图片地址不是字符串")
    if re.search(r"[\x00-\x20\x7f]", url):
        raise ValueError("图片地址包含空白或控制字符")
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError:
        raise ValueError("图片地址格式无效") from None
    if (parts.scheme.lower() != "https" or not host or port not in (None, 443)
            or parts.username is not None or parts.password is not None
            or host.lower() not in allowed_hosts or not parts.path.startswith("/")):
        raise ValueError("图片地址必须是可信主机上的 HTTPS 直链（端口 443）")
    if not HOST_RE.fullmatch(host) or len(host) > 253:
        raise ValueError("图片地址主机名无效")
    try:
        addresses = resolver(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        raise ValueError("图片地址域名解析失败") from None
    if not addresses:
        raise ValueError("图片地址域名没有解析结果")
    first = None
    for entry in addresses:
        try:
            address = ipaddress.ip_address(entry[4][0])
        except (ValueError, IndexError, TypeError):
            raise ValueError("图片地址域名解析结果无效") from None
        if not address.is_global:
            raise ValueError("图片地址解析到了非公网地址")
        family = socket.AF_INET if address.version == 4 else socket.AF_INET6
        if entry[0] != family or entry[1] != socket.SOCK_STREAM:
            raise ValueError("图片地址域名解析结果无效")
        if first is None:
            sockaddr = (str(address), 443) if family == socket.AF_INET else (str(address), 443, 0, 0)
            first = PinnedTarget(host.lower(), family, entry[2], sockaddr)
    return first


def validate_url(url, allowed_hosts, resolver=socket.getaddrinfo):
    """保留原有的 URL 校验接口；下载时直接复用同次校验得到的地址。"""
    validated_target(url, allowed_hosts, resolver=resolver)
    return url


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """用数值 IP 建连，原始域名只用于 HTTP Host、TLS SNI 与证书校验。"""

    def __init__(self, host, target, **kwargs):
        super().__init__(host, **kwargs)
        self.target = target

    def connect(self):
        if self.host.lower() != self.target.host or self.port != 443 or self._tunnel_host:
            raise ValueError("图片连接目标与已校验域名不一致")
        sock = socket.socket(self.target.family, socket.SOCK_STREAM, self.target.protocol)
        try:
            sock.settimeout(self.timeout)
            if self.source_address:
                sock.bind(self.source_address)
            sock.connect(self.target.address)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.target.host)
        except Exception:
            sock.close()
            raise


class PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, target):
        super().__init__(context=ssl.create_default_context())
        self.target = target

    def https_open(self, request):
        return self.do_open(
            lambda host, **kwargs: PinnedHTTPSConnection(host, self.target, **kwargs),
            request, context=self._context,
        )


def public_url(url):
    """映射表与控制台仅保留定位路径，不保存短期签名 query。"""
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        netloc = host if parts.port is None else f"{host}:{parts.port}"
        return urlunsplit((parts.scheme, netloc, parts.path, "", ""))
    except (TypeError, ValueError):
        return "[invalid URL]"


def public_note(note):
    if not isinstance(note, str):
        return ""
    return re.sub(r"https?://[^\s<>\"']+", lambda m: public_url(m.group(0)), note)


def destination(out, name):
    """即使父目录有 symlink，也验证最终文件仍在已解析的输出目录内。"""
    target = out / name
    if target.resolve(strict=False).parent != out.resolve(strict=True):
        raise ValueError("目标文件不在输出目录内")
    return target


def write_new(target, data):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
    except Exception:
        target.unlink(missing_ok=True)
        raise


def sniff_ext(data: bytes) -> str:
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[:4] in (b"GIF8",):
        return ".gif"
    return ".bin"


def supported_image(data: bytes):
    """只接受能识别格式且宽高均有效的图片，不把错误页当作下载成功。"""
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("图片响应体超过 20 MiB 上限")
    extension = sniff_ext(data)
    size = image_size(data)
    if extension == ".bin" or not size or len(size) != 2 or not all(isinstance(v, int) and v > 0 for v in size):
        raise ValueError("图片格式不支持或尺寸无效")
    return extension, size


def size_label(limit: int) -> str:
    if limit % (1024 * 1024) == 0:
        return f"{limit // (1024 * 1024)} MiB"
    return f"{limit // 1024} KiB"


def image_size(data: bytes):
    """读 PNG、JPEG、GIF、WebP 的宽高，读不出返回 None。"""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        if data[:4] == b"GIF8":
            return int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little")
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            chunk = data[12:16]
            if chunk == b"VP8 ":
                return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                        int.from_bytes(data[28:30], "little") & 0x3FFF)
            if chunk == b"VP8L":
                b = data[21:25]
                return (1 + (b[0] | ((b[1] & 0x3F) << 8)),
                        1 + (((b[1] & 0xC0) >> 6) | (b[2] << 2) | ((b[3] & 0x0F) << 10)))
            if chunk == b"VP8X":
                return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
        if data[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                m = data[i + 1]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
                i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    except Exception:
        pass
    return None


def divider_level(size):
    """strong = 特别扁（如手册的 1280x67 横线），多半是装饰分隔线；
    weak = 有点扁（如 1080x160 的章节横幅，也可能是 699x92 这种一行记录的真截图），打开看一眼再定；None = 不像。"""
    if not size or not size[1]:
        return None
    w, h = size
    if w / h > 10:
        return "strong"
    if h < 150 or w / h > 6:
        return "weak"
    return None


def strip_markup(s: str) -> str:
    s = MD_IMAGE_RE.sub(" ", s)
    s = IMG_TAG_RE.sub(" ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[#>*`\[\]()_|-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def unwrap(data):
    """客户端存盘的接口返回，外面可能包一层 [{"type": "text", "text": "..."}]，拆开。"""
    for _ in range(3):
        blocks = None
        if isinstance(data, list) and data and all(isinstance(b, dict) and "text" in b for b in data):
            blocks = data
        elif (isinstance(data, dict) and isinstance(data.get("content"), list) and data["content"]
              and all(isinstance(b, dict) and "text" in b for b in data["content"])):
            blocks = data["content"]
        if blocks is None:
            return data
        text = "".join(b["text"] for b in blocks)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text
    return data


def short_name(s: str) -> str:
    """「步骤7prIiZPJ.webp」这种紧挨汉字的 8 位占位，只留文件名本身。"""
    m = re.search(r"[A-Za-z0-9]{8}\.webp$", s)
    return m.group(0) if m and not re.search(r"[A-Za-z0-9]$", s[:m.start()]) else s


def notes_before(text: str, spans):
    """每张图前面、上一张图后面的那段文字，用来核对这张图讲的是什么。"""
    notes, prev_end, prev_note = [], 0, ""
    for start, end in spans:
        between = strip_markup(text[prev_end:start])
        note = between[-80:] if between else ("（紧跟上一张图）" + prev_note)[:80]
        notes.append(note)
        prev_end, prev_note = end, note
    return notes


def load_items(path: Path):
    """返回 (items, kind, placeholders)。items 为 [{url, name, note}]。"""
    raw = path.read_text(encoding="utf-8")
    try:
        data = unwrap(json.loads(raw))
    except json.JSONDecodeError:
        data = raw

    # 帖子：topicDetail 返回
    if isinstance(data, dict) and ("topicDTO" in data or "imageList" in data):
        topic = data.get("topicDTO", data)
        if not isinstance(topic, dict):
            raise ValueError("topicDTO 必须是帖子对象")
        urls = topic.get("imageList") or []
        if not isinstance(urls, list):
            raise ValueError("imageList 必须是图片地址列表")
        for f in ("articleContentContainFeishuDoc", "articleContent"):
            if f in topic and not isinstance(topic[f], str):
                raise ValueError(f"{f} 必须是正文字符串")
        # 占位常常只在含飞书长文的那个字段里；两个字段都数，取和 imageList 数量对得上的
        cands = []
        for f in ("articleContentContainFeishuDoc", "articleContent"):
            text = topic.get(f) or ""
            cands.append((text, list(PLACEHOLDER_RE.finditer(text))))
        text, ms = next(((tx, m) for tx, m in cands if m and len(m) == len(urls)),
                        max(cands, key=lambda c: len(c[1])))
        if not urls:
            # imageList 是空的，但正文里嵌着 <img src="…">（公开图），按正文里的位置取
            for f in ("articleContentContainFeishuDoc", "articleContent"):
                body = topic.get(f) or ""
                tags = list(IMG_TAG_RE.finditer(body))
                if tags:
                    notes = notes_before(body, [m.span() for m in tags])
                    return [{"url": m.group(1), "name": None, "note": n} for m, n in zip(tags, notes)], "post", None
        notes = notes_before(text, [m.span() for m in ms]) if len(ms) == len(urls) else [""] * len(urls)
        items = [{"url": u, "name": None, "note": n} for u, n in zip(urls, notes)]
        return items, "post", [short_name(m.group(0)) for m in ms]

    # 自己整理的清单（JSON）
    if isinstance(data, dict) and "images" in data:
        if not isinstance(data["images"], list):
            raise ValueError("images 必须是图片地址或对象组成的列表")
        items = []
        for index, x in enumerate(data["images"], 1):
            if isinstance(x, str):
                items.append({"url": x, "name": None, "note": ""})
            elif isinstance(x, dict):
                items.append({"url": x.get("url", ""), "name": x.get("name"), "note": x.get("note", "")})
            else:
                raise ValueError(f"images 第 {index} 项必须是图片地址字符串或对象")
        exp = data.get("expected_count")
        if exp is not None and (type(exp) is not int or not 0 <= exp <= MAX_EXPECTED_COUNT):
            raise ValueError(f"expected_count 必须是 0 到 {MAX_EXPECTED_COUNT} 的整数")
        return items, "list", exp

    # 手册：返回 JSON 里的 content，或直接是 Markdown 正文
    text = data.get("content", "") if isinstance(data, dict) else str(data)

    # 自己整理的清单（纯文本，一行一个链接）
    if not MD_IMAGE_RE.search(text):
        lines = [l.strip() for l in text.splitlines() if l.strip().startswith(("http://", "https://"))]
        if lines:
            items = []
            for l in lines:
                parts = l.split(None, 1)
                items.append({"url": parts[0], "name": None, "note": parts[1] if len(parts) > 1 else ""})
            return items, "list", None

    ms = list(MD_IMAGE_RE.finditer(text))
    notes = notes_before(text, [m.span() for m in ms])
    items = [{"url": m.group(2), "name": None, "note": n} for m, n in zip(ms, notes)]
    if re.search(r"!\[[^\]]*\]\(https?://\S*$", text.rstrip()):
        print("⚠️ 最后一张图的链接被截断了（分段读取时切在了链接中间）。"
              "把下一段正文接上再提取，或调大 maxChars 一次读完。")
    return items, "manual", None


def download(url: str, allowed_hosts=DEFAULT_HOSTS, retries: int = 2,
             resolver=None, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_IMAGE_BYTES:
        raise ValueError("图片读取上限无效")
    if resolver is None:
        resolver = socket.getaddrinfo
    target = validated_target(url, allowed_hosts, resolver=resolver)
    req = urllib.request.Request(url, headers={"User-Agent": "field-manual-customizer/0.10.1"})
    # 显式空代理配置：即使环境设置 HTTPS_PROXY，也只能直连已校验的数值 IP。
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect(), PinnedHTTPSHandler(target)
    )
    for i in range(retries + 1):
        try:
            with opener.open(req, timeout=30) as response:
                declared = response.headers.get("Content-Length")
                if declared is not None:
                    try:
                        declared_size = int(declared)
                    except ValueError:
                        raise ValueError("图片响应的 Content-Length 无效") from None
                    if declared_size < 0 or declared_size > max_bytes:
                        raise ValueError(f"图片响应声明超过 {size_label(max_bytes)} 上限")
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise ValueError(f"图片响应体超过 {size_label(max_bytes)} 上限")
                return data
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == retries:
                raise ValueError(f"图片请求返回 HTTP {e.code}") from None
        except urllib.error.URLError:
            if i == retries:
                raise ValueError("图片请求失败；请检查链接是否过期或网络连接") from None
        if i < retries:
            time.sleep(1 + i)
    raise RuntimeError("图片请求失败")


def main():
    ap = argparse.ArgumentParser(description="下载手册和帖子截图")
    ap.add_argument("input", help="topicDetail JSON、手册 Markdown/JSON、下载清单（纯文本或 JSON）、客户端存盘的接口返回")
    ap.add_argument("--out", default="images", help="保存目录，默认 images")
    ap.add_argument("--prefix", default="img", help="文件名前缀，默认 img")
    ap.add_argument("--allow-host", action="append", default=[], metavar="HOST",
                    help="核对原资料后追加一个可信的精确域名；可多次使用，不接受通配符")
    ap.add_argument("--dry-run", action="store_true", help="只列出要下载的图片，不下载")
    args = ap.parse_args()
    try:
        safe_stem(args.prefix, "prefix")
        allowed_hosts = DEFAULT_HOSTS | {trusted_host(host) for host in args.allow_host}
    except ValueError as e:
        ap.error(str(e))

    try:
        items, kind, placeholders = load_items(Path(args.input))
    except (TypeError, ValueError) as e:
        ap.error(f"输入内容格式错误：{e}")
    if not items:
        print("输入里没有找到图片地址。")
        if kind == "manual":
            print("手册正文里只有「[图片]」时，说明调用时没传 format=\"markdown\"，或这是旧手册。")
        if kind == "post":
            print("帖子的 imageList 是空的，这篇取不到图，只能用文字。")
        return 2

    try:
        for it in items:
            it["url"] = html.unescape(it["url"])
            if it.get("name") is not None:
                safe_stem(it["name"], "name")
    except (TypeError, ValueError) as e:
        ap.error(str(e))

    print(f"类型：{ {'post': '帖子', 'manual': '手册', 'list': '下载清单'}[kind] }，图片 {len(items)} 张")

    reliable = True
    if placeholders is not None:
        placeholder_count = placeholders if isinstance(placeholders, int) else len(placeholders)
        if placeholder_count == len(items):
            print(f"数量核对：正文占位 {placeholder_count} 个 = 图片地址 {len(items)} 个，可以按顺序对应。")
        else:
            reliable = False
            print(f"⚠️ 数量核对：正文占位 {placeholder_count} 个，图片地址 {len(items)} 个，对不上。"
                  "不要按顺序硬套，配图前逐张打开核对。")

    expires = [int(m.group(1)) for it in items for m in [EXPIRES_RE.search(it["url"])] if m]
    if expires:
        first = min(expires)
        left = first - time.time()
        when = datetime.fromtimestamp(first).strftime("%Y-%m-%d %H:%M")
        if left <= 0:
            print(f"⚠️ 签名链接已经过期（{when}），请重新读一次原文（手册或帖子）拿新链接。")
        else:
            print(f"签名链接最早在 {when} 过期（还剩约 {left / 3600:.1f} 小时）。")

    if args.dry_run:
        for i, it in enumerate(items, 1):
            print(f"{i:02d}  {public_url(it['url'])}")
        return 0

    out = Path(args.out)
    if out.is_symlink():
        ap.error("输出目录不能是符号链接")
    if out.exists():
        if not out.is_dir():
            ap.error("输出位置不是目录")
        if stat.S_IMODE(out.stat().st_mode) & 0o077:
            print(f"⚠️ 输出目录权限较宽，请自行检查：{out}", file=sys.stderr)
    else:
        out.mkdir(mode=0o700, parents=True, exist_ok=False)
        out.chmod(0o700)  # mkdir 受 umask 影响，仅收紧本次新建的目录。
    map_path = destination(out, f"{args.prefix}_map.json")
    if map_path.exists() or map_path.is_symlink():
        ap.error(f"对应表已存在，拒绝覆盖：{map_path}")
    rows, ok, failed = [], 0, 0
    for i, it in enumerate(items, 1):
        row = {"index": i, "url": public_url(it["url"]), "note": public_note(it["note"]),
               "file": None, "bytes": 0, "ok": False}
        if placeholders:
            if isinstance(placeholders, list):
                row["placeholder"] = placeholders[i - 1] if i - 1 < len(placeholders) else None
            else:
                row["placeholder"] = None
        try:
            data = download(it["url"], allowed_hosts=allowed_hosts)
            extension, size = supported_image(data)
            name = (it["name"] or f"{args.prefix}_{i:02d}") + extension
            write_new(destination(out, name), data)
            level = divider_level(size)
            row.update(file=name, bytes=len(data), ok=True,
                       size=f"{size[0]}x{size[1]}" if size else None,
                       divider=level is not None, divider_level=level)
            ok += 1
        except Exception as e:
            row["error"] = str(e)[:200]
            failed += 1
        rows.append(row)

    mapping = {"source": args.input, "kind": kind, "order_reliable": reliable,
               "downloaded": ok, "failed": failed, "items": rows}
    write_new(map_path, json.dumps(mapping, ensure_ascii=False, indent=2).encode("utf-8"))

    print(f"下载完成：成功 {ok} 张，失败 {failed} 张。对应表：{map_path}")
    dividers = [r for r in rows if r.get("divider_level") == "strong"]
    maybe = [r for r in rows if r.get("divider_level") == "weak"]
    if dividers:
        print(f"？其中 {len(dividers)} 张特别扁，请打开核对：可能是装饰线，也可能是真正的界面横条；不能只按尺寸删图：")
        for r in dividers:
            print(f"  · 第 {r['index']} 张 {r['file']}（{r['size']}）")
    if maybe:
        print(f"？另有 {len(maybe)} 张有点扁，可能是章节横幅，也可能是一行记录的真截图，打开看一眼再定：")
        for r in maybe:
            print(f"  · 第 {r['index']} 张 {r['file']}（{r['size']}）")
    for r in rows:
        if not r["ok"]:
            print(f"  ✗ 第 {r['index']} 张：{r.get('error')}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
