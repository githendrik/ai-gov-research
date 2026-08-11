#!/usr/bin/env python3
"""Build a brutalist email HTML from the latest rendered Hugo post.

Reads public/posts/<latest>/index.html, extracts .post-content inner HTML,
title, and date, and wraps them in an email-safe HTML document with inline
CSS matching the site's brutalist theme.

Usage:
    python3 scripts/build_email.py <post-url-path>  # e.g. posts/2026-08-10-ai-governance/
"""

from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = REPO_ROOT / "public"
BASE_URL = "https://aigov.philine.ch"

# Theme constants (from assets/css/main.css)
ACCENT = "#ff4500"
INK = "#1a1a1a"
PAPER = "#fdfdfd"
MUTED = "#666"
BORDER = "#e3e3e3"
CODE_BG = "#f4f4f4"
TAG_BG = "#eef3f8"


def extract_post(html: str) -> dict:
    """Extract title, date, and post-content inner HTML from rendered page."""
    title_match = re.search(r'<h1 class=post-title>(.+?)</h1>', html)
    title = title_match.group(1) if title_match else "AI Governance Weekly Digest"

    date_match = re.search(r'<time datetime=[^>]*>(.+?)</time>', html)
    date_str = date_match.group(1) if date_match else ""

    content_match = re.search(r'<div class=post-content>(.*?)</div>\s*</article>', html, re.DOTALL)
    if not content_match:
        content_match = re.search(r'<div class=post-content>(.*?)</div>\s*<footer', html, re.DOTALL)
    content_html = content_match.group(1).strip() if content_match else ""

    return {
        "title": title,
        "date": date_str,
        "content_html": content_html,
    }


def rewrite_links_absolute(html: str) -> str:
    """Rewrite relative href/src to absolute URLs."""
    html = re.sub(r'href=/(?!/)', f'href={BASE_URL}/', html)
    html = re.sub(r'src=/(?!/)', f'src={BASE_URL}/', html)
    return html


def inline_styles(html: str) -> str:
    """Add inline styles to HTML elements to match brutalist theme for email clients."""
    # Style h2 headings
    html = re.sub(
        r'<h2([^>]*)>',
        r'<h2\1 style="margin-top:1.8em;margin-bottom:0.4em;font-size:1.4em;font-weight:900;'
        r'letter-spacing:-0.01em;font-family:\'Helvetica Neue\',Helvetica,Arial,sans-serif;'
        r'border-left:8px solid ' + ACCENT + r';padding-left:0.4em;">',
        html,
    )
    # Style h3 headings (item titles)
    html = re.sub(
        r'<h3([^>]*)>',
        r'<h3\1 style="margin-top:1.5em;margin-bottom:0.3em;font-size:1.15em;font-weight:700;'
        r"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">",
        html,
    )
    # Style paragraphs
    html = re.sub(
        r'<p>',
        r'<p style="margin:0.8em 0;line-height:1.65;font-size:16px;'
        r"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        r"'Helvetica Neue',Arial,sans-serif;color:" + INK + r';">',
        html,
    )
    # Style list items
    html = re.sub(
        r'<li>',
        r'<li style="margin:0.3em 0;line-height:1.65;font-size:16px;'
        r"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        r"'Helvetica Neue',Arial,sans-serif;color:" + INK + r';">',
        html,
    )
    # Style strong tags
    html = re.sub(
        r'<strong>',
        r'<strong style="color:' + INK + r';font-weight:700;">',
        html,
    )
    # Style links
    html = re.sub(
        r'<a href=([^ >]+)>',
        r'<a href=\1 style="color:' + INK + r';text-decoration:none;'
        r'border-bottom:2px solid ' + ACCENT + r';">',
        html,
    )
    # Style sup tags
    html = re.sub(
        r'<sup>',
        r'<sup style="font-size:0.75em;color:' + MUTED + r';line-height:0;">',
        html,
    )
    # Style ul
    html = re.sub(
        r'<ul>',
        r'<ul style="padding-left:1.4em;margin:0.8em 0;">',
        html,
    )
    # Style code
    html = re.sub(
        r'<code>',
        r'<code style="background:' + CODE_BG + r';padding:0.1em 0.3em;'
        r"border-radius:3px;font-size:0.9em;font-family:'SFMono-Regular',"
        r"Menlo,Monaco,Consolas,monospace;\">",
        html,
    )
    return html


