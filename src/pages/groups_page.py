from dataclasses import asdict

from nicegui import ui


class GroupsPage:
    table: ui.table | None

    def __init__(self):
        self.items = []
        self.selected_item = None
        self.table = None

    async def load_items(self):
        wfs = await list_groups()
        wfs_dicts = [asdict(wf) for wf in wfs]
        self.items = wfs_dicts
        if self.table:
            self.table.rows = self.items  # Assign new rows
            self.table.update()

    async def render(self):
        pass


def init():
    @ui.page("/workflows")
    async def page():
        ui.dark_mode().auto()
        page = GroupsPage()
        await page.render()
        await page.load_items()
