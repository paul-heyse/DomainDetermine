"""Prototype entrypoint for running the NiceGUI app."""

from __future__ import annotations

from gui.app import create_app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000)

