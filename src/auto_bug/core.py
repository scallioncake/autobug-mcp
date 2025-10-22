from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from .config import AppConfig
from .llm import LLMClient
from .logs import extract_excerpt, extract_stack_summary
from .models import (
    DebugRenderContext,
    DebugReport,
    LLMReport,
    RenderContext,
)
from .renderer import render_markdown
from .storage import (
    ensure_project_dir,
    next_bug_filename,
    next_sequence_filename,
    write_bug_file,
    write_report_file,
)


class GenerationResult(BaseModel):
    project: str
    sequence: str
    markdown: str
    report: LLMReport
    environment: str
    command: str
    file_path: Optional[Path]
    persisted: bool


class DebugGenerationResult(BaseModel):
    project: str
    sequence: str
    markdown: str
    report: DebugReport
    environment: str
    command: str
    file_path: Optional[Path]
    persisted: bool


def build_messages(
    config: AppConfig,
    project: str,
    command: str,
    log_excerpt: str,
    stack_summary: str,
    default_tags: Optional[str],
) -> list[dict[str, str]]:
    import json

    system_prompt = (
        config.llm.prompt.system
        or "你是一名资深 QA 工程师，请根据提供的日志生成结构化的缺陷报告 JSON。"
    )

    user_payload = {
        "project": project,
        "command": command,
        "log_excerpt": log_excerpt,
        "stack_summary": stack_summary,
        "default_tags": default_tags or "",
        "expected_fields": [
            "bug_title",
            "severity",
            "expected",
            "actual",
            "probable_cause",
            "reproduction_steps",
            "log_excerpt",
            "stack_summary",
            "extra_notes",
            "tags",
        ],
    }

    example = {
        "bug_title": "pytest: test_user_login 在无 token 环境下失败",
        "severity": "high",
        "expected": "在未登录时返回 401 并提示认证失败。",
        "actual": "接口直接崩溃，返回 500。",
        "probable_cause": "登录模块对缺失 token 的判断没有捕获异常。",
        "reproduction_steps": [
            "执行命令: pytest tests/test_login.py::test_user_login",
            "确认环境变量 LOGIN_TOKEN 未设置",
        ],
        "log_excerpt": "AssertionError: Expected status 401 but got 500",
        "stack_summary": "File tests/test_login.py, in test_user_login -> assert resp.status_code == 401",
        "extra_notes": "建议检查最近合并的认证模块改动。",
        "tags": ["登录", "后端"],
    }

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "请严格输出 JSON，不要包含额外说明。\n"
                f"示例：\n```json\n{json.dumps(example, ensure_ascii=False, indent=2)}\n```\n"
                f"当前输入：```json\n{json.dumps(user_payload, ensure_ascii=False)}\n```"
            ),
        },
    ]


def parse_llm_json(raw: str) -> LLMReport:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError(f"未在 LLM 输出中找到 JSON：{raw}")

    json_str = raw[start : end + 1]
    return LLMReport.model_validate_json(json_str)


def build_debug_messages(
    config: AppConfig,
    project: str,
    command: str,
    environment: str,
    log_excerpt: str,
    stack_summary: str,
) -> list[dict[str, str]]:
    import json

    system_prompt = (
        config.llm.prompt.system
        or "你是一名资深工程师，请根据日志总结调试过程，并补全调试报告模板。"
    )

    user_payload = {
        "project": project,
        "command": command,
        "environment": environment,
        "log_excerpt": log_excerpt,
        "stack_summary": stack_summary,
        "expected_fields": [
            "report_title",
            "initial_state",
            "symptom_summary",
            "analysis_process",
            "root_cause",
            "fix_steps",
            "verification",
            "lessons",
            "extra_notes",
        ],
    }

    example = {
        "report_title": "调试记录：支付服务超时",
        "initial_state": "CI 环境执行 nightly 构建时，支付接口稳定在线。",
        "symptom_summary": "调用 `POST /payments` 时 60s 超时，日志出现 TimeoutError。",
        "analysis_process": [
            "复现问题：运行 `python services/payments/run.py`，确认 60s 超时。",
            "检查最近提交：发现网络重试逻辑合并于 2024-05-12。",
            "对比日志：重试已触发 3 次，实际请求未到达第三方沙箱。",
        ],
        "root_cause": "连接池配置错误，最长连接保持时间设为 5 秒导致频繁断开。",
        "fix_steps": [
            "更新 `config/default.yaml` 中的 `keepalive_timeout` 为 120。",
            "部署补丁到 staging 并监控 10 分钟。",
        ],
        "verification": "在 staging 连续跑 20 次支付用例，全部成功且响应时间恢复至 1.2s。",
        "lessons": "回归测试需覆盖连接池参数变更，必要时增加 smoke test。",
        "extra_notes": "与 SRE 同步观察期至 2024-05-20。",
    }

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "请严格输出 JSON，不要包含额外说明。\n"
                f"示例：\n```json\n{json.dumps(example, ensure_ascii=False, indent=2)}\n```\n"
                f"当前输入：```json\n{json.dumps(user_payload, ensure_ascii=False)}\n```"
            ),
        },
    ]


