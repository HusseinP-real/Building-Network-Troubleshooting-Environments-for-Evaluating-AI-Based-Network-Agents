"""Gemini native REST adapter with the benchmark's existing read-only MCP tools."""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import json
import os
from pathlib import Path
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GeminiAPIError(RuntimeError):
    def __init__(self, status: int):
        self.status = status
        message = "Google service temporarily unavailable" if status in (500, 502, 503, 504) else "check model access, quota and key configuration"
        super().__init__(f"Gemini API HTTP {status}; {message}")


def api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set GEMINI_API_KEY in the server terminal, then restart the dashboard")
    return key


def _request(model: str, payload: dict) -> dict:
    if not re.fullmatch(r"gemini-[A-Za-z0-9._-]+", model):
        raise ValueError("Invalid Gemini model ID")
    key = api_key()
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            return json.load(response)
    except HTTPError as exc:
        # Do not persist remote error bodies, which may contain request details.
        raise GeminiAPIError(exc.code) from None
    except URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise RuntimeError("Gemini HTTPS certificate verification failed; check the Python CA certificate configuration") from None
        raise RuntimeError(f"Gemini API connection failed ({type(exc.reason).__name__})") from None
    except TimeoutError:
        raise RuntimeError("Gemini API connection failed or timed out") from None


async def generate(model: str, payload: dict) -> dict:
    for attempt in range(3):
        try:
            return await asyncio.to_thread(_request, model, payload)
        except GeminiAPIError as exc:
            if exc.status not in (500, 502, 503, 504) or attempt == 2:
                raise
            delay = 2 ** (attempt + 1)
            print(f"Gemini: HTTP {exc.status}; retrying in {delay}s ({attempt + 1}/2)", flush=True)
            await asyncio.sleep(delay)


def _content(response: dict) -> dict:
    candidates = response.get("candidates", [])
    if not candidates or not candidates[0].get("content", {}).get("parts"):
        raise RuntimeError("Gemini returned no content (possibly blocked)")
    return candidates[0]["content"]


def _text(content: dict) -> str:
    return "\n".join(p["text"] for p in content["parts"] if "text" in p and not p.get("thought")).strip()


async def judge(model: str, system_prompt: str, payload: dict) -> dict:
    response = await generate(model, {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(payload)}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    })
    return {"text": _text(_content(response)), "usage": response.get("usageMetadata", {})}


def _skills(agent_dir: Path) -> dict[str, Path]:
    root = (agent_dir / ".claude/skills").resolve()
    return {p.parent.name: p for p in root.glob("*/SKILL.md") if p.resolve().is_relative_to(root)}


async def run(model: str, prompt: str, system_prompt: str, max_turns: int,
              servers: dict, agent_dir: Path) -> dict:
    trace, usage, final, tool_calls = [], {}, "", 0
    skills = _skills(agent_dir) if servers else {}
    declarations, handlers = [], {}
    async with AsyncExitStack() as stack:
        if servers:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            for server_name, config in servers.items():
                # Only operational environment reaches the tool server; no provider keys.
                env = {k: os.environ[k] for k in ("PATH", "HOME", "TMPDIR") if k in os.environ}
                env.update(config.get("env", {}))
                read, write = await stack.enter_async_context(stdio_client(StdioServerParameters(
                    command=config["command"], args=config["args"], env=env,
                )))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                for tool in (await session.list_tools()).tools:
                    name = f"mcp__{server_name}__{tool.name}"
                    declarations.append({"name": name, "description": tool.description or name,
                                         "parametersJsonSchema": tool.inputSchema})
                    handlers[name] = (session, tool.name)
        if skills:
            catalog = []
            for name, path in sorted(skills.items()):
                description = re.search(r"^description:\s*(.+)$", path.read_text(), re.MULTILINE)
                catalog.append(f"{name}: {description.group(1) if description else name}")
            system_prompt += "\n\nAvailable project Skills (load with Skill):\n" + "\n".join(catalog)
            declarations.append({"name": "Skill", "description": "Load a project diagnostic Skill by name.",
                                 "parametersJsonSchema": {"type": "object", "properties": {"skill": {"type": "string"}}, "required": ["skill"]}})
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        for _ in range(max_turns):
            print(f"Gemini: requesting {model}, turn {_ + 1}/{max_turns} (waiting for Google API response)...", flush=True)
            payload = {"systemInstruction": {"parts": [{"text": system_prompt}]}, "contents": contents}
            if declarations:
                payload["tools"] = [{"functionDeclarations": declarations}]
            response = await generate(model, payload)
            print("Gemini: API response received", flush=True)
            for key, value in response.get("usageMetadata", {}).items():
                if isinstance(value, (int, float)):
                    usage[key] = usage.get(key, 0) + value
            content = _content(response)
            # Keep the full model content, including thought signatures, for subsequent turns.
            contents.append(content)
            text = _text(content)
            if text:
                final = text
                trace.append({"kind": "text", "text": text})
            calls = [p["functionCall"] for p in content["parts"] if "functionCall" in p]
            if not calls:
                return {"sdk_error": None, "hit_max_turns": False, "system_prompt": system_prompt,
                        "available_mcp_servers": list(servers), "final_text": final, "trace": trace,
                        "tool_calls": tool_calls, "usage": usage, "total_cost_usd": None}
            results = []
            for call in calls:
                name, args = call["name"], call.get("args", {})
                tool_calls += 1
                trace.append({"kind": "tool", "name": name, "input": args})
                if name == "Skill" and skills:
                    path = skills.get(args.get("skill"))
                    result = {"content": path.read_text() if path else "Unknown Skill"}
                elif name in handlers:
                    session, tool_name = handlers[name]
                    output = await session.call_tool(tool_name, args)
                    result = output.model_dump(mode="json", exclude_none=True)
                else:
                    result = {"error": "Unknown or unavailable tool"}
                trace.append({"kind": "tool_result", "content": json.dumps(result)})
                function_response = {"name": name, "response": result}
                if "id" in call:
                    function_response["id"] = call["id"]
                results.append({"functionResponse": function_response})
            contents.append({"role": "user", "parts": results})
    return {"sdk_error": "Gemini reached maximum number of turns", "hit_max_turns": True,
            "system_prompt": system_prompt, "available_mcp_servers": list(servers),
            "final_text": final, "trace": trace, "tool_calls": tool_calls,
            "usage": usage, "total_cost_usd": None}
