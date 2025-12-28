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
from ...db.store import VideoStore


class RegistryScreen(Screen):
    """Screen for browsing and searching supported sites."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("/", "focus_search", "Search"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "cycle_sort", "Sort"),
    ]

    def __init__(self, store: VideoStore):
        super().__init__()
        self.health = SiteHealth(store)
        self._all_sites: list[dict] = []
        self._filtered_sites: list[dict] = []
        self._sort_cols = ["name", "working", "country", "language"]
        self._sort_index = 0

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="registry-container"):
            with Horizontal(id="registry-header"):
                yield Label("Site Registry", id="registry-title")
                yield Input(placeholder="Search sites...", id="registry-search")
                yield Label("", id="registry-stats")

            with Horizontal(id="registry-main"):
                # Left side: The list
                yield DataTable(id="registry-table", cursor_type="row")

                # Right side: The Detail Pane
                with Vertical(id="registry-details"):
                    yield Label("SITE DETAILS", id="details-header")
                    yield Static("", id="site-desc")
                    with Vertical(id="details-meta"):
                        yield Label("", id="site-country")
                        yield Label("", id="site-lang")
                        yield Label("", id="site-category")
                        yield Label("", id="site-confidence")
                        yield Label("", id="site-working-status")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the site list."""
        table = self.query_one("#registry-table", DataTable)
        table.add_column("Site Name", width=25)
        table.add_column("Health", width=8)  # New column
        table.add_column("Category", width=20)
        table.add_column("Status", width=12)
        table.add_column("Region", width=8)
        table.add_column("Language", width=15)
        table.zebra_stripes = True

        await self._load_data()
        self.query_one("#registry-search", Input).focus()

    async def _load_data(self) -> None:
        """Fetch and populate site data."""
        self.notify("Syncing site intelligence...", timeout=2)
        matrix = await self.health.get_working_matrix()

        # Convert to list of enriched site info
        self._all_sites = []
        for site_name in sorted(matrix.keys()):
            self._all_sites.append(self.health.get_site_info(site_name))

        self._filtered_sites = self._all_sites
        self._populate_table()
        self._update_stats()

    def _populate_table(self) -> None:
        """Update table rows."""
        table = self.query_one("#registry-table", DataTable)
        table.clear()

        for site_info in self._filtered_sites:
            # Determine Health Icon
            health_data = site_info.get("health")
            if health_data:
                health_icon = "🟢" if health_data["status"] == "PASS" else "🔴"
            else:
                health_icon = "⚪"

            # Use dimming for broken sites via Markdown or CSS if possible
            # Here we just use the status text color
            table.add_row(
                site_info["name"],
                health_icon,
                site_info.get("category", "Uncategorized"),
                status,
                site_info.get("country", "Unknown"),
                site_info.get("language", "Universal"),
                key=site_info["name"],
            )

        # If we have data, focus first row
        if self._filtered_sites:
            self._update_details(self._filtered_sites[0])

    def _update_stats(self) -> None:
        """Update the stats label."""
        total = len(self._all_sites)
        working = sum(1 for s in self._all_sites if s["working"])
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
                self._filtered_sites = [
                    s
                    for s in self._all_sites
                    if query in s["name"].lower() or query in s.get("category", "").lower()
                ]
            self._populate_table()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update details pane when navigating the table."""
        if event.row_key:
            site_name = str(event.row_key)
            site_info = next((s for s in self._filtered_sites if s["name"] == site_name), None)
            if site_info:
                self._update_details(site_info)

    def _update_details(self, site_info: dict) -> None:
        """Update the side detail panel."""
        # Use simple string formatting for description, cleaner layout
        desc = site_info["description"]
        if not desc or desc == "No description available.":
            desc = "[italic]No detailed description available.[/italic]"

        self.query_one("#site-desc", Static).update(desc)

        self.query_one("#site-country", Label).update(
            f"[bold]Region:[/bold] {site_info.get('country', 'Unknown')}"
        )
        self.query_one("#site-lang", Label).update(
            f"[bold]Language:[/bold] {site_info.get('language', 'Universal')}"
        )
        self.query_one("#site-category", Label).update(
            f"[bold]Category:[/bold] {site_info.get('category', 'Uncategorized')}"
        )

        confidence = site_info.get("confidence", "low").upper()
        conf_color = (
            "green" if confidence == "HIGH" else "yellow" if confidence == "MEDIUM" else "red"
        )

        self.query_one("#site-confidence", Label).update(
            f"[bold]Confidence:[/bold] [{conf_color}]{confidence}[/{conf_color}]"
        )

        status_text = (
            "[green]● OPERATIONAL[/green]" if site_info["working"] else "[red]● FAILED CHECKS[/red]"
        )
        self.query_one("#site-working-status", Label).update(f"[bold]Status:[/bold] {status_text}")

        # Add Last Verified
        health_data = site_info.get("health")
        verified_text = "[italic]Never verified[/italic]"
        if health_data:
            dt = health_data["timestamp"].split("T")[0]
            lat = health_data["latency"]
            color = "green" if health_data["status"] == "PASS" else "red"
            verified_text = f"[{color}]{health_data['status']} ({lat}s) on {dt}[/{color}]"

            if health_data.get("error"):
                verified_text += f"\n[red]Error: {health_data['error']}[/red]"

        # We might need a new label for this in the compose method,
        # but for now append to status label or replace a static
        # Let's assume we can append to the description or add a yield in compose.
        # Edit: I will add a yield in compose first via a separate edit,
        # or just append to working status here for simplicity.
        self.query_one("#site-working-status", Label).update(
            f"[bold]Status:[/bold] {status_text}\n[bold]Verified:[/bold] {verified_text}"
        )

    def action_focus_search(self) -> None:
        self.query_one("#registry-search", Input).focus()

    async def action_refresh(self) -> None:
        await self._load_data()

    def action_cycle_sort(self) -> None:
        """Cycle through sort columns."""
        self._sort_index = (self._sort_index + 1) % len(self._sort_cols)
        col = self._sort_cols[self._sort_index]
        self.notify(f"Sorting by {col.capitalize()}...", timeout=1)

        self._all_sites.sort(key=lambda x: x[col], reverse=(col == "working"))
        self._populate_table()

    def action_go_back(self) -> None:
        self.app.pop_screen()
