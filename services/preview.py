"""
Dry-run and preview helpers.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class FilePreview:
    path: str
    changed: bool
    diff: str


def build_unified_diff(
    before: str,
    after: str,
    *,
    fromfile: str = "before",
    tofile: str = "after",
) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )
    )


def preview_text_change(path: str, before: str, after: str) -> FilePreview:
    return FilePreview(
        path=path,
        changed=before != after,
        diff=build_unified_diff(before, after, fromfile=f"{path} (before)", tofile=f"{path} (after)"),
    )
