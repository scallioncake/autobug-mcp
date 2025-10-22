from __future__ import annotations

from pathlib import Path
from rich.console import Console

console = Console()


def ensure_project_dir(vault_root: Path, project: str) -> Path:
    project_dir = vault_root / project
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def next_sequence_filename(project_dir: Path, prefix: str) -> tuple[str, Path]:
    """查找指定前缀的下一个序号文件，例如 debug001、bug002。"""
    existing = sorted(project_dir.glob(f"{prefix}*.md"))
    max_idx = 0
    for item in existing:
        stem = item.stem
        if stem.startswith(prefix):
            suffix = stem[len(prefix) :]
            if suffix.isdigit():
                max_idx = max(max_idx, int(suffix))

    next_idx = max_idx + 1
    sequence = f"{next_idx:03d}"
    filename = project_dir / f"{prefix}{sequence}.md"
    return sequence, filename


def next_bug_filename(project_dir: Path) -> tuple[str, Path]:
    """兼容旧逻辑：Bug 报告文件命名为 bugNNN.md。"""
    return next_sequence_filename(project_dir, "bug")


def write_report_file(path: Path, content: str, label: str = "报告") -> None:
    if path.exists():
        console.print(f"[yellow]警告：目标文件已存在，跳过写入: {path}[/yellow]")
        return

    path.write_text(content, encoding="utf-8")
    console.print(f"[green]已创建 {label} 文档: {path}[/green]")


def write_bug_file(path: Path, content: str) -> None:
    """向后兼容的别名。"""
    write_report_file(path, content, label="Bug")
