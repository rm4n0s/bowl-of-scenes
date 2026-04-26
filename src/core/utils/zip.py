import asyncio
import zipfile
from pathlib import Path


def _create_zip(files: list[Path], output: str):
    """Runs in a thread — blocking is fine here."""
    with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as zf:
        for file in files:
            zf.write(file, arcname=file.name)


async def create_zip(files: list[Path], output: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _create_zip, files, output)
