import asyncio
import io
import os

from PIL import Image
from yet_another_comfy_client import (
    EventType,
    StatusData,
    YetAnotherComfyClient,
    edit_prompt,
)

from src.controllers.ctrl_types import ServerData
from src.controllers.server_ctrl import StatusEnum
from src.core.config import Config
from src.core.utils import LoRAInjector
from src.core.utils.maskinjector import inject_masks
from src.db.records import (
    FixerRecord,
    GeneratorRecord,
    JobRecord,
    ServerRecord,
)
from src.db.records.job_rec import JobStatus, MaskRegionPrompt


async def listen_for_events_from_comfyui(sd: ServerData):
    async for event in sd.client.get_events():
        print(
            "Event from Comfyui ",
            sd.code_name,
            ": ",
            event.type,
            "data",
            event.data,
        )
        if event.type == EventType.EXECUTION_SUCCESS:
            break

        elif event.type == EventType.STATUS:
            assert isinstance(event.data, StatusData)
            if event.data.status.exec_info.queue_remaining == 0:
                break

    print("Event from Comfyui ", sd.code_name, " closed")


class Manager:
    _servers: dict[str, ServerData]
    _jobid_queue: asyncio.Queue[int]
    _cmdid_queue: asyncio.Queue[int]

    def __init__(self, conf: Config):
        self._conf = conf
        self._servers = {}
        self._jobid_queue = asyncio.Queue()
        self._cmdid_queue = asyncio.Queue()

    async def start_background_tasks(self):
        asyncio.create_task(self.update_servers_thread())
        asyncio.create_task(self.execute_jobs())
        asyncio.create_task(self.execute_commands())

    async def update_servers_thread(self):
        while True:
            servers = await ServerRecord.all()
            for server in servers:
                client = YetAnotherComfyClient(server.host)
                status = StatusEnum.ONLINE
                try:
                    await client.get_history()
                except Exception:
                    status = StatusEnum.OFFLINE

                if status == StatusEnum.ONLINE:
                    if server.code_name not in self._servers.keys():
                        print("adding server", server.code_name)
                        sd = ServerData(
                            id=server.id,
                            host=server.host,
                            code_name=server.code_name,
                            client=client,
                        )
                        print("comfyui with code name", sd.code_name, "is online")
                        self._servers[server.code_name] = sd
                    else:
                        await client.close()

                        # def event_worker():
                        #     asyncio.run(listen_for_events_from_comfyui(sd))

                        # thread = Thread(target=event_worker, daemon=True)
                        # thread.start()

                elif status == StatusEnum.OFFLINE:
                    await client.close()
                    if server.code_name in self._servers.keys():
                        print("removing server", server.code_name)
                        await self._servers[server.code_name].client.close()
                        del self._servers[server.code_name]

            await asyncio.sleep(1)

    async def add_job(self, job_id: int):
        await self._jobid_queue.put(job_id)

    async def add_command(self, cmd_id: int):
        await self._cmdid_queue.put(cmd_id)

    async def execute_commands(self):
        print("ready for commands")
        while True:
            cmd_id = await self._cmdid_queue.get()
            print("received command", cmd_id)
            jobs = await JobRecord.filter(command_id=cmd_id).values("id")
            for v in jobs:
                job = await JobRecord.get_or_none(id=v["id"])
                if job is None:
                    continue

                if job.server_code_name in self._servers.keys():
                    client = self._servers[job.server_code_name].client
                    if job.generator_code_name is not None:
                        await generate_image(client, job)
                    elif job.fixer_code_name is not None:
                        await fix_image(client, job)

    async def execute_jobs(self):
        print("ready for jobs from queue")
        while True:
            job_id = await self._jobid_queue.get()
            print("Received job", job_id)
            job = await JobRecord.get_or_none(id=job_id)
            if job is None:
                continue

            if job.server_code_name in self._servers.keys():
                client = self._servers[job.server_code_name].client
                if job.generator_code_name is not None:
                    await generate_image(client, job)
                elif job.fixer_code_name is not None:
                    await fix_image(client, job)


