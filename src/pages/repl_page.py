from nicegui import ui

from src.controllers.manager_ctrl import Manager
from src.core.config import Config
from src.pages.common.nav_menu import common_nav_menu


class ReplPage:
    def __init__(self, conf: Config, manager: Manager):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.manager = manager

    async def render(self):
        """Render REPL"""
        ui.label("REPL").classes("text-h4 q-mb-md")


def init(conf: Config, manager: Manager | None):
    @ui.page("/repl")
    async def page():
        ui.dark_mode().auto()
        assert manager is not None
        page = ReplPage(conf, manager)
        await common_nav_menu()
        await page.render()
