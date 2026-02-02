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

    args = parser.parse_args()

    if args.open:
        import webbrowser
        import threading
        import time

        def open_browser():
            time.sleep(1.5)  # Give server time to start
            url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}"
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("zget.server.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