async def fix_image(client: YetAnotherComfyClient, job: JobRecord):
    fixer = await FixerRecord.get_or_none(code_name=job.fixer_code_name)
    if fixer is None:
        return

    original_job = await JobRecord.get_or_none(id=job.fix_job_id)
    if original_job is None:
        return

    img_path = os.path.abspath(original_job.result_img)
    prompt = edit_prompt(
        fixer.workflow_json,
        fixer.load_image_title,
        "image",
        img_path,
    )
    res = await client.queue_prompt(prompt)
    job.comfyui_prompt_id = res["prompt_id"]
    job.status = JobStatus.PROCESSING
    await job.save()
    print("Processing job", job)
    async for event in client.get_events():
        if event.type == EventType.EXECUTION_SUCCESS:
            break

        elif event.type == EventType.STATUS:
            assert isinstance(event.data, StatusData)
            if event.data.status.exec_info.queue_remaining == 0:
                break
    output = await client.get_images_by_prompt_id(job.comfyui_prompt_id)
    if output is not None:
        for node_id, node_images in output.output_images.items():
            for oid, image_data in enumerate(node_images):
                image = Image.open(io.BytesIO(image_data))
                image.save(job.result_img)

    job.status = JobStatus.FINISHED
    await job.save()
    print("Finished job", job.id)


async def generate_image(client: YetAnotherComfyClient, job: JobRecord):
    gen = await GeneratorRecord.get_or_none(code_name=job.generator_code_name)
    if gen is None:
        return

    prompt = edit_prompt(
        gen.workflow_json,
        gen.positive_prompt_title,
        "text",
        job.prompt_positive,
    )
    prompt = edit_prompt(
        gen.workflow_json,
        gen.negative_prompt_title,
        "text",
        job.prompt_negative,
    )

    if (
        job.reference_controlnet_img is not None
        and gen.load_image_controlnet_title is not None
        and len(gen.load_image_controlnet_title) > 0
    ):
        prompt = edit_prompt(
            prompt,
            gen.load_image_controlnet_title,
            "image",
            job.reference_controlnet_img,
        )

    if (
        job.reference_ipadapter_img is not None
        and gen.load_image_ipadapter_title is not None
        and len(gen.load_image_ipadapter_title) > 0
    ):
        prompt = edit_prompt(
            prompt,
            gen.load_image_ipadapter_title,
            "image",
            job.reference_ipadapter_img,
        )

    if job.lora_list is not None and len(job.lora_list) > 0:
        inj = LoRAInjector(prompt)
        inj.add_multiple_loras(job.lora_list)
        prompt = inj.get_workflow()

    if job.mask_region_prompts is not None:
        ccps = []
        for v in job.mask_region_prompts.values():
            ccp = MaskRegionPrompt(**v)
            ccps.append(ccp)

        prompt = inject_masks(
            prompt,
            ccps,
        )
        print("masked workflow", prompt)

    res = await client.queue_prompt(prompt)
    job.comfyui_prompt_id = res["prompt_id"]
    job.status = JobStatus.PROCESSING
    await job.save()
    print("Processing job", job)
    async for event in client.get_events():
        if event.type == EventType.EXECUTION_SUCCESS:
            break

        elif event.type == EventType.STATUS:
            assert isinstance(event.data, StatusData)
            if event.data.status.exec_info.queue_remaining == 0:
                break
    output = await client.get_images_by_prompt_id(job.comfyui_prompt_id)
    if output is not None:
        for node_id, node_images in output.output_images.items():
            for oid, image_data in enumerate(node_images):
                image = Image.open(io.BytesIO(image_data))
                image.save(job.result_img)

    job.status = JobStatus.FINISHED
    await job.save()
    print("Finished job", job.id)
