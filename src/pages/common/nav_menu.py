from dataclasses import dataclass

from nicegui import ui


@dataclass
class NavMenuInput:
    name: str
    link: str


async def nav_menu(input: list[NavMenuInput]):
    with ui.header().classes("items-center justify-between"):
        with ui.row():
            for nv in input:
                ui.link(nv.name, nv.link).classes("text-white")

        ui.label("Bowl of scenes").classes("text-h6")


async def common_nav_menu():
    await nav_menu(
        [
            NavMenuInput(name="Servers", link="/servers"),
            NavMenuInput(name="Generators", link="/generators"),
            NavMenuInput(name="Fixers", link="/fixers"),
            NavMenuInput(name="Categories", link="/categories"),
            NavMenuInput(name="Groups", link="/groups"),
            NavMenuInput(name="Projects", link="/projects"),
            NavMenuInput(name="REPL", link="/repl"),
        ]
    )
