from fastapi import HTTPException
from nicegui import ui

from src.controllers.project_ctrl import ProjectOutput, get_project
from src.core.config import Config


class CommandsPage:
    def __init__(self, conf: Config, project: ProjectOutput):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.project = project


def init(conf: Config):
    @ui.page("/projects/{project_id}/commands")
    async def page(project_id: int):
        ui.dark_mode().auto()
        project = await get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Group not found")
        page = CommandsPage(conf, project)
        await page.render()
        await page.load_items()
