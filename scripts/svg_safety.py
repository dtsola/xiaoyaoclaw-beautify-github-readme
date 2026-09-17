#!/usr/bin/env python3
"""Shared trust boundary for untrusted SVG input, plus the single funnel for
every external process this skill starts.

Every script in this skill that renders repository-supplied SVG (visual_verify.py,
render_motion_gif.py) must run the same checks before handing a file to a
renderer. This module is the single source of truth for those checks so the two
render paths cannot drift apart again.

Trust model
-----------
A README (and every asset it references) is **untrusted data**. It may be
written by a third party and may embed instructions, external resource
references, or parser-stressing content. Static checks are therefore
fail-closed: anything that could make a renderer talk to the network, reach
outside the isolated render directory, or execute code is refused, and the
script reports the reason instead of rendering.

External processes
------------------
`run_external()` is the only place in this skill that spawns a child process.
Callers pass a pre-validated argument list (never a shell string), and it
enforces `shell=False`, a hard timeout, and a bounded error report — so a
malformed asset cannot hang the run, and there is exactly one code path to
audit for process launching.

Checks
------
1. XML well-formedness (unparseable input is refused).
2. No executable / embedding elements: <script>, <foreignObject>, <iframe>,
   <object>, <embed>, <audio>, <video>, <canvas>.
3. No remote fonts or stylesheets (@font-face, Google Fonts, <link rel=stylesheet>).
4. Every resource-bearing reference (href / xlink:href / src, and CSS `url(...)`)
   must be local: a `#fragment` or a `data:` URI. Remote URLs, protocol-relative
   URLs, root-absolute paths, Windows-drive paths and parent-directory traversal
   are refused. Plain sibling-relative references are permitted but unresolvable
   — they resolve to the throwaway preview origin, which serves exactly one file.
5. No CSS `@import` (always an out-of-band fetch).
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

# Elements that can execute code, embed foreign content, or pull in a document.
UNSAFE_SVG_TAGS = {
    "script",
    "foreignObject",
    "iframe",
    "object",
    "embed",
    "audio",
    "video",
    "canvas",
}

# Remote fonts / stylesheets: GitHub strips them anyway, and they are an
# out-of-band network fetch when rendered locally.
REMOTE_FONT = r"@font-face|fonts\.(googleapis|gstatic)\.com|<link\b[^>]*stylesheet"

# Attributes that carry a resource reference.
REF_ATTRS = {"href", "src"}

# href/src values that leave the single-file preview origin. `data:` URIs and
# `#fragment` references are intentionally NOT matched here.
DANGEROUS_REF = (
    r"""(?:(?:xlink:)?href|src)\s*=\s*["']\s*(?:(?:https?|file|ftp|javascript|vbscript|blob):|//|/|[A-Za-z]:[\\/]|\.\./)"""
)

# One target inside a CSS url(...) token, e.g. url(#grad) or url("hero.png").
URL_TOKEN = r"""url\(\s*(['"]?)([^'")]*)\1\s*\)"""

# A target that leaves the preview origin (schemes, protocol-relative,
# root-absolute, drive letters, parent-directory traversal).
EXTERNAL_TARGET = r"""(?i)^(?:(?:https?|file|ftp|javascript|vbscript|blob):|//|/|[A-Za-z]:[\\/])|(?:^|[\\/])\.\.(?:[\\/]|$)"""

# Any @import at all — it is always an out-of-band fetch.
IMPORT_RULE = r"@import\b"


def _local_tag(tag: str) -> str:
    """Return the local name of a possibly namespaced tag."""
    return tag.rsplit("}", 1)[-1]


