# Using Gemini in the benchmark

Both Agent model and Quality judge offer the following Gemini models in the dashboard:

| Model | API free tier listed in the existing configuration |
| --- | --- |
| Gemini 3.8 Flash | Limited free quota |
| Gemini 3.6 Flash | Limited free quota |
| Gemini 3.5 Flash-Lite | Limited free quota |
| Gemini 3.1 Flash-Lite | Limited free quota |
| Gemini 3.1 Pro (Preview) | Not listed |
| Gemini 4 Argon | Not listed |

The original configuration notes reference the [Google API pricing page](https://ai.google.dev/gemini-api/docs/pricing), with a recorded review date of 2026-10-28. These entries describe the existing configuration; this translation does not independently verify model availability or pricing. Free-tier availability depends on project eligibility and quota. Paid projects use API pricing; Google One subscriptions do not determine API billing. For a free-tier API project, select an eligible agent model and use Same as agent or another eligible model for Quality judge.

Model IDs should follow Google's official model catalog. Actual access depends on AI Studio project permissions and quota. The CLI options `--model` and `--judge-model` also accept other model IDs starting with `gemini-`.

## Set the key before the next run

Run the following in macOS Terminal using zsh. Input is hidden and the key value is not saved in command history:

```zsh
read -s 'GEMINI_API_KEY?Google AI Studio API key: '
export GEMINI_API_KEY
printf '\n'
cd /Users/husseinpeng/Documents/ChatGPT/Capstone/enterprise-topology/SOFT3888_TU14_04/EnterpriseTopology
python3 dashboard/server.py --nika-root /Users/husseinpeng/Documents/ChatGPT/Capstone/nika-demo
```

If the previous server occupies the port, stop it with Ctrl+C in its terminal and restart it from the terminal containing the key. A running server does not inherit newly set environment variables. The server does not read `.env` or create a key file. `GOOGLE_API_KEY` is supported as an alias; `GEMINI_API_KEY` takes precedence when both are set.

With only a Gemini key configured, choose Gemini for Agent model and Same as agent or Gemini for Quality judge. The default Claude judge still requires Claude authentication. Same as agent makes a separate judging request and consumes API quota. Use a fixed judge for formal comparisons.

## Integration and validation scope

Gemini uses Google's native `generateContent` REST API, reusing the existing prompts, read-only MCP server, Skill documentation, scoring rules, and fault recovery workflow. Function-call thought signatures and call IDs are preserved. The no-tools mode does not connect to MCP or provide a Skill. Judging is a separate request without tools and uses the same scoring schema.

Without a Gemini key, the dashboard rejects experiment launch and the CLI stops before fault injection. HTTP failures record only the status code; keys are sent in headers. Results record cumulative token usage. Dollar cost is null because it is not estimated; this does not mean the run is free. Token accounting and tool scheduling rounds can differ between models. Reports should state that Gemini uses the native runner, while Claude and DeepSeek use the Claude SDK.

Offline simulations and local stdio MCP integration have been checked. Google API compatibility and live benchmarks have not been validated with a real key.

Official references:

- [Model catalog](https://ai.google.dev/gemini-api/docs/models)
- [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [generateContent API](https://ai.google.dev/api/generate-content)
