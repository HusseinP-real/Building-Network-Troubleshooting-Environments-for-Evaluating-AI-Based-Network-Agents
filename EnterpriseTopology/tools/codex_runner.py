"""Subscription-only Codex adapter; host executes only the existing read-only MCP tools.

One bounded SDK turn requests a batch of tool calls or a final answer. This explicit
JSON tool bridge keeps the same 20 model/tool rounds without exposing the lab's
source files, operator commands, or ground truth to a general coding agent.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
import tomllib
from contextlib import AsyncExitStack
from pathlib import Path

MODELS = {"gpt-6.1-sol", "gpt-6.1-terra"}
# Disable ambient integrations and built-in execution. Only the host-side MCP
# bridge below can inspect the network. Never change the user's saved config.
OVERRIDES = (
    'model_provider="openai"',
    'web_search="disabled"',
    'features.shell_tool=false',
    'features.apply_patch=false',
    'features.code_mode=false',
    'features.code_mode_host=false',
    'features.multi_agent=false',
    'features.apps=false',
    'features.skills=false',
    'features.shell_snapshot=false',
    'apps._default.enabled=false',
    'project_doc_max_bytes=0',
)


def _config(cwd, *, subscription=False):
    from openai_codex import CodexConfig

    # SDK merges this with os.environ: explicitly blank keys rather than merely
    # omitting them. Never borrow an API key or persist/copied login credentials.
    env = {key: "" for key in os.environ if any(word in key.upper() for word in ('API_KEY', 'AUTH_TOKEN', 'ACCESS_TOKEN'))}
    env.update(OPENAI_API_KEY="", CODEX_API_KEY="", OPENAI_BASE_URL="https://api.openai.com/v1")
    extra = ('forced_login_method="chatgpt"',) if subscription else ()
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    config_path = home / 'config.toml'
    user_config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
    disabled = tuple(f'mcp_servers.{name}.enabled=false' for name in user_config.get('mcp_servers', {}) if re.fullmatch(r'[A-Za-z0-9_-]+', name))
    disabled += tuple(f'plugins.{name}.enabled=false' for name in user_config.get('plugins', {}) if re.fullmatch(r'[A-Za-z0-9_-]+', name))
    return CodexConfig(cwd=str(cwd), env=env, config_overrides=OVERRIDES + disabled + extra)


def _account_type(response):
    account = response.account
    account = getattr(account, 'root', account)
    return getattr(account, 'type', None)


async def _ensure_isolated(client):
    from openai_codex.generated.v2_all import ConfigReadResponse
    response = await client._client.request('config/read', {'includeLayers': False}, response_model=ConfigReadResponse)
    config = response.model_dump(mode='json', by_alias=True)['config']
    if any(value.get('enabled', True) for value in (config.get('mcp_servers') or {}).values()):
        raise RuntimeError('Ambient Codex MCP servers are still enabled; refusing benchmark inference')
    if config.get('features', {}).get('shell_tool') is not False:
        raise RuntimeError('Codex shell tool is not disabled; refusing benchmark inference')


async def check_subscription(model=None):
    """Read-only authentication/model check; never log in/out or run inference."""
    from openai_codex import AsyncCodex

    if model and model not in MODELS:
        raise ValueError('Unsupported Codex subscription model')
    with tempfile.TemporaryDirectory(prefix='sade-codex-check-') as cwd:
        async with AsyncCodex(config=_config(cwd)) as client:
            if _account_type(await client.account()) not in ('chatgpt', 'chatgptAuthTokens'):
                raise RuntimeError('Codex benchmark requires an existing ChatGPT subscription login. API billing fallback is disabled. Sign in to Codex with ChatGPT first.')
            await _ensure_isolated(client)
            available = await client.models()
            slugs = {entry.model for entry in available.data}
            if model and model not in slugs:
                raise RuntimeError(f'{model} is not available to this Codex subscription/runtime; no alternative model was selected.')
            return {'auth_mode': 'codex-subscription', 'models': sorted(MODELS & slugs)}


ENVELOPE = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'tool_calls': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'properties': {'name': {'type': 'string'}, 'arguments_json': {'type': 'string'}},
            'required': ['name', 'arguments_json'],
        }},
        'final_text': {'type': 'string'},
    },
    'required': ['tool_calls', 'final_text'],
}


def _usage(result):
    if result.usage is None:
        return {}
    u = result.usage.total
    cached = u.cached_input_tokens or 0
    # Codex input includes cached tokens; avoid double-counting on the dashboard.
    return {'input_tokens': max(0, u.input_tokens - cached),
            'cache_read_input_tokens': cached, 'output_tokens': u.output_tokens,
            'cache_creation_input_tokens': 0}


async def run(model, prompt, system_prompt, max_turns, servers, agent_dir):
    from gemini_runner import _skills
    from openai_codex import ApprovalMode, AsyncCodex, Sandbox

    if model not in MODELS:
        raise ValueError('Unsupported Codex subscription model')
    trace, usage, calls, final = [], {}, 0, ''
    skills = _skills(Path(agent_dir)) if servers else {}
    declarations, handlers = [], {}
    async with AsyncExitStack() as stack:
        if servers:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            for name, config in servers.items():
                env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR') if k in os.environ}
                env.update(config.get('env', {}))
                read, write = await stack.enter_async_context(stdio_client(StdioServerParameters(command=config['command'], args=config['args'], env=env)))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                for tool in (await session.list_tools()).tools:
                    key = f'mcp__{name}__{tool.name}'
                    declarations.append({'name': key, 'description': tool.description, 'parameters': tool.inputSchema})
                    handlers[key] = (session, tool.name)
        if skills:
            declarations.append({'name': 'Skill', 'description': 'Load an existing diagnostic skill.', 'parameters': {'type': 'object', 'properties': {'skill': {'type': 'string'}}, 'required': ['skill']}})
            system_prompt += '\nAvailable diagnostic skills: ' + ', '.join(sorted(skills))
        bridge = ('\nUse only the supplied host tool bridge, never built-in tools or local files. '
                  'Return JSON with tool_calls (name, arguments_json) and final_text. '
                  'To inspect the network, put one or more calls in tool_calls and leave final_text empty. '
                  'After receiving results, investigate further or return an empty tool_calls array and '
                  'the complete required diagnosis in final_text. Do not request tools and final answer together.\n'
                  'Available tools: ' + json.dumps(declarations))
        cwd = stack.enter_context(tempfile.TemporaryDirectory(prefix='sade-codex-workspace-'))
        async with AsyncCodex(config=_config(cwd, subscription=True)) as client:
            if _account_type(await client.account()) not in ('chatgpt', 'chatgptAuthTokens'):
                raise RuntimeError('Codex subscription authentication required; API fallback disabled')
            await _ensure_isolated(client)
            thread = await client.thread_start(model=model, model_provider='openai', cwd=cwd,
                                               base_instructions=system_prompt + bridge,
                                               sandbox=Sandbox.read_only, approval_mode=ApprovalMode.deny_all,
                                               ephemeral=True)
            message = prompt
            for turn in range(1, max_turns + 1):
                print(f'Codex subscription: {model}, round {turn}/{max_turns}', flush=True)
                result = await asyncio.wait_for(thread.run(message, output_schema=ENVELOPE), timeout=240)
                usage = _usage(result)  # Thread cumulative usage, not summed again.
                response = json.loads(result.final_response or '')
                batch = response.get('tool_calls', [])
                if not batch:
                    final = response.get('final_text', '')
                    trace.append({'kind': 'text', 'text': final})
                    return _result(None, False, final, trace, calls, usage, system_prompt, servers, turn)
                outputs = []
                for call in batch:
                    name = call['name']
                    args = json.loads(call['arguments_json'])
                    calls += 1
                    trace.append({'kind': 'tool', 'name': name, 'input': args})
                    if name == 'Skill' and skills:
                        path = skills.get(args.get('skill'))
                        output = {'content': path.read_text() if path else 'Unknown Skill'}
                    elif name in handlers:
                        session, tool = handlers[name]
                        output = (await session.call_tool(tool, args)).model_dump(mode='json', exclude_none=True)
                    else:
                        output = {'error': 'Unknown or unavailable tool'}
                    trace.append({'kind': 'tool_result', 'content': json.dumps(output)})
                    outputs.append({'tool': name, 'result': output})
                message = json.dumps({'tool_results': outputs, 'rounds_remaining': max_turns - turn})
    return _result('Codex reached maximum number of turns', True, final, trace, calls, usage, system_prompt, servers, max_turns)


def _result(error, hit_limit, final, trace, calls, usage, prompt, servers, turns):
    return {'sdk_error': error, 'hit_max_turns': hit_limit, 'final_text': final,
            'trace': trace, 'tool_calls': calls, 'usage': usage, 'total_cost_usd': None,
            'system_prompt': prompt, 'available_mcp_servers': list(servers),
            'auth_mode': 'codex-subscription', 'billing_source': 'ChatGPT/Codex subscription',
            'interaction_rounds': turns, 'tool_transport': 'host-json-mcp-bridge'}


async def judge(model, system_prompt, payload):
    # No network tools, skills, files or source ground truth outside the supplied rubric.
    result = await run(model, json.dumps(payload), system_prompt, 1, {}, Path('.'))
    if result['sdk_error']:
        raise RuntimeError(result['sdk_error'])
    return {'text': result['final_text'], 'usage': result['usage']}
