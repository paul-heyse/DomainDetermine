"""Configuration models for the governed LLM engine build workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_DRIVER_VERSION = "555.85"
DEFAULT_GPU_NAME = "NVIDIA RTX 5090"
DEFAULT_BUILD_CONTAINER_TAG = "24.05-trtllm-python-py3"
DEFAULT_TRITON_CONTAINER_TAG = "24.05-trtllm-python-py3"
DEFAULT_CONTAINER_IMAGE = "nvcr.io/nvidia/tensorrt-llm/release"
DEFAULT_TRITON_IMAGE = "nvcr.io/nvidia/tritonserver"
DEFAULT_CUDA_VERSION = "12.4"
DEFAULT_TENSORRT_VERSION = "9.0"


@dataclass(frozen=True, slots=True)
class NGCContainerSpec:
    """Describes an NVIDIA NGC container and its versioning requirements."""

    image: str
    tag: str
    cuda_version: str
    tensorrt_version: str
    description: str

    @property
    def reference(self) -> str:
        """Return the fully qualified container reference."""

        return f"{self.image}:{self.tag}"


@dataclass(frozen=True, slots=True)
class BuildEnvironment:
    """Pinned environment information for TensorRT-LLM engine builds."""

    driver_version: str
    gpu_name: str
    containers: tuple[NGCContainerSpec, ...]
    volumes: tuple[Path, ...]
    extra_env: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation of the build environment."""

        return {
            "driver_version": self.driver_version,
            "gpu_name": self.gpu_name,
            "containers": [spec.__dict__ for spec in self.containers],
            "volumes": [str(volume) for volume in self.volumes],
            "extra_env": {key: value for key, value in self.extra_env},
        }


@dataclass(frozen=True, slots=True)
class ContainerLaunchPlan:
    """Instructions for launching the build container reproducibly."""

    spec: NGCContainerSpec
    command: tuple[str, ...]
    volumes: tuple[Path, ...]
    env: tuple[tuple[str, str], ...]

    def docker_args(self) -> list[str]:
        """Generate the docker run arguments for this plan."""

        args: list[str] = ["docker", "run", "--rm", "--gpus", "all"]
        for key, value in self.env:
            args.extend(["-e", f"{key}={value}"])
        for host_path in self.volumes:
            args.extend(["-v", f"{host_path}:{host_path}:rw"])
        args.append(self.spec.reference)
        args.extend(self.command)
        return args


def default_build_environment(artifact_root: Path, cache_root: Path) -> BuildEnvironment:
    """Create the default build environment pinned to approved container tags."""

    build_spec = NGCContainerSpec(
        image=DEFAULT_CONTAINER_IMAGE,
        tag=DEFAULT_BUILD_CONTAINER_TAG,
        cuda_version=DEFAULT_CUDA_VERSION,
        tensorrt_version=DEFAULT_TENSORRT_VERSION,
        description="TensorRT-LLM build image",
    )
    triton_spec = NGCContainerSpec(
        image=DEFAULT_TRITON_IMAGE,
        tag=DEFAULT_TRITON_CONTAINER_TAG,
        cuda_version=DEFAULT_CUDA_VERSION,
        tensorrt_version=DEFAULT_TENSORRT_VERSION,
        description="Triton TensorRT-LLM serving image",
    )
    volumes = (
        artifact_root.expanduser().resolve(),
        cache_root.expanduser().resolve(),
    )
    extra_env = (
        ("CUDA_VISIBLE_DEVICES", "0"),
        ("HF_HOME", str(cache_root / "hf")),
    )
    return BuildEnvironment(
        driver_version=DEFAULT_DRIVER_VERSION,
        gpu_name=DEFAULT_GPU_NAME,
        containers=(build_spec, triton_spec),
        volumes=volumes,
        extra_env=extra_env,
    )


def default_launch_plan(workspace: Path) -> ContainerLaunchPlan:
    """Provide a reference docker invocation for building the engine."""

    build_env = default_build_environment(workspace / "artifacts", workspace / "cache")
    command = (
        "bash",
        "-lc",
        "scripts/llm/build_engine.sh",
    )
    return ContainerLaunchPlan(
        spec=build_env.containers[0],
        command=command,
        volumes=build_env.volumes,
        env=build_env.extra_env,
    )
