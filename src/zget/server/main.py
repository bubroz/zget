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

    args = parser.parse_args()

    uvicorn.run("zget.server.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
