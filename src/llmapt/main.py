"""ASGI entry point used by Uvicorn and container runtimes."""

from llmapt.api import create_app

app = create_app()
