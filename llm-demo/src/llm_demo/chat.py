"""Interactive chat client for the warmup stack."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import httpx
import typer
from rich.console import Console
from rich.prompt import Prompt

from .config import WarmupConfig, load_model_config
from .paths import DemoPaths
from .utils import redact

console = Console()


def _timestamp() -> str:
    return datetime.utcnow().isoformat()


def _transcript_path(paths: DemoPaths, session_id: str) -> Path:
    paths.ensure()
    transcript_dir = paths.transcripts
    transcript_dir.mkdir(parents=True, exist_ok=True)
    return transcript_dir / f"{session_id}.jsonl"


def _write_transcript_line(path: Path, payload: Dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def chat(
    *,
    root_path: str,
    model_config_path: str,
    session_id: str | None = None,
) -> None:
    paths = DemoPaths(Path(root_path).resolve())
    paths.ensure()
    run_id = session_id or datetime.utcnow().strftime("chat-%Y%m%d-%H%M%S")
    transcript_path = _transcript_path(paths, run_id)
    warmup_config = load_model_config(paths.root / model_config_path)
    model_config = warmup_config.model

    console.print(f"[bold green]LLM demo chat[/] using model [cyan]{model_config.identifier}[/]")
    console.print("Type ':exit' to quit or ':reset' to clear context.")

    memory: List[Dict[str, str]] = []
    history: List[Dict[str, str]] = []
    patterns = model_config.redaction_patterns or ["key", "token", "secret"]

    with httpx.Client(timeout=60.0) as client:
        while True:
            try:
                prompt = Prompt.ask("[bold blue]You[/]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold yellow]Session terminated[/]")
                break

            if not prompt:
                continue
            if prompt.strip().lower() == ":exit":
                break
            if prompt.strip().lower() == ":reset":
                memory.clear()
                console.print("[italic]Memory cleared[/]")
                continue

            memory.append({"role": "user", "content": prompt})
            start = time.perf_counter()

            if model_config.dry_run:
                response_text = f"[dry-run reply] Echo: {prompt[:60]}"
            else:
                payload = {
                    "inputs": prompt,
                    "parameters": {"max_output_tokens": model_config.tensor_rt_llm.max_output_len},
                    "conversation": memory,
                }
                http_response = client.post(model_config.endpoints.http, json=payload)
                if http_response.status_code >= 400:
                    console.print(f"[red]Error {http_response.status_code}[/]: {http_response.text}")
                    continue
                response_json = http_response.json()
                if isinstance(response_json, dict) and "outputs" in response_json:
                    response_text = str(response_json["outputs"])
                else:
                    response_text = http_response.text

            memory.append({"role": "assistant", "content": response_text})
            latency = time.perf_counter() - start
            console.print(f"[bold magenta]Model[/]: {response_text}")
            console.print(f"[dim]Latency: {latency:.2f}s[/]")

            history.append(
                {
                    "timestamp": _timestamp(),
                    "prompt": prompt,
                    "response": response_text,
                    "latency_s": latency,
                }
            )
            _write_transcript_line(
                transcript_path,
                {
                    "prompt": redact(prompt, patterns),
                    "response": redact(response_text, patterns),
                    "latency_s": latency,
                    "timestamp": _timestamp(),
                },
            )

    console.print(f"[bold green]Transcript saved to[/] {transcript_path}")


def chat_command(
    root_path: str,
    model_config_path: str,
    session_id: str | None,
) -> None:
    try:
        chat(root_path=root_path, model_config_path=model_config_path, session_id=session_id)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Chat session failed:[/] {exc}")
        sys.exit(1)
