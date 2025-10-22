from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Annotated, Optional

from dotenv import load_dotenv
from pydantic import Field
from rich.console import Console

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "缺少 mcp[cli] 依赖，请执行 `pip install '.[mcp]'` 或 "
        "`uv pip install --editable '.[mcp]'` 后再启动 MCP 服务。"
    ) from exc

from .config import load_config
from .core import generate_bug_record, generate_debug_record

console = Console()


def create_server(host: str, port: int, instructions: Optional[str] = None) -> FastMCP:
    server = FastMCP(
        "auto-bug-mcp",
        instructions=instructions
        or "接收日志并生成缺陷报告，必要时写入 Obsidian Vault。",
        host=host,
        port=port,
        log_level="INFO",
    )

    @server.tool(
        name="bug_report",
        description="根据日志文本生成缺陷报告，可选写入 Obsidian。",
    )
    async def bug_report(  # type: ignore[unused-variable]
        log_text: Annotated[str, Field(description="完整的终端/测试日志文本")],
        project: Annotated[
            Optional[str], Field(description="项目名，留空则使用配置默认值")
        ] = None,
        command: Annotated[
            str, Field(description="触发日志的命令或操作")
        ] = "unknown",
        environment: Annotated[
            str, Field(description="执行环境描述，例如 local-dev、CI 等")
        ] = "local",
        persist: Annotated[
            bool, Field(description="是否写入 Obsidian Vault")
        ] = True,
        config_path: Annotated[
            Optional[str],
            Field(description="自定义配置文件路径，默认为工作目录下 config.toml"),
        ] = None,
    ) -> dict[str, object]:
        load_dotenv()
        base_dir = Path.cwd()

        resolved_config: Path
        if config_path:
            resolved_config = Path(config_path).expanduser().resolve()
            config_dir = resolved_config.parent
            config_name = resolved_config.name
        else:
            config_dir = base_dir
            config_name = "config.toml"

        try:
            config = load_config(config_dir, config_name)
        except Exception as exc:  # pragma: no cover - surfaced to MCP client
            raise ValueError(f"配置加载失败：{exc}") from exc

        target_project = project or config.default_project

        try:
            result = generate_bug_record(
                base_dir=base_dir,
                config=config,
                project=target_project,
                log_text=log_text,
                command=command,
                environment=environment,
                persist=persist,
            )
        except Exception as exc:  # pragma: no cover - surfaced to MCP client
            raise ValueError(f"生成缺陷报告失败：{exc}") from exc

        return {
            "project": result.project,
            "sequence": result.sequence,
            "persisted": result.persisted,
            "bug_title": result.report.bug_title,
            "severity": result.report.severity,
            "command": result.command,
            "environment": result.environment,
            "markdown": result.markdown,
            "file_path": str(result.file_path) if result.file_path else None,
            "reproduction_steps": result.report.reproduction_steps,
            "expected": result.report.expected,
            "actual": result.report.actual,
            "probable_cause": result.report.probable_cause,
            "tags": result.report.tags,
        }

    @server.tool(
        name="debug_report",
        description="根据日志生成调试报告模板，包含初始状态、分析过程与解决方案。",
    )
    async def debug_report(  # type: ignore[unused-variable]
        log_text: Annotated[str, Field(description="完整的终端/测试日志文本")],
        project: Annotated[
            Optional[str], Field(description="项目名，留空则使用配置默认值")
        ] = None,
        command: Annotated[
            str, Field(description="触发日志的命令或操作")
        ] = "unknown",
        environment: Annotated[
            str, Field(description="执行环境描述，例如 local-dev、CI 等")
        ] = "local",
        persist: Annotated[
            bool, Field(description="是否写入 Obsidian Vault")
        ] = True,
        config_path: Annotated[
            Optional[str],
            Field(description="自定义配置文件路径，默认为工作目录下 config.toml"),
        ] = None,
    ) -> dict[str, object]:
        load_dotenv()
        base_dir = Path.cwd()

        resolved_config: Path
        if config_path:
            resolved_config = Path(config_path).expanduser().resolve()
            config_dir = resolved_config.parent
            config_name = resolved_config.name
        else:
            config_dir = base_dir
            config_name = "config.toml"

        try:
            config = load_config(config_dir, config_name)
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"配置加载失败：{exc}") from exc

        target_project = project or config.default_project

        try:
            result = generate_debug_record(
                base_dir=base_dir,
                config=config,
                project=target_project,
                log_text=log_text,
                command=command,
                environment=environment,
                persist=persist,
            )
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"生成调试报告失败：{exc}") from exc

        return {
            "project": result.project,
            "sequence": result.sequence,
            "persisted": result.persisted,
            "report_title": result.report.report_title,
            "command": result.command,
            "environment": result.environment,
            "markdown": result.markdown,
            "file_path": str(result.file_path) if result.file_path else None,
            "initial_state": result.report.initial_state,
            "symptom_summary": result.report.symptom_summary,
            "analysis_process": result.report.analysis_process,
            "root_cause": result.report.root_cause,
            "fix_steps": result.report.fix_steps,
            "verification": result.report.verification,
            "lessons": result.report.lessons,
            "extra_notes": result.report.extra_notes,
        }

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="auto-bug MCP server（FastMCP）")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=os.getenv("AUTO_BUG_MCP_TRANSPORT", "sse"),
        help="传输方式：stdio 适合本地调试；sse 会启动 HTTP 服务供 Cursor 等客户端使用。",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("AUTO_BUG_MCP_HOST", "127.0.0.1"),
        help="仅在 transport=sse 时有效，HTTP 服务监听地址。",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AUTO_BUG_MCP_PORT", "8001")),
        help="仅在 transport=sse 时有效，HTTP 服务监听端口。",
    )
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    console.print(
        f"[cyan]Auto-bug MCP server 已启动[/cyan] "
        f"(transport={args.transport}, host={args.host}, port={args.port})"
    )

    try:
        server.run(transport=args.transport)  # 阻塞运行
    except KeyboardInterrupt:
        console.print("[yellow]Auto-bug MCP server 已停止[/yellow]")


if __name__ == "__main__":
    main()
