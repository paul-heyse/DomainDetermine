"""Launch and teardown of Triton/TensorRT services."""
from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .config import LaunchConfig, ModelConfig
from .exceptions import LaunchError
from .paths import RunContext
from .telemetry import append_stage_log
from .utils import wait_for_http, wait_for_tcp

logger = logging.getLogger(__name__)


@dataclass
class LaunchHandle:
    mode: str
    process: Optional[subprocess.Popen] = None


class Launcher:
    def __init__(self, model_config: ModelConfig, context: RunContext) -> None:
        self.model_config = model_config
        self.context = context
        self.handle: Optional[LaunchHandle] = None

    def start(self) -> LaunchHandle:
        launch = self.model_config.launch
        if self.model_config.dry_run:
            append_stage_log(
                self.context.launch_log_path,
                {"event": "dry_run_launch", "mode": launch.mode},
            )
            self.handle = LaunchHandle(mode="dry_run")
            return self.handle
        if launch.mode == "docker_compose":
            self.handle = self._start_compose(launch)
        elif launch.mode == "process":
            self.handle = self._start_process(launch)
        else:
            raise LaunchError(f"Unsupported launch mode: {launch.mode}")

        self._wait_for_health()
        return self.handle

    def _start_compose(self, launch: LaunchConfig) -> LaunchHandle:
        if not launch.compose_file:
            raise LaunchError("compose_file must be set for docker_compose mode")
        compose_path = (self.context.paths.root / launch.compose_file).resolve()
        if not compose_path.exists():
            raise LaunchError(f"docker-compose file not found: {compose_path}")
        env = self._resolve_env(launch.env)
        command = ["docker", "compose", "-f", str(compose_path), "up", "-d"]
        logger.info("Launching Triton via docker compose: %s", " ".join(command))
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        append_stage_log(
            self.context.launch_log_path,
            {
                "event": "docker_compose_up",
                "returncode": result.returncode,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            },
        )
        if result.returncode != 0:
            raise LaunchError(f"Docker compose failed: {result.stderr}")
        return LaunchHandle(mode="docker_compose")

    def _start_process(self, launch: LaunchConfig) -> LaunchHandle:
        command_env = self._resolve_env(launch.env)
        command_str = command_env.get("TRITON_COMMAND")
        if not command_str:
            raise LaunchError("TRITON_COMMAND must be provided in launch.env for process mode")
        command = command_str.split()
        process = subprocess.Popen(
            command,
            env=command_env,
            stdout=open(self.context.launch_log_path, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )
        append_stage_log(
            self.context.launch_log_path,
            {"event": "process_start", "command": command},
        )
        return LaunchHandle(mode="process", process=process)

    def _wait_for_health(self) -> None:
        http_url = self.model_config.endpoints.http
        metrics_url = self.model_config.endpoints.metrics
        grpc_endpoint = self.model_config.endpoints.grpc
        timeout = self.model_config.launch.health_timeout_s

        wait_for_http(http_url, timeout)
        append_stage_log(
            self.context.launch_log_path,
            {"event": "http_ready", "url": http_url},
        )
        metrics_timeout = max(30, min(timeout, 600))
        wait_for_http(metrics_url, metrics_timeout)
        append_stage_log(
            self.context.launch_log_path,
            {"event": "metrics_ready", "url": metrics_url},
        )

        host, port = self._parse_host_port(grpc_endpoint)
        wait_for_tcp(host, port, timeout)
        append_stage_log(
            self.context.launch_log_path,
            {"event": "grpc_ready", "endpoint": grpc_endpoint},
        )

    def stop(self) -> None:
        if not self.handle:
            return
        if self.handle.mode == "dry_run":
            append_stage_log(
                self.context.cleanup_log_path,
                {"event": "dry_run_teardown"},
            )
            self.handle = None
            return
        if self.handle.mode == "docker_compose":
            self._stop_compose()
        elif self.handle.mode == "process" and self.handle.process:
            self.handle.process.terminate()
            try:
                self.handle.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.handle.process.kill()
        append_stage_log(
            self.context.cleanup_log_path,
            {"event": "teardown_complete", "mode": self.handle.mode},
        )
        self.handle = None

    def _stop_compose(self) -> None:
        launch = self.model_config.launch
        compose_path = (self.context.paths.root / launch.compose_file).resolve()
        env = self._resolve_env(launch.env)
        command = ["docker", "compose", "-f", str(compose_path), "down"]
        subprocess.run(command, env=env, check=False)

    @staticmethod
    def _parse_host_port(endpoint: str) -> tuple[str, int]:
        if ":" in endpoint:
            host, port_str = endpoint.rsplit(":", 1)
            return host, int(port_str)
        raise LaunchError(f"Invalid gRPC endpoint format: {endpoint}")

    def _resolve_env(self, launch_env: Dict[str, str]) -> Dict[str, str]:
        resolved = os.environ.copy()
        for key, value in launch_env.items():
            resolved[key] = self._expand_env(value)
        return resolved

    @staticmethod
    def _expand_env(value: str) -> str:
        pattern = re.compile(r"\$\{([^}]+)\}")

        def replacer(match: re.Match[str]) -> str:
            name = match.group(1)
            return os.environ.get(name, "")

        return pattern.sub(replacer, value)
