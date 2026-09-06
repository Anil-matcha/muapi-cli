# muapi CLI

Official command-line interface for [muapi.ai](https://muapi.ai) — generate images, videos, and audio directly from your terminal.

**Agent-first design** — every command works for both humans (colored output, tables) and AI agents (`--output-json`, `--jq` filtering, semantic exit codes, MCP server mode).

## Install

```bash
# npm (recommended — no Python required)
npm install -g muapi-cli

# pip
pip install muapi-cli

# or run without installing
npx muapi-cli --help
```

## Quick Start

```bash
# New user? Create an account
muapi auth register --email you@example.com --password "..."
muapi auth verify --email you@example.com --otp 123456
muapi auth login --email you@example.com --password "..."

# Or paste an existing API key
muapi auth configure --api-key "YOUR_KEY"

# Generate
muapi image generate "a cyberpunk city at night" --model flux-dev
muapi video generate "a dog running on a beach" --model kling-master
muapi audio create "upbeat lo-fi hip hop for studying"

# Check balance
muapi account balance

# Wait for an existing job
muapi predict wait <request_id>
```

## Commands

### `muapi auth`
| Command | Description |
|---------|-------------|
| `muapi auth register --email x --password y` | Create a new account (sends OTP) |
| `muapi auth verify --email x --otp 123456` | Verify email after registration |
| `muapi auth login --email x --password y` | Log in and save API key automatically |
| `muapi auth forgot-password --email x` | Send password reset OTP |
| `muapi auth reset-password --email x --otp y --password z` | Reset password |
| `muapi auth configure` | Manually save an API key |
| `muapi auth whoami` | Show current API key (masked) |
| `muapi auth logout` | Remove stored API key |

### `muapi account`
| Command | Description |
|---------|-------------|
| `muapi account balance` | Show current credit balance |
| `muapi account topup --amount 20` | Add credits via Stripe checkout |

### `muapi keys`
| Command | Description |
|---------|-------------|
| `muapi keys list` | List all API keys on your account |
| `muapi keys create --name label` | Create a new API key (shown once) |
| `muapi keys delete <id>` | Delete an API key by ID |

### `muapi image`
| Command | Description |
|---------|-------------|
| `muapi image generate <prompt>` | Text-to-image generation |
| `muapi image edit <prompt> --image <url>` | Image-to-image editing |
| `muapi image models` | List available models |

**Models:** `flux-dev`, `flux-schnell`, `flux-kontext-dev/pro/max`, `hidream-fast/dev/full`, `wan2.1`, `reve`, `gpt4o`, `midjourney`, `seedream`, `qwen`

### `muapi video`
| Command | Description |
|---------|-------------|
| `muapi video generate <prompt>` | Text-to-video generation |
| `muapi video from-image <prompt> --image <url>` | Image-to-video animation |
| `muapi video models` | List available models |

**Models:** `veo3`, `veo3-fast`, `kling-master`, `kling-std`, `kling-pro`, `wan2.1/2.2`, `seedance-pro/lite`, `hunyuan`, `runway`, `pixverse`, `vidu`, `minimax-std/pro`

### `muapi audio`
| Command | Description |
|---------|-------------|
| `muapi audio create <prompt>` | Create music with Suno |
| `muapi audio remix <song-id>` | Remix an existing Suno song |
| `muapi audio extend <song-id>` | Extend a Suno song |
| `muapi audio from-text <prompt>` | Generate audio with MMAudio |
| `muapi audio from-video <video-url>` | Add AI audio to a video |

### `muapi enhance`
| Command | Description |
|---------|-------------|
| `muapi enhance upscale <url>` | AI image upscaling |
| `muapi enhance bg-remove <url>` | Remove background |
| `muapi enhance face-swap --source <url> --target <url>` | Face swap image/video |
| `muapi enhance skin <url>` | Skin enhancement |
| `muapi enhance colorize <url>` | Colorize B&W photo |
| `muapi enhance ghibli <url>` | Ghibli anime style |
| `muapi enhance anime <url>` | Anime style conversion |
| `muapi enhance extend <url>` | Outpaint/extend image |
| `muapi enhance product-shot <url>` | Professional product photo |
| `muapi enhance erase <url> --mask <url>` | Object removal |

### `muapi edit`
| Command | Description |
|---------|-------------|
| `muapi edit effects --video <url> --effect <name>` | AI video/image effects |
| `muapi edit lipsync --video <url> --audio <url>` | Lip sync to audio |
| `muapi edit dance --image <url> --video <url>` | Make person dance |
| `muapi edit dress --image <url>` | Change clothing |
| `muapi edit clipping <video-url>` | AI highlight extraction |

### `muapi predict`
| Command | Description |
|---------|-------------|
| `muapi predict result <id>` | Fetch current status (no polling) |
| `muapi predict wait <id>` | Wait until complete |

### `muapi upload`
| Command | Description |
|---------|-------------|
| `muapi upload file <path>` | Upload a local file → get hosted URL |

### `muapi models`
| Command | Description |
|---------|-------------|
| `muapi models list` | List all models |
| `muapi models list --category video` | Filter by category |

### `muapi config`
| Command | Description |
|---------|-------------|
| `muapi config set <key> <value>` | Set a persistent default |
| `muapi config get <key>` | Read a config value |
| `muapi config list` | Show all config |

**Useful keys:** `output` (json/human), `model.image`, `model.video`, `no_color` (true/false)

### `muapi docs`
| Command | Description |
|---------|-------------|
| `muapi docs openapi` | Fetch the full OpenAPI spec |
| `muapi docs open` | Open Swagger UI in browser |

### `muapi mcp`
| Command | Description |
|---------|-------------|
| `muapi mcp serve` | Start MCP server (stdio) for AI agents |

## Global Options

| Flag | Description |
|------|-------------|
| `--wait / --no-wait` | Poll until done (default: `--wait`) |
| `--output-json` / `-j` | Print raw JSON response |
| `--jq <expr>` | Filter JSON output (e.g. `'.outputs[0]'`) |
| `--download <dir>` / `-d` | Auto-download outputs to directory |
| `--no-color` | Disable colored output |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MUAPI_API_KEY` | API key (overrides keychain/config) |
| `MUAPI_BASE_URL` | Override API base URL |
| `NO_COLOR` | Disable colored output |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `3` | Authentication error |
| `4` | Rate limited |
| `5` | Not found |
| `6` | Billing error |
| `7` | Timeout |
| `8` | Validation error |

## MCP Server

Run as a Model Context Protocol server for Claude Desktop, Cursor, or any MCP-compatible agent:

```bash
muapi mcp serve
```

**Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "muapi": {
      "command": "muapi",
      "args": ["mcp", "serve"],
      "env": { "MUAPI_API_KEY": "your-key-here" }
    }
  }
}
```

Exposes **19 tools**: image generate/edit, video generate/from-image, audio create/from-text, enhance (upscale/bg-remove/face-swap/ghibli), edit lipsync/clipping, predict result, upload file, keys list/create/delete, account balance/topup.

## Agentic Pipeline Examples

```bash
# Full onboarding without human intervention
muapi auth register --email agent@example.com --password "secret"
muapi auth verify --email agent@example.com --otp 123456
muapi auth login --email agent@example.com --password "secret"
muapi account balance --output-json
muapi account topup --amount 10 --output-json --no-open

# Submit async, capture request_id, poll when ready
REQUEST_ID=$(muapi video generate "a dog on a beach" \
  --model kling-master --no-wait --output-json --jq '.request_id' | tr -d '"')
muapi predict wait "$REQUEST_ID" --download ./outputs

# Chain: upload → edit → download
URL=$(muapi upload file ./photo.jpg --output-json --jq '.url' | tr -d '"')
muapi image edit "make it look like a painting" --image "$URL" \
  --model flux-kontext-pro --download ./outputs

# Rotate API keys programmatically
NEW_KEY=$(muapi keys create --name "ci-$(date +%Y%m%d)" --output-json --jq '.api_key' | tr -d '"')
OLD_ID=$(muapi keys list --output-json --jq '.[0].id')
muapi keys delete "$OLD_ID" --yes

# Discover available endpoints
muapi docs openapi --jq '.paths | keys[]'
```

## Shell Completions

```bash
muapi --install-completion bash
muapi --install-completion zsh
muapi --install-completion fish
```
