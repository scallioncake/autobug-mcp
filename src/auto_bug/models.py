from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LLMReport(BaseModel):
    bug_title: str = Field(default="未命名缺陷")
    severity: str = Field(default="medium")
    expected: str = Field(default="待补充")
    actual: str = Field(default="待补充")
    probable_cause: str = Field(default="待补充")
    reproduction_steps: List[str] = Field(default_factory=list)
    log_excerpt: str = Field(default="")
    stack_summary: str = Field(default="")
    extra_notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class DebugReport(BaseModel):
    report_title: str = Field(default="调试记录")
    initial_state: str = Field(default="待补充")
    symptom_summary: str = Field(default="待补充")
    analysis_process: List[str] = Field(default_factory=list)
    root_cause: str = Field(default="待补充")
    fix_steps: List[str] = Field(default_factory=list)
    verification: str = Field(default="待补充")
    lessons: Optional[str] = None
    extra_notes: Optional[str] = None


class RenderContext(BaseModel):
    sequence: str
    project: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    environment: str = Field(default="local")
    severity: str
    command: str
    reproduction_steps: List[str]
    expected: str
    actual: str
    probable_cause: str
    log_excerpt: str
    stack_summary: str
    extra_notes: str
    tags: List[str]


class DebugRenderContext(BaseModel):
    sequence: str
    project: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    environment: str = Field(default="local")
    command: str
    report_title: str
    initial_state: str
    symptom_summary: str
    analysis_process: List[str]
    root_cause: str
    fix_steps: List[str]
    verification: str
    lessons: str
    extra_notes: str
    log_excerpt: str
    stack_summary: str
