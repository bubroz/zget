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

from ...health import SiteHealth, COUNTRY_CODES
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
        self._sort_cols = ["name", "country", "category"]
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
                        yield Label("", id="site-category")
                        yield Label("", id="site-confidence")
                        yield Label("", id="site-health-status")
                        yield Label("", id="site-health-verified")
                        yield Label("ARCHIVE.ORG", id="archive-header")
                        yield Label("", id="site-archive-snapshot")
                        yield Label("", id="site-archive-link")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the site list."""
        table = self.query_one("#registry-table", DataTable)
        table.add_column("Site Name", width=40)
        table.add_column("Health", width=6)
        table.add_column("Category", width=25)
        table.add_column("Country", width=20)
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
            # Determine Health Icon from smokescreen verification
            health_data = site_info.get("health")
            if health_data:
                status_val = health_data.get("status", "unknown")
                if status_val == "ok":
                    health_icon = "🟢"
                elif status_val == "geo_blocked":
                    health_icon = "🟡"
                elif status_val in ("broken", "timeout"):
                    health_icon = "🔴"
                else:
                    health_icon = "⚪"
            else:
                health_icon = "⚪"  # Never verified

            # Country full name
            country_code = site_info.get("country", "Unknown")
            country_name = COUNTRY_CODES.get(country_code, country_code)

            table.add_row(
                site_info["name"],
                health_icon,
                site_info.get("category", "Uncategorized"),
                country_name,
                key=site_info["name"],
            )

        # If we have data, focus first row
        if self._filtered_sites:
            self._update_details(self._filtered_sites[0])

    def _update_stats(self) -> None:
        """Update the stats label."""
        total = len(self._all_sites)
        working = sum(1 for s in self._all_sites if s.get("working", True))
        broken = total - working

        # Count verified sites
        verified = sum(1 for s in self._all_sites if s.get("health"))

        stats = self.query_one("#registry-stats", Label)
        stats.update(
            f"Total: {total} | [green]Working: {working}[/green] | "
            f"[red]Broken: {broken}[/red] | Verified: {verified}"
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
                    if query in s["name"].lower()
                    or query in s.get("category", "").lower()
                    or query in COUNTRY_CODES.get(s.get("country", ""), "").lower()
                    or query in s.get("country", "").lower()
                ]
            self._populate_table()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update details pane when navigating the table."""
        # Use simple coordinate-based indexing for 100% reliability
        row_idx = event.cursor_row
        if 0 <= row_idx < len(self._filtered_sites):
            site_info = self._filtered_sites[row_idx]
            self.run_worker(self._update_details(site_info))

    def _update_details(self, site_info: dict) -> None:
        """Update the side detail panel."""
        # Description
        desc = site_info.get("description", "")
        if not desc or desc == "No description available.":
            desc = "[italic]No detailed description available.[/italic]"
        self.query_one("#site-desc", Static).update(desc)

        # Country
        country_code = site_info.get("country", "Unknown")
        country_name = COUNTRY_CODES.get(country_code, country_code)
        self.query_one("#site-country", Label).update(
            f"[bold]Country:[/bold] {country_name} ({country_code})"
        )

        # Category
        self.query_one("#site-category", Label).update(
            f"[bold]Category:[/bold] {site_info.get('category', 'Uncategorized')}"
        )

        # Confidence
        confidence = site_info.get("confidence", "low").upper()
        conf_color = (
            "green" if confidence == "HIGH" else "yellow" if confidence == "MEDIUM" else "red"
        )
        self.query_one("#site-confidence", Label).update(
            f"[bold]Confidence:[/bold] [{conf_color}]{confidence}[/{conf_color}]"
        )

        # Health Status (from yt-dlp matrix)
        working = site_info.get("working", True)
        status_text = "[green]● OPERATIONAL[/green]" if working else "[red]● BROKEN[/red]"
        self.query_one("#site-health-status", Label).update(
            f"[bold]yt-dlp Status:[/bold] {status_text}"
        )

        # Smokescreen Verification
        health_data = site_info.get("health")
        if health_data:
            status_val = health_data.get("status", "unknown")
            latency = health_data.get("latency_ms", 0)
            verified_at = health_data.get("verified_at", "")
            tested_from = health_data.get("tested_from", "local")

            # Format the verified time
            if verified_at:
                try:
                    from datetime import datetime

                    # Handle Z suffix often used in ISO format
                    dt = datetime.fromisoformat(verified_at.replace("Z", ""))
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    time_str = verified_at[:16]
            else:
                time_str = "Unknown"

            # Color based on status
            status_colors = {
                "ok": "green",
                "broken": "red",
                "timeout": "yellow",
                "geo_blocked": "yellow",
            }
            color = status_colors.get(status_val, "white")

            # Map location identifiers to flags
            loc_names = {"us": "🇺🇸 US", "nl": "🇳🇱 NL", "se": "🇸🇪 SE", "local": "🏠 Local"}
            loc_display = loc_names.get(tested_from.lower(), tested_from.upper())

            verified_text = f"[{color}]{status_val.upper()}[/{color}] ({latency}ms) @ {time_str}"
            if health_data.get("error"):
                verified_text += f"\n[dim]{health_data['error'][:60]}[/dim]"

            self.query_one("#site-health-verified", Label).update(
                f"[bold]Smokescreen:[/bold] {verified_text}\n[bold]Tested From:[/bold] {loc_display}"
            )
        else:
            self.query_one("#site-health-verified", Label).update(
                f"[bold]Smokescreen:[/bold] [dim]Not yet verified[/dim]"
            )

        # Archive.org Lookup
        archive_snap = self.query_one("#site-archive-snapshot", Label)
        archive_link = self.query_one("#site-archive-link", Label)

        archive_snap.update("[dim]Checking Archive.org...[/dim]")
        archive_link.update("")

        # Fetch archive info
        domain = site_info.get("domain", site_info["name"])
        snapshot = await self.health.get_archive_snapshot(domain)

        if snapshot:
            archive_snap.update(f"[bold]Latest Snapshot:[/bold] {snapshot['date']}")
            archive_link.update(
                f"[bold]Historical Link:[/bold] [blue underline]{snapshot['url']}[/blue underline]"
            )
        else:
            archive_snap.update("[bold]Archive.org:[/bold] [dim]No snapshots found[/dim]")
            archive_link.update("")

    def action_focus_search(self) -> None:
        self.query_one("#registry-search", Input).focus()

    async def action_refresh(self) -> None:
        await self._load_data()

    def action_cycle_sort(self) -> None:
        """Cycle through sort columns."""
        self._sort_index = (self._sort_index + 1) % len(self._sort_cols)
        col = self._sort_cols[self._sort_index]
        self.notify(f"Sorting by {col.capitalize()}...", timeout=1)

        # Sort with proper handling of missing keys
        self._all_sites.sort(key=lambda x: str(x.get(col, "")), reverse=(col == "working"))
        self._filtered_sites = self._all_sites
        self._populate_table()

    def action_go_back(self) -> None:
        self.app.pop_screen()
