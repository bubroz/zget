"""
Main zget TUI application.

Textual-based terminal interface for video acquisition and library management.
"""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from ..config import DB_PATH, ensure_directories
from ..db import VideoStore
from .screens.unified import UnifiedScreen
from .screens.registry import RegistryScreen


class ZgetApp(App):
    """zget - Video Archive."""

    TITLE = "zget"
    SUB_TITLE = "The Archivist's Terminal"

    CSS_PATH = "styles/retro.tcss"

    def __init__(self):
        super().__init__()
        ensure_directories()
        self.store = VideoStore(DB_PATH)

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        self.install_screen(RegistryScreen(), name="registry")
        self.push_screen(UnifiedScreen())


def run():
    """Run the zget TUI application."""
    app = ZgetApp()
    app.run()


if __name__ == "__main__":
    run()
