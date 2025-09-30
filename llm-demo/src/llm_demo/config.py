"""Configuration models for the llm-demo warmup harness."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class VersionSpec(BaseModel):
    min_version: str = Field(..., description="Minimum acceptable semantic version string")


class TritonSpec(VersionSpec):
    image: Optional[str] = Field(
        default=None, description="Container image reference for Triton server"
    )


class HardwareSpec(BaseModel):
    gpu_architectures: List[str] = Field(default_factory=list)
    min_vram_gb: int = Field(default=0)
    min_driver_version: str = Field(default="")


class CommandSpec(BaseModel):
    name: str


class CommandConfig(BaseModel):
    required: List[CommandSpec] = Field(default_factory=list)
    optional: List[CommandSpec] = Field(default_factory=list)


class EnvironmentVarSpec(BaseModel):
    name: str
    description: Optional[str] = None
    optional: bool = False


class EnvironmentConfig(BaseModel):
    required: List[EnvironmentVarSpec] = Field(default_factory=list)


class FileSpec(BaseModel):
    path: Path
    description: Optional[str] = None


class FileConfig(BaseModel):
    optional: List[FileSpec] = Field(default_factory=list)


class SoftwareSpec(BaseModel):
    cuda: VersionSpec
    tensorrt: VersionSpec
    triton: TritonSpec


class PrerequisitesConfig(BaseModel):
    hardware: HardwareSpec
    software: SoftwareSpec
    commands: CommandConfig = Field(default_factory=CommandConfig)
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    files: FileConfig = Field(default_factory=FileConfig)


class CacheConfig(BaseModel):
    ttl_hours: int = Field(default=48, ge=1)
    path: Path = Field(default=Path("../cache"))


class TensorRTLLMConfig(BaseModel):
    max_batch_size: int = Field(default=1, ge=1)
    max_input_len: int = Field(default=2048, ge=1)
    max_output_len: int = Field(default=512, ge=1)
    builder_optimization_level: int = Field(default=4, ge=0, le=5)
    workspace_size_gb: int = Field(default=20, ge=1)
    parallel_build: bool = True
    extra_flags: List[str] = Field(default_factory=list)


class GoldenSampleConfig(BaseModel):
    prompt: str
    expected_substring: str
    tolerance: float = Field(default=0.0, ge=0.0)


class LaunchConfig(BaseModel):
    mode: str = Field(default="docker_compose")
    compose_file: Optional[Path] = None
    env: Dict[str, str] = Field(default_factory=dict)
    health_timeout_s: int = Field(default=300, ge=1)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        allowed = {"docker_compose", "process"}
        if value not in allowed:
            raise ValueError(f"launch.mode must be one of {sorted(allowed)}")
        return value


class EndpointConfig(BaseModel):
    http: str
    grpc: str
    metrics: str


class ModelConfig(BaseModel):
    provider: str = Field(default="huggingface")
    identifier: str
    revision: str = Field(default="main")
    tokenizer: str
    precision: str = Field(default="fp16")
    tensor_rt_llm: TensorRTLLMConfig
    cache: CacheConfig = Field(default_factory=CacheConfig)
    offline_mode: bool = False
    dry_run: bool = False
    requires_auth: bool = False
    warmup_prompts: List[str] = Field(default_factory=list)
    golden_sample: GoldenSampleConfig
    endpoints: EndpointConfig
    launch: LaunchConfig
    redaction_patterns: List[str] = Field(
        default_factory=lambda: ["key", "token", "secret"],
        description="Patterns to redact from transcripts",
    )

    @property
    def cache_key(self) -> str:
        return f"{self.identifier}@{self.revision}:{self.precision}"


class WarmupConfig(BaseModel):
    model: ModelConfig


class ChatConfig(BaseModel):
    endpoints: EndpointConfig
    transcript_dir: Path
    session_metadata: Dict[str, Any]
    redaction_patterns: List[str] = Field(default_factory=lambda: ["apikey", "token", "secret"])


class Settings(BaseModel):
    root: Path
    prereq_config_path: Path
    model_config_path: Path


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_prerequisites_config(path: Path) -> PrerequisitesConfig:
    data = load_yaml(path)
    return PrerequisitesConfig.model_validate(data)


def load_model_config(path: Path) -> WarmupConfig:
    data = load_yaml(path)
    return WarmupConfig.model_validate(data)
