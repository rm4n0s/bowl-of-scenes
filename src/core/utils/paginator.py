from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

from nicegui import ui

T = TypeVar("T")


@dataclass
class PaginatedOutput(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class Paginator(Generic[T]):
    def __init__(
        self,
        fetch_fn: Callable[[int, int], Awaitable[PaginatedOutput[T]]],
        on_change: Callable[[list[T]], Awaitable[None]],
        page_size: int = 20,
        window: int = 2,  # pages shown around current page
    ):
        self._fetch_fn = fetch_fn
        self._on_change = on_change
        self.page_size = page_size
        self.window = window
        self.page = 1
        self.total = 0
        self.total_pages = 1
        self.items: list[T] = []
        self._controls_row = None

    async def load(self):
        result = await self._fetch_fn(self.page, self.page_size)
        self.items = result.items
        self.total = result.total
        self.total_pages = result.total_pages
        self._refresh_controls()
        await self._on_change(self.items)

    async def go_to(self, page: int):
        target = max(1, min(page, self.total_pages))
        if target != self.page:
            self.page = target
            await self.load()

    async def reset(self):
        self.page = 1
        await self.load()

    def _page_numbers(self) -> list[int | None]:
        total = self.total_pages
        cur = self.page

        if total <= 1:
            return [1]  # nothing to paginate, just show page 1

        w = self.window
        always = set()
        always.add(1)
        always.add(total)
        for p in range(max(1, cur - w), min(total, cur + w) + 1):
            always.add(p)

        sorted_pages = sorted(always)

        result: list[int | None] = []
        prev = None
        for p in sorted_pages:
            if prev is not None and p - prev > 1:
                result.append(None)
            result.append(p)
            prev = p

        return result

    def _refresh_controls(self):
        if self._controls_row:
            self._controls_row.clear()
            with self._controls_row:
                self._render_buttons()

    def _render_buttons(self):
        is_first = self.page == 1
        is_last = self.page == self.total_pages

        # First page
        ui.button(icon="first_page", on_click=lambda: self.go_to(1)).props(
            "flat dense"
        ).set_enabled(not is_first)

        # Prev page
        ui.button(
            icon="chevron_left", on_click=lambda: self.go_to(self.page - 1)
        ).props("flat dense").set_enabled(not is_first)

        # Page number buttons with ellipsis
        for p in self._page_numbers():
            if p is None:
                ui.label("…").classes("q-px-xs self-center")
            else:
                is_current = p == self.page
                (
                    ui.button(str(p), on_click=lambda p=p: self.go_to(p))  # pyright: ignore[reportArgumentType]
                    .props(f"{'unelevated' if is_current else 'flat'} dense")
                    .classes("q-px-xs" + (" text-primary" if is_current else ""))
                )

        # Next page
        ui.button(
            icon="chevron_right", on_click=lambda: self.go_to(self.page + 1)
        ).props("flat dense").set_enabled(not is_last)

        # Last page
        ui.button(
            icon="last_page", on_click=lambda: self.go_to(self.total_pages)
        ).props("flat dense").set_enabled(not is_last)

        # Jump-to input
        ui.separator().props("vertical").classes("q-mx-sm")
        jump_input = (
            ui.number(
                label="Go to page",
                value=self.page,
                min=1,
                max=self.total_pages,
                precision=0,
            )
            .props("dense outlined")
            .style("width: 100px")
        )

        async def on_jump():
            val = jump_input.value
            if val is not None:
                await self.go_to(int(val))

        ui.button("Go", on_click=on_jump).props("dense flat")

        # Total label
        ui.separator().props("vertical").classes("q-mx-sm")
        ui.label(f"{self.total} total").classes("self-center text-grey-6 text-caption")

    def render_controls(self):
        """Call once inside your page render to place the pagination bar."""
        with ui.row().classes("items-center q-mt-md flex-wrap gap-1") as row:
            self._controls_row = row
            self._render_buttons()
