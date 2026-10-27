"""Local ComfyUI model downloader MCP server and tiny browser UI."""
from __future__ import annotations

import os
import re
import urllib.request
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from huggingface_hub import hf_hub_download
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

ROOT = Path(os.environ.get("COMFYUI_MODELS", "./ComfyUI/models")).expanduser().resolve()
CATEGORIES = {
    "checkpoints": "checkpoints",
    "diffusion_models": "diffusion_models",
    "text_encoders": "text_encoders",
    "vae": "vae",
    "loras": "loras",
    "upscale_models": "upscale_models",
    "clip_vision": "clip_vision",
}
ALLOWED = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf"}
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")

from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    "ComfyUI Model Downloader",
    host="0.0.0.0",
    port=8000,
    # Tailnet/firewall is the network boundary for this private endpoint.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)
app = FastAPI(title="ComfyUI Model Drop")


def download_model(repo_id: str, filename: str, category: str, revision: str = "main") -> str:
    """Download one Hugging Face model file into an approved ComfyUI model folder."""
    if not REPO_RE.fullmatch(repo_id):
        raise ValueError("Use a Hugging Face repo ID in the form owner/repository.")
    if category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
    rel = Path(filename)
    if rel.is_absolute() or ".." in rel.parts or not filename.strip():
        raise ValueError("Filename must be a relative path inside the Hugging Face repository.")
    if rel.suffix.lower() not in ALLOWED:
        raise ValueError(f"Only model weight files are allowed: {', '.join(sorted(ALLOWED))}")
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,160}", revision):
        raise ValueError("Revision contains unsupported characters.")

    target_dir = (ROOT / CATEGORIES[category]).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = (target_dir / rel.name).resolve()
    if target_dir not in destination.parents:
        raise ValueError("Invalid destination filename.")
    if destination.exists():
        raise ValueError(f"File already exists: {destination}")
    downloaded = Path(hf_hub_download(repo_id=repo_id, filename=filename, revision=revision))
    # Copy from Hub cache into ComfyUI models; avoid trusting remote path components.
    import shutil
    shutil.copy2(downloaded, destination)
    return str(destination)


