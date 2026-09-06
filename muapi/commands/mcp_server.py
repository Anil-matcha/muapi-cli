"""muapi mcp serve — expose all muapi tools as an MCP server.

Run:  muapi mcp serve
Then add to Claude Desktop / VS Code / any MCP client.

Each generation endpoint becomes a structured MCP tool with:
- Full JSON Schema input definition
- outputSchema for validated structured responses
- Proper isError signalling (no silent failures)
- Tool annotations (read-only vs. side-effecting)
"""
import json
import sys
from typing import Any

import typer

from .. import __version__, client as api_client
from ..config import get_api_key

app = typer.Typer(help="Run muapi as an MCP server for AI agent integration.")


# ── Shared schemas ────────────────────────────────────────────────────────────

def _prediction_output_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "request_id": {"type": "string"},
            "status":     {"type": "string", "enum": ["pending", "processing", "completed", "failed"]},
            "outputs":    {"type": "array", "items": {"type": "string", "format": "uri"}},
            "error":      {"type": "string"},
        },
        "required": ["status"],
    }


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = [
    # ── Images ──────────────────────────────────────────────────────────────
    {
        "name": "muapi_image_generate",
        "description": "Generate an image from a text prompt using muapi.ai. Returns URLs of generated images.",
        "endpoint": None,  # dynamic — chosen from 'model' param
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":       {"type": "string",  "description": "Text description of the image to generate"},
                "model":        {"type": "string",  "description": "Model name", "default": "flux-dev",
                                 "enum": ["flux-dev","flux-schnell","flux-krea",
                                          "flux-kontext-dev","flux-kontext-pro","flux-kontext-max",
                                          "flux-2-dev","flux-2-pro","flux-2-flex",
                                          "flux-2-klein-4b","flux-2-klein-9b",
                                          "hidream-fast","hidream-dev","hidream-full",
                                          "wan2.1","wan2.5","wan2.6","wan2.7","wan2.7-pro",
                                          "gpt4o","gpt-image","gpt-image-2",
                                          "imagen4","imagen4-fast","imagen4-ultra",
                                          "midjourney","midjourney-v7","midjourney-v8","midjourney-niji",
                                          "seedream","seedream-v3","seedream-v4","seedream-v4.5","seedream-5",
                                          "qwen","qwen-2","qwen-2-pro",
                                          "nano-banana","nano-banana-pro","nano-banana-2",
                                          "kling-o1","kling-o3",
                                          "hunyuan","hunyuan-3","ideogram","reve",
                                          "z-image","z-image-turbo",
                                          "leonardo-lucid","leonardo-phoenix",
                                          "grok","grok-quality","chroma",
                                          "sdxl","perfect-pony","neta-lumina"]},
                "width":        {"type": "integer", "description": "Image width in pixels", "default": 1024},
                "height":       {"type": "integer", "description": "Image height in pixels", "default": 1024},
                "num_images":   {"type": "integer", "description": "Number of images (1-4)", "default": 1, "minimum": 1, "maximum": 4},
                "aspect_ratio": {"type": "string",  "description": "Aspect ratio (used by kontext/midjourney models)", "default": "1:1"},
            },
            "required": ["prompt"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    {
        "name": "muapi_image_edit",
        "description": "Edit or transform an image using a text prompt and a source image URL.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":       {"type": "string", "description": "Edit instruction"},
                "image_url":    {"type": "string", "description": "Source image URL", "format": "uri"},
                "model":        {"type": "string", "default": "flux-kontext-dev",
                                 "enum": ["flux-kontext-dev","flux-kontext-pro","flux-kontext-max",
                                          "flux-kontext-effects",
                                          "flux-2-dev-edit","flux-2-pro-edit","flux-2-flex-edit",
                                          "flux-2-klein-4b-edit","flux-2-klein-9b-edit",
                                          "gpt4o","gpt4o-edit","gpt-image-edit","gpt-image-2-edit",
                                          "reve","seededit",
                                          "seedream-edit","seedream-v4.5-edit","seedream-5-edit",
                                          "seedance-character",
                                          "midjourney","midjourney-style","midjourney-omni",
                                          "qwen","qwen-plus","qwen-plus-lora","qwen-2511",
                                          "qwen-2-edit","qwen-2-pro-edit",
                                          "nano-banana-edit","nano-banana-effects",
                                          "nano-banana-2-edit","nano-banana-pro-edit",
                                          "kling-o1-edit","kling-o3-edit",
                                          "wan2.5-edit","wan2.6-edit","wan2.7-edit","wan2.7-edit-pro",
                                          "ideogram-character","ideogram-reframe",
                                          "flux-redux","flux-pulid","grok",
                                          "photo-pack","portrait-stylist",
                                          "minimax-subject","vidu-q2-ref"]},
                "aspect_ratio": {"type": "string", "default": "1:1"},
                "num_images":   {"type": "integer", "default": 1, "minimum": 1, "maximum": 4},
            },
            "required": ["prompt", "image_url"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    # ── Videos ──────────────────────────────────────────────────────────────
    {
        "name": "muapi_video_generate",
        "description": "Generate a video from a text prompt using muapi.ai.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":       {"type": "string", "description": "Video description prompt"},
                "model":        {"type": "string", "default": "kling-master",
                                 "enum": ["veo3","veo3-fast","veo3.1","veo3.1-fast","veo3.1-4k",
                                          "veo3.1-lite","veo4",
                                          "kling-master","kling-v2.5-pro","kling-v2.6-pro",
                                          "kling-v3-pro","kling-v3-std","kling-v3-4k",
                                          "kling-v3-omni","kling-v3-omni-std","kling-v3-omni-4k",
                                          "kling-o1",
                                          "wan2.1","wan2.2","wan2.2-5b-fast",
                                          "wan2.5","wan2.5-fast","wan2.6","wan2.7",
                                          "seedance-pro","seedance-pro-fast","seedance-lite",
                                          "seedance-v1.5","seedance-v1.5-fast","seedance-v2",
                                          "seedance-2","seedance-2-fast",
                                          "seedance-2-vip","seedance-2-vip-fast",
                                          "hunyuan","hunyuan-fast","runway",
                                          "pixverse","pixverse-v4.5","pixverse-v5","pixverse-v5.5","pixverse-v6",
                                          "vidu","vidu-q2-pro","vidu-q2-turbo","vidu-q3-pro","vidu-q3-turbo",
                                          "minimax-std","minimax-pro","minimax-2.3-pro","minimax-2.3-std",
                                          "ltx-2","ltx-2-fast","ltx-2-19b","ltx-2.3",
                                          "sora","sora-2","sora-2-pro","sora-2-standard","sora-2-storyboard",
                                          "ovi","grok","happy-horse","happy-horse-720"]},
                "duration":     {"type": "integer", "description": "Duration in seconds", "default": 5},
                "aspect_ratio": {"type": "string", "default": "16:9"},
            },
            "required": ["prompt"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    {
        "name": "muapi_video_from_image",
        "description": "Animate an image into a video using muapi.ai.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":       {"type": "string", "description": "Motion/animation prompt"},
                "image_url":    {"type": "string", "description": "Source image URL", "format": "uri"},
                "model":        {"type": "string", "default": "kling-std",
                                 "enum": ["veo3","veo3-fast","veo3.1","veo3.1-fast","veo3.1-ref",
                                          "veo3.1-lite","veo4",
                                          "kling-std","kling-pro","kling-master",
                                          "kling-v2.5-pro","kling-v2.5-std","kling-v2.6-pro",
                                          "kling-v3-pro","kling-v3-std","kling-v3-4k",
                                          "kling-v3-omni","kling-v3-omni-std","kling-v3-omni-4k",
                                          "kling-o1","kling-o1-std","kling-o1-ref",
                                          "wan2.1","wan2.1-ref","wan2.2","wan2.2-spicy",
                                          "wan2.5","wan2.5-fast","wan2.6","wan2.7","wan2.7-ref",
                                          "seedance-pro","seedance-pro-fast","seedance-lite",
                                          "seedance-lite-ref","seedance-v1.5","seedance-v1.5-fast",
                                          "seedance-v2","seedance-v2-omni",
                                          "seedance-2","seedance-2-fast","seedance-2-flf",
                                          "seedance-2-omni","seedance-2-vip",
                                          "hunyuan","runway","runway-act-two",
                                          "pixverse-v4.5","pixverse-v5","pixverse-v5.5",
                                          "pixverse-v6","pixverse-v6-trans",
                                          "vidu","vidu-q1-ref","vidu-q2-pro","vidu-q2-turbo",
                                          "vidu-q2-ref","vidu-q2-start-end",
                                          "vidu-q3-pro","vidu-q3-turbo","vidu-q3-flf",
                                          "midjourney",
                                          "minimax-std","minimax-pro","minimax-2.3-pro",
                                          "minimax-2.3-std","minimax-2.3-fast",
                                          "ltx-2","ltx-2-fast","ltx-2-19b","ltx-2.3",
                                          "sora-2","sora-2-pro","sora-2-standard",
                                          "ovi","grok","leonardo",
                                          "happy-horse","happy-horse-ref",
                                          "infinitetalk","video-effects","wan-effects"]},
                "duration":     {"type": "integer", "default": 5},
                "aspect_ratio": {"type": "string", "default": "16:9"},
            },
            "required": ["prompt", "image_url"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    # ── Audio ────────────────────────────────────────────────────────────────
    {
        "name": "muapi_audio_create",
        "description": "Create original music using Suno via muapi.ai.",
        "endpoint": "suno-create-music",
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":         {"type": "string", "description": "Music description or lyrics"},
                "title":          {"type": "string", "default": ""},
                "tags":           {"type": "string", "description": "Genre/style tags", "default": ""},
                "make_instrumental": {"type": "boolean", "default": False},
            },
            "required": ["prompt"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    {
        "name": "muapi_audio_from_text",
        "description": "Generate sound effects or ambient audio from a text prompt using MMAudio.",
        "endpoint": "mmaudio-v2/text-to-audio",
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":   {"type": "string"},
                "duration": {"type": "number", "default": 10.0},
            },
            "required": ["prompt"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    # ── Enhance ──────────────────────────────────────────────────────────────
    {
        "name": "muapi_enhance_upscale",
        "description": "Upscale an image using AI.",
        "endpoint": "ai-image-upscale",
        "annotations": {"readOnlyHint": False, "idempotentHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"image_url": {"type": "string", "format": "uri"}},
            "required": ["image_url"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    {
        "name": "muapi_enhance_bg_remove",
        "description": "Remove the background from an image.",
        "endpoint": "ai-background-remover",
        "annotations": {"readOnlyHint": False, "idempotentHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"image_url": {"type": "string", "format": "uri"}},
            "required": ["image_url"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    {
        "name": "muapi_enhance_face_swap",
        "description": "Swap faces in an image or video.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_url": {"type": "string", "description": "Face source image URL", "format": "uri"},
                "target_url": {"type": "string", "description": "Target image or video URL", "format": "uri"},
                "mode":       {"type": "string", "enum": ["image", "video"], "default": "image"},
            },
            "required": ["source_url", "target_url"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    {
        "name": "muapi_enhance_ghibli",
        "description": "Convert an image to Studio Ghibli anime style.",
        "endpoint": "ai-ghibli-style",
        "annotations": {"readOnlyHint": False, "idempotentHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"image_url": {"type": "string", "format": "uri"}},
            "required": ["image_url"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    # ── Edit ─────────────────────────────────────────────────────────────────
    {
        "name": "muapi_edit_lipsync",
        "description": "Sync lip movements in a video to an audio file.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_url": {"type": "string", "format": "uri"},
                "audio_url": {"type": "string", "format": "uri"},
                "model":     {"type": "string", "default": "sync",
                              "enum": ["sync","latentsync","creatify","veed",
                                       "ltx-2","ltx-2.3","kling-v1","kling-v2","wan2.2"]},
            },
            "required": ["video_url", "audio_url"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    {
        "name": "muapi_edit_clipping",
        "description": "Extract AI-selected highlight clips from a long video.",
        "endpoint": "ai-clipping",
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_url":      {"type": "string", "format": "uri"},
                "num_highlights": {"type": "integer", "default": 3},
                "aspect_ratio":   {"type": "string", "default": "9:16"},
            },
            "required": ["video_url"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    # ── Predict ──────────────────────────────────────────────────────────────
    {
        "name": "muapi_predict_result",
        "description": "Fetch the current result of an async prediction by request ID.",
        "endpoint": None,
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string", "description": "Prediction request ID"},
            },
            "required": ["request_id"],
        },
        "outputSchema": _prediction_output_schema(),
    },
    {
        "name": "muapi_upload_file",
        "description": "Upload a local file to muapi.ai and get back a hosted URL.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute local file path"},
            },
            "required": ["file_path"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Hosted file URL"},
            },
        },
    },
    # ── Keys ─────────────────────────────────────────────────────────────────
    {
        "name": "muapi_keys_list",
        "description": "List all API keys on the authenticated muapi.ai account.",
        "endpoint": None,
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
        "inputSchema": {"type": "object", "properties": {}},
        "outputSchema": {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":           {"type": "integer"},
                            "name":         {"type": "string"},
                            "is_active":    {"type": "boolean"},
                            "created_at":   {"type": "string"},
                            "last_used_at": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
    {
        "name": "muapi_keys_create",
        "description": "Create a new API key for the authenticated account. The raw key is returned once — store it immediately.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Label for the key", "default": "cli"},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "id":      {"type": "integer"},
                "name":    {"type": "string"},
                "api_key": {"type": "string", "description": "Raw API key — shown once"},
            },
            "required": ["api_key"],
        },
    },
    {
        "name": "muapi_keys_delete",
        "description": "Delete an API key by ID.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "key_id": {"type": "integer", "description": "Key ID from muapi_keys_list"},
            },
            "required": ["key_id"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
        },
    },
    # ── Workflow ──────────────────────────────────────────────────────────────
    {
        "name": "muapi_workflow_list",
        "description": "List all saved workflows for the authenticated user.",
        "endpoint": None,
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
        "inputSchema": {"type": "object", "properties": {}},
        "outputSchema": {
            "type": "object",
            "properties": {
                "workflows": {"type": "array"},
            },
        },
    },
    {
        "name": "muapi_workflow_create",
        "description": "Generate a new multi-step AI workflow from a text description using the AI architect. Returns the workflow definition with nodes and connections.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Describe the workflow, e.g. 'generate image with flux then upscale it'"},
                "sync":   {"type": "boolean", "default": True},
            },
            "required": ["prompt"],
        },
        "outputSchema": {"type": "object"},
    },
    {
        "name": "muapi_workflow_get",
        "description": "Get a workflow definition by ID including its nodes and connections.",
        "endpoint": None,
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"workflow_id": {"type": "string"}},
            "required": ["workflow_id"],
        },
        "outputSchema": {"type": "object"},
    },
    {
        "name": "muapi_workflow_execute",
        "description": "Execute a workflow with specific node inputs. Returns a run_id to poll with muapi_workflow_status.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string"},
                "inputs":      {"type": "object", "description": "Map of {node_id: {param: value}}"},
            },
            "required": ["workflow_id"],
        },
        "outputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}}},
    },
    {
        "name": "muapi_workflow_status",
        "description": "Get the node-by-node status of a workflow run.",
        "endpoint": None,
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
        "outputSchema": {"type": "object"},
    },
    {
        "name": "muapi_workflow_outputs",
        "description": "Get the final output URLs of a completed workflow run.",
        "endpoint": None,
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
        "outputSchema": {"type": "object"},
    },
    # ── Account ──────────────────────────────────────────────────────────────
    {
        "name": "muapi_account_balance",
        "description": "Get the current account balance for the authenticated muapi.ai user.",
        "endpoint": None,
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
        "inputSchema": {"type": "object", "properties": {}},
        "outputSchema": {
            "type": "object",
            "properties": {
                "balance":  {"type": "number", "description": "Current balance in USD"},
                "currency": {"type": "string"},
                "email":    {"type": "string"},
            },
            "required": ["balance", "currency"],
        },
    },
    {
        "name": "muapi_account_topup",
        "description": "Create a Stripe checkout session to add credits to the muapi.ai account. Returns a checkout URL — open it in a browser to complete payment.",
        "endpoint": None,
        "annotations": {"readOnlyHint": False, "idempotentHint": False},
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount":   {"type": "integer", "description": "Amount in USD to add (minimum 1)", "default": 10, "minimum": 1},
                "currency": {"type": "string", "default": "usd"},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "checkout_url": {"type": "string", "format": "uri"},
                "amount":       {"type": "integer"},
                "currency":     {"type": "string"},
            },
            "required": ["checkout_url"],
        },
    },
]


# ── Tool dispatch ─────────────────────────────────────────────────────────────

def _dispatch(tool_name: str, args: dict) -> dict:
    """Call the appropriate muapi endpoint for a tool name."""
    from .image   import T2I_MODELS, I2I_MODELS, WIDTH_HEIGHT_MODELS, LIST_INPUT_MODELS
    from .video   import T2V_MODELS, I2V_MODELS, LIST_INPUT_I2V
    from .audio   import app as _  # import to ensure module loaded
    from .enhance import app as _
    from .edit    import app as _

    LIPSYNC_MAP = {
        "sync":       "sync-lipsync",
        "latentsync": "latentsync-video",
        "creatify":   "creatify-lipsync",
        "veed":       "veed-lipsync",
        "ltx-2":      "ltx-2-19b-lipsync",
        "ltx-2.3":    "ltx-2.3-lipsync",
        "kling-v1":   "kling-v1-avatar-pro",
        "kling-v2":   "kling-v2-avatar-pro",
        "wan2.2":     "wan2.2-speech-to-video",
    }

    if tool_name == "muapi_image_generate":
        model    = args.get("model", "flux-dev")
        endpoint = T2I_MODELS.get(model)
        if not endpoint:
            raise ValueError(f"Unknown image model: {model}")
        payload  = {"prompt": args["prompt"], "num_images": args.get("num_images", 1)}
        if model in WIDTH_HEIGHT_MODELS:
            payload["width"]  = args.get("width",  1024)
            payload["height"] = args.get("height", 1024)
        else:
            payload["aspect_ratio"] = args.get("aspect_ratio", "1:1")
        return api_client.generate(endpoint, payload)

    if tool_name == "muapi_image_edit":
        model    = args.get("model", "flux-kontext-dev")
        endpoint = I2I_MODELS.get(model)
        if not endpoint:
            raise ValueError(f"Unknown image edit model: {model}")
        payload  = {
            "prompt":       args["prompt"],
            "aspect_ratio": args.get("aspect_ratio", "1:1"),
            "num_images":   args.get("num_images", 1),
        }
        if model in LIST_INPUT_MODELS:
            payload["images_list"] = [args["image_url"]]
        else:
            payload["image_url"] = args["image_url"]
        return api_client.generate(endpoint, payload)

    if tool_name == "muapi_video_generate":
        model    = args.get("model", "kling-master")
        endpoint = T2V_MODELS.get(model)
        if not endpoint:
            raise ValueError(f"Unknown video model: {model}")
        return api_client.generate(endpoint, {
            "prompt": args["prompt"],
            "duration": args.get("duration", 5),
            "aspect_ratio": args.get("aspect_ratio", "16:9"),
        })

    if tool_name == "muapi_video_from_image":
        model    = args.get("model", "kling-std")
        endpoint = I2V_MODELS.get(model)
        if not endpoint:
            raise ValueError(f"Unknown i2v model: {model}")
        payload = {
            "prompt": args["prompt"],
            "duration": args.get("duration", 5),
            "aspect_ratio": args.get("aspect_ratio", "16:9"),
        }
        if model in LIST_INPUT_I2V:
            payload["images_list"] = [args["image_url"]]
        else:
            payload["image_url"] = args["image_url"]
        return api_client.generate(endpoint, payload)

    if tool_name == "muapi_audio_create":
        return api_client.generate("suno-create-music", {
            "prompt": args["prompt"], "title": args.get("title", ""),
            "tags": args.get("tags", ""), "make_instrumental": args.get("make_instrumental", False),
        })

    if tool_name == "muapi_audio_from_text":
        return api_client.generate("mmaudio-v2/text-to-audio", {
            "prompt": args["prompt"], "duration": args.get("duration", 10.0),
        })

    if tool_name == "muapi_enhance_upscale":
        return api_client.generate("ai-image-upscale", {"image_url": args["image_url"]})

    if tool_name == "muapi_enhance_bg_remove":
        return api_client.generate("ai-background-remover", {"image_url": args["image_url"]})

    if tool_name == "muapi_enhance_face_swap":
        ep = "ai-video-face-swap" if args.get("mode") == "video" else "ai-image-face-swap"
        return api_client.generate(ep, {"source_url": args["source_url"], "target_url": args["target_url"]})

    if tool_name == "muapi_enhance_ghibli":
        return api_client.generate("ai-ghibli-style", {"image_url": args["image_url"]})

    if tool_name == "muapi_edit_lipsync":
        model = args.get("model", "sync")
        ep    = LIPSYNC_MAP.get(model, "lipsync")
        return api_client.generate(ep, {"video_url": args["video_url"], "audio_url": args["audio_url"]})

    if tool_name == "muapi_edit_clipping":
        return api_client.generate("ai-clipping", {
            "video_url": args["video_url"],
            "num_highlights": args.get("num_highlights", 3),
            "aspect_ratio": args.get("aspect_ratio", "9:16"),
        })

    if tool_name == "muapi_predict_result":
        return api_client.get_result(args["request_id"])

    if tool_name == "muapi_upload_file":
        return api_client.upload_file(args["file_path"])

    if tool_name == "muapi_workflow_list":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured.")
        wf_base = BASE_URL.replace("/api/v1", "") + "/workflow"
        resp = _httpx.get(f"{wf_base}/get-workflow-defs", headers={"x-api-key": key}, timeout=30.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return {"workflows": resp.json()}

    if tool_name == "muapi_workflow_create":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured.")
        wf_base = BASE_URL.replace("/api/v1", "") + "/workflow"
        body = {"prompt": args["prompt"], "sync": args.get("sync", True)}
        resp = _httpx.post(f"{wf_base}/architect", json=body, headers={"x-api-key": key}, timeout=120.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    if tool_name == "muapi_workflow_get":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured.")
        wf_base = BASE_URL.replace("/api/v1", "") + "/workflow"
        resp = _httpx.get(f"{wf_base}/get-workflow-def/{args['workflow_id']}", headers={"x-api-key": key}, timeout=30.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    if tool_name == "muapi_workflow_execute":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured.")
        wf_base = BASE_URL.replace("/api/v1", "") + "/workflow"
        body = {"inputs": args.get("inputs", {})}
        resp = _httpx.post(f"{wf_base}/{args['workflow_id']}/api-execute", json=body,
                           headers={"x-api-key": key}, timeout=60.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    if tool_name == "muapi_workflow_status":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured.")
        wf_base = BASE_URL.replace("/api/v1", "") + "/workflow"
        resp = _httpx.get(f"{wf_base}/run/{args['run_id']}/status", headers={"x-api-key": key}, timeout=30.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    if tool_name == "muapi_workflow_outputs":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured.")
        wf_base = BASE_URL.replace("/api/v1", "") + "/workflow"
        resp = _httpx.get(f"{wf_base}/run/{args['run_id']}/api-outputs", headers={"x-api-key": key}, timeout=30.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    if tool_name == "muapi_keys_list":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured. Run: muapi auth configure")
        resp = _httpx.get(f"{BASE_URL}/keys", headers={"x-api-key": key}, timeout=30.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return {"keys": resp.json()}

    if tool_name == "muapi_keys_create":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured. Run: muapi auth configure")
        resp = _httpx.post(
            f"{BASE_URL}/keys",
            json={"name": args.get("name", "cli")},
            headers={"x-api-key": key},
            timeout=30.0,
        )
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    if tool_name == "muapi_keys_delete":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured. Run: muapi auth configure")
        resp = _httpx.delete(
            f"{BASE_URL}/keys/{args['key_id']}",
            headers={"x-api-key": key},
            timeout=30.0,
        )
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    if tool_name == "muapi_account_balance":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured. Run: muapi auth configure")
        resp = _httpx.get(f"{BASE_URL}/account/balance", headers={"x-api-key": key}, timeout=30.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    if tool_name == "muapi_account_topup":
        from ..config import BASE_URL, get_api_key
        import httpx as _httpx
        key = get_api_key()
        if not key:
            raise ValueError("No API key configured. Run: muapi auth configure")
        payload = {"amount": args.get("amount", 10), "currency": args.get("currency", "usd")}
        resp = _httpx.post(f"{BASE_URL}/account/topup", json=payload, headers={"x-api-key": key}, timeout=30.0)
        if resp.status_code >= 400:
            raise api_client.MuapiError(resp.text, resp.status_code)
        return resp.json()

    raise ValueError(f"Unknown tool: {tool_name}")


# ── MCP stdio server ──────────────────────────────────────────────────────────

def _mcp_response(id: Any, result: Any) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": id, "result": result})


def _mcp_error(id: Any, code: int, message: str) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})


def _tool_result(data: Any, is_error: bool = False) -> dict:
    text = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
    result = {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }
    if not is_error and isinstance(data, dict):
        result["structuredContent"] = data
    return result


def _handle_request(request: dict) -> str:
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return _mcp_response(req_id, {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "muapi", "version": __version__},
        })

    if method == "tools/list":
        tools_list = []
        for t in TOOLS:
            entry = {
                "name":        t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
                "annotations": t.get("annotations", {}),
            }
            if "outputSchema" in t:
                entry["outputSchema"] = t["outputSchema"]
            tools_list.append(entry)
        return _mcp_response(req_id, {"tools": tools_list})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = _dispatch(tool_name, arguments)
            return _mcp_response(req_id, _tool_result(result, is_error=False))
        except api_client.MuapiError as e:
            return _mcp_response(req_id, _tool_result({"error": str(e)}, is_error=True))
        except ValueError as e:
            return _mcp_error(req_id, -32602, str(e))
        except Exception as e:
            return _mcp_response(req_id, _tool_result({"error": str(e)}, is_error=True))

    if method == "notifications/initialized":
        return ""  # No response for notifications

    # Unknown method
    return _mcp_error(req_id, -32601, f"Method not found: {method}")


@app.command("serve")
def serve(
    check_auth: bool = typer.Option(True, "--check-auth/--no-check-auth",
                                    help="Verify API key is configured before starting"),
):
    """Start the muapi MCP server (stdio transport).

    Add to Claude Desktop config:

    \\b
    {
      "mcpServers": {
        "muapi": {
          "command": "muapi",
          "args": ["mcp", "serve"],
          "env": { "MUAPI_API_KEY": "your-key-here" }
        }
      }
    }
    """
    if check_auth and not get_api_key():
        sys.stderr.write(
            json.dumps({"error": "No MUAPI_API_KEY configured. Set env var or run: muapi auth configure"}) + "\n"
        )
        sys.exit(3)

    sys.stderr.write(json.dumps({"status": "muapi MCP server ready", "tools": len(TOOLS), "version": __version__}) + "\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = _mcp_error(None, -32700, "Parse error")
            sys.stdout.write(response + "\n")
            sys.stdout.flush()
            continue

        response = _handle_request(request)
        if response:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()
