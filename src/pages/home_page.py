from nicegui import ui

from src.pages.common.nav_menu import common_nav_menu


def init():
    @ui.page("/")
    async def home_page():
        ui.dark_mode().auto()
        ui.label("Home Page").classes("text-h3")
        await common_nav_menu()
