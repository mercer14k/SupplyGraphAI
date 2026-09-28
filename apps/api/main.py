"""ASGI entry point; run uvicorn apps.api.main:app."""

from supplygraph.api import create_app

app = create_app()
