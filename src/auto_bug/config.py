from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError
from rich.console import Console

console = Console()


class PromptConfig(BaseModel):
    system: Optional[str] = None
    default_tags: Optional[str] = None


class LLMConfig(BaseModel):
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-4o-mini")
    api_key_env: str = Field(default="OPENAI_API_KEY")
    api_base: Optional[str] = None
    timeout: float = 30.0
    prompt: PromptConfig = Field(default_factory=PromptConfig)


class AppConfig(BaseModel):
    vault_root: Path
    default_project: str = Field(default="default_project")
    template_path: Path = Field(default=Path("templates/bug_report.md.j2"))
    debug_template_path: Path = Field(default=Path("templates/debug_report.md.j2"))
    llm: LLMConfig = Field(default_factory=LLMConfig)

    def resolve_template(self, base_dir: Path) -> Path:
        template = self.template_path
        if not template.is_absolute():
            template = base_dir / template
        return template

    def resolve_debug_template(self, base_dir: Path) -> Path:
        template = self.debug_template_path
        if not template.is_absolute():
            template = base_dir / template
        return template


def load_config(base_dir: Path, filename: str = "config.toml") -> AppConfig:
    config_file = base_dir / filename
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件未找到: {config_file}")

    with config_file.open("rb") as fp:
        data = tomllib.load(fp)

    try:
        config = AppConfig.model_validate(data)
    except ValidationError as exc:
        console.print("[red]配置文件解析失败：[/red]")
        console.print(exc)
        raise

    return config


def get_api_key(env_name: str) -> str:
    api_key = os.getenv(env_name)
    if not api_key:
        raise RuntimeError(f"环境变量 {env_name} 未设置，无法读取 LLM API Key")
    return api_key
