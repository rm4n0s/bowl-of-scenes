from nicegui import ui


def init():
    @ui.page("/")
    def home_page():
        ui.dark_mode().auto()
        ui.label("Home Page").classes("text-h3")
        ui.link("Servers", "/servers")
        ui.link("Workflows", "/workflows")
        ui.link("Categories", "/categories")
        ui.link("Groups", "/groups")
