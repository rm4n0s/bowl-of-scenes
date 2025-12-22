from dataclasses import dataclass
from typing import Any

from src.db.records import WorkflowRecord


@dataclass
class WorkflowInput:
    name: str
    code_name: str
    workflow_json: dict[str, Any]
    load_image_ipadapter_title: str | None
    load_image_controlnet_title: str | None
    save_image_title: str


@dataclass
class WorkflowOutput:
    id: int
    name: str
    code_name: str
    load_image_ipadapter_title: str | None
    load_image_controlnet_title: str | None
    save_image_title: str


async def add_workflow(input: WorkflowInput):
    await WorkflowRecord.create(
        name=input.name,
        code_name=input.code_name,
        load_image_ipadapter_title=input.load_image_ipadapter_title,
        load_image_controlnet_title=input.load_image_controlnet_title,
        save_image_title=input.save_image_title,
        workflow_json=input.workflow_json,
    )


async def list_workflows() -> list[WorkflowOutput]:
    wf_recs = await WorkflowRecord.all()
    wf_outs = []
    for wf in wf_recs:
        wout = WorkflowOutput(
            id=wf.id,
            name=wf.name,
            code_name=wf.code_name,
            load_image_ipadapter_title=wf.load_image_ipadapter_title,
            load_image_controlnet_title=wf.load_image_controlnet_title,
            save_image_title=wf.save_image_title,
        )
        wf_outs.append(wout)
    return wf_outs
