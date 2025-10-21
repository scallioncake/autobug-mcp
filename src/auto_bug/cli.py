from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress

from .config import AppConfig, load_config
from .core import GenerationResult, generate_bug_record
from .logs import read_log

console = Console()
app = typer.Typer(help="auto-bug CLI：日志 -> Obsidian Bug 表单")


def select_config(base_dir: Path, config_file: Optional[Path]) -> AppConfig:
    if config_file:
        return load_config(config_file.parent, config_file.name)
    return load_config(base_dir)


@app.command()
def ingest(
    project: Optional[str] = typer.Argument(None, help="项目名称，不填则使用 config 默认值"),
    source: str = typer.Argument(..., help="日志文件路径，或 '-' 表示从标准输入读取"),
    command: str = typer.Option("unknown", "--command", "-c", help="触发日志的命令"),
    environment: str = typer.Option("local", "--env", help="触发环境描述"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-f", help="指定配置文件路径（默认仓库根目录 config.toml）"
    ),
    no_persist: bool = typer.Option(
        False, "--no-persist", help="仅输出 Markdown，不写入 Obsidian Vault"
    ),
) -> None:
    """读取日志 -> 调用 LLM -> 输出 Markdown 文件到 Obsidian Vault。"""
    load_dotenv()
    base_dir = Path.cwd()

    try:
        config = select_config(base_dir, config_path)
    except Exception as exc:  # pylint: disable=broad-except
        console.print(f"[red]配置加载失败：{exc}[/red]")
        raise typer.Exit(code=1)

    target_project = project or config.default_project
    try:
        log_text = read_log(source)
    except Exception as exc:  # pylint: disable=broad-except
        console.print(f"[red]读取日志失败：{exc}[/red]")
        raise typer.Exit(code=1)

    result: GenerationResult
    with Progress() as progress:
        task = progress.add_task("调用 LLM 生成报告", total=None)
        try:
            result = generate_bug_record(
                base_dir=base_dir,
                config=config,
                project=target_project,
                log_text=log_text,
                command=command,
                environment=environment,
                persist=not no_persist,
            )
        except Exception as exc:  # pylint: disable=broad-except
            progress.update(task, completed=True)
            console.print(f"[red]生成 Bug 报告失败：{exc}[/red]")
            raise typer.Exit(code=1)
        progress.update(task, completed=True)

    console.print("[cyan]Bug 标题：[/cyan]" + result.report.bug_title)
    if result.file_path:
        console.print(f"[green]已写入文件：{result.file_path}[/green]")
    else:
        console.print("[yellow]未持久化到文件，以下为 Markdown 内容：[/yellow]")
        console.print(result.markdown)
