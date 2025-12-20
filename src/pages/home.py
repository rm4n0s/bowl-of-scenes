from nicegui import ui


def init():
    @ui.page("/")
    def home_page():
        ui.dark_mode().auto()
        ui.label("Home Page").classes("text-h3")
        ui.link("Go to Servers", "/servers")
