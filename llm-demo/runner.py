import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from llm_demo.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
