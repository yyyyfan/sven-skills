---
name: codex-antigravity-cli
description: 在 Grok Bot 的 Linux box 上安装、登录、无头调用并监控 Codex CLI 与 Antigravity CLI（agy）额度；适用于把编码/文件类任务外包给这两个 CLI、由 Bot 只负责验收，以及每日额度巡检。
---

# Codex CLI 与 Antigravity CLI（Grok Bot box）

让 Grok Bot 把执行类任务（写代码、处理文件、数据处理）交给 Codex 或 Antigravity CLI，Bot 只负责派活与验收，节省 Grok 额度。用中文报告结果。

## 固定偏好与边界

- Codex 默认模型 `gpt-6.1-sol`，推理强度 `medium`；Antigravity 默认 `gemini-3.8-flash-high`。
- 登录一律走用户**自己浏览器**里的授权（设备码 / OAuth 授权码）。**绝不**在 box 浏览器里登录 Google/OpenAI 账号。
- 授权码通过掩码的密钥请求（环境变量）交给 Agent，不在聊天或日志中回显；本文件与仓库中不保存任何令牌、授权码或账号信息。
- 不读取或复制 `~/.codex/auth.json`、`~/.gemini` 等凭据文件的内容。
- 为什么不用 Gemini CLI：个人 Google 账号登录会被拒（"This client is no longer supported for Gemini Code Assist for individuals… migrate to Antigravity"）；Gemini Pro 订阅也不作用于 AI Studio API key（免费档 key 调 `gemini-3.8-flash` 常返回 503）。因此统一用 `agy` + Google OAuth。

## 安装

```bash
# Codex（实测 v0.163.0，Node 20）
npm install -g @openai/codex
codex --version

# Antigravity CLI（实测 1.4.0），安装到 ~/.local/bin/agy
curl -fsSL https://antigravity.google/cli/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
agy --version
```

## 登录

### Codex（设备码）

1. 在 tmux 中运行：`tmux new -d -s cxlogin 'codex login --device-auth'`，再 `tmux capture-pane -pt cxlogin`。
2. 输出含 `https://auth.openai.com/codex/device` 与一次性代码（约 15 分钟有效），发给用户在自己浏览器打开并输入。
3. 用户完成后验证：`codex login status` 应输出 `Logged in using ChatGPT`。

### Antigravity（Google OAuth）

1. `unset GEMINI_API_KEY`（否则会优先走 API key），在 tmux 里交互运行：`tmux new -d -s agylogin -x 250 -y 60 'agy'`。
2. 选择 `1. Google OAuth`，agy 打印一条 `accounts.google.com` OAuth URL。pane 中 URL 会折行：用 `capture-pane -pJ` 或手动拼接各行，注意 `state` 参数在文字 `If you aren't...` 之前结束，不要把提示文字拼进去。
3. 把链接发给用户，在自己浏览器登录订阅了 Gemini Pro 的账号，页面显示授权码。
4. 用掩码密钥请求把授权码放进环境变量（如 `$AGY_CODE`），然后：
   `tmux send-keys -t agylogin -l "$AGY_CODE" && tmux send-keys -t agylogin Enter`
5. 之后按 Enter 走完引导（主题等），退出。用 `agy -p "reply OK" --model gemini-3.8-flash-high` 验证。

## 默认模型配置

`~/.codex/config.toml`：

```toml
model = "gpt-6.1-sol"
model_reasoning_effort = "medium"
```

- `sol-6.1` 这种名字会被拒；可用 slug 见 `~/.codex/models_cache.json`。
- `agy models` 列出可用模型：`gemini-3.8-flash-high/medium/low`、`claude-sonnet-4-6`、`claude-opus-4-6-thinking`、`gpt-oss-120b-medium`。

## 无头调用

```bash
# Codex：stdin 必须关闭，否则卡在 "Reading additional input from stdin"
codex exec --skip-git-repo-check "<任务>" </dev/null

# Antigravity
agy -p "<任务>" --model gemini-3.8-flash-high
#   可选：--output-format json  --dangerously-skip-permissions  --print-timeout <秒>
```

注意：`--skip-git-repo-check` 只属于 `codex exec`，交互式 `codex` 不接受该参数。

工作模式：Bot 写清任务与验收标准 → 交给 CLI 执行 → Bot 检查产物（diff、测试、输出）→ 不合格则带反馈重派 → 合格后交付用户。浏览器操作、联网调研仍由 Bot 自己做。

## 额度监控

Grok Bot 客户端没有显示这两者额度的地方，需由 Agent 查询：

- **Antigravity**：无头即可，`agy -p "/usage" </dev/null` 输出制表符分隔表格，例如：
  ```
  Gemini Models          Weekly Limit Remaining     98%   <UTC 重置时间>
  Gemini Models          Five Hour Limit Remaining  98%   <UTC 重置时间>
  Claude and GPT models  Weekly Limit Remaining     100%  <UTC 重置时间>
  Claude and GPT models  Five Hour Limit Remaining  100%  <UTC 重置时间>
  ```
- **Codex**：`/status` 只在交互界面可用，用 tmux 驱动：
  ```bash
  cd /tmp && tmux new -d -s cxs -x 200 -y 50 "bash -lc 'codex; sleep 30'"
  sleep 8; tmux send-keys -t cxs Enter; sleep 2
  tmux send-keys -t cxs -l '/status'; sleep 1; tmux send-keys -t cxs Enter; sleep 5
  tmux capture-pane -pt cxs | grep -E 'Model:|Weekly limit|Credits'
  tmux kill-session -t cxs
  ```
  读取 `Weekly limit: … NN% left (resets …)` 与 `Credits:` 行。登录状态用 `codex login status`。
- 时间戳以 `Z` 结尾的是 UTC，向用户报告时换算到用户时区（如北京时间）。

### 每日巡检（建议每天 9:00）

1. 运行上面两项检查及 `codex login status`。
2. 汇报各项剩余百分比与重置时间。
3. 任一项低于 20%、命令报未登录/授权过期时特别提醒，并给出重新登录步骤。

## 调用示例

"用 Codex 帮我写个脚本……" / "让 Antigravity 处理这个文件……" / "Codex 和 Antigravity 额度还剩多少？"
