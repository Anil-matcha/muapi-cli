# muapi CLI

[![Powered by MuAPI](https://img.shields.io/badge/Powered%20by-MuAPI-6366f1?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMSAxNHYtNGgtMnYtMmg0djZoLTJ6bTAtOFY2aDJ2MmgtMnoiLz48L3N2Zz4=)](https://muapi.ai?utm_source=github&utm_medium=badge&utm_campaign=muapi-cli)


Official command-line interface for [muapi.ai](https://muapi.ai?utm_source=github&utm_medium=readme&utm_campaign=muapi-cli) — generate images, videos, and audio directly from your terminal.

**Agent-first design** — every command works for both humans (colored output, tables) and AI agents (`--output-json`, `--jq` filtering, semantic exit codes, MCP server mode).

## Related Projects

- [MuAPI CLI docs](https://muapi.ai/docs/cli) — Command reference and setup guidance.
- [MuAPI API reference](https://muapi.ai/docs/api-reference) — Underlying endpoints and prediction lifecycle.
- [midjourney-api](https://github.com/Anil-matcha/midjourney-api) — Python SDK for Midjourney V7, V8, and Niji image generation.
- [suno-api](https://github.com/Anil-matcha/suno-api) — Python SDK for Suno music, audio, and voice workflows.
- [minimax-music-3-api](https://github.com/SamurAIGPT/minimax-music-3-api) — Python SDK for MiniMax Music 3.0 text-to-music generation on Muapi.
- [awesome-minimax-music-3-prompts](https://github.com/Anil-matcha/awesome-minimax-music-3-prompts) — Curated song prompts and lyrics-formatting guide for MiniMax Music 3.0.
- [MiniMax-H3-API](https://github.com/Anil-matcha/MiniMax-H3-API) — Python SDK for MiniMax H3 video-generation workflows on Muapi.
- [awesome-minimax-h3-prompts](https://github.com/Anil-matcha/awesome-minimax-h3-prompts) — Prompt gallery with runnable MiniMax H3 examples for the CLI.
- [Wan-3.0-API](https://github.com/Anil-matcha/Wan-3.0-API) — Python SDK and MCP server for Wan 3.0-compatible AI video generation.
- [Wan-3.0-Prime-API](https://github.com/Anil-matcha/Wan-3.0-Prime-API) — Python SDK and MCP server for the higher-fidelity Wan 3.0 Prime tier.
- [Gemini-Omni-1.1-Flash-API](https://github.com/Anil-matcha/Gemini-Omni-1.1-Flash-API) — Python SDK and MCP server for Google's newly announced Gemini Omni 1.1 Flash update.
- [Awesome-Gemini-Omni-API-Prompts](https://github.com/Anil-matcha/Awesome-Gemini-Omni-API-Prompts) — Curated Gemini Omni prompts and REST examples.
- [Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) — Browser-based GUI for the same models — no CLI required
- [Awesome-GPT-Image-2-API-Prompts](https://github.com/Anil-matcha/Awesome-GPT-Image-2-API-Prompts) — Curated prompt library to run via this CLI
- [ai-creator-academy](https://github.com/Anil-matcha/ai-creator-academy) — free curriculum teaching creators how to monetize generative AI, including running models via this CLI
- [Flux-3-Dev-API](https://github.com/Anil-matcha/Flux-3-Dev-API) — Python wrapper for Black Forest Labs' FLUX 3 (Dev variant) — text-to-image, image-to-image, text-to-video, image-to-video
- [Grok-Imagine-Image-2-API](https://github.com/Anil-matcha/Grok-Imagine-Image-2-API) — Python SDK and MCP server for Grok Imagine Image 2.0 generation and editing through MuAPI
- [awesome-flux-3-api-prompts](https://github.com/Anil-matcha/awesome-flux-3-api-prompts) — FLUX 3 API guide, prompts, and parameters
- [flux-3-video-api](https://github.com/SamurAIGPT/flux-3-video-api) — Python wrapper focused on FLUX 3 Text-to-Video and Image-to-Video
- [seedance-2.5-mcp](https://github.com/Anil-matcha/seedance-2.5-mcp) — MCP server for generating Seedance 2.5 Preview videos through MuAPI.
- [seedance-2-mcp](https://github.com/Anil-matcha/seedance-2-mcp) — MCP server for generating Seedance 2 videos through MuAPI.
- [Text-to-Speech-API](https://github.com/Anil-matcha/Text-to-Speech-API) — speech model comparison and raw API examples that can be run through the CLI.
- [Speech-to-Text-API](https://github.com/Anil-matcha/Speech-to-Text-API) — transcription and audio-analysis examples for the same Muapi endpoints.
- [Image-Enhancement-API](https://github.com/Anil-matcha/Image-Enhancement-API) — image upscaling and background-removal API examples.
- [Video-Utilities-API](https://github.com/Anil-matcha/Video-Utilities-API) — video enhancement and MMAudio utility examples.
- [AI-3D-Model-API](https://github.com/Anil-matcha/AI-3D-Model-API) — Tripo3D and Meshy API comparisons and examples.

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

# Generate — pick a curated verb…
muapi image generate "a cyberpunk city at night" --model flux-dev
muapi video generate "a dog running on a beach" --model kling-master
muapi audio create "upbeat lo-fi hip hop for studying"

# …or run any model by endpoint name (schema-driven, covers the whole catalog)
muapi run flux-dev-image -p "a cyberpunk city at night"
muapi run seedance-2-text-to-video -p "drone shot over snowy peaks" -i duration=5
muapi run <model> -h          # introspects the live OpenAPI schema

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

### `muapi run` — generic, schema-driven runner

Reaches **any** model in the muapi.ai catalog by endpoint name, even ones not covered by the curated `image / video / audio / enhance / edit` verbs. The input schema is fetched from the live OpenAPI spec, so `muapi run <model> -h` always reflects the real, current parameters.

| Command | Description |
|---------|-------------|
| `muapi run <model> -h` | Print model-specific inputs from the live OpenAPI schema |
| `muapi run <model> -p "..."` | Run with a prompt |
| `muapi run <model> -p "..." -i k=v -i k=v` | Pass arbitrary inputs (JSON-parsed when valid) |
| `muapi run <model> --input-file inputs.json` | Inputs from a JSON file |
| `muapi run <model> ... --dry-run` | Show the request body without sending |

`<model>` accepts either a real endpoint slug (`flux-dev-image`, `nano-banana-2`, `seedance-2-text-to-video`) or a short alias from the curated tables (`flux-dev`, `seedream`, `kling-master`).

**Merge order for inputs** (later wins): `--input-file` → `-i k=v` → `-p prompt`.

```bash
# Discover a model's real inputs
muapi run nano-banana-2 -h

# Run it
muapi run nano-banana-2 -p "a logo for a coffee shop" -i num_images=2 --download ./out

# Pipe-safe JSON
muapi run flux-dev-image -p "..." --output-json --jq '.outputs[0]'
```

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

muapi supports two MCP transport modes. Both expose the same **19 tools**: image generate/edit, video generate/from-image, audio create/from-text, enhance (upscale/bg-remove/face-swap/ghibli), edit lipsync/clipping, predict result, upload file, keys list/create/delete, account balance/topup.

### Option 1 — Hosted (Recommended, no CLI required)

The hosted MCP server at `https://api.muapi.ai/mcp` uses the standard Streamable HTTP transport. Any MCP client can connect with just your API key — no CLI install needed.

**Claude Code:**
```bash
claude mcp add --transport http muapi \
  https://api.muapi.ai/mcp \
  --header "Authorization: Bearer YOUR_MUAPI_KEY"
```

**Cursor** — add to `mcp.json` (`Cmd+Shift+P` → Open MCP settings):
```json
{
  "mcpServers": {
    "muapi": {
      "url": "https://api.muapi.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_MUAPI_KEY" }
    }
  }
}
```

**Windsurf** — open **Settings → MCP**:
```json
{
  "mcpServers": {
    "muapi": {
      "serverUrl": "https://api.muapi.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_MUAPI_KEY" }
    }
  }
}
```

### Option 2 — stdio via CLI (Claude Desktop)

Run the CLI as a local stdio MCP server. Requires the CLI to be installed.

```bash
muapi mcp serve
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
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

**Any stdio-compatible client** — use the `command` + `args` pattern above, substituting your client's config format.

> For more details on the self-hosted MCP server see [muapi-mcp-server](https://github.com/SamurAIGPT/muapi-mcp-server).

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
