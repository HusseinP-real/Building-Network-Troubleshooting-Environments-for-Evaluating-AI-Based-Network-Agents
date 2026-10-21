# 在网页切换 Claude / DeepSeek

在 Launch benchmark 的 Agent model 下拉框选择 Claude Haiku、DeepSeek Flash 或 DeepSeek V4 Pro。Quality judge 单独选择；正式对比时固定同一个 judge。Same as agent 是用同一个模型另开一次独立评审调用，也会计费。

## 本地密钥（终端环境变量）

在 https://platform.deepseek.com/ 创建 API key。不要把密钥粘贴到聊天、网页或代码里。

在 macOS Terminal 的 zsh 中运行以下命令；输入密钥时不会显示，也不会把密钥字面量写入命令历史：

```zsh
read -s 'DEEPSEEK_API_KEY?DeepSeek API key: '
export DEEPSEEK_API_KEY
printf '\n'
cd /Users/husseinpeng/Documents/ChatGPT/Capstone/enterprise-topology/SOFT3888_TU14_04/EnterpriseTopology
python3 dashboard/server.py --nika-root /Users/husseinpeng/Documents/ChatGPT/Capstone/nika-demo
```

若旧服务占用 8765，在原终端按 Ctrl+C 停止后重新启动；或给上述命令添加 `--port 8766`。浏览器打开服务打印的网址。必须从设置密钥的同一个终端启动服务；已经运行的服务不会自动获得新环境变量。

密钥只在当前终端会话及其子进程中生效，关闭终端后需重新设置。本次没有自动创建密钥文件，也不读取 `.env`。

只配置 DeepSeek 时，把 Agent model 设为 DeepSeek，Quality judge 选 Same as agent 或 DeepSeek。保留默认 Claude judge 则另需 ANTHROPIC_API_KEY 或已有 Claude 登录。

## 切换原理与验证范围

后端为每次诊断和评审分别设置 SDK 子进程环境。DeepSeek 模型使用 `https://api.deepseek.com/anthropic` 和 DEEPSEEK_API_KEY；Claude 使用官方 Anthropic 接口。不会把整个终端的 Claude 配置改成 DeepSeek。诊断与评审仍复用 SADE 的工具、提示词和评分流程。

接口依据：https://api-docs.deepseek.com/guides/anthropic_api/

已做离线测试；需要设置真实密钥后才能验证实际 API、工具调用兼容性和费用。没有预先执行付费跑分。
