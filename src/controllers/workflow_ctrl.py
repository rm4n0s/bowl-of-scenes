from src.controllers.ctrl_types import WorkflowInput, WorkflowOutput
from src.db.records import WorkflowRecord


async def add_workflow(input: WorkflowInput):
    await WorkflowRecord.create(
        name=input.name,
        code_name=input.code_name,
        positive_prompt_title=input.positive_prompt_title,
        negative_prompt_title=input.negative_prompt_title,
        load_image_ipadapter_title=input.load_image_ipadapter_title,
        load_image_controlnet_title=input.load_image_controlnet_title,
        save_image_title=input.save_image_title,
        workflow_json=input.workflow_json,
    )


async def edit_workflow(id: int, input: WorkflowInput):
    wf = await WorkflowRecord.get_or_none(id=id)
    if wf is None:
        raise ValueError("workflow doesn't exist")

    wf.name = input.name
    wf.code_name = input.code_name
    if input.positive_prompt_title is not None:
        wf.positive_prompt_title = input.positive_prompt_title

    if input.negative_prompt_title is not None:
        wf.negative_prompt_title = input.negative_prompt_title

    if input.load_image_ipadapter_title is not None:
        wf.load_image_ipadapter_title = input.load_image_ipadapter_title

    if input.load_image_controlnet_title is not None:
        wf.load_image_controlnet_title = input.load_image_controlnet_title

    wf.save_image_title = input.save_image_title
    wf.workflow_json = input.workflow_json

    await wf.save()


async def list_workflows() -> list[WorkflowOutput]:
    wf_recs = await WorkflowRecord.all()
    wf_outs = []
    for wf in wf_recs:
        wout = WorkflowOutput(
            id=wf.id,
            name=wf.name,
            code_name=wf.code_name,
            workflow_json=wf.workflow_json,
            positive_prompt_title=wf.positive_prompt_title,
            negative_prompt_title=wf.negative_prompt_title,
            load_image_ipadapter_title=wf.load_image_ipadapter_title,
            load_image_controlnet_title=wf.load_image_controlnet_title,
            save_image_title=wf.save_image_title,
        )
        wf_outs.append(wout)
    return wf_outs


async def delete_workflow(id: int):
    wf = await WorkflowRecord.get_or_none(id=id)
    if wf is None:
        raise ValueError("workflow doesn't exist")

    await wf.delete()
