#!/usr/bin/env python3
"""Render-and-verify GitHub README visual assets.

Complements audit_readme.py (static XML checks) with what static checks cannot
see: real rendering, clipped/edge-touching content, and WCAG text contrast.

Checks performed per SVG asset:
  1. Render the SVG with headless Chrome at its declared size (PNG output).
  2. Edge scan: warn when rendered content is NOT a uniform full-bleed
     background on every edge (possible clipping or accidental border content).
  3. Contrast check: every <text> fill vs the dominant <rect> background fill
     (WCAG: 4.5:1 body / 3:1 large text, using the 900px GitHub render scale).
  4. Structural sanity: viewBox present, <title> + <desc> present, no
     <script>/<foreignObject>/remote font references.

Usage:
  python3 scripts/visual_verify.py /path/to/repository/README.md [--out DIR]
  python3 scripts/visual_verify.py /path/to/hero.svg [--out DIR]

Prints a report and exits non-zero when issues are found.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ---------------------------------------------------------------- discovery

MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
HTML_IMAGE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)
UNSAFE_SVG_TAGS = {"script", "foreignObject"}
REMOTE_FONT = re.compile(r"@font-face|fonts\.(googleapis|gstatic)\.com|<link\b[^>]*stylesheet", re.I)
# References that would escape the isolated render sandbox: remote URLs
# (http/https/file), protocol-relative, root-absolute, Windows-drive, or
# parent-directory paths. Plain relative refs and data:/#fragment are allowed.
DANGEROUS_REF = re.compile(
    r"""(?:href|src)\s*=\s*["']\s*(?:(?:https?:|file:)?//|/|[A-Za-z]:[\\/]|\.\./)""",
    re.I,
)


