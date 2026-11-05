# Switching between Claude and DeepSeek in the dashboard

Under Launch benchmark, choose Claude Haiku, DeepSeek Flash, or DeepSeek V4 Pro from Agent model. Select Quality judge separately and keep the same judge for formal comparisons. Same as agent makes a separate judging call using the same model and may incur charges.

## Local credentials through terminal environment variables

Create an API key at https://platform.deepseek.com/. Do not paste credentials into chat, the dashboard, or source code.

Run the following in macOS Terminal using zsh. Key input is hidden and the literal key is not saved in command history:

```zsh
read -s 'DEEPSEEK_API_KEY?DeepSeek API key: '
export DEEPSEEK_API_KEY
printf '\n'
cd /Users/husseinpeng/Documents/ChatGPT/Capstone/enterprise-topology/SOFT3888_TU14_04/EnterpriseTopology
python3 dashboard/server.py --nika-root /Users/husseinpeng/Documents/ChatGPT/Capstone/nika-demo
```

If an existing server occupies port 8765, stop it with Ctrl+C in its original terminal before restarting, or add `--port 8766`. Open the URL printed by the server. Start the server from the terminal where the key was set; an already running service does not inherit new environment variables.

The key applies only to the current terminal session and its child processes. Set it again after closing the terminal. No key file is created and `.env` is not read.

With only DeepSeek configured, select DeepSeek for Agent model and Same as agent or DeepSeek for Quality judge. The default Claude judge additionally requires `ANTHROPIC_API_KEY` or an existing Claude login.

## Switching behavior and validation scope

The backend sets the SDK subprocess environment separately for each diagnosis and judging request. DeepSeek uses `https://api.deepseek.com/anthropic` and `DEEPSEEK_API_KEY`; Claude uses the official Anthropic endpoint. This does not change the terminal's overall Claude configuration. Diagnosis and judging reuse SADE tools, prompts, and scoring.

Interface reference: https://api-docs.deepseek.com/guides/anthropic_api/

Offline tests have been performed. Actual API behavior, tool-call compatibility, and cost require validation with real credentials. No paid benchmark was run in advance.
