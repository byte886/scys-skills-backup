#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载单个 SkillHub 托管 zip：校验 sha256 → 解压到 extracted/。
用法：
  python3 scripts/fetch_package.py --code media-transcriber --version 1.1.0 \
      --sha256 <artifactSha256> --url '<当次 installguide 返回的签名 URL>'
说明：
- 签名 URL 约 1 小时有效，必须用当次 MCP 返回值，禁止拼地址。
- 国内 OSS（aliyuncs.com）强制直连，不走本机代理。
- sha256 不符立即非 0 退出，不保留解压内容。
"""
import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--url", required=True)
    args = ap.parse_args()

    sdir = ROOT / "skills" / args.code
    sdir.mkdir(parents=True, exist_ok=True)
    zip_path = sdir / f"{args.code}-{args.version}.zip"
    ext_dir = sdir / "extracted"

    # 强制直连（国内 OSS），覆盖系统/环境代理
    cmd = ["curl", "--noproxy", "*", "-fSL", "--retry", "2",
           "--connect-timeout", "20", "--output", str(zip_path), args.url]
    print(f"[fetch] {args.code} {args.version} -> {zip_path}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-800:])
        sys.exit(f"下载失败: {args.code}")

    data = zip_path.read_bytes()
    got = hashlib.sha256(data).hexdigest()
    print(f"[sha256] expected={args.sha256}")
    print(f"[sha256] got     ={got}")
    if got != args.sha256:
        sys.exit(f"!! sha256 不符，停止: {args.code}")

    if ext_dir.exists():
        for p in sorted(ext_dir.rglob("*"), reverse=True):
            if p.is_file() or p.is_symlink():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
    ext_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(ext_dir)
    names = sorted(
        str(p.relative_to(ext_dir))
        for p in ext_dir.rglob("*") if p.is_file()
    )
    print(f"[extract] {len(names)} 个文件 -> {ext_dir}")
    for n in names:
        print("   ", n)
    print(f"[OK] {args.code} {args.version} ({len(data)} bytes, {len(names)} files)")


if __name__ == "__main__":
    main()
