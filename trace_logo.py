#!/usr/bin/env python3
"""Trace the logo in the brand sketch into a vector path.

One-time step: writes logo/src/logo-traced.svg. build.py colours it.

    python3 trace_logo.py
"""
from pathlib import Path

import potrace
from PIL import Image, ImageOps

ROOT = Path(__file__).parent
SKETCH = ROOT / "tek tek oy brand first idea.png"
OUT = ROOT / "logo" / "src" / "logo-traced.svg"

# Logo area of the sketch, in its own pixels (left, top, right, bottom).
CROP = (30, 25, 235, 265)
SCALE = 4  # upscale before tracing, so curves come out smooth


def trace(bitmap_image):
    bitmap = potrace.Bitmap(bitmap_image)
    return bitmap.trace(turdsize=400, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                        alphamax=1.0, opticurve=True, opttolerance=0.2)


def fmt(point):
    return f"{point.x:.2f} {point.y:.2f}"


def to_svg_path(plist, height):
    parts = []
    for curve in plist:
        start = curve.start_point
        parts.append(f"M{fmt(start)}")
        for segment in curve.segments:
            if segment.is_corner:
                parts.append(f"L{fmt(segment.c)}L{fmt(segment.end_point)}")
            else:
                parts.append(f"C{fmt(segment.c1)} {fmt(segment.c2)} {fmt(segment.end_point)}")
        parts.append("Z")
    return "".join(parts)


def main():
    sketch = Image.open(SKETCH).convert("L").crop(CROP)
    sketch = sketch.resize((sketch.width * SCALE, sketch.height * SCALE), Image.LANCZOS)
    sketch = ImageOps.autocontrast(sketch)

    # Trim to the letters, keeping a small margin.
    ink = sketch.point(lambda v: 255 if v < 128 else 0)
    left, top, right, bottom = ink.getbbox()
    margin = 12 * SCALE
    sketch = sketch.crop((max(left - margin, 0), max(top - margin, 0),
                          min(right + margin, sketch.width), min(bottom + margin, sketch.height)))
    plist = trace(sketch)

    # Flip so the SVG reads top-down, then fit to the traced area.
    width, height = sketch.size
    d = to_svg_path(plist, height)
    OUT.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
        f'<path fill="#0B2A44" fill-rule="evenodd" d="{d}"/></svg>\n',
        encoding="utf-8",
    )
    print(f"traced {len(plist)} shapes -> {OUT}")


if __name__ == "__main__":
    main()
