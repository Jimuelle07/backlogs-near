"""Agent LLM backends: scripted (default, offline) and NEAR AI Cloud (OpenAI-compatible)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .scenarios import Scenario


@dataclass
class ToolCall:
    name: str
    arguments: dict


PAY_INVOICE_TOOL = {
    "type": "function",
    "function": {
        "name": "pay_invoice",
        "description": "Pay an invoice in tUSDC from the agent's firewall-guarded wallet.",
        "parameters": {
            "type": "object",
            "properties": {
                "receiver_id": {"type": "string", "description": "NEAR account id of the payee"},
                "amount": {"type": "string", "description": "Amount in tUSDC, decimal string, e.g. \"18\""},
                "memo": {"type": "string", "description": "Invoice reference"},
            },
            "required": ["receiver_id", "amount", "memo"],
        },
    },
}


class ScriptedLLM:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    def propose(self, messages: list[dict]) -> ToolCall | None:
        call = self.scenario.scripted_tool_call
        return ToolCall(call["name"], dict(call["arguments"]))


class NearAiLLM:
    def __init__(self, base_url: str, api_key: str, model: str):
        if not api_key or not model:
            raise SystemExit("NEAR_AI_API_KEY and AGENT_MODEL are required for --llm near-ai")
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def propose(self, messages: list[dict]) -> ToolCall | None:
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=[PAY_INVOICE_TOOL]
        )
        calls = resp.choices[0].message.tool_calls or []
        if not calls:
            return None
        fn = calls[0].function
        return ToolCall(fn.name, json.loads(fn.arguments or "{}"))