def build_email(post: dict) -> str:
    """Build the full HTML email document."""
    content = rewrite_links_absolute(post["content_html"])
    content = inline_styles(content)

    # Title block (orange overlay, no hero image — images render unreliably in email clients)
    hero_html = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;margin:0 auto 20px;border-collapse:collapse;">
      <tr>
        <td style="background:{ACCENT};border:4px solid {INK};padding:16px 20px;">
          <h1 style="margin:0;font-size:24px;font-weight:900;letter-spacing:-0.015em;
            font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:{INK};
            line-height:1.15;">{post['title']}</h1>
          <p style="margin:6px 0 0;font-size:14px;color:{INK};opacity:0.8;
            font-family:'SFMono-Regular',Menlo,Monaco,Consolas,monospace;">{post['date']}</p>
        </td>
      </tr>
    </table>"""

    # Brutalist banner header (matches .site-banner)
    banner_html = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;margin:0 auto 20px;border-collapse:collapse;">
      <tr>
        <td style="border:4px solid {INK};background:{PAPER};">
          <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;">
            <tr>
              <td style="background:{ACCENT};border-bottom:4px solid {INK};padding:10px 14px;">
                <span style="font-size:18px;font-weight:900;text-transform:uppercase;
                  letter-spacing:-0.02em;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                  color:{INK};">The AI Gov Digest</span>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 14px;">
                <span style="font-size:12px;text-transform:uppercase;letter-spacing:0.06em;
                  font-family:'SFMono-Regular',Menlo,Monaco,Consolas,monospace;color:{INK};">
                  Weekly AI Governance &middot; Regulation &middot; Safety
                </span>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>"""

    # Content wrapper with brutalist border
    content_wrapper_open = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;margin:0 auto;border-collapse:collapse;">
      <tr>
        <td style="border:4px solid {INK};background:{PAPER};padding:24px 20px;">"""

    content_wrapper_close = f"""
        </td>
      </tr>
    </table>"""

    # Footer
    footer_html = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;margin:20px auto 0;">
      <tr>
        <td style="border-top:1px solid {BORDER};padding:16px 0;">
          <p style="margin:0;font-size:14px;color:{MUTED};
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,
            'Helvetica Neue',Arial,sans-serif;">
            &copy; 2026 The AI Gov Digest &middot;
            <a href="{BASE_URL}" style="color:{MUTED};text-decoration:none;
            border-bottom:1px solid {ACCENT};">{BASE_URL.replace('https://','')}</a>
          </p>
        </td>
      </tr>
    </table>"""

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(post['title'])}</title>
</head>
<body style="margin:0;padding:0;background:{PAPER};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:{INK};">

  <div style="padding:20px 12px;">

{banner_html}

{hero_html}

{content_wrapper_open}
{content}
{content_wrapper_close}

{footer_html}

  </div>

</body>
</html>"""

    return full_html


def main(argv: list[str]) -> int:
    if len(argv) < 1:
        print("usage: build_email.py <post-url-path>  (e.g. posts/2026-08-10-ai-governance/)", file=sys.stderr)
        return 1

    post_path = argv[0].strip("/")
    html_file = PUBLIC_DIR / post_path / "index.html"
    if not html_file.exists():
        print(f"error: {html_file} not found — run `hugo` first", file=sys.stderr)
        return 1

    raw = html_file.read_text(encoding="utf-8")
    post = extract_post(raw)

    if not post["content_html"]:
        print("error: could not extract post-content from rendered HTML", file=sys.stderr)
        return 1

    email_html = build_email(post)

    out_file = REPO_ROOT / "scripts" / "email_output.html"
    out_file.write_text(email_html, encoding="utf-8")
    print(f"wrote {out_file.relative_to(REPO_ROOT)} ({len(email_html)} bytes)")
    print(f"  title: {post['title']}")
    print(f"  date:  {post['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
