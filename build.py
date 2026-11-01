#!/usr/bin/env python3
"""Build the tektek brand files from brand.json.

Edit brand.json, then run:

    python3 build.py

It writes:
    logo/tektek-logo.svg           main logo (traced from the sketch), ink colour
    logo/tektek-logo-reverse.svg   main logo, background colour on ink
    logo/tektek-tagline.svg        "GOOD COFFEE / BETTER CODE"
    icons/*.svg                    icons in the ink colour (from icons/src)
    tokens.css                     colours and fonts as CSS variables
    preview.html                   one page to check the whole brand

Needs: pip install fonttools
"""
import json
import math
import re
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).parent
BRAND = json.loads((ROOT / "brand.json").read_text(encoding="utf-8"))

FONT = TTFont(ROOT / BRAND["fonts"]["logo_file"])
GLYPHS = FONT.getGlyphSet()
CMAP = FONT.getBestCmap()
UPM = FONT["head"].unitsPerEm
CAP_HEIGHT = FONT["OS/2"].sCapHeight

COLORS = BRAND["colors"]
ROLES = BRAND["roles"]


def hex_of(role):
    """Colour hex for a role such as 'ink' or 'background'."""
    return COLORS[ROLES[role]]


def fmt(value):
    return f"{value:.2f}"


def outline(text, size, tracking):
    """Turn one line of text into SVG path data. Returns (d, width, cap height)."""
    scale = size / UPM
    pen = SVGPathPen(GLYPHS, ntos=fmt)
    x = 0.0
    for char in text:
        glyph = GLYPHS[CMAP[ord(char)]]
        glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
        x += glyph.width * scale + tracking
    return pen.getCommands(), x - tracking, CAP_HEIGHT * scale


def compose(lines, fill, background=None, padding=30):
    """Stack lines of text, each possibly tilted and shifted. Returns an SVG string."""
    paths, points = [], []
    y = 0.0
    for line in lines:
        d, width, cap = outline(line["text"], line["size"], line["tracking"])
        y += line.get("gap", 0)
        baseline = y + cap
        tilt = line.get("tilt", 0)
        dx = line.get("dx", 0)

        # Corners of the line's box after tilt, used to size the canvas.
        angle = math.radians(tilt)
        pivot_x, pivot_y = width / 2, -cap / 2
        for cx, cy in [(0, -cap), (width, -cap), (width, 0), (0, 0)]:
            rx, ry = cx - pivot_x, cy - pivot_y
            points.append((
                rx * math.cos(angle) - ry * math.sin(angle) + pivot_x + dx,
                rx * math.sin(angle) + ry * math.cos(angle) + pivot_y + baseline,
            ))

        paths.append(
            f'<path transform="translate({fmt(dx)} {fmt(baseline)}) '
            f'rotate({fmt(tilt)} {fmt(pivot_x)} {fmt(pivot_y)})" '
            f'd="{d}" fill="{fill}"/>'
        )
        y = baseline

    min_x = min(p[0] for p in points) - padding
    max_x = max(p[0] for p in points) + padding
    min_y = min(p[1] for p in points) - padding
    max_y = max(p[1] for p in points) + padding
    width, height = max_x - min_x, max_y - min_y

    rect = ""
    if background:
        rect = (f'<rect x="{fmt(min_x)}" y="{fmt(min_y)}" width="{fmt(width)}" '
                f'height="{fmt(height)}" fill="{background}"/>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fmt(min_x)} {fmt(min_y)} '
        f'{fmt(width)} {fmt(height)}" width="{round(width)}" height="{round(height)}">'
        f'{rect}{"".join(paths)}</svg>\n'
    )


def traced_logo(fill, background=None):
    """The logo traced from the sketch (logo/src/logo-traced.svg), recoloured."""
    source = (ROOT / BRAND["logo"]["source"]).read_text(encoding="utf-8")
    view_box = re.search(r'viewBox="([^"]+)"', source).group(1)
    _, _, width, height = (float(v) for v in view_box.split())
    path = re.search(r"<path[^>]*/>", source).group(0)
    path = re.sub(r'fill="[^"]*"', f'fill="{fill}"', path)
    rect = (f'<rect x="0" y="0" width="{fmt(width)}" height="{fmt(height)}" fill="{background}"/>'
            if background else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
            f'width="{round(width)}" height="{round(height)}">{rect}{path}</svg>\n')


