"""
Registry screen.

Searchable list of all yt-dlp supported sites and their health status.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from ...health import SiteHealth


class RegistryScreen(Screen):
    """Screen for browsing and searching supported sites."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("/", "focus_search", "Search"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.health = SiteHealth()
        self._matrix: dict[str, bool] = {}
        self._all_sites: list[tuple[str, bool]] = []
        self._filtered_sites: list[tuple[str, bool]] = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="registry-container"):
            with Horizontal(id="registry-header"):
                yield Label("Site Registry", id="registry-title")
                yield Input(placeholder="Search sites...", id="registry-search")
                yield Label("", id="registry-stats")

            yield DataTable(id="registry-table", cursor_type="row")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the site list."""
        table = self.query_one("#registry-table", DataTable)
        table.add_column("Site Name", width=30)
        table.add_column("Status", width=15)
        table.zebra_stripes = True

        await self._load_data()
        self.query_one("#registry-search", Input).focus()

    async def _load_data(self) -> None:
        """Fetch and populate site data."""
        self.notify("Fetching site intelligence...", timeout=2)
        self._matrix = await self.health.fetch_status_matrix()

        # Convert matrix to sortable list
        self._all_sites = sorted(self._matrix.items(), key=lambda x: x[0])
        self._filtered_sites = self._all_sites
        self._populate_table()
        self._update_stats()

    def _populate_table(self) -> None:
        """Update table rows."""
        table = self.query_one("#registry-table", DataTable)
        table.clear()

        for site, is_working in self._filtered_sites:
            status = " [green]Working[/green]" if is_working else " [red]Broken[/red]"
            table.add_row(site, status)

    def _update_stats(self) -> None:
        """Update the stats label."""
        total = len(self._all_sites)
        working = sum(1 for _, w in self._all_sites if w)
        broken = total - working

        stats = self.query_one("#registry-stats", Label)
        stats.update(
            f"Total: {total} | [green]Working: {working}[/green] | [red]Broken: {broken}[/red]"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter list as user types."""
        if event.input.id == "registry-search":
            query = event.value.strip().lower()
            if not query:
                self._filtered_sites = self._all_sites
            else:
                self._filtered_sites = [(s, w) for s, w in self._all_sites if query in s.lower()]
            self._populate_table()

    def action_focus_search(self) -> None:
        self.query_one("#registry-search", Input).focus()

    async def action_refresh(self) -> None:
        await self._load_data()

    def action_go_back(self) -> None:
        self.app.pop_screen()
