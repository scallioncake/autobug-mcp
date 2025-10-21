from __future__ import annotations

from pathlib import Path
from typing import Iterable


def read_log(source: str) -> str:
    """读取日志内容；source 为文件路径或 '-'（代表 stdin）。"""
    if source == "-":
        import sys

        return sys.stdin.read()

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"日志文件不存在: {source}")

    return path.read_text(encoding="utf-8", errors="ignore")


def extract_excerpt(raw: str, max_lines: int = 80) -> str:
    """截取日志最后若干行，防止 token 过长。"""
    lines = raw.strip().splitlines()
    if len(lines) <= max_lines:
        return raw.strip()
    return "\n".join(lines[-max_lines:])


def extract_stack_summary(raw: str, keywords: Iterable[str] | None = None, max_lines: int = 40) -> str:
    """简单提取包含关键字的行，用于堆栈摘要。"""
    if keywords is None:
        keywords = ("Traceback", "Error", "Exception", "AssertionError", "at ", "File \"")

    selected = [
        line for line in raw.splitlines()
        if any(keyword in line for keyword in keywords)
    ]

    if not selected:
        selected = raw.splitlines()[-max_lines:]

    return "\n".join(selected[-max_lines:])