def parse_debug_json(raw: str) -> DebugReport:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError(f"未在 LLM 输出中找到 JSON：{raw}")

    json_str = raw[start : end + 1]
    return DebugReport.model_validate_json(json_str)


def generate_bug_record(
    *,
    base_dir: Path,
    config: AppConfig,
    project: str,
    log_text: str,
    command: str,
    environment: str,
    persist: bool = True,
) -> GenerationResult:
    excerpt = extract_excerpt(log_text)
    stack_summary = extract_stack_summary(log_text)

    messages = build_messages(
        config=config,
        project=project,
        command=command,
        log_excerpt=excerpt,
        stack_summary=stack_summary,
        default_tags=config.llm.prompt.default_tags,
    )

    client = LLMClient(config.llm)
    raw_response = client.create_bug_report(messages)
    report = parse_llm_json(raw_response)

    if config.llm.prompt.default_tags and not report.tags:
        report.tags = [
            tag.strip() for tag in config.llm.prompt.default_tags.split(",") if tag.strip()
        ]

    vault_root = config.vault_root
    project_dir = ensure_project_dir(vault_root, project)
    sequence, filename = next_bug_filename(project_dir)

    context = RenderContext(
        sequence=sequence,
        project=project,
        environment=environment,
        severity=report.severity,
        command=command,
        reproduction_steps=report.reproduction_steps,
        expected=report.expected,
        actual=report.actual,
        probable_cause=report.probable_cause,
        log_excerpt=report.log_excerpt or excerpt,
        stack_summary=report.stack_summary or stack_summary,
        extra_notes=report.extra_notes or "",
        tags=report.tags or [],
    )

    template_path = config.resolve_template(base_dir)
    markdown = render_markdown(template_path, context)

    file_path: Optional[Path] = None
    persisted = False
    if persist:
        write_bug_file(filename, markdown)
        file_path = filename
        persisted = True

    return GenerationResult(
        project=project,
        sequence=sequence,
        markdown=markdown,
        report=report,
        environment=environment,
        command=command,
        file_path=file_path,
        persisted=persisted,
    )


def generate_debug_record(
    *,
    base_dir: Path,
    config: AppConfig,
    project: str,
    log_text: str,
    command: str,
    environment: str,
    persist: bool = True,
) -> DebugGenerationResult:
    excerpt = extract_excerpt(log_text)
    stack_summary = extract_stack_summary(log_text)

    messages = build_debug_messages(
        config=config,
        project=project,
        command=command,
        environment=environment,
        log_excerpt=excerpt,
        stack_summary=stack_summary,
    )

    client = LLMClient(config.llm)
    raw_response = client.create_bug_report(messages)
    report = parse_debug_json(raw_response)

    vault_root = config.vault_root
    project_dir = ensure_project_dir(vault_root, project)
    sequence, filename = next_sequence_filename(project_dir, "debug")

    context = DebugRenderContext(
        sequence=sequence,
        project=project,
        environment=environment,
        command=command,
        report_title=report.report_title,
        initial_state=report.initial_state,
        symptom_summary=report.symptom_summary,
        analysis_process=report.analysis_process,
        root_cause=report.root_cause,
        fix_steps=report.fix_steps,
        verification=report.verification,
        lessons=report.lessons or "",
        extra_notes=report.extra_notes or "",
        log_excerpt=excerpt,
        stack_summary=stack_summary,
    )

    template_path = config.resolve_debug_template(base_dir)
    markdown = render_markdown(template_path, context)

    file_path: Optional[Path] = None
    persisted = False
    if persist:
        write_report_file(filename, markdown, label="调试")
        file_path = filename
        persisted = True

    return DebugGenerationResult(
        project=project,
        sequence=sequence,
        markdown=markdown,
        report=report,
        environment=environment,
        command=command,
        file_path=file_path,
        persisted=persisted,
    )
