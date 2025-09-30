"""Utility functions."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional

import httpx


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_command(command: list[str], *, timeout: int | None = None) -> CommandResult:
    process = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return CommandResult(command=command, returncode=process.returncode, stdout=process.stdout, stderr=process.stderr)


def which(command: str) -> Optional[str]:
    return shutil.which(command)


def compare_versions(installed: str, minimum: str) -> bool:
    def normalize(value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in value.split(".") if part.isdigit())

    return normalize(installed) >= normalize(minimum)


def sha256_of_path(path: Path) -> str:
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(path.rglob("*")):
            if child.is_file():
                digest.update(child.relative_to(path).as_posix().encode("utf-8"))
                digest.update(child.read_bytes())
        return digest.hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def read_json(path: Path) -> MutableMapping[str, object]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_env_vars(env_specs: Iterable[tuple[str, Optional[str]]]) -> Mapping[str, str]:
    resolved: dict[str, str] = {}
    for name, fallback in env_specs:
        value = os.environ.get(name, fallback)
        if value is None:
            raise EnvironmentError(f"Missing required environment variable: {name}")
        resolved[name] = value
    return resolved


def wait_for_http(url: str, timeout: int, *, verify_ssl: bool = True) -> None:
    deadline = time.time() + timeout
    with httpx.Client(verify=verify_ssl, timeout=10.0) as client:
        while time.time() < deadline:
            try:
                response = client.get(url)
                if response.status_code < 500:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(2)
    raise TimeoutError(f"HTTP endpoint did not become ready: {url}")


def wait_for_tcp(address: str, port: int, timeout: int) -> None:
    import socket

    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            try:
                sock.connect((address, port))
                return
            except OSError:
                time.sleep(2)
    raise TimeoutError(f"Port {address}:{port} did not open within {timeout}s")


def redact(value: str, patterns: Iterable[str]) -> str:
    redacted = value
    for pattern in patterns:
        redacted = redacted.replace(pattern, "***")
    return redacted