def find_chrome() -> str | None:
    candidates = []
    if sys.platform == "win32":
        base = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        base86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(base86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(base86, "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    else:
        for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            hit = shutil.which(name)
            if hit:
                return hit
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def local_svg_sources(readme: Path) -> list[tuple[str, Path]]:
    """Return [(src_text, absolute_path)] for local SVG references.

    Only references that resolve inside the README's own directory tree are
    accepted; anything pointing outside it (e.g. ``../../``, root-absolute, or
    Windows-drive paths) is skipped so the checker never reads files from
    outside the requested repository.
    """
    text = readme.read_text(encoding="utf-8")
    srcs = list(MARKDOWN_IMAGE.findall(text))
    srcs += [m for m in HTML_IMAGE.findall(text)]
    root = readme.parent.resolve()
    out = []
    skipped = []
    for src in dict.fromkeys(srcs):
        if src.startswith(("http://", "https://", "data:", "#")):
            continue
        clean = src.split("#", 1)[0].split("?", 1)[0]
        if not clean.lower().endswith(".svg"):
            continue
        p = (readme.parent / clean).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            skipped.append(src)
            continue
        if p.is_file():
            out.append((src, p))
    if skipped:
        print(f"WARNING: skipped SVG reference(s) resolving outside the README tree: {skipped}")
    return out


# ---------------------------------------------------------------- contrast

def parse_color(value: str) -> tuple[int, int, int] | None:
    v = value.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", v)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"#([0-9a-fA-F]{3})", v)
    if m:
        h = m.group(1)
        return tuple(int(c * 2, 16) for c in h)
    m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", v)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def luminance(rgb: tuple[int, int, int]) -> float:
    def chan(c: int) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def svg_contrast_issues(path: Path) -> list[str]:
    """Check each <text> fill against its container <rect> background.

    Background resolution order: the first filled <rect> declared inside the
    text's own parent group, then up the ancestor chain, then the largest
    <rect> in the document (fallback).
    """
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"invalid SVG XML: {exc}"]
    raw_tag = root.tag
    ns = raw_tag.rsplit("}", 1)[0] + "}" if "}" in raw_tag else ""
    def tag(name: str) -> str:
        return f"{ns}{name}"

    # parent map
    parent_of: dict[ET.Element, ET.Element | None] = {root: None}
    for node in root.iter():
        for child in node:
            parent_of[child] = node

    rects: list[tuple[float, tuple[int, int, int]]] = []
    for rect in root.iter(tag("rect")):
        w = float(rect.get("width", "0") or 0)
        h = float(rect.get("height", "0") or 0)
        fill = parse_color(rect.get("fill", ""))
        if fill:
            rects.append((w * h, fill))
    if not rects:
        return ["no <rect> background found; cannot verify contrast"]
    dominant = max(rects, key=lambda r: r[0])[1]

    def container_bg(text_el: ET.Element) -> tuple[int, int, int] | None:
        """Nearest plausible container background.

        Walk ancestors; inside each group take the last filled <rect> declared
        BEFORE the text in document order (paint order: background first).
        Ignore tiny decorative rects (area smaller than roughly the text's own
        bounding box) so small color chips are not mistaken for backgrounds.
        Fall back to the largest rect in the document.
        """
        fs = float(text_el.get("font-size", "16") or 16)
        est = fs * fs * 2  # rough text bbox area
        node: ET.Element | None = text_el
        while node is not None:
            children = list(node)
            try:
                my_idx = children.index(text_el)
            except ValueError:
                my_idx = len(children)
            best: tuple[int, int, int] | None = None
            for child in children[:my_idx]:
                if child.tag != tag("rect"):
                    continue
                fill = parse_color(child.get("fill", ""))
                if not fill:
                    continue
                w = float(child.get("width", "0") or 0)
                h = float(child.get("height", "0") or 0)
                if w * h >= est:
                    best = fill  # last qualifying rect before the text wins
            if best is not None:
                return best
            node = parent_of.get(node)
        return None

    issues: list[str] = []
    for text in root.iter(tag("text")):
        fill = parse_color(text.get("fill", ""))
        if not fill:
            continue
        bg = container_bg(text) or dominant
        size = float(text.get("font-size", "16") or 16)
        weight = text.get("font-weight", "400")
        bold = weight in ("bold", "700", "800", "900") or (weight.isdigit() and int(weight) >= 700)
        # 900px GitHub render => 0.75 scale; large-text thresholds at 24px+ / 18.66px bold+
        rendered = size * 0.75
        large = rendered >= 24 or (bold and rendered >= 18.66)
        ratio = contrast_ratio(fill, bg)
        limit = 3.0 if large else 4.5
        if ratio < limit:
            sample = (text.text or "").strip()[:28]
            issues.append(
                f"low contrast: fill={text.get('fill')} vs bg #{''.join(f'{c:02X}' for c in bg)} "
                f"ratio={ratio:.2f} (<{limit:.1f}, {'large' if large else 'body'} text @{rendered:.0f}px): {sample!r}"
            )
    return issues


# ---------------------------------------------------------------- rendering

def render_svg(svg: Path, chrome: str, out_png: Path) -> tuple[int, str]:
    """Render one SVG to PNG inside a hardened sandbox. Returns (ok, err).

    Trust boundary: the SVG under test is treated as untrusted input (it may
    come from a third-party repository). Four layers of isolation:

      1. The SVG is copied into a fresh, empty directory that contains nothing
         else, and only that directory is served — the SVG cannot read sibling
         files from the repository it came from.
      2. JavaScript is disabled (--blink-settings=scriptEnabled=false), so any
         <script> in the SVG is inert. SVG is static content on GitHub; it
         never needs JS to render.
      3. DNS resolution is blocked for every host (--host-resolver-rules), so
         the SVG cannot pull remote fonts/images. The preview server URL uses
         an explicit 127.0.0.1 IP so it stays reachable without DNS.
      4. The preview server binds loopback only, on an ephemeral port.
    """
    svg = svg.resolve()
    with tempfile.TemporaryDirectory(prefix="vverify-serve-") as td:
        serve_dir = Path(td)
        isolated = serve_dir / svg.name
        shutil.copy2(svg, isolated)
        class QuietHandler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(serve_dir), **kw)
            def log_message(self, *a):  # silence access log noise
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)  # ephemeral port
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{port}/{isolated.name}"
            size = svg_size(svg)
            if size:
                w, h = size
            else:
                w = h = 1200
            cmd = [
                chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
                "--no-first-run", "--no-default-browser-check",
                # Network isolation: block DNS for every hostname except
                # 127.0.0.1 (the loopback preview server, reached by explicit
                # IP below). Scripts never reach here (is_safe_to_render gates
                # them out), and remote resource loads are refused statically,
                # so loopback exemption only serves the preview itself.
                '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1',
                "--user-data-dir=" + str(tempfile.mkdtemp(prefix="chrome-vverify-")),
                f"--window-size={w},{h}",
                f"--screenshot={out_png}",
                url,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                  encoding="utf-8", errors="replace")
            if not out_png.exists() or out_png.stat().st_size == 0:
                detail = (proc.stderr or "") + " | STDOUT: " + (proc.stdout or "")
                return False, f"rc={proc.returncode} " + (detail.strip() or "no screenshot produced")[:400]
            return True, ""
        except subprocess.TimeoutExpired:
            return False, "Chrome render timed out"
        finally:
            server.shutdown()
            thread.join(timeout=5)


def svg_size(path: Path) -> tuple[int, int] | None:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    w = root.get("width")
    h = root.get("height")
    if w and h:
        try:
            return int(float(w)), int(float(h))
        except ValueError:
            return None
    vb = root.get("viewBox")
    if vb:
        parts = vb.split()
        if len(parts) == 4:
            try:
                return int(float(parts[2])), int(float(parts[3]))
            except ValueError:
                return None
    return None


