---
name: muapi-media
description: Create, edit, enhance, and inspect AI images, videos, music, and audio through Muapi when the user asks for generative-media work.
---

# Muapi media tools

Use the Muapi MCP server for generative-media requests. Muapi provides a live model catalog and asynchronous generation tools for images, videos, audio, and media enhancement.

## Select a model

When the user names a model, use that model if it supports the requested operation. When they do not name one, call `search_models` with the requested media type, capability, and constraints. Prefer a model whose returned description and pricing match the user's needs; do not invent model names or parameters.

Before a credit-consuming call, tell the user which model and important options you selected. A clear request to create or transform media authorizes that generation, but account top-ups, key changes, social publishing, and other account or external actions always require explicit confirmation.

## Generate and retrieve results

Use the appropriate tool:

- `muapi_image_generate` for text-to-image.
- `muapi_image_edit` for prompt-based image transformation.
- `muapi_video_generate` for text-to-video.
- `muapi_video_from_image` to animate an image.
- `muapi_audio_create` for music and `muapi_audio_from_text` for sound or ambient audio.
- `muapi_enhance_upscale`, `muapi_enhance_bg_remove`, `muapi_enhance_face_swap`, or `muapi_enhance_ghibli` for supported enhancements.
- `muapi_edit_lipsync` or `muapi_edit_clipping` for supported video workflows.

Generation tools normally return a `request_id` before the asset is ready. Call `muapi_predict_result` with that ID until the status is terminal, then return the output URL(s), status, and any relevant error. Do not claim an asset is ready from a pending response.

For local input files, use `muapi_upload_file` when that tool is available. For an existing public URL, pass the URL directly to the relevant tool. Do not expose API keys or place them in prompts, generated files, or chat output.

## Safe operation

- Never call `muapi_account_topup`, `muapi_keys_create`, or `muapi_keys_delete` without explicit user confirmation.
- Never call social publishing or account-connection tools without explicit confirmation immediately before the external action.
- If credits are insufficient, explain the failure and link the user to `https://muapi.ai/dashboard`; do not retry by topping up.
- If a request is ambiguous, ask only for the missing creative input or approval boundary; keep defaults conservative.
- Return concise progress updates for long-running video or audio jobs and preserve the `request_id` if polling stops.
