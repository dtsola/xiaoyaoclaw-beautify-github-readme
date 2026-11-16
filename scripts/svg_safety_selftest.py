# -*- coding: utf-8 -*-
"""svg_safety 回归自测：证明不可信 SVG 的可执行形态会被拒绝。

用法：python scripts/svg_safety_selftest.py

只做两件事：在临时目录写几份小 SVG，调用 svg_safety.safety_issues() 判定，
打印 PASS/FAIL。不联网、不启动浏览器、不修改仓库文件。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svg_safety import safety_issues  # noqa: E402

BASE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">{}</svg>'

# (说明, SVG 内容, 是否应当被拒绝)
CASES = [
    ("普通 SVG 允许通过",
     BASE.format('<rect width="10" height="10" fill="#123"/>'), False),
    ("内联渐变 + fragment 引用允许通过",
     BASE.format('<defs><linearGradient id="g"><stop offset="0"/></linearGradient></defs>'
                 '<rect width="10" height="10" fill="url(#g)"/>'), False),
    ("事件属性 onload 被拒绝",
     BASE.format('<rect width="10" height="10" onload="alert(1)"/>'), True),
    ("事件属性 onclick 被拒绝",
     BASE.format('<rect width="10" height="10" onclick="fetch(\'//evil\')"/>'), True),
    ("SMIL 安装 onload 被拒绝",
     BASE.format('<rect width="10" height="10">'
                 '<set attributeName="onload" to="alert(1)"/></rect>'), True),
    ("<script> 被拒绝",
     BASE.format('<script>alert(1)</script>'), True),
    ("<foreignObject> 被拒绝",
     BASE.format('<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">x</div>'
                 '</foreignObject>'), True),
    ("远程 href 被拒绝",
     BASE.format('<image href="https://example.com/a.png" width="10" height="10"/>'), True),
    ("远程 CSS url() 被拒绝",
     BASE.format('<style>rect{fill:url(https://example.com/p.svg#g)}</style>'
                 '<rect width="10" height="10"/>'), True),
    ("@import 被拒绝",
     BASE.format('<style>@import url("https://example.com/a.css");</style>'), True),
    ("父目录遍历被拒绝",
     BASE.format('<image href="../secret.png" width="10" height="10"/>'), True),
]


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory(prefix="svg-safety-selftest-") as td:
        tmp = Path(td)
        for index, (label, content, should_reject) in enumerate(CASES):
            path = tmp / f"case{index}.svg"
            path.write_text(content, encoding="utf-8")
            issues = safety_issues(path)
            rejected = bool(issues)
            ok = rejected == should_reject
            mark = "PASS" if ok else "FAIL"
            detail = "" if ok else f" → 实际 issues={issues!r}"
            print(f"[{mark}] {label}{detail}")
            if not ok:
                failures += 1

    total = len(CASES)
    print(f"\n{total - failures}/{total} passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
