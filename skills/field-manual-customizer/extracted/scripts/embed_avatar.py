#!/usr/bin/env python3
"""从 topicDetail JSON 提取案例作者头像，输出可离线使用的 data URI。

用法：python3 scripts/embed_avatar.py <topic-detail.json>
标准输出为 JSON：成功时 status=ok、name 和 data_uri；没有头像或下载失败时
status=skipped、reason，不输出原始头像 URL。失败不影响引用正文。
"""

import argparse
import base64
import binascii
import html
import json
import sys
import zlib
from pathlib import Path

import fetch_images


MAX_AVATAR_BYTES = 200 * 1024
# 已核对的 topicDetail 试跑返回：topicUserDTO.avatar 的主机名。
AVATAR_HOSTS = frozenset({"search01.shengcaiyoushu.com"})
AVATAR_MIMES = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}


def _png_scanlines(width, height, depth, color, interlace):
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    passes = ((0, 0, 1, 1),) if interlace == 0 else (
        (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
        (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))
    lengths = []
    for x, y, dx, dy in passes:
        columns = max(0, (width - x + dx - 1) // dx)
        rows = max(0, (height - y + dy - 1) // dy)
        if columns and rows:
            lengths.append((1 + (columns * channels * depth + 7) // 8, rows))
    return lengths


def _png_idat_valid(parts, scanlines):
    expected = sum(length * rows for length, rows in scanlines)
    # 头像压缩体虽有 200 KiB 限额，解压结果仍可能是压缩炸弹。
    if expected > 64 * 1024 * 1024:
        return False
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(b"".join(parts), expected + 1)
        if len(raw) > expected or decoder.unconsumed_tail:
            return False
        raw += decoder.flush(expected + 1 - len(raw))
    except zlib.error:
        return False
    if not decoder.eof or decoder.unused_data or len(raw) != expected:
        return False
    offset = 0
    for length, rows in scanlines:
        for _ in range(rows):
            if raw[offset] > 4:
                return False
            offset += length
    return True


def _webp_bitstream_valid(kind, payload):
    if kind == b"VP8 ":
        return (len(payload) >= 10 and payload[0] & 1 == 0
                and payload[3:6] == b"\x9d\x01\x2a"
                and (int.from_bytes(payload[6:8], "little") & 0x3FFF) > 0
                and (int.from_bytes(payload[8:10], "little") & 0x3FFF) > 0)
    if kind == b"VP8L":
        return (len(payload) >= 5 and payload[0] == 0x2F
                and (payload[4] & 0xE0) == 0)
    if kind == b"VP8X":
        return (len(payload) == 10 and payload[0] & 0xC1 == 0
                and payload[1:4] == b"\0\0\0"
                and 1 + int.from_bytes(payload[4:7], "little") > 0
                and 1 + int.from_bytes(payload[7:10], "little") > 0)
    return False


def complete_image_structure(data, extension):
    """核对 PNG 扫描行与 JPEG/WebP 位流头。

    标准库无法完成 JPEG/WebP 像素解码；PNG 也不重建像素或检查所有辅助块语义。
    因而通过这里只代表所列结构有效，浏览器仍可能拒绝个别图片。
    """
    if extension == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return False
        offset, chunks, idat_parts, scanlines = 8, 0, [], None
        while offset + 12 <= len(data):
            length = int.from_bytes(data[offset:offset + 4], "big")
            end = offset + 12 + length
            if end > len(data):
                return False
            kind = data[offset + 4:offset + 8]
            payload = data[offset + 8:end - 4]
            crc = int.from_bytes(data[end - 4:end], "big")
            if binascii.crc32(kind + payload) & 0xFFFFFFFF != crc:
                return False
            if chunks == 0 and (kind != b"IHDR" or length != 13):
                return False
            if chunks > 0 and kind == b"IHDR":
                return False
            if kind == b"IHDR":
                width = int.from_bytes(payload[:4], "big")
                height = int.from_bytes(payload[4:8], "big")
                depth, color, compression, filtering, interlace = payload[8:13]
                allowed = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8),
                           4: (8, 16), 6: (8, 16)}
                if (not width or not height or depth not in allowed.get(color, ())
                        or compression != 0 or filtering != 0 or interlace not in (0, 1)):
                    return False
                scanlines = _png_scanlines(width, height, depth, color, interlace)
            if kind == b"IDAT":
                idat_parts.append(payload)
            if kind == b"IEND":
                return (length == 0 and bool(idat_parts) and end == len(data)
                        and _png_idat_valid(idat_parts, scanlines))
            chunks += 1
            offset = end
        return False

    if extension == ".jpg":
        if not data.startswith(b"\xff\xd8"):
            return False
        offset, saw_sos, saw_sof, in_scan = 2, False, False, False
        while offset < len(data):
            if in_scan and data[offset] != 0xFF:
                offset += 1
                continue
            if data[offset] != 0xFF:
                return False
            while offset < len(data) and data[offset] == 0xFF:
                offset += 1
            if offset >= len(data):
                return False
            marker = data[offset]
            offset += 1
            if in_scan and (marker == 0 or 0xD0 <= marker <= 0xD7):
                continue
            if marker == 0xD9:
                return saw_sos and saw_sof and offset == len(data)
            if marker in (0x00, 0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                return False
            if offset + 2 > len(data):
                return False
            length = int.from_bytes(data[offset:offset + 2], "big")
            if length < 2 or offset + length > len(data):
                return False
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                frame = data[offset + 2:offset + length]
                if len(frame) < 6:
                    return False
                precision = frame[0]
                height = int.from_bytes(frame[1:3], "big")
                width = int.from_bytes(frame[3:5], "big")
                components = frame[5]
                # 基线 DCT 只允许 8 位；扩展 DCT 常用 8/12 位；无损 SOF 可用 2–16 位。
                allowed_precisions = ((8,) if marker == 0xC0 else
                                      range(2, 17) if marker in (0xC3, 0xC7, 0xCB, 0xCF)
                                      else (8, 12))
                if (precision not in allowed_precisions or not width or not height
                        or not 1 <= components <= 4 or len(frame) != 6 + 3 * components):
                    return False
                factors = [frame[6 + 3 * i + 1] for i in range(components)]
                if any(not 1 <= factor >> 4 <= 4 or not 1 <= factor & 15 <= 4
                       for factor in factors):
                    return False
                saw_sof = True
            if marker == 0xDA:
                if not saw_sof:
                    return False
                saw_sos = True
                in_scan = True
            else:
                in_scan = False
            offset += length
        return False

    if extension == ".webp":
        if len(data) < 20 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
            return False
        if int.from_bytes(data[4:8], "little") + 8 != len(data):
            return False
        offset, chunks, has_image, has_animation = 12, 0, False, False
        while offset + 8 <= len(data):
            kind = data[offset:offset + 4]
            length = int.from_bytes(data[offset + 4:offset + 8], "little")
            end = offset + 8 + length + (length & 1)
            if end > len(data):
                return False
            if chunks == 0 and kind not in (b"VP8 ", b"VP8L", b"VP8X"):
                return False
            payload = data[offset + 8:offset + 8 + length]
            if kind == b"VP8 ":
                has_image = has_image or _webp_bitstream_valid(kind, payload)
                if not has_image:
                    return False
            elif kind == b"VP8L":
                has_image = has_image or _webp_bitstream_valid(kind, payload)
                if not has_image:
                    return False
            elif kind == b"VP8X":
                if not _webp_bitstream_valid(kind, payload):
                    return False
            elif kind == b"ANIM":
                has_animation = has_animation or length >= 6
            elif kind == b"ANMF":
                frame = payload[16:]
                if len(payload) < 24 or not has_animation:
                    return False
                frame_kind = frame[:4]
                frame_size = int.from_bytes(frame[4:8], "little")
                if (frame_kind not in (b"VP8 ", b"VP8L")
                        or 8 + frame_size + (frame_size & 1) > len(frame)
                        or not _webp_bitstream_valid(frame_kind, frame[8:8 + frame_size])):
                    return False
                has_image = True
            chunks += 1
            offset = end
        return offset == len(data) and has_image
    return False


def embed_avatar(payload, downloader=None):
    """优先采信 topicDetail 顶层作者，兼容旧嵌套输入；头像异常即跳过。"""
    try:
        payload = fetch_images.unwrap(payload)
    except (TypeError, ValueError):
        return {"status": "skipped", "reason": "author_missing"}
    if not isinstance(payload, dict):
        return {"status": "skipped", "reason": "author_missing"}
    # topicDetail 的真实返回把作者放在 topicDTO 的同级；兼容旧的嵌套输入。
    author = payload.get("topicUserDTO")
    if not isinstance(author, dict):
        topic = payload.get("topicDTO")
        author = topic.get("topicUserDTO") if isinstance(topic, dict) else None
    if not isinstance(author, dict):
        return {"status": "skipped", "reason": "author_missing"}
    name = author.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"status": "skipped", "reason": "author_missing"}
    result = {"status": "skipped", "name": name, "reason": "avatar_missing"}
    url = author.get("avatar")
    if not isinstance(url, str) or not url:
        return result
    try:
        data = (downloader or fetch_images.download)(
            html.unescape(url), allowed_hosts=AVATAR_HOSTS, max_bytes=MAX_AVATAR_BYTES
        )
        if len(data) > MAX_AVATAR_BYTES:
            raise ValueError("头像过大")
        extension, size = fetch_images.supported_image(data)
        mime = AVATAR_MIMES.get(extension)
        if mime is None or not complete_image_structure(data, extension):
            raise ValueError("头像格式不支持或结构不完整")
    except Exception:
        result["reason"] = "avatar_unavailable"
        return result
    return {"status": "ok", "name": name, "width": size[0], "height": size[1],
            "data_uri": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="把 topicDetail 的作者头像转换成离线 data URI")
    parser.add_argument("input", help="topicDetail JSON 文件；请保存在当前用户的私有工作目录")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("无法读取 topicDetail JSON", file=sys.stderr)
        return 2
    print(json.dumps(embed_avatar(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
