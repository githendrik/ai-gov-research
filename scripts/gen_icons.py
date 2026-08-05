#!/usr/bin/env python3
"""Generate favicon and Apple touch icon from the existing hero image."""
from PIL import Image
from pathlib import Path

SRC = Path("static/images/2026-08-04-ai-governance.png")
OUT = Path("static")

img = Image.open(SRC)
w, h = img.size

# Center-crop to square (use the middle of the 16:9 image)
size = min(w, h)
left = (w - size) // 2
top = (h - size) // 2
square = img.crop((left, top, left + size, top + size))

# Favicon (32x32 + 180x180 for apple-touch-icon)
favicon = square.resize((32, 32), Image.LANCZOS)
favicon.save(OUT / "favicon.ico", format="ICO", sizes=[(32, 32)])
print(f"favicon.ico: 32x32")

apple = square.resize((180, 180), Image.LANCZOS)
apple.save(OUT / "apple-touch-icon.png", format="PNG", optimize=True)
print(f"apple-touch-icon.png: 180x180 ({(OUT / 'apple-touch-icon.png').stat().st_size / 1024:.0f} KB)")
