import argparse

import uvicorn


def main():
    from ..config import PERSISTENT_CONFIG

    parser = argparse.ArgumentParser(description="zget Headless Archival Server")
    parser.add_argument(
        "--host", default=PERSISTENT_CONFIG.get("host", "0.0.0.0"), help="Host to bind to"
    )
    parser.add_argument(
        "--port", type=int, default=PERSISTENT_CONFIG.get("port", 9989), help="Port to listen on"
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
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import JSONResponse

        from ..net import get_tailscale_ip
        from .app import app

        ts_ip = get_tailscale_ip()

        # In Secure Mode, we bind to 0.0.0.0 so we can catch ALL requests,
        # but we use Middleware to reject anyone who isn't Localhost or Tailscale.
        args.host = "0.0.0.0"

        allowed_ips = {"127.0.0.1", "::1", "localhost"}
        if ts_ip:
            allowed_ips.add(ts_ip)
            print(f"🔒 SECURE MODE: Active (Tailscale IP: {ts_ip})")
        else:
            print("⚠️  Tailscale not detected! Secure Mode restricted to Localhost only.")

        print(f"   Allowed: {', '.join(sorted(allowed_ips))}")
        print("   Blocked: Public Wi-Fi / LAN")

        class SecureMeshMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                client_ip = request.client.host
                if client_ip not in allowed_ips:
                    print(f"⛔️ BLOCKED connection attempt from: {client_ip}")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": (
                                "Access Denied: Secure Mesh Restriction. Connect via Tailscale."
                            )
                        },
                    )
                return await call_next(request)

        app.add_middleware(SecureMeshMiddleware)

        # When using middleware dynamically, we must pass the app object, not the string.
        # This disables 'reload', but secure mode is for production/archival usage.
        uvicorn.run(app, host=args.host, port=args.port)
        return

    if args.open:
        import threading
        import time
        import webbrowser

        def open_browser():
            time.sleep(1.5)  # Give server time to start
            url = f"http://localhost:{args.port}"
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("zget.server.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
