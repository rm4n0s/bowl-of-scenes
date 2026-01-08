from yet_another_comfy_client import (
    YetAnotherComfyClient,
)

from src.controllers.ctrl_types import ServerInput, ServerOutput, StatusEnum
from src.db.records import ServerRecord


async def add_server(input: ServerInput):
    await ServerRecord.create(
        name=input.name,
        host=input.host,
        code_name=input.code_name,
        is_local=input.is_local,
    )


async def edit_server(id: int, input: ServerInput):
    srv = await ServerRecord.get_or_none(id=id)
    if srv is None:
        raise ValueError("Server not found")

    srv.name = input.name
    srv.code_name = input.code_name
    srv.host = input.host
    srv.is_local = input.is_local
    await srv.save()


async def delete_server(id: int):
    srv = await ServerRecord.get_or_none(id=id)
    if srv is None:
        raise ValueError("Server not found")

    await srv.delete()


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
            id=sr.id,
            name=sr.name,
            host=sr.host,
            is_local=sr.is_local,
            code_name=sr.code_name,
            status=status,
        )
        server_outs.append(sout)
    return server_outs