def download_civitai_model(version_id: int, category: str, filename: Optional[str] = None) -> str:
    """Download the primary file for a Civitai model version into ComfyUI."""
    if version_id <= 0:
        raise ValueError("Civitai model version ID must be a positive number.")
    if category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
    target_dir = (ROOT / CATEGORIES[category]).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("CIVITAI_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(f"https://civitai.com/api/download/models/{version_id}", headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        suggested = response.headers.get_filename()
        name = Path(filename or suggested or f"civitai-{version_id}.safetensors").name
        if Path(name).suffix.lower() not in ALLOWED:
            raise ValueError(f"Only model weight files are allowed: {', '.join(sorted(ALLOWED))}")
        destination = (target_dir / name).resolve()
        if target_dir not in destination.parents:
            raise ValueError("Invalid destination filename.")
        if destination.exists():
            raise ValueError(f"File already exists: {destination}")
        with destination.open("xb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
    return str(destination)


@mcp.tool()
def download_comfyui_model(repo_id: str, filename: str, category: Literal[
    "checkpoints", "diffusion_models", "text_encoders", "vae", "loras", "upscale_models", "clip_vision"
], revision: str = "main") -> str:
    """Download one explicitly named Hugging Face weight file to ComfyUI models."""
    return download_model(repo_id, filename, category, revision)


@mcp.tool()
def download_civitai_comfyui_model(version_id: int, category: Literal[
    "checkpoints", "diffusion_models", "text_encoders", "vae", "loras", "upscale_models", "clip_vision"
], filename: str = "") -> str:
    """Download the primary file for a Civitai model version ID into ComfyUI."""
    return download_civitai_model(version_id, category, filename or None)


class DownloadRequest(BaseModel):
    provider: Literal["huggingface", "civitai"] = "huggingface"
    repo_id: str = ""
    filename: str = ""
    version_id: int = 0
    category: Literal["checkpoints", "diffusion_models", "text_encoders", "vae", "loras", "upscale_models", "clip_vision"]
    revision: str = "main"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.post("/download")
def download(req: DownloadRequest) -> dict[str, str]:
    try:
        if req.provider == "civitai":
            return {"path": download_civitai_model(req.version_id, req.category, req.filename or None)}
        return {"path": download_model(req.repo_id, req.filename, req.category, req.revision)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ComfyUI Model Drop</title>
<style>
:root{color-scheme:dark;--bg:#111315;--panel:#1b1f22;--line:#343b40;--ink:#f4f1e9;--muted:#a5adae;--accent:#c5f36b}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 80% 0%,#273321 0,transparent 40%),var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}.wrap{max-width:960px;margin:auto;padding:42px 24px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:46px}.brand{font-weight:800;letter-spacing:.08em}.pill{color:var(--accent);border:1px solid #586c3f;padding:6px 12px;border-radius:99px;font-size:12px;text-transform:uppercase;letter-spacing:.12em}h1{font-size:clamp(38px,7vw,72px);line-height:.98;letter-spacing:-.06em;margin:0 0 20px;max-width:700px}h1 span{color:var(--accent)}.lede{color:var(--muted);max-width:630px;margin:0 0 32px}.card{background:color-mix(in srgb,var(--panel) 92%,transparent);border:1px solid var(--line);border-radius:18px;padding:28px;max-width:700px;box-shadow:0 24px 90px #0005}label{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.12em;margin:18px 0 7px}input,select{width:100%;height:48px;background:#111416;color:var(--ink);border:1px solid var(--line);border-radius:9px;padding:0 13px;font:inherit}input:focus,select:focus{outline:2px solid var(--accent);border-color:transparent}.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}button{margin-top:24px;background:var(--accent);color:#17200d;font:700 15px system-ui;border:0;border-radius:9px;padding:13px 18px;cursor:pointer}button:disabled{opacity:.6;cursor:wait}.note{font-size:12px;color:var(--muted);margin:15px 0 0}#result{white-space:pre-wrap;color:var(--accent);font:13px/1.6 ui-monospace,monospace;margin-top:17px}.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:45px}.step{border-top:1px solid var(--line);padding-top:13px;color:var(--muted);font-size:13px}.step b{color:var(--ink);display:block;margin-bottom:4px}@media(max-width:600px){.row,.steps{grid-template-columns:1fr}.top{margin-bottom:34px}}
</style></head><body><main class="wrap"><header class="top"><div class="brand">MODEL DROP <span style="color:var(--accent)">/</span> COMFYUI</div><div class="pill">Tailnet</div></header><h1>Bring the model.<br><span>Make the video.</span></h1><p class="lede">Download one model file into your ComfyUI models folder. Large video models can take a while.</p><section class="card"><form id="form"><label>Source</label><select name="provider" id="provider"><option value="huggingface">Hugging Face</option><option value="civitai">Civitai</option></select><div id="hf"><label>Hugging Face repository</label><input name="repo_id" placeholder="owner/model-repository" required pattern="[^/]+/[^/]+"><label>Weight filename</label><input name="filename" placeholder="model.safetensors" required><label>Revision</label><input name="revision" value="main"></div><div id="civitai" hidden><label>Civitai model version ID</label><input name="version_id" type="number" min="1" placeholder="123456" disabled><label>Filename override (optional)</label><input name="civitai_filename" placeholder="Use Civitai filename" disabled></div><div class="row"><div><label>ComfyUI folder</label><select name="category"><option>diffusion_models</option><option>checkpoints</option><option>text_encoders</option><option>vae</option><option>loras</option><option>upscale_models</option><option>clip_vision</option></select></div><div style="display:flex;align-items:end;color:var(--muted);font-size:12px;padding-bottom:12px">Choose the destination folder that matches the model.</div></div><button id="submit">Download model</button><p class="note">Civitai downloads need a server-side API token. Existing files are never overwritten.</p><div id="result" role="status"></div></form></section><div class="steps"><div class="step"><b>01 / Choose</b>Enter a Hugging Face repo and filename, or Civitai version ID.</div><div class="step"><b>02 / Place</b>Select the matching ComfyUI folder for the model type.</div><div class="step"><b>03 / Load</b>Refresh ComfyUI’s model list or restart it, then build your workflow.</div></div></main><script>const f=document.querySelector('#form'),b=document.querySelector('#submit'),o=document.querySelector('#result'),p=document.querySelector('#provider');function source(){const civ=p.value==='civitai';document.querySelector('#hf').hidden=civ;document.querySelector('#civitai').hidden=!civ;for(const n of ['repo_id','filename','revision']){const x=f.elements[n];x.disabled=civ;x.required=!civ}for(const n of ['version_id','civitai_filename'])f.elements[n].disabled=!civ;f.elements.version_id.required=civ}p.onchange=source;source();f.onsubmit=async e=>{e.preventDefault();b.disabled=true;b.textContent='Downloading…';o.textContent='';try{const d=Object.fromEntries(new FormData(f));d.filename=d.provider==='civitai'?(d.civitai_filename||''):d.filename;const r=await fetch('/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});const j=await r.json();if(!r.ok)throw Error(j.detail);o.textContent='Saved to '+j.path}catch(x){o.textContent='Download failed: '+x.message}finally{b.disabled=false;b.textContent='Download model'}};</script></body></html>"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "ui":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8765)
    elif len(sys.argv) > 1 and sys.argv[1] == "mcp-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
