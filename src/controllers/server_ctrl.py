import enum
from dataclasses import dataclass

from yet_another_comfy_client import (
    YetAnotherComfyClient,
)

from src.db.records import ServerRecord


class StatusEnum(enum.StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass
class ServerInput:
    name: str
    host: str
    is_local: bool


@dataclass
class ServerOutput:
    id: int
    name: str
    host: str
    is_local: bool
    status: StatusEnum


async def add_server(input: ServerInput):
    await ServerRecord.create(name=input.name, host=input.host, is_local=input.is_local)


async def list_servers() -> list[ServerOutput]:
    server_recs = await ServerRecord.all()
    server_outs = []
    for sr in server_recs:
        client = YetAnotherComfyClient(sr.host)
        status = StatusEnum.ONLINE
        try:
            await client.get_history()
        except Exception:
            status = StatusEnum.OFFLINE

        sout = ServerOutput(
            id=sr.id, name=sr.name, host=sr.host, is_local=sr.is_local, status=status
        )
        server_outs.append(sout)
    return server_outs
