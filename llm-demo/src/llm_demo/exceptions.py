"""Custom exception types for the warmup workflow."""


class WarmupError(RuntimeError):
    """Base class for warmup-related failures."""


class PrerequisiteError(WarmupError):
    """Raised when host prerequisites are not met."""


class DownloadError(WarmupError):
    """Raised when model download or cache validation fails."""


class EngineBuildError(WarmupError):
    """Raised when TensorRT-LLM engine compilation fails."""


class LaunchError(WarmupError):
    """Raised when Triton/TensorRT services fail to start."""


class InferenceError(WarmupError):
    """Raised when warmup inference checks fail."""
