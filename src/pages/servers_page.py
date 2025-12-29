from dataclasses import asdict

from nicegui import ui

from src.controllers.server_ctrl import (
    ServerInput,
    add_server,
    list_servers,
)


class ServersPage:
    table: ui.table | None

    def __init__(self):
        self.servers = []
        self.selected_server = None
        self.table = None

    async def load_servers(self):
        """Load servers from database"""
        srvs = await list_servers()
        servers_dicts = [asdict(server) for server in srvs]
        print("load_servers", servers_dicts)
        self.servers = servers_dicts
        if self.table:
            self.table.rows = self.servers  # Assign new rows
            self.table.update()

    async def delete_server(self, server_id):
        """Delete server"""
        # await ServerRecord.filter(id=server_id).delete()
        await self.load_servers()
        ui.notify("Server deleted successfully", type="positive")

    def show_create_dialog(self):
        """Show dialog for creating new server"""
        with ui.dialog() as dialog, ui.card():
            ui.label("Create New Server").classes("text-h6")

            name_input = ui.input("Name").props("outlined")
            host_input = ui.input("Host", value="http://127.0.0.1:8188").props(
                "outlined"
            )
            code_name_input = ui.input("Code name").props("outlined")
            is_local = ui.checkbox("Is Local", value=True).props("outlined")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Create",
                    on_click=lambda: self.handle_create(
                        dialog,
                        name_input.value,
                        host_input.value,
                        code_name_input.value,
                        is_local.value,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_create(
        self, dialog, name: str, host: str, code_name: str, is_local: bool
    ):
        """Handle server creation"""
        if not name or not host:
            ui.notify("Name and IP are required", type="negative")
            return

        input = ServerInput(
            name=name, host=host, code_name=code_name, is_local=is_local
        )
        await add_server(input)
        await self.load_servers()
        ui.notify("Server created successfully", type="positive")

        dialog.close()

    def show_edit_dialog(self, server):
        """Show dialog for editing server"""
        with ui.dialog() as dialog, ui.card():
            ui.label("Edit Server").classes("text-h6")

            name_input = ui.input("Name", value=server["name"]).props("outlined")
            host_input = ui.input("Host", value=server["host"]).props("outlined")
            code_name_input = ui.input("Code name", value=server["code_name"]).props(
                "outlined"
            )
            is_local = ui.checkbox("Is Local").props("outlined")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Update",
                    on_click=lambda: self.handle_update(
                        dialog,
                        server["id"],
                        name_input.value,
                        host_input.value,
                        code_name_input.value,
                        is_local.value,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_update(self, dialog, server_id, name, host, code_name, is_local):
        """Handle server update"""
        if not name or not host:
            ui.notify("Name and IP are required", type="negative")
            return

        await self.load_servers()
        ui.notify("Server updated successfully", type="positive")
        dialog.close()

    def show_delete_dialog(self, server):
        """Show confirmation dialog for deletion"""
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete {server['name']}?").classes("text-h6")
            ui.label("This action cannot be undone.")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Delete", on_click=lambda: self.handle_delete(dialog, server["id"])
                ).props("color=negative")

        dialog.open()

    async def handle_delete(self, dialog, server_id):
        """Handle server deletion"""
        await self.delete_server(server_id)
        dialog.close()

    async def render(self):
        """Render the CRUD page"""
        ui.label("Server Management").classes("text-h4 q-mb-md")

        # Action buttons
        with ui.row().classes("q-mb-md"):
            ui.button("Add Server", icon="add", on_click=self.show_create_dialog).props(
                "color=primary"
            )
            ui.button("Refresh", icon="refresh", on_click=self.load_servers)

        @ui.refreshable
        async def server_table():
            await self.load_servers()
            # Table with servers
            columns = [
                {"name": "id", "label": "ID", "field": "id", "align": "left"},
                {"name": "name", "label": "Name", "field": "name", "align": "left"},
                {"name": "host", "label": "Host", "field": "host", "align": "left"},
                {
                    "name": "is_local",
                    "label": "Is Local",
                    "field": "is_local",
                    "align": "left",
                },
                {
                    "name": "code_name",
                    "label": "Code name",
                    "field": "code_name",
                    "align": "left",
                },
                {
                    "name": "status",
                    "label": "Status",
                    "field": "status",
                    "align": "left",
                },
                {
                    "name": "actions",
                    "label": "Actions",
                    "field": "actions",
                    "align": "right",
                },
            ]
            print("self_servers", self.servers)
            self.table = ui.table(
                columns=columns, rows=self.servers, row_key="id"
            ).classes("w-full")

            # Add action buttons to each row
            self.table.add_slot(
                "body-cell-actions",
                """
                <q-td :props="props">
                    <q-btn flat dense icon="edit" @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat dense icon="delete" color="negative" @click="$parent.$emit('delete', props.row)" />
                </q-td>
            """,
            )

            self.table.on("edit", lambda e: self.show_edit_dialog(e.args))
            self.table.on("delete", lambda e: self.show_delete_dialog(e.args))

        await server_table()


def init():
    @ui.page("/servers")
    async def servers_page():
        ui.dark_mode().auto()
        page = ServersPage()
        await page.render()
        await page.load_servers()