def edge_scan_issues(png: Path) -> list[str]:
    """Warn when rendered content is not a uniform full-bleed background.

    Transparent pixels (rounded-corner outside areas) are ignored. The dominant
    color of each 4px edge band is treated as background; other colors covering
    more than 2% of the band suggest content touching the edge (clipping risk).
    """
    if not HAS_PIL:
        return []
    im = Image.open(png).convert("RGBA")
    w, h = im.size
    px = im.load()
    issues: list[str] = []
    edges = {"top": [(x, y) for x in range(w) for y in range(min(4, h))],
             "bottom": [(x, y) for x in range(w) for y in range(max(0, h - 4), h)],
             "left": [(x, y) for x in range(min(4, w)) for y in range(h)],
             "right": [(x, y) for x in range(max(0, w - 4), w) for y in range(h)]}
    for name, cells in edges.items():
        colors: dict[tuple[int, int, int], int] = {}
        total = 0
        for x, y in cells:
            r, g, b, a = px[x, y]
            if a < 128 or (r, g, b) == (255, 255, 255):
                # skip transparent/AA fringe (rounded corners) and the white
                # canvas Chrome paints outside the SVG's own background
                continue
            colors[(r, g, b)] = colors.get((r, g, b), 0) + 1
            total += 1
        if total == 0:
            continue
        dominant = max(colors, key=colors.get)
        others = sum(n for c, n in colors.items() if c != dominant)
        if others / total > 0.06:
            issues.append(
                f"edge '{name}' has {others / total:.0%} non-background pixels in the 4px band "
                f"- content may touch/clip the edge; inspect the render"
            )
    return issues


# ---------------------------------------------------------------- main

def audit_svg_static(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"invalid SVG XML: {exc}"]
    if "viewBox" not in root.attrib:
        issues.append("missing viewBox")
    text = path.read_text(encoding="utf-8")
    if REMOTE_FONT.search(text):
        issues.append("remote font reference detected (GitHub strips remote fonts)")
    found_title = found_desc = False
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "title":
            found_title = True
        if tag == "desc":
            found_desc = True
        if tag in UNSAFE_SVG_TAGS:
            issues.append(f"contains unsupported <{tag}>")
    if DANGEROUS_REF.search(text):
        issues.append("external/absolute reference detected (http, file, /, drive, or ../)")
    if not found_title:
        issues.append("missing <title>")
    if not found_desc:
        issues.append("missing <desc>")
    return issues


def is_safe_to_render(path: Path) -> tuple[bool, str]:
    """Gate before rendering: refuse to execute content that could escape the
    sandbox (scripts, foreignObject, remote fonts, external/absolute refs).
    Structural quality issues (viewBox/title/desc) do not block rendering."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return False, f"invalid SVG XML: {exc}"
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] in UNSAFE_SVG_TAGS:
            return False, f"contains <{node.tag.rsplit('}', 1)[-1]}>"
    text = path.read_text(encoding="utf-8")
    if REMOTE_FONT.search(text):
        return False, "remote font reference"
    if DANGEROUS_REF.search(text):
        return False, "external/absolute reference"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", help="README.md or an .svg file")
    ap.add_argument("--out", default=None, help="directory for rendered PNG previews")
    args = ap.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.is_file():
        print(f"ERROR: not found: {target}")
        return 2

    if target.suffix.lower() == ".svg":
        sources = [("(direct)", target)]
    else:
        sources = local_svg_sources(target)
        if not sources:
            print(f"No local SVG references found in {target.name}")

    chrome = find_chrome()
    if not chrome and sources:
        print("WARNING: Chrome/Edge not found - rendering skipped (static checks only)")

    out_dir = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="readme-vverify-"))
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for src, svg in sources:
        print(f"\n== {svg.relative_to(target.parent) if target.suffix.lower() != '.svg' else svg.name}")
        static = audit_svg_static(svg)
        contrast = svg_contrast_issues(svg)
        for issue in static:
            print(f"  [static] {issue}")
        for issue in contrast:
            print(f"  [contrast] {issue}")
        if static or contrast:
            failures += 1

        if chrome:
            safe, reason = is_safe_to_render(svg)
            if not safe:
                print(f"  [render] SKIPPED (untrusted content: {reason})")
                failures += 1
                continue
            png = out_dir / (svg.stem + ".png")
            ok, err = render_svg(svg, chrome, png)
            if not ok:
                print(f"  [render] FAILED: {err}")
                failures += 1
            else:
                print(f"  [render] {png.name} ({png.stat().st_size // 1024} KB)")
                for issue in edge_scan_issues(png):
                    print(f"  [edge] {issue}")
                    failures += 1
        else:
            print("  [render] skipped (no Chrome/Edge)")

    print(f"\nRendered previews: {out_dir}")
    print("Next: visually inspect every PNG at GitHub width (~900px) and 360px, "
          "then confirm with a vision model before publishing.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
