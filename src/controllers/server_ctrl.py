from yet_another_comfy_client import (
    YetAnotherComfyClient,
)

from src.controllers.ctrl_types import ServerInput, ServerOutput, StatusEnum
from src.controllers.serializers import serialize_server
from src.core.utils.paginator import PaginatedOutput
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
        sout = await serialize_server(sr)
        server_outs.append(sout)
    return server_outs


async def list_servers_paginated(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedOutput:
    offset = (page - 1) * page_size

    total = await ServerRecord.all().count()
    items = await ServerRecord.all().offset(offset).limit(page_size)

    return PaginatedOutput(
        items=[await serialize_server(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
