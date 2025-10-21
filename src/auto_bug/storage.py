from __future__ import annotations

from pathlib import Path
from rich.console import Console

console = Console()


def ensure_project_dir(vault_root: Path, project: str) -> Path:
    project_dir = vault_root / project
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def next_bug_filename(project_dir: Path) -> tuple[str, Path]:
    """查找下一个 bug 序号（bug001、bug002 ...）。"""
    existing = sorted(project_dir.glob("bug*.md"))
    max_idx = 0
    for item in existing:
        stem = item.stem  # bug001
        if stem.startswith("bug"):
            suffix = stem[3:]
            if suffix.isdigit():
                max_idx = max(max_idx, int(suffix))

    next_idx = max_idx + 1
    sequence = f"{next_idx:03d}"
    filename = project_dir / f"bug{sequence}.md"
    return sequence, filename


def write_bug_file(path: Path, content: str) -> None:
    if path.exists():
        console.print(f"[yellow]警告：目标文件已存在，跳过写入: {path}[/yellow]")
        return

    path.write_text(content, encoding="utf-8")
    console.print(f"[green]已创建 Bug 文档: {path}[/green]")
