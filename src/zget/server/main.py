import uvicorn
import argparse


def main():
    parser = argparse.ArgumentParser(description="zget Headless Archival Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    uvicorn.run("zget.server.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
