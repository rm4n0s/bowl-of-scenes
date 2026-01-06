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

from src.controllers.ctrl_types import JobOutput, ServerData
from src.controllers.server_ctrl import StatusEnum
from src.core.config import Config
from src.core.utils import LoRAInjector
from src.db.records import JobRecord, ServerRecord, WorkflowRecord
from src.db.records.job_rec import JobStatus


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
    _job_queue: asyncio.Queue[JobOutput]

    def __init__(self, conf: Config):
        self._conf = conf
        self._servers = {}
        self._job_queue = asyncio.Queue()

    async def start_background_tasks(self):
        asyncio.create_task(self.update_servers_thread())
        asyncio.create_task(self.execute_jobs())

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

    async def add_job(self, job: JobOutput):
        await self._job_queue.put(job)

    async def execute_jobs(self):
        print("ready for jobs from queue")
        while True:
            job = await self._job_queue.get()
            print("Received job", job)
            if job.server_code_name in self._servers.keys():
                client = self._servers[job.server_code_name].client
                wf = await WorkflowRecord.get_or_none(code_name=job.workflow_code_name)
                if wf is None:
                    continue

                prompt = edit_prompt(
                    wf.workflow_json,
                    wf.positive_prompt_title,
                    "text",
                    job.prompt_positive,
                )
                prompt = edit_prompt(
                    wf.workflow_json,
                    wf.negative_prompt_title,
                    "text",
                    job.prompt_negative,
                )

                if (
                    job.reference_controlnet_img is not None
                    and wf.load_image_controlnet_title is not None
                    and len(wf.load_image_controlnet_title) > 0
                ):
                    img_path = os.path.abspath(job.reference_controlnet_img)
                    prompt = edit_prompt(
                        prompt,
                        wf.load_image_controlnet_title,
                        "image",
                        img_path,
                    )

                if (
                    job.reference_ipadapter_img is not None
                    and wf.load_image_ipadapter_title is not None
                    and len(wf.load_image_ipadapter_title) > 0
                ):
                    img_path = os.path.abspath(job.reference_ipadapter_img)
                    prompt = edit_prompt(
                        prompt,
                        wf.load_image_ipadapter_title,
                        "image",
                        img_path,
                    )

                if job.lora_list is not None and len(job.lora_list) > 0:
                    inj = LoRAInjector(prompt)
                    inj.add_multiple_loras(job.lora_list)
                    prompt = inj.get_workflow()

                res = await client.queue_prompt(prompt)
                job_rec = await JobRecord.get(id=job.id)
                job_rec.comfyui_prompt_id = res["prompt_id"]
                job_rec.status = JobStatus.PROCESSING
                await job_rec.save()
                print("Processing job", job)
                async for event in client.get_events():
                    if event.type == EventType.EXECUTION_SUCCESS:
                        break

                    elif event.type == EventType.STATUS:
                        assert isinstance(event.data, StatusData)
                        if event.data.status.exec_info.queue_remaining == 0:
                            break
                output = await client.get_images_by_prompt_id(job_rec.comfyui_prompt_id)
                if output is not None:
                    for node_id, node_images in output.output_images.items():
                        for oid, image_data in enumerate(node_images):
                            image = Image.open(io.BytesIO(image_data))
                            image.save(job.result_img)

                job_rec.status = JobStatus.FINISHED
                await job_rec.save()
                print("Finished job", job_rec.id)
