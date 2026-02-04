import uvicorn
import argparse


def main():
    from ..config import PERSISTENT_CONFIG

    parser = argparse.ArgumentParser(description="zget Headless Archival Server")
    parser.add_argument(
        "--host", default=PERSISTENT_CONFIG.get("host", "0.0.0.0"), help="Host to bind to"
    )
    parser.add_argument(
        "--port", type=int, default=PERSISTENT_CONFIG.get("port", 8000), help="Port to listen on"
    )
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--open", action="store_true", help="Open browser on startup")

    parser.add_argument(
        "--secure",
        "--tailscale",
        dest="secure",
        action="store_true",
        help="Bind only to Tailscale VPN IP (Secure Mode)",
    )

    args = parser.parse_args()

    # Handle Secure Mode
    if args.secure:
        from ..net import get_tailscale_ip

        ts_ip = get_tailscale_ip()
        if ts_ip:
            print(f"🔒 SECURE MODE: Binding strictly to Tailscale IP ({ts_ip})")
            print("   Public Wi-Fi access is BLOCKED. Access via http://zget:8000")
            args.host = ts_ip
        else:
            print("⚠️  Tailscale not detected! Falling back to localhost for security.")
            args.host = "127.0.0.1"

    if args.open:
        import webbrowser
        import threading
        import time

        def open_browser():
            time.sleep(1.5)  # Give server time to start
            # If bound to 0.0.0.0 or Tailscale IP, open localhost for the user on this machine
            # (Users own machine can always reach localhost, assuming port isn't blocked output-wise)
            # Actually, if we bind to Tailscale IP (100.x), localhost (127.0.0.1) MIGHT NOT work depending on OS routing.
            # But usually 100.x is reachable locally. Let's try opening the specific IP if secure.
            target_host = "localhost"
            if args.host not in ("0.0.0.0", "127.0.0.1", "localhost"):
                target_host = args.host  # Open the specific bound IP

            url = f"http://{target_host}:{args.port}"
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("zget.server.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