def safety_issues(path: Path) -> list[str]:
    """Return the list of blocking trust-boundary violations for `path`.

    An empty list means the file is safe to hand to a renderer. The first item
    is a short machine-friendly reason, suitable for a SKIPPED/FAILED line.
    """
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"invalid SVG XML: {exc}"]
    except OSError as exc:
        return [f"unreadable SVG: {exc}"]

    issues: list[str] = []

    for node in root.iter():
        tag = _local_tag(node.tag)
        if tag in UNSAFE_SVG_TAGS:
            issues.append(f"contains <{tag}>")
        for name, value in node.attrib.items():
            if not isinstance(value, str) or not value.strip():
                continue
            local = _local_tag(name).lower()
            if local in REF_ATTRS:
                if re.match(EXTERNAL_TARGET, value.strip()):
                    issues.append(
                        f"external/absolute reference in {_local_tag(name)}: {value.strip()[:60]}"
                    )
            if "url(" in value.lower():
                for _, target in re.findall(URL_TOKEN, value, re.I):
                    target = target.strip()
                    if target == "" or target.startswith("#"):
                        continue
                    if re.match(EXTERNAL_TARGET, target):
                        issues.append(f"external resource in url(): {target[:60]}")
            if IMPORT_RULE in value or re.search(IMPORT_RULE, value, re.I):
                issues.append("CSS @import (out-of-band stylesheet fetch)")

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"unreadable SVG: {exc}"]

    if re.search(REMOTE_FONT, text, re.I):
        issues.append("remote font or stylesheet reference")
    if re.search(IMPORT_RULE, text, re.I):
        issues.append("CSS @import (out-of-band stylesheet fetch)")
    if re.search(DANGEROUS_REF, text, re.I):
        issues.append(
            "external/absolute reference detected (http, file, //, /, drive, or ../)"
        )
    # CSS `url(...)` tokens also appear in stylesheet *text* (inside <style> or
    # CDATA), not only in attributes — so scan the raw document as well.
    for _, target in re.findall(URL_TOKEN, text, re.I):
        target = target.strip()
        if target == "" or target.startswith("#"):
            continue
        if re.match(EXTERNAL_TARGET, target):
            issues.append(f"external resource in url(): {target[:60]}")

    # De-duplicate while keeping order.
    seen: set[str] = set()
    ordered: list[str] = []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            ordered.append(issue)
    return ordered


def is_safe_to_render(path: Path) -> tuple[bool, str]:
    """Gate before rendering. Returns (safe, reason).

    Structural quality problems (missing viewBox/title/desc) do not block
    rendering; only trust-boundary violations do.
    """
    issues = safety_issues(path)
    if issues:
        return False, "; ".join(issues[:3])
    return True, ""


def assert_safe_to_render(path: Path) -> None:
    """Raise SystemExit with a clear message when `path` must not be rendered."""
    safe, reason = is_safe_to_render(path)
    if not safe:
        raise SystemExit(
            f"ERROR: refusing to render {path.name}: {reason}\n"
            "       Untrusted SVG input must be local-only (data: URIs or "
            "#fragment references); reauthor the asset without remote or "
            "external references."
        )


def run_external(
    command: list[str],
    *,
    timeout: int,
    label: str,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run one external tool. The only process-launching path in this skill.

    The caller supplies an explicit argument list built from locally validated
    values — never a shell string — and it is passed to subprocess with
    `shell=False`, so no shell interpretation, globbing, or metacharacter
    expansion can occur. A hard timeout bounds every run, so malformed or
    computationally expensive input cannot hang the skill. Errors carry the
    tool label and a truncated stderr instead of an opaque traceback.

    Raises SystemExit when the tool is missing, times out, or exits non-zero
    (with check=True).
    """
    if not command or not all(isinstance(part, str) for part in command):
        raise SystemExit(f"ERROR: {label}: invalid argument list")

    try:
        return subprocess.run(
            command,
            check=check,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label}: executable not found: {command[0]}") from None
    except subprocess.TimeoutExpired:
        raise SystemExit(f"ERROR: {label}: timed out after {timeout}s") from None
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()[:400]
        raise SystemExit(f"ERROR: {label}: exited {exc.returncode}. {detail}") from None
