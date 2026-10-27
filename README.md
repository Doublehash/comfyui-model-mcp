# ComfyUI Model Drop + MCP

A small download page, HTTP API, and MCP server for putting Hugging Face or Civitai model weights into ComfyUI. Downloads are explicit one-file requests; source identifiers and destination folders are validated, and existing files are not overwritten.

## Run with Docker Compose

Copy `.env.example` to `.env`, set `COMFYUI_MODELS_HOST` to the existing ComfyUI models folder, and add a Civitai API token if you plan to download Civitai files. Civitai's download endpoint requires an account token; it is read only by the server and never sent to the browser.

```sh
cp .env.example .env
# Edit .env with your ComfyUI models path and CIVITAI_TOKEN
docker compose up -d --build
```

Open the ComfyUI instance in this stack at `http://<host-tailscale-ip>:8189`, the model UI at `http://<host-tailscale-ip>:8765`, and the MCP endpoint at `http://<host-tailscale-ip>:8000/mcp`. Port 8188 was already occupied by another ComfyUI container on this host, so this stack publishes its GPU-enabled ComfyUI on 8189. The API docs are at port 8765 `/docs`; agent usage instructions are in [AGENT_API.md](AGENT_API.md). All three ports listen on all interfaces. Restrict ports 8189, 8765, and 8000 in the host firewall to Tailscale so they cannot be reached from the public or local network. The services have no app login; anyone who can reach them can use ComfyUI, start downloads, or call the MCP tools. Only download models whose license permits your intended use.

The ComfyUI service uses the CUDA 13 Blackwell-compatible image and reserves the NVIDIA GPU through Docker Compose. Your host's NVIDIA Container Toolkit must be working for GPU passthrough. ComfyUI models are shared with the downloader at `COMFYUI_MODELS_HOST`; workflows, inputs, outputs, custom nodes, and cache persist under `COMFYUI_DATA_HOST`.

For Hugging Face gated models, run `hf auth login` on the host, or configure Hugging Face credentials inside the containers if required. Public Hugging Face repositories need no login.

## Run as an MCP server without Compose

Use Python 3.11 or newer. Install dependencies, set `COMFYUI_MODELS` and optionally `CIVITAI_TOKEN`, then run `python server.py mcp-http` for remote MCP or `python server.py` for local stdio.

The MCP tools are `download_comfyui_model` for Hugging Face and `download_civitai_comfyui_model` for Civitai. Both services in Compose mount the same ComfyUI models directory.

## Friend's video generation session

The MCP server handles downloads; it does not share GPU execution. Run ComfyUI on your GPU machine, then let your friend connect to ComfyUI using Tailscale. Bind ComfyUI to `0.0.0.0` only if needed for remote access, and restrict its port in the host firewall to Tailscale as well. Avoid exposing ComfyUI or the downloader port directly to the public internet. Your friend needs a compatible video workflow and any required custom nodes; after downloading models, refresh the model list or restart ComfyUI.

## Limits

- Hugging Face downloads use an `owner/repository` ID and a single relative weight filename. Civitai downloads use a numeric model version ID and its primary file.
- Supported extensions are `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.bin`, and `.gguf`.
- Routes files to an allowlisted ComfyUI category and saves by basename; it will not overwrite an existing file.
- Large video models may need substantial disk space and download time.
- The UI and MCP HTTP endpoint have no separate authentication; their access control is the host firewall and tailnet membership.

## License

Project code and documentation are licensed under the [MIT License](LICENSE). Downloaded model files remain subject to their respective creators' licenses and terms; this project license does not grant rights to those models. Dependencies retain their own licenses.
