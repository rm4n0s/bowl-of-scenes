import asyncio
import json
import os
import shutil
from pathlib import Path

import aiofiles
import aiohttp
from bs4 import BeautifulSoup


async def list_loras_from_comfyui(host="http://localhost:8188"):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{host}/models/loras") as response:
            return await response.json()


def copy_lora_to_comfyui(file_path: str, comfyui_path: str, subfolder: str = "") -> str:
    """
    Copy a LoRA model file to ComfyUI's loras folder.

    Args:
        file_path: Path to the source .safetensors or .pt file
        comfyui_path: Root path of your ComfyUI installation
        subfolder: Optional subfolder inside loras/ (e.g. "characters")

    Returns:
        Destination path where the file was copied
    """
    loras_dir = os.path.join(comfyui_path, "models", "loras", subfolder)
    os.makedirs(loras_dir, exist_ok=True)

    file_name = os.path.basename(file_path)
    dest_path = os.path.join(loras_dir, file_name)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")

    shutil.copy2(file_path, dest_path)
    print(f"✓ Copied {file_name} -> {dest_path}")

    return dest_path


async def download_lora_from_civitai(
    model_id: int, output_folder: str, api_token: str | None = None
) -> dict:
    """
    Async — downloads a LoRA model from Civitai along with its metadata.

    Saves:
      - <model_id>.safetensors  — the model weights
      - <model_id>.json         — trigger words, tags, description, and model info

    Args:
        model_id:      Civitai model ID (the number in the URL: civitai.com/models/<ID>)
        output_folder: Local folder path where files will be saved
        api_token:     Civitai API token (optional but recommended — required for
                       models whose creators have enabled login-only downloads)

    Returns:
        A dict with the saved metadata (same content as the .json file)

    Raises:
        ValueError:   If the model is not found or has no versions
        RuntimeError: If the download requires auth or fails
    """

    # ------------------------------------------------------------------ #
    # 0. Setup                                                             #
    # ------------------------------------------------------------------ #
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    async with aiohttp.ClientSession(headers=headers) as session:
        # -------------------------------------------------------------- #
        # 1. Fetch model metadata                                          #
        # -------------------------------------------------------------- #
        meta_url = f"https://civitai.com/api/v1/models/{model_id}"

        async with session.get(
            meta_url, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 404:
                raise ValueError(f"Model {model_id} not found on Civitai.")
            resp.raise_for_status()
            model_data = await resp.json()

        # -------------------------------------------------------------- #
        # 2. Extract metadata fields                                       #
        # -------------------------------------------------------------- #
        model_name = model_data.get("name", "")
        model_type = model_data.get("type", "")
        raw_description = model_data.get("description") or ""
        tags = model_data.get("tags", [])

        # Strip HTML tags from description
        description = BeautifulSoup(raw_description, "html.parser").get_text(
            separator="\n", strip=True
        )

        versions = model_data.get("modelVersions", [])
        if not versions:
            raise ValueError(f"Model {model_id} has no available versions.")

        latest_version = versions[0]
        version_id = latest_version["id"]
        version_name = latest_version.get("name", "")
        base_model = latest_version.get("baseModel", "")
        trigger_words = latest_version.get("trainedWords", [])

        print(f"Model   : {model_name!r}  (type={model_type}, version={version_name})")
        print(f"Base    : {base_model}")
        print(f"Triggers: {trigger_words}")
        print(f"Tags    : {tags}")

        # -------------------------------------------------------------- #
        # 3. Save <model_id>.json                                          #
        # -------------------------------------------------------------- #
        metadata = {
            "model_id": model_id,
            "model_name": model_name,
            "model_type": model_type,
            "version_id": version_id,
            "version_name": version_name,
            "base_model": base_model,
            "trigger_words": trigger_words,
            "tags": tags,
            "description": description,
        }

        json_path = output_path / f"{model_id}.json"
        async with aiofiles.open(json_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))
        print(f"Metadata saved → {json_path}")

        # -------------------------------------------------------------- #
        # 4. Download .safetensors                                         #
        # -------------------------------------------------------------- #
        download_url = f"https://civitai.com/api/download/models/{version_id}"
        if api_token:
            download_url += f"?token={api_token}"

        safetensor_path = output_path / f"{model_id}.safetensors"
        if not os.path.exists(safetensor_path):
            print(f"Downloading model from {download_url} …")

            async with session.get(
                download_url,
                timeout=aiohttp.ClientTimeout(total=3600),  # 1h cap for large models
                allow_redirects=True,
            ) as resp:
                if resp.status == 401:
                    raise RuntimeError(
                        "Download requires authentication. "
                        "Please provide a valid api_token."
                    )
                resp.raise_for_status()

                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB

                async with aiofiles.open(safetensor_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = downloaded / total * 100
                            print(
                                f"  {pct:5.1f}%  ({downloaded:,} / {total:,} bytes)",
                                end="\r",
                            )

        print(f"\nModel saved    → {safetensor_path}")

    return metadata
