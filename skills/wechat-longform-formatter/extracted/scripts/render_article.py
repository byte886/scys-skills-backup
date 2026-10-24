#!/usr/bin/env python3
"""把已写好的公众号正文排成自包含 HTML，不改写正文内容。"""

import argparse
import html
import re
from pathlib import Path


STYLES = {
    "清爽蓝": ("#244C7F", "#EAF1F8"),
    "稳重绿": ("#2E654C", "#EAF3ED"),
    "暖橙生活": ("#A65B28", "#FCF1E8"),
    "柔和紫": ("#70517D", "#F3ECF6"),
    "黑白素雅": ("#333333", "#F3F3F3"),
}


def inline_markup(value: str, primary: str) -> str:
    safe = html.escape(value, quote=True)
    safe = re.sub(r"\*\*(.+?)\*\*", rf'<strong style="color:{primary};font-weight:700;">\1</strong>', safe)
    return safe


def render_body(source: str, primary: str, pale: str) -> str:
    blocks = []
    for raw in re.split(r"\n\s*\n", source.strip()):
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            continue
        if len(lines) == 1 and lines[0].startswith("## "):
            blocks.append(f'<h2 style="color:{primary};font-size:20px;line-height:1.5;font-weight:700;margin:40px 0 20px;">{inline_markup(lines[0][3:], primary)}</h2>')
        elif len(lines) == 1 and lines[0].startswith("### "):
            blocks.append(f'<h3 style="color:{primary};font-size:18px;line-height:1.5;font-weight:700;margin:30px 0 14px;">{inline_markup(lines[0][4:], primary)}</h3>')
        elif all(line.startswith("- ") for line in lines):
            items = "".join(f'<li style="font-size:17px;line-height:1.95;color:#262626;margin-bottom:8px;">{inline_markup(line[2:], primary)}</li>' for line in lines)
            blocks.append(f'<ul style="margin:0 0 22px;padding-left:1.4em;">{items}</ul>')
        elif len(lines) == 1 and lines[0].startswith("> "):
            blocks.append(f'<blockquote style="margin:28px 0;padding:14px 18px;border-left:4px solid {primary};background:{pale};font-size:17px;line-height:1.95;">{inline_markup(lines[0][2:], primary)}</blockquote>')
        elif len(lines) == 1 and lines[0].startswith("[配图："):
            blocks.append(f'<p class="image-note" style="padding:14px 18px;color:#777;background:{pale};text-align:center;font-size:14px;line-height:1.7;">{inline_markup(lines[0], primary)}</p>')
        else:
            blocks.append(f'<p style="font-size:17px;line-height:1.95;color:#262626;margin:0 0 22px;">{"<br>".join(inline_markup(line, primary) for line in lines)}</p>')
    return "\n    ".join(blocks)


def render_page(title: str, body: str, style: str) -> str:
    primary, pale = STYLES[style]
    safe_title = html.escape(title, quote=True)
    safe_body = render_body(body, primary, pale)
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{safe_title}</title>
  <style>
    :root {{ --main: {primary}; --pale: {pale}; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f6f7f8; color: #262626; font-family: -apple-system, BlinkMacSystemFont, \"PingFang SC\", \"Microsoft YaHei\", sans-serif; }}
    .toolbar {{ position: sticky; top: 0; z-index: 2; padding: 12px 18px; background: #fff; border-bottom: 1px solid #e7e7e7; text-align: center; }}
    button {{ border: 0; border-radius: 6px; padding: 9px 18px; background: var(--main); color: #fff; font-size: 15px; cursor: pointer; }}
    .hint {{ display: block; margin-top: 5px; color: #777; font-size: 12px; }}
    #article {{ max-width: 760px; margin: 24px auto 64px; padding: 48px 34px 72px; background: #fff; font-size: 17px; line-height: 1.95; }}
    #article h1 {{ margin: 0 0 42px; color: var(--main); font-size: 25px; line-height: 1.45; text-align: center; }}
    #article h2 {{ margin: 40px 0 20px; padding: 0 0 8px 12px; border-left: 4px solid var(--main); border-bottom: 1px solid #ededed; color: var(--main); font-size: 20px; line-height: 1.5; }}
    #article h3 {{ margin: 30px 0 14px; color: var(--main); font-size: 18px; }}
    #article p {{ margin: 0 0 22px; }}
    #article strong {{ color: var(--main); font-weight: 700; }}
    #article blockquote {{ margin: 28px 0; padding: 14px 18px; border-left: 4px solid var(--main); background: var(--pale); }}
    #article ul {{ margin: 0 0 22px; padding-left: 1.4em; }}
    #article li {{ margin-bottom: 8px; }}
    #article .image-note {{ padding: 14px 18px; color: #777; background: var(--pale); text-align: center; font-size: 14px; }}
    @media (max-width: 600px) {{ #article {{ margin: 0; padding: 30px 20px 54px; font-size: 17px; }} #article h1 {{ font-size: 22px; }} }}
  </style>
</head>
<body>
  <div class=\"toolbar\"><button type=\"button\" onclick=\"copyArticle()\">复制正文</button><span class=\"hint\">复制后粘贴到公众号后台，再用手机预览检查样式。</span></div>
  <main id=\"article\">
    <h1>{safe_title}</h1>
    <div id=\"article-body\">
      {safe_body}
    </div>
  </main>
  <script>
    async function copyArticle() {{
      const article = document.getElementById('article-body');
      const range = document.createRange();
      range.selectNodeContents(article);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      let ok = false;
      try {{ ok = document.execCommand('copy'); }} catch (error) {{ ok = false; }}
      if (ok) {{ selection.removeAllRanges(); alert('已复制正文，请到公众号后台粘贴并预览。'); }}
      else {{ alert('自动复制未成功。请手动选中网页正文复制。'); }}
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="生成公众号排版正文和网页成品")
    parser.add_argument("--title", required=True, help="文章标题")
    parser.add_argument("--body", required=True, type=Path, help="UTF-8 正文 Markdown 文件")
    parser.add_argument("--style", default="清爽蓝", choices=STYLES.keys(), help="排版样式")
    parser.add_argument("--out-dir", required=True, type=Path, help="成品保存目录")
    args = parser.parse_args()
    title = args.title.strip()
    if not title:
        parser.error("标题不能为空")
    body = args.body.read_text(encoding="utf-8").strip()
    if not body:
        parser.error("正文不能为空")
    output = args.out_dir
    output.mkdir(parents=True, exist_ok=True)
    (output / "标题.txt").write_text(title + "\n", encoding="utf-8")
    (output / "排版正文.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    (output / "article.html").write_text(render_page(title, body, args.style), encoding="utf-8")
    print(f"已生成：{output / '标题.txt'}、{output / '排版正文.md'}、{output / 'article.html'}")


if __name__ == "__main__":
    main()
