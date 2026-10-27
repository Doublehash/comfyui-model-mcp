# Model Drop API instructions for an AI agent

Use this service only when the user asks to install a model into the owner's ComfyUI model directory. Downloads consume disk space and may be large, so confirm the exact source/version and destination category with the user if these are not already clear.

## MCP endpoint

Connect using MCP Streamable HTTP at `http://<owner-tailscale-ip>:8000/mcp`. The ComfyUI browser is at `http://<owner-tailscale-ip>:8189`, and the download UI is at `http://<owner-tailscale-ip>:8765`. These endpoints are intended for the owner's private Tailscale network. Configure host firewall rules so ports 8000, 8189, and 8765 are reachable only from the tailnet.

Available tools:

- `download_comfyui_model(repo_id, filename, category, revision="main")` downloads one named Hugging Face weight file. Use `repo_id` as `owner/repository`, `filename` as the exact repository path, `category` as one of `checkpoints`, `diffusion_models`, `text_encoders`, `vae`, `loras`, `upscale_models`, or `clip_vision`.
- `download_civitai_comfyui_model(version_id, category, filename="")` downloads the primary file from one Civitai model version. Use the numeric **model version ID** from the version page or API, not the model page ID. `filename` is an optional local filename override; leave it empty to use Civitai's response filename.

After a successful tool call, report the installed path and tell the user to refresh ComfyUI's model list or restart ComfyUI. Do not guess model versions or category; ask when unclear. Respect each model's license and the user's usage rights.

## HTTP API

The browser service exposes a JSON endpoint at `POST http://<owner-tailscale-ip>:8765/download` and interactive OpenAPI docs at `/docs`.

Hugging Face request:

```json
{
  "provider": "huggingface",
  "repo_id": "owner/repository",
  "filename": "path/to/model.safetensors",
  "category": "diffusion_models",
  "revision": "main"
}
```

Civitai request:

```json
{
  "provider": "civitai",
  "version_id": 123456,
  "filename": "",
  "category": "loras"
}
```

Success returns `{"path":"/models/<category>/<filename>"}`. Invalid inputs, unavailable models, failed authentication, or existing destination files return HTTP 400 with a `detail` message. The API has no application login; tailnet membership and host firewall rules are the access control. Never send Civitai tokens in request bodies or URLs.
