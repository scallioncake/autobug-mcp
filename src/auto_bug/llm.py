from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx
from rich.console import Console

from .config import LLMConfig, get_api_key

console = Console()


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = get_api_key(config.api_key_env)

    def _build_headers(self) -> Dict[str, str]:
        if self.config.provider == "openai":
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        if self.config.provider == "deepseek":
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        raise ValueError(f"未知 provider: {self.config.provider}")

    def _endpoint(self) -> str:
        if self.config.api_base:
            return self.config.api_base
        if self.config.provider == "openai":
            return "https://api.openai.com/v1/chat/completions"
        if self.config.provider == "deepseek":
            return "https://api.deepseek.com/v1/chat/completions"
        raise ValueError(f"未知 provider: {self.config.provider}")

    def create_bug_report(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        endpoint = self._endpoint()
        headers = self._build_headers()

        console.log(f"调用 LLM: provider={self.config.provider}, model={self.config.model}")

        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(endpoint, headers=headers, content=json.dumps(payload))

        if response.status_code >= 400:
            raise RuntimeError(
                f"LLM 请求失败：{response.status_code} {response.text[:200]}"
            )

        data = response.json()
        # OpenAI / DeepSeek 类似结构：choices[0].message.content
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"解析 LLM 响应失败：{data}") from exc

        return content