def tagline_lines():
    tag = BRAND["tagline"]
    return [
        {"text": text, "size": tag["size"], "tracking": tag["tracking"],
         "tilt": 0, "dx": 0, "gap": tag["gap"] if i else 0}
        for i, text in enumerate(tag["lines"])
    ]


def write_logos():
    out = ROOT / "logo"
    out.mkdir(exist_ok=True)
    ink = hex_of("ink")
    bg = hex_of("background")

    (out / "tektek-logo.svg").write_text(traced_logo(fill=ink), encoding="utf-8")
    (out / "tektek-logo-reverse.svg").write_text(
        traced_logo(fill=bg, background=ink), encoding="utf-8")
    (out / "tektek-tagline.svg").write_text(
        compose(tagline_lines(), fill=ink, padding=BRAND["tagline"]["padding"]), encoding="utf-8")


def write_icons():
    out = ROOT / "icons"
    out.mkdir(exist_ok=True)
    ink = hex_of("ink")
    for src in sorted((out / "src").glob("*.svg")):
        svg = src.read_text(encoding="utf-8").replace("currentColor", ink)
        (out / src.name).write_text(svg, encoding="utf-8")


def write_tokens():
    lines = [":root {", "  /* generated by build.py from brand.json: do not edit by hand */"]
    for name, value in COLORS.items():
        lines.append(f"  --tektek-{name}: {value};")
    for role, name in ROLES.items():
        if role.startswith("_"):
            continue
        lines.append(f"  --tektek-{role}: var(--tektek-{name});")
    lines.append(f"  --tektek-font-display: {BRAND['fonts']['css_family']};")
    lines.append(f"  --tektek-font-body: {BRAND['fonts']['body_family']};")
    lines.append("}")
    (ROOT / "tokens.css").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_preview():
    swatches = "\n".join(
        f'<div class="swatch"><div class="dot" style="background:{hex_}"></div>'
        f'<div><strong>{name}</strong><br><code>{hex_}</code></div></div>'
        for name, hex_ in COLORS.items()
    )
    roles = "\n".join(
        f"<li><code>{role}</code> = {name}</li>"
        for role, name in ROLES.items() if not role.startswith("_")
    )
    icons = "\n".join(
        f'<figure><img src="icons/{name}.svg" width="48" height="48" alt="{name}"><figcaption>{name}</figcaption></figure>'
        for name in ["bolt", "coffee", "code"]
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>tektek brand preview</title>
<link rel="stylesheet" href="tokens.css">
<style>
  body {{ margin: 0; padding: 32px; background: var(--tektek-background); color: var(--tektek-ink);
         font-family: var(--tektek-font-body); }}
  h2 {{ font-family: var(--tektek-font-display); font-size: 18px; letter-spacing: 0.04em; margin: 40px 0 12px; }}
  .row {{ display: flex; flex-wrap: wrap; gap: 24px; align-items: center; }}
  .swatch {{ display: flex; gap: 10px; align-items: center; width: 180px; }}
  .dot {{ width: 56px; height: 56px; border-radius: 50%; flex: none; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.15); }}
  .panel {{ padding: 24px; border-radius: 12px; }}
  figure {{ margin: 0; text-align: center; }}
  figcaption {{ font-size: 13px; }}
  code {{ font-size: 13px; }}
</style>
</head>
<body>
<h1 style="font-family: var(--tektek-font-display); font-size: 28px; margin: 0;">{BRAND['name']}</h1>

<h2>Logo</h2>
<div class="row">
  <div class="panel"><img src="logo/tektek-logo.svg" alt="{BRAND['name']} logo" style="height: 260px"></div>
  <div class="panel" style="background: var(--tektek-ink)"><img src="logo/tektek-logo-reverse.svg" alt="{BRAND['name']} logo reversed" style="height: 260px"></div>
</div>

<h2>Tagline</h2>
<img src="logo/tektek-tagline.svg" alt="Tagline" style="height: 140px">

<h2>Colours</h2>
<div class="row">{swatches}</div>

<h2>Icons</h2>
<div class="row">{icons}</div>

<h2>Typography</h2>
<p style="font-family: var(--tektek-font-display); font-size: 40px; margin: 0;">{BRAND['name']}</p>
<p style="font-family: var(--tektek-font-body); font-size: 18px;">Body text uses the system sans-serif font.</p>

<h2>Roles</h2>
<ul>{roles}</ul>
</body>
</html>
"""
    (ROOT / "preview.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    write_logos()
    write_icons()
    write_tokens()
    write_preview()
    print("Built logo/, icons/, tokens.css and preview.html from brand.json")
