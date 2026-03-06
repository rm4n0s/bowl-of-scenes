import asyncio
import json
import os
from pathlib import Path

import aiofiles
import aiohttp
from bs4 import BeautifulSoup


async def list_loras_from_comfyui(host="http://localhost:8188"):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{host}/models/loras") as response:
            return await response.json()


async def upload_multiple_loras_from_comfyui(folder_path, host="http://localhost:8188"):
    lora_files = [
        f for f in os.listdir(folder_path) if f.endswith((".safetensors", ".pt"))
    ]
    results = []

    async with aiohttp.ClientSession() as session:
        tasks = [
            upload_single_lora_comfyui(session, os.path.join(folder_path, f), host)
            for f in lora_files
        ]
        results = await asyncio.gather(*tasks)

    return results


async def upload_single_lora_comfyui(session, file_path, host="http://localhost:8188"):
    file_name = os.path.basename(file_path)
    print(f"Uploading {file_name}...")

    with open(file_path, "rb") as f:
        form = aiohttp.FormData()
        form.add_field("file", f, filename=file_name)
        form.add_field("type", "loras")
        form.add_field("overwrite", "true")

        async with session.post(f"{host}/upload/model", data=form) as response:
            result = await response.json()
            print(f"  ✓ Done: {file_name} - {response.status}")
            return {"file": file_name, "status": response.status, "response": result}


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
