import json
import sys

from rich.console import Console
from rich.table import Table

from zget.config import CONFIG_DIR, CONFIG_FILE

console = Console()


def handle_config(args):
    """Handle zget config command."""
    # If using subparsers, action and params will be on args
    action = getattr(args, "config_action", None)
    params = getattr(args, "config_params", [])

    if not action or action == "show":
        show_config()
    elif action == "set":
        if len(params) < 2:
            console.print("[red]Error: 'set' requires a key and a value.[/red]")
            console.print("Usage: zget config set <key> <value>")
            sys.exit(1)
        set_config(params[0], params[1])
    elif action == "unset":
        if not params:
            console.print("[red]Error: 'unset' requires a key.[/red]")
            sys.exit(1)
        unset_config(params[0])
    else:
        console.print(f"[red]Unknown config action: {action}[/red]")
        sys.exit(1)


def show_config():
    """Show current persistent configuration."""
    if not CONFIG_FILE.exists():
        console.print("[dim]No persistent config found at " + str(CONFIG_FILE) + "[/dim]")
        return

    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except Exception as e:
        console.print(f"[red]Error reading config: {e}[/red]")
        return

    if not config:
        console.print("[dim]Persistent config is empty.[/dim]")
        return

    table = Table(title="zget Persistent Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for k, v in config.items():
        table.add_row(k, str(v))

    console.print(table)


def set_config(key, value):
    """Set a configuration value."""
    # Map friendly keys if needed, but for now we'll allow anything
    # Friendly mapping for common keys
    key_map = {
        "output_dir": "output_dir",
        "flat": "flat_output",
        "template": "filename_template",
        "zget_home": "zget_home",
    }

    config_key = key_map.get(key, key)

    # Try to parse numeric/bool types
    if value.lower() == "true":
        typed_value = True
    elif value.lower() == "false":
        typed_value = False
    else:
        try:
            typed_value = int(value)
        except ValueError:
            typed_value = value

    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            console.print(f"[yellow]Warning: could not read existing config: {e}[/yellow]")

    config[config_key] = typed_value

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

    console.print(f"[green]✓[/green] Set [cyan]{config_key}[/cyan] to [green]{typed_value}[/green]")


def unset_config(key):
    """Remove a configuration key."""
    if not CONFIG_FILE.exists():
        return

    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        console.print(f"[yellow]Warning: could not read config: {e}[/yellow]")
        return

    if key in config:
        del config[key]
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        console.print(f"[green]✓[/green] Unset [cyan]{key}[/cyan]")
    else:
        # Check mapped keys too
        key_map = {
            "output_dir": "output_dir",
            "flat": "flat_output",
            "template": "filename_template",
        }
        mapped_key = key_map.get(key)
        if mapped_key and mapped_key in config:
            del config[mapped_key]
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            console.print(f"[green]✓[/green] Unset [cyan]{mapped_key}[/cyan]")
        else:
            console.print(f"[yellow]Key not found: {key}[/yellow]")
